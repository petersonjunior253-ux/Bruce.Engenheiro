from __future__ import annotations
import asyncio,hashlib,hmac,json,os,re,secrets,sqlite3,time,unicodedata
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Literal,Any
import httpx
from fastapi import Depends,FastAPI,Header,HTTPException,Query
from fastapi.responses import Response,JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from pydantic_settings import BaseSettings,SettingsConfigDict
from vercel import blob
import edge_tts

class Settings(BaseSettings):
 model_config=SettingsConfigDict(env_prefix="BRUCE_",env_file=".env",extra="ignore")
 api_key:str="development-only-change-me"
 model_base_url:str=os.getenv("BRUCE_MODEL_BASE_URL", "" if os.getenv("VERCEL") else "http://127.0.0.1:11434/v1")
 model_api_key:str=""
 anthropic_api_key:str=""
 gemini_api_key:str=""
 model_provider:str="gemini"
 model_name:str="gemini-3.8-flash"
 system_prompt:str="Você é BRUCE, o assistente pessoal exclusivo do usuário. Fale em português brasileiro com voz natural, sofisticada, calorosa e objetiva. Sua personalidade é adaptativa: seja compreensivo quando o usuário precisar de apoio e firme, respeitoso e direto quando houver procrastinação ou quebra de consistência. Atue de forma proativa: ajude a organizar rotina, treino, estudos, metas, projetos e desenvolvimento pessoal; antecipe conflitos; proponha próximos passos úteis sem ser insistente. Conduza a conversa e faça somente a pergunta essencial quando faltar informação. Use o contexto e as memórias disponíveis sem inventar lembranças nem afirmar que conhece dados que não foram fornecidos. Use as ferramentas de tarefas e memória para registrar compromissos, consultar pendências, concluir tarefas e guardar informações que o usuário pedir explicitamente para lembrar. Converta datas relativas usando America/Sao_Paulo e confirme quando faltar informação essencial. Execute apenas ações autorizadas e reversíveis; ações sensíveis, financeiras, externas ou irreversíveis exigem aprovação explícita. Nunca diga que uma ação foi concluída sem confirmação do dispositivo. Diferencie reconhecimento de voz offline do processamento do modelo: não afirme que a inteligência está local ou funcionando sem internet quando o provedor estiver na nuvem. Respeite a privacidade e nunca misture dados de pessoas diferentes."
 max_context_messages:int=80
 max_output_tokens:int=4096
 database_path:str=os.getenv("BRUCE_DATABASE_PATH", "/tmp/bruce.sqlite3" if os.getenv("VERCEL") else "./data/bruce.sqlite3")
 device_online_seconds:int=90
settings=Settings()
db=Path(settings.database_path);db.parent.mkdir(parents=True,exist_ok=True)
blob_path="bruce/private-state.sqlite3"
db_lock=asyncio.Lock()
blob_enabled=bool(os.getenv("BLOB_READ_WRITE_TOKEN") or os.getenv("BLOB_STORE_ID"))
app=FastAPI(title="BRUCE Personal Intelligence API",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("BRUCE_ALLOWED_ORIGINS","https://bruce-preview-six.vercel.app,https://bruce-preview-petersonjunior253-8756s-projects.vercel.app,http://localhost:5173,http://127.0.0.1:5173").split(","),allow_credentials=False,allow_methods=["GET","POST","PATCH","DELETE"],allow_headers=["Authorization","Content-Type"])

def connect():
 c=sqlite3.connect(db);c.row_factory=sqlite3.Row;return c
def init_db():
 with connect() as c:
  c.execute("CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'geral',due_at TEXT,notes TEXT,status TEXT NOT NULL DEFAULT 'pending',created_at INTEGER NOT NULL,completed_at INTEGER)")
  c.execute("CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,name TEXT NOT NULL,platform TEXT NOT NULL,last_seen INTEGER NOT NULL,metadata TEXT NOT NULL DEFAULT '{}')")
  c.execute("CREATE TABLE IF NOT EXISTS device_commands(id TEXT PRIMARY KEY,device_id TEXT NOT NULL,tool TEXT NOT NULL,args TEXT NOT NULL,status TEXT NOT NULL,created_at INTEGER NOT NULL,result TEXT)")
  c.execute("CREATE INDEX IF NOT EXISTS idx_messages ON messages(conversation_id,id)")
  c.execute("CREATE INDEX IF NOT EXISTS idx_commands ON device_commands(device_id,status,created_at)")
  c.commit()
@app.on_event("startup")
def startup():init_db()

@app.middleware("http")
async def durable_private_state(request, call_next):
 if not blob_enabled or request.url.path in {"/health","/v1/voice","/docs","/openapi.json","/redoc"} or request.method=="OPTIONS":
  return await call_next(request)
 async with db_lock:
  try:
   stored=await blob.get_blob(blob_path,access="private")
   db.write_bytes(stored.body)
  except blob.BlobNotFoundError:
   init_db()
  except Exception:
   return JSONResponse({"detail":"O armazenamento privado do BRUCE está indisponível; os dados não foram alterados."},status_code=503)
  response=await call_next(request)
  if response.status_code < 500:
   try:
    await blob.put_blob(blob_path,db.read_bytes(),access="private",allow_overwrite=True,content_type="application/vnd.sqlite3",cache_control_max_age=60)
   except Exception:
    return JSONResponse({"detail":"Não consegui salvar a memória persistente do BRUCE. A operação não foi confirmada."},status_code=503)
  return response

def auth(authorization:str|None=Header(default=None)):
 if not settings.api_key or settings.api_key=="development-only-change-me":raise HTTPException(503,"Configure BRUCE_API_KEY no servidor.")
 if not authorization or not hmac.compare_digest(authorization,"Bearer "+settings.api_key):raise HTTPException(401,"Token privado inválido.")
class Message(BaseModel):
 role:Literal["user","assistant"];content:str=Field(min_length=1,max_length=100000)
class ChatRequest(BaseModel):
 conversation_id:str|None=None;messages:list[Message]=Field(min_length=1,max_length=100)
class MemoryRequest(BaseModel):
 category:str=Field(default="geral",max_length=60);content:str=Field(min_length=1,max_length=12000)
class TaskRequest(BaseModel):
 title:str=Field(min_length=1,max_length=240);category:str=Field(default="geral",max_length=60);due_at:str|None=None;notes:str=Field(default="",max_length=4000)
class TaskUpdate(BaseModel):
 status:Literal["pending","completed"]
class DeviceRegistration(BaseModel):
 device_id:str=Field(min_length=6,max_length=100);name:str="BRUCE Android";platform:str="android";metadata:dict[str,Any]={}
class CommandResult(BaseModel):
 status:Literal["completed","failed","denied"];result:dict[str,Any]={}
class VoiceRequest(BaseModel):
 text:str=Field(min_length=1,max_length=12000)
 voice:str="pt-BR-AntonioNeural"
TOOLS=[
 {"type":"function","function":{"name":"open_app","description":"Abrir um aplicativo instalado no Android do usuário pelo nome ou pacote.","parameters":{"type":"object","properties":{"package_name":{"type":"string"},"app_name":{"type":"string"}},"required":["app_name"]}}},
 {"type":"function","function":{"name":"create_calendar_event","description":"Criar um evento no calendário Android. O aplicativo mostrará a tela de confirmação antes de salvar.","parameters":{"type":"object","properties":{"title":{"type":"string"},"start_iso":{"type":"string"},"end_iso":{"type":"string"},"description":{"type":"string"}},"required":["title","start_iso"]}}},
 {"type":"function","function":{"name":"open_file_picker","description":"Abrir seletor nativo de arquivos para o usuário escolher um documento.","parameters":{"type":"object","properties":{"mime_type":{"type":"string"}}}}},
 {"type":"function","function":{"name":"create_notification","description":"Mostrar uma notificação local no Android.","parameters":{"type":"object","properties":{"title":{"type":"string"},"message":{"type":"string"}},"required":["title","message"]}}},
 {"type":"function","function":{"name":"set_alarm","description":"Abrir o relógio Android para configurar um alarme.","parameters":{"type":"object","properties":{"hour":{"type":"integer"},"minute":{"type":"integer"},"message":{"type":"string"}},"required":["hour","minute"]}}},
 {"type":"function","function":{"name":"open_device_settings","description":"Abrir uma página de configurações Android solicitada pelo usuário.","parameters":{"type":"object","properties":{"section":{"type":"string","enum":["settings","wifi","bluetooth","sound","display","apps","accessibility","notifications","notification_access","files"]}},"required":["section"]}}},
 {"type":"function","function":{"name":"get_device_info","description":"Consultar informações básicas do dispositivo conectado.","parameters":{"type":"object","properties":{} } }},
 {"type":"function","function":{"name":"list_installed_apps","description":"Listar aplicativos instalados e visíveis no Android.","parameters":{"type":"object","properties":{} } }},
 {"type":"function","function":{"name":"list_notifications","description":"Ler notificações ativas do Android. Requer que o usuário habilite o acesso a notificações do BRUCE nas configurações do sistema.","parameters":{"type":"object","properties":{} } }},
 {"type":"function","function":{"name":"get_screen_text","description":"Ler o texto visível na tela Android atual. Requer serviço de acessibilidade BRUCE habilitado.","parameters":{"type":"object","properties":{} }}},
 {"type":"function","function":{"name":"tap_text","description":"Tocar em um botão, link ou controle da tela procurando pelo texto ou descrição informado. Use somente quando o usuário pedir a ação.","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}},
 {"type":"function","function":{"name":"type_text","description":"Digitar texto no campo atualmente focado. Use somente quando o usuário pedir explicitamente para preencher ou enviar texto.","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}},
 {"type":"function","function":{"name":"scroll_screen","description":"Rolar a tela Android para cima ou para baixo.","parameters":{"type":"object","properties":{"direction":{"type":"string","enum":["up","down"]}},"required":["direction"]}}},
 {"type":"function","function":{"name":"press_back","description":"Voltar uma tela no Android.","parameters":{"type":"object","properties":{} }}},
 {"type":"function","function":{"name":"press_home","description":"Ir para a tela inicial do Android.","parameters":{"type":"object","properties":{} }}},
 {"type":"function","function":{"name":"list_files","description":"Listar arquivos e pastas no armazenamento compartilhado do Android. Requer que o usuário conceda acesso a todos os arquivos nas configurações.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Pasta relativa, por exemplo Download ou Documents"}}}}},
 {"type":"function","function":{"name":"read_file","description":"Ler um arquivo de texto no armazenamento compartilhado do Android. Requer acesso a todos os arquivos e limita a leitura a 1 MB.","parameters":{"type":"object","properties":{"path":{"type":"string","description":"Caminho relativo, por exemplo Download/notas.txt"}},"required":["path"]}}},
 {"type":"function","function":{"name":"create_text_file","description":"Criar um arquivo de texto novo no armazenamento compartilhado. Nunca sobrescreve arquivos existentes. Requer acesso a todos os arquivos.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
 {"type":"function","function":{"name":"create_task","description":"Registrar uma atividade ou compromisso pessoal único na agenda BRUCE. Entenda pedidos como hoje às 20h, amanhã de manhã, sexta às 14:30 ou daqui a duas horas. due_at deve ser data/hora ISO local America/Sao_Paulo YYYY-MM-DDTHH:MM; se não houver horário, use YYYY-MM-DD. Pergunte se faltar informação essencial. Nunca torne recorrente sem pedido explícito.","parameters":{"type":"object","properties":{"title":{"type":"string"},"category":{"type":"string","enum":["rotina","estudos","treino","trabalho","pessoal","saude","geral"]},"due_at":{"type":"string","description":"Data e hora local America/Sao_Paulo em YYYY-MM-DDTHH:MM, ou YYYY-MM-DD"},"notes":{"type":"string"}},"required":["title","category"]}}},
 {"type":"function","function":{"name":"list_tasks","description":"Consultar compromissos e tarefas, incluindo agenda de hoje, mais tarde, amanhã e semana. Use status pending para pendências, completed para concluídas, all para todas.","parameters":{"type":"object","properties":{"status":{"type":"string","enum":["pending","completed","all"]},"category":{"type":"string"},"date_from":{"type":"string","description":"Data inicial YYYY-MM-DD"},"date_to":{"type":"string","description":"Data final YYYY-MM-DD"}}}}},
 {"type":"function","function":{"name":"complete_task","description":"Marcar uma atividade como concluída pelo identificador ou título.","parameters":{"type":"object","properties":{"task_id":{"type":"string"},"title":{"type":"string"}}}}},
 {"type":"function","function":{"name":"save_memory","description":"Salvar uma preferência ou informação que o usuário pediu explicitamente para lembrar.","parameters":{"type":"object","properties":{"category":{"type":"string"},"content":{"type":"string"}},"required":["content"]}}},
 {"type":"function","function":{"name":"list_memories","description":"Consultar memórias pessoais salvas.","parameters":{"type":"object","properties":{"category":{"type":"string"}}}}},
 {"type":"function","function":{"name":"delete_memory","description":"Apagar uma memória pessoal específica que o usuário pediu para esquecer.","parameters":{"type":"object","properties":{"memory_id":{"type":"integer"}},"required":["memory_id"]}}}
]
@app.post("/v1/voice",dependencies=[Depends(auth)])
async def neural_voice(p:VoiceRequest):
 voice=p.voice if p.voice in {"pt-BR-AntonioNeural","pt-BR-FranciscaNeural"} else "pt-BR-AntonioNeural"
 try:
  audio=bytearray()
  communicator=edge_tts.Communicate(p.text,voice=voice,rate="+0%",pitch="+0Hz")
  async for chunk in communicator.stream():
   if chunk.get("type")=="audio":audio.extend(chunk.get("data",b""))
  if not audio:raise RuntimeError("O serviço de voz não retornou áudio.")
  return Response(content=bytes(audio),media_type="audio/mpeg",headers={"Cache-Control":"no-store"})
 except Exception as e:
  raise HTTPException(502,"Não foi possível gerar a voz neural agora.") from e

@app.get("/health")
async def health():
 storage="disabled"
 if blob_enabled:
  try:
   await blob.get_blob(blob_path,access="private")
   storage="ready"
  except blob.BlobNotFoundError:
   try:
    await blob.put_blob(blob_path,db.read_bytes(),access="private",allow_overwrite=False,content_type="application/vnd.sqlite3")
    storage="initialized"
   except Exception:
    try:
     await blob.get_blob(blob_path,access="private")
     storage="ready"
    except Exception:
     storage="error"
  except Exception:
   storage="error"
 return {"status":"ok" if storage!="error" else "degraded","service":"BRUCE Personal Intelligence API","model_configured":bool((settings.gemini_api_key if settings.model_provider.lower()=="gemini" else settings.anthropic_api_key if settings.model_provider.lower()=="anthropic" else settings.model_base_url) and settings.model_name),"persistent_storage":storage,"model_name":settings.model_name,"model_provider":"Gemini" if settings.model_provider.lower()=="gemini" else "Anthropic" if settings.model_provider.lower()=="anthropic" else "OpenAI-compatible","database":"sqlite","device_tools":True,"time":int(time.time())}
def offline_intent(text:str):
 normalized=unicodedata.normalize("NFD",text).encode("ascii","ignore").decode("ascii").lower()
 normalized=normalized.replace("wi-fi","wifi")
 normalized=re.sub(r"\s+"," ",normalized).strip()
 if re.search(r"\b(que horas|horas sao|horario agora)\b",normalized):
  return None,{}, "Agora são "+datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M")+" no horário de Brasília."
 if re.search(r"\b(que dia e hoje|data de hoje|qual a data)\b",normalized):
  return None,{}, "Hoje é "+datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y")+"."
 if re.search(r"\b(abrir|abra|abre|ir para|mostrar)\b.*\b(configuracoes|ajustes)\b",normalized):
  section="accessibility" if "acessibilidade" in normalized else "notification_access" if "notificacoes" in normalized and ("acesso" in normalized or "permissao" in normalized) else "files" if "arquivo" in normalized else "wifi" if "wifi" in normalized else "bluetooth" if "bluetooth" in normalized else "sound" if "som" in normalized or "audio" in normalized else "display" if "tela" in normalized or "brilho" in normalized else "apps" if "aplicativo" in normalized else "settings"
  return "open_device_settings",{"section":section},"Vou abrir as configurações solicitadas."
 if re.search(r"\b(ler|mostrar|ver|consultar)\b.*\b(notificacoes)\b",normalized):
  return "list_notifications",{},"Vou consultar as notificações ativas."
 if re.search(r"\b(listar|mostrar|ver)\b.*\b(aplicativos|apps)\b",normalized):
  return "list_installed_apps",{},"Vou consultar os aplicativos instalados."
 if re.search(r"\b(ler|mostrar|o que aparece|o que esta escrito)\b.*\b(tela|screen)\b",normalized):
  return "get_screen_text",{},"Vou ler o conteúdo visível da tela."
 if re.search(r"\b(voltar|volte|botao voltar)\b",normalized):
  return "press_back",{},"Voltando uma tela."
 if re.search(r"\b(tela inicial|ir para home|voltar para o inicio|ir para inicio)\b",normalized):
  return "press_home",{},"Indo para a tela inicial."
 if re.search(r"\b(rolar|descer)\b.*\b(baixo|para baixo)\b",normalized):
  return "scroll_screen",{"direction":"down"},"Rolando a tela para baixo."
 if re.search(r"\b(rolar|subir)\b.*\b(cima|para cima)\b",normalized):
  return "scroll_screen",{"direction":"up"},"Rolando a tela para cima."
 if re.search(r"\b(abrir|mostrar|selecionar)\b.*\b(arquivos|documentos|meus arquivos)\b",normalized):
  return "open_file_picker",{"mime_type":"*/*"},"Abrindo o seletor de arquivos."
 if re.search(r"\b(listar|mostrar)\b.*\b(arquivos|pastas)\b",normalized):
  path_match=re.search(r"\b(?:pasta|em)\s+([a-z0-9_./ -]+)$",text.strip(),re.I)
  return "list_files",{"path":path_match.group(1).strip() if path_match else ""},"Vou listar os arquivos disponíveis."
 file_match=re.search(r"\b(?:ler|abrir)\s+(?:o\s+)?arquivo\s+(.+)$",text.strip(),re.I)
 if file_match:
  return "read_file",{"path":file_match.group(1).strip().strip('"')},"Vou ler esse arquivo."
 tap_match=re.search(r"\b(?:toque|tocar|clique|clicar)\s+(?:em\s+)?(.+)$",text.strip(),re.I)
 if tap_match:
  return "tap_text",{"text":tap_match.group(1).strip()},"Vou localizar esse controle na tela."
 type_match=re.search(r"\b(?:digite|escreva|preencha)\s+(.+)$",text.strip(),re.I)
 if type_match:
  return "type_text",{"text":type_match.group(1).strip()},"Vou preencher o campo que estiver selecionado."
 alarm_match=re.search(r"\b(?:alarme|despertador)\b.*?\b(\d{1,2})(?:\s*(?:h|:)\s*(\d{2}))?\b",normalized)
 if alarm_match:
  hour=int(alarm_match.group(1));minute=int(alarm_match.group(2) or 0)
  if 0<=hour<=23 and 0<=minute<=59:
   return "set_alarm",{"hour":hour,"minute":minute,"message":"BRUCE"},"Vou abrir o relógio para configurar o alarme."
 app_match=re.search(r"\b(?:abra|abrir|abre|inicie|iniciar|execute|executar)\s+(?:o\s+)?(?:app\s+|aplicativo\s+)?(.+)$",text.strip(),re.I)
 if app_match:
  name=app_match.group(1).strip().strip(" .!?")
  if name and len(name)<=80:
   return "open_app",{"app_name":name},"Vou abrir "+name+"."
 return None,{},None

@app.post("/v1/chat",dependencies=[Depends(auth)])
async def chat(p:ChatRequest):
 provider=settings.model_provider.lower().strip()
 configured=bool(settings.gemini_api_key) if provider=="gemini" else bool(settings.anthropic_api_key) if provider=="anthropic" else bool(settings.model_base_url)
 if not configured:
  tool,args,offline_answer=offline_intent(p.messages[-1].content)
  if offline_answer is None: raise HTTPException(503,"API BRUCE ativa. Configure a chave do provedor selecionado (BRUCE_GEMINI_API_KEY para Gemini) no servidor para habilitar conversa livre. Comandos locais compatíveis continuam disponíveis.")
  now=int(time.time());cid=p.conversation_id or secrets.token_hex(12)
  with connect() as c:
   c.execute("INSERT OR IGNORE INTO conversations VALUES(?,?,?,?)",(cid,"Nova conversa",now,now))
   for message in p.messages:c.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(cid,message.role,message.content,now))
   title=p.messages[0].content.strip()[:72] or "Nova conversa"
   c.execute("UPDATE conversations SET updated_at=?,title=CASE WHEN title='Nova conversa' THEN ? ELSE title END WHERE id=?",(now,title,cid))
   device=c.execute("SELECT id FROM devices WHERE last_seen>=? ORDER BY last_seen DESC LIMIT 1",(now-settings.device_online_seconds,)).fetchone()
   queued=[]
   if tool and device:
    command_id=secrets.token_hex(12)
    c.execute("INSERT INTO device_commands(id,device_id,tool,args,status,created_at) VALUES(?,?,?,?,?,?)",(command_id,device["id"],tool,json.dumps(args,ensure_ascii=False),"queued",now))
    queued=[{"id":command_id,"tool":tool,"args":args}]
    offline_answer+=" Comando enviado ao seu Samsung; aguardando confirmação."
   elif tool and not device:
    offline_answer="Não encontrei o Samsung conectado. Abra o BRUCE no celular, salve a conexão e ative o serviço antes de enviar comandos."
   c.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(cid,"assistant",offline_answer,now));c.commit()
  return {"conversation_id":cid,"message":offline_answer,"model":"BRUCE LOCAL COMMAND ROUTER","queued_actions":queued}
 now=int(time.time());cid=p.conversation_id or secrets.token_hex(12)
 with connect() as c:
  c.execute("INSERT OR IGNORE INTO conversations VALUES(?,?,?,?)",(cid,"Nova conversa",now,now))
  old=c.execute("SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",(cid,settings.max_context_messages)).fetchall()
  for m in p.messages:c.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(cid,m.role,m.content,now))
  title=p.messages[0].content.strip()[:72] or "Nova conversa"
  c.execute("UPDATE conversations SET updated_at=?,title=CASE WHEN title='Nova conversa' THEN ? ELSE title END WHERE id=?",(now,title,cid));c.commit()
 with connect() as c:mem=c.execute("SELECT category,content FROM memories ORDER BY id DESC LIMIT 30").fetchall()
 with connect() as c:devices=c.execute("SELECT id,name,last_seen FROM devices WHERE last_seen>=?",(now-settings.device_online_seconds,)).fetchall()
 context=settings.system_prompt+"\\n\\nData e hora atuais do usuário: "+datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%A, %d/%m/%Y %H:%M")+" (America/Sao_Paulo). Interprete hoje, mais tarde, amanhã e daqui a X horas usando este relógio. Antes de salvar compromisso, converta para YYYY-MM-DDTHH:MM no fuso local. Se disser hoje às 20h, use a data de hoje e 20:00. Compromissos são únicos por padrão; nunca crie recorrência sem pedido explícito."
 if mem:context+="\n\nMemórias do usuário:\n"+"\n".join(f"- [{x['category']}] {x['content']}" for x in mem)
 if devices:context+="\n\nUm dispositivo Android está conectado e pode receber comandos por ferramentas. Use-as somente quando o usuário pedir uma ação concreta. O aplicativo Android exige confirmação em ações que alteram dados."
 with connect() as c:recent=c.execute("SELECT tool,status,result FROM device_commands ORDER BY created_at DESC LIMIT 5").fetchall()
 if recent:
  context+="\n\nResultados recentes de ações no dispositivo (use apenas como histórico, não repita sem pedido):\n"+"\n".join(f"- {x['tool']}: {x['status']} — {x['result'] or 'sem retorno'}" for x in recent)
 else:context+="\n\nNenhum dispositivo Android está conectado agora. Não diga que executou ações no aparelho."
 messages=[{"role":"system","content":context}]+[{"role":x["role"],"content":x["content"]} for x in reversed(old)]+[{"role":m.role,"content":m.content} for m in p.messages]
 calls=[]
 try:
  async with httpx.AsyncClient(timeout=httpx.Timeout(150,connect=15)) as client:
   if provider=="gemini" and settings.gemini_api_key:
    gemini_tools=[{"name":x["function"]["name"],"description":x["function"]["description"],"parameters":{k:(v.upper() if k=="type" and isinstance(v,str) else {kk:(vv.upper() if kk=="type" and isinstance(vv,str) else vv) for kk,vv in v.items()} if k=="properties" and isinstance(v,dict) else v) for k,v in x["function"]["parameters"].items()}} for x in TOOLS]
    gemini_contents=[]
    for item in messages:
     if item["role"]=="system":continue
     gemini_contents.append({"role":"model" if item["role"]=="assistant" else "user","parts":[{"text":item["content"]}]})
    body={"systemInstruction":{"parts":[{"text":context}]},"contents":gemini_contents,"generationConfig":{"maxOutputTokens":settings.max_output_tokens,"temperature":0.7},"tools":[{"functionDeclarations":gemini_tools}]}
    headers={"Content-Type":"application/json","x-goog-api-key":settings.gemini_api_key}
    r=await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{settings.model_name}:generateContent",headers=headers,json=body);r.raise_for_status();data=r.json()
    parts=data.get("candidates",[{}])[0].get("content",{}).get("parts",[])
    answer="\\n".join(x.get("text","") for x in parts if x.get("text")).strip()
    calls=[{"function":{"name":x.get("functionCall",{}).get("name"),"arguments":json.dumps(x.get("functionCall",{}).get("args",{}),ensure_ascii=False)}} for x in parts if x.get("functionCall")]
   elif provider=="anthropic" and settings.anthropic_api_key:
    anthropic_tools=[{"name":x["function"]["name"],"description":x["function"]["description"],"input_schema":x["function"]["parameters"]} for x in TOOLS]
    anthropic_messages=[{"role":x["role"],"content":x["content"]} for x in messages if x["role"]!="system"]
    body={"model":settings.model_name,"system":context,"messages":anthropic_messages,"max_tokens":settings.max_output_tokens,"tools":anthropic_tools}
    headers={"Content-Type":"application/json","x-api-key":settings.anthropic_api_key,"anthropic-version":"2026-10-21"}
    r=await client.post("https://api.anthropic.com/v1/messages",headers=headers,json=body);r.raise_for_status();data=r.json()
    blocks=data.get("content",[])
    answer="\\n".join(x.get("text","") for x in blocks if x.get("type")=="text").strip()
    calls=[{"function":{"name":x.get("name"),"arguments":json.dumps(x.get("input",{}),ensure_ascii=False)}} for x in blocks if x.get("type")=="tool_use"]
   else:
    body={"model":settings.model_name,"messages":messages,"max_tokens":settings.max_output_tokens,"tools":TOOLS,"tool_choice":"auto"}
    headers={"Content-Type":"application/json"}
    if settings.model_api_key:headers["Authorization"]="Bearer "+settings.model_api_key
    r=await client.post(settings.model_base_url.rstrip("/")+"/chat/completions",headers=headers,json=body);r.raise_for_status();data=r.json()
    choice=data["choices"][0]["message"];answer=choice.get("content") or "";calls=choice.get("tool_calls") or []
 except httpx.HTTPStatusError as e:
  detail=("A chave Gemini foi recusada. Confira BRUCE_GEMINI_API_KEY no servidor." if provider=="gemini" and e.response.status_code in (401,403) else "A chave Anthropic foi recusada. Confira BRUCE_ANTHROPIC_API_KEY e os créditos da conta." if provider=="anthropic" and e.response.status_code in (401,403) else f"Provedor de IA retornou HTTP {e.response.status_code}.")
  raise HTTPException(502,detail)
 except (httpx.HTTPError,KeyError,ValueError) as e:raise HTTPException(502,"Não foi possível consultar o modelo configurado.")
 queued=[]
 local_results=[]
 local_tools={"create_task","list_tasks","complete_task","save_memory","list_memories","delete_memory"}
 android_tools={x["function"]["name"] for x in TOOLS}-local_tools
 for call in calls:
  fn=call.get("function",{});name=fn.get("name")
  try:args=json.loads(fn.get("arguments") or "{}")
  except ValueError:args={}
  if name in local_tools:
   try:
    with connect() as c:
     if name=="create_task":
      task_id=secrets.token_hex(8);title=str(args.get("title","")).strip()
      if not title:raise ValueError("Informe o título da tarefa.")
      due_at=str(args.get("due_at") or "").strip() or None
      c.execute("INSERT INTO tasks(id,title,category,due_at,notes,status,created_at) VALUES(?,?,?,?,?,?,?)",(task_id,title,str(args.get("category") or "geral"),due_at,str(args.get("notes") or ""),"pending",now));c.commit()
      local_results.append({"tool":name,"created":True,"task_id":task_id,"title":title,"due_at":due_at})
     elif name=="list_tasks":
      status=str(args.get("status") or "pending");category=str(args.get("category") or "").strip()
      query="SELECT id,title,category,due_at,notes,status,created_at FROM tasks";clauses=[];params=[]
      if status in {"pending","completed"}:clauses.append("status=?");params.append(status)
      if category:clauses.append("category=?");params.append(category)
      date_from=str(args.get("date_from") or "").strip();date_to=str(args.get("date_to") or "").strip()
      if date_from:clauses.append("substr(due_at,1,10)>=?");params.append(date_from)
      if date_to:clauses.append("substr(due_at,1,10)<=?");params.append(date_to)
      if clauses:query+=" WHERE "+" AND ".join(clauses)
      query+=" ORDER BY CASE WHEN due_at IS NULL OR due_at='' THEN 1 ELSE 0 END,due_at,created_at DESC LIMIT 50"
      local_results.append({"tool":name,"tasks":[dict(row) for row in c.execute(query,params).fetchall()]})
     elif name=="complete_task":
      task_id=str(args.get("task_id") or "").strip();title=str(args.get("title") or "").strip()
      if task_id:cur=c.execute("UPDATE tasks SET status='completed',completed_at=? WHERE id=?",(now,task_id))
      elif title:cur=c.execute("UPDATE tasks SET status='completed',completed_at=? WHERE id=(SELECT id FROM tasks WHERE title LIKE ? AND status='pending' ORDER BY created_at LIMIT 1)",(now,"%"+title+"%"))
      else:raise ValueError("Informe o identificador ou título da tarefa.")
      c.commit();local_results.append({"tool":name,"completed":bool(cur.rowcount),"matched":task_id or title})
     elif name=="save_memory":
      content=str(args.get("content") or "").strip()
      if not content:raise ValueError("A memória está vazia.")
      cur=c.execute("INSERT INTO memories(category,content,created_at) VALUES(?,?,?)",(str(args.get("category") or "geral"),content,now));c.commit()
      local_results.append({"tool":name,"saved":True,"memory_id":cur.lastrowid})
     elif name=="list_memories":
      category=str(args.get("category") or "").strip()
      if category:rows=c.execute("SELECT id,category,content,created_at FROM memories WHERE category=? ORDER BY id DESC LIMIT 50",(category,)).fetchall()
      else:rows=c.execute("SELECT id,category,content,created_at FROM memories ORDER BY id DESC LIMIT 50").fetchall()
      local_results.append({"tool":name,"memories":[dict(row) for row in rows]})
     elif name=="delete_memory":
      memory_id=int(args.get("memory_id") or 0);cur=c.execute("DELETE FROM memories WHERE id=?",(memory_id,));c.commit()
      local_results.append({"tool":name,"deleted":bool(cur.rowcount),"memory_id":memory_id})
   except Exception as e:local_results.append({"tool":name,"error":str(e)})
  elif name in android_tools:
   if not devices:
    local_results.append({"tool":name,"error":"O dispositivo Android não está conectado."})
    continue
   command_id=secrets.token_hex(12)
   with connect() as c:c.execute("INSERT INTO device_commands(id,device_id,tool,args,status,created_at) VALUES(?,?,?,?,?,?)",(command_id,devices[0]["id"],name,json.dumps(args,ensure_ascii=False),"queued",now));c.commit()
   queued.append({"id":command_id,"tool":name,"args":args})
 if local_results:
  lines=[]
  for item in local_results:
   name=item.get("tool")
   if item.get("error"):lines.append("Não consegui concluir "+str(name)+": "+str(item["error"]))
   elif name=="create_task":
    due=str(item.get("due_at") or "")
    when=(" para "+datetime.strptime(due[:16],"%Y-%m-%dT%H:%M").strftime("%d/%m/%Y às %H:%M") if len(due)>=16 and "T" in due else (" para "+datetime.strptime(due[:10],"%Y-%m-%d").strftime("%d/%m/%Y") if len(due)>=10 else ""))
    lines.append("Anotei na sua agenda: "+str(item.get("title"))+when+". É um compromisso único.")
   elif name=="list_tasks":
    tasks=item.get("tasks",[])
    lines.append("Você tem "+str(len(tasks))+" tarefa(s) pendente(s): "+("; ".join(str(x.get("title")) for x in tasks) if tasks else "nenhuma tarefa pendente")+".")
   elif name=="complete_task":lines.append("Tarefa marcada como concluída." if item.get("completed") else "Não encontrei essa tarefa para concluir.")
   elif name=="save_memory":lines.append("Guardei essa informação na sua memória pessoal.")
   elif name=="list_memories":
    memories=item.get("memories",[])
    lines.append("Memórias encontradas: "+("; ".join(str(x.get("id"))+": "+str(x.get("content")) for x in memories) if memories else "nenhuma memória salva")+".")
   elif name=="delete_memory":lines.append("Memória apagada." if item.get("deleted") else "Não encontrei essa memória.")
  if lines:answer=(answer+"\n\n"+"\n".join(lines)).strip()
 if queued and not answer:answer="Recebi seu pedido e enviei a ação ao BRUCE no celular. Vou confirmar o resultado assim que o dispositivo responder."
 if not answer:answer="Não recebi uma resposta válida do modelo."
 with connect() as c:c.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(cid,"assistant",answer,int(time.time())));c.commit()
 return {"conversation_id":cid,"message":answer,"model":settings.model_name,"model_provider":"Gemini" if provider=="gemini" else "Anthropic" if provider=="anthropic" else "OpenAI-compatible","queued_actions":queued}
@app.post("/v1/device/register",dependencies=[Depends(auth)])
def register_device(p:DeviceRegistration):
 with connect() as c:c.execute("INSERT INTO devices(id,name,platform,last_seen,metadata) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,platform=excluded.platform,last_seen=excluded.last_seen,metadata=excluded.metadata",(p.device_id,p.name,p.platform,int(time.time()),json.dumps(p.metadata)));c.commit()
 return {"registered":True,"device_id":p.device_id,"poll_seconds":5}
@app.post("/v1/device/heartbeat",dependencies=[Depends(auth)])
def heartbeat(device_id:str=Query(...)):
 with connect() as c:
  cur=c.execute("UPDATE devices SET last_seen=? WHERE id=?",(int(time.time()),device_id));c.commit()
 if not cur.rowcount:raise HTTPException(404,"Dispositivo não registrado.")
 return {"ok":True}
@app.get("/v1/device/commands",dependencies=[Depends(auth)])
def device_commands(device_id:str=Query(...)):
 now=int(time.time())
 with connect() as c:
  c.execute("UPDATE devices SET last_seen=? WHERE id=?",(now,device_id))
  rows=c.execute("SELECT id,tool,args,created_at FROM device_commands WHERE device_id=? AND status='queued' ORDER BY created_at LIMIT 10",(device_id,)).fetchall()
  for row in rows:c.execute("UPDATE device_commands SET status='sent' WHERE id=?",(row["id"],))
  c.commit()
 return [{"id":r["id"],"tool":r["tool"],"arguments":json.loads(r["args"]),"created_at":r["created_at"]} for r in rows]
@app.get("/v1/device/commands/{command_id}",dependencies=[Depends(auth)])
def command_status(command_id:str):
 with connect() as c:row=c.execute("SELECT id,tool,status,created_at,result FROM device_commands WHERE id=?",(command_id,)).fetchone()
 if not row:raise HTTPException(404,"Comando não encontrado.")
 return {"id":row["id"],"tool":row["tool"],"status":row["status"],"created_at":row["created_at"],"result":json.loads(row["result"]) if row["result"] else None}
@app.post("/v1/device/commands/{command_id}/result",dependencies=[Depends(auth)])
def command_result(command_id:str,p:CommandResult):
 with connect() as c:
  cur=c.execute("UPDATE device_commands SET status=?,result=? WHERE id=?",(p.status,json.dumps(p.result,ensure_ascii=False),command_id));c.commit()
 if not cur.rowcount:raise HTTPException(404,"Comando não encontrado.")
 return {"saved":True}
@app.get("/v1/device/status",dependencies=[Depends(auth)])
def device_status():
 with connect() as c:rows=c.execute("SELECT id,name,platform,last_seen,metadata FROM devices ORDER BY last_seen DESC").fetchall()
 return [{"device_id":r["id"],"name":r["name"],"platform":r["platform"],"online":int(time.time())-r["last_seen"]<settings.device_online_seconds,"last_seen":r["last_seen"],"metadata":json.loads(r["metadata"])} for r in rows]
@app.get("/v1/conversations",dependencies=[Depends(auth)])
def conversations():
 with connect() as c:return [dict(x) for x in c.execute("SELECT id,title,created_at,updated_at FROM conversations ORDER BY updated_at DESC LIMIT 100")]
@app.get("/v1/conversations/{cid}",dependencies=[Depends(auth)])
def conversation(cid:str):
 with connect() as c:rows=c.execute("SELECT role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id",(cid,)).fetchall()
 return {"conversation_id":cid,"messages":[dict(x) for x in rows]}
@app.delete("/v1/conversations/{cid}",dependencies=[Depends(auth)])
def delete_conversation(cid:str):
 with connect() as c:c.execute("DELETE FROM messages WHERE conversation_id=?",(cid,));cur=c.execute("DELETE FROM conversations WHERE id=?",(cid,));c.commit()
 if not cur.rowcount:raise HTTPException(404,"Conversa não encontrada.")
 return {"deleted":True}
@app.get("/v1/tasks",dependencies=[Depends(auth)])
def list_tasks(status:str="pending",category:str|None=None):
 query="SELECT id,title,category,due_at,notes,status,created_at,completed_at FROM tasks";clauses=[];params=[]
 if status in {"pending","completed"}:clauses.append("status=?");params.append(status)
 if category:clauses.append("category=?");params.append(category)
 if clauses:query+=" WHERE "+" AND ".join(clauses)
 query+=" ORDER BY CASE WHEN due_at IS NULL OR due_at='' THEN 1 ELSE 0 END,due_at,created_at DESC LIMIT 200"
 with connect() as c:return [dict(x) for x in c.execute(query,params).fetchall()]
@app.post("/v1/tasks",dependencies=[Depends(auth)])
def add_task(p:TaskRequest):
 task_id=secrets.token_hex(8);now=int(time.time())
 with connect() as c:c.execute("INSERT INTO tasks(id,title,category,due_at,notes,status,created_at) VALUES(?,?,?,?,?,?,?)",(task_id,p.title,p.category,p.due_at,p.notes,"pending",now));c.commit()
 return {"id":task_id,"created":True}
@app.patch("/v1/tasks/{task_id}",dependencies=[Depends(auth)])
def update_task(task_id:str,p:TaskUpdate):
 with connect() as c:
  cur=c.execute("UPDATE tasks SET status=?,completed_at=? WHERE id=?",(p.status,int(time.time()) if p.status=="completed" else None,task_id));c.commit()
 if not cur.rowcount:raise HTTPException(404,"Tarefa não encontrada.")
 return {"updated":True,"id":task_id,"status":p.status}
@app.get("/v1/memories",dependencies=[Depends(auth)])
def memories():
 with connect() as c:return [dict(x) for x in c.execute("SELECT id,category,content,created_at FROM memories ORDER BY id DESC LIMIT 100")]
@app.post("/v1/memories",dependencies=[Depends(auth)])
def add_memory(p:MemoryRequest):
 with connect() as c:cur=c.execute("INSERT INTO memories(category,content,created_at) VALUES(?,?,?)",(p.category,p.content,int(time.time())));c.commit()
 return {"id":cur.lastrowid,"saved":True}
@app.delete("/v1/memories/{mid}",dependencies=[Depends(auth)])
def delete_memory(mid:int):
 with connect() as c:cur=c.execute("DELETE FROM memories WHERE id=?",(mid,));c.commit()
 if not cur.rowcount:raise HTTPException(404,"Memória não encontrada.")
 return {"deleted":True}
@app.get("/v1/capabilities",dependencies=[Depends(auth)])
def capabilities():
 with connect() as c:online=c.execute("SELECT COUNT(*) FROM devices WHERE last_seen>=?",(int(time.time())-settings.device_online_seconds,)).fetchone()[0]>0
 return {"assistant":"BRUCE","chat":bool((settings.gemini_api_key if settings.model_provider.lower()=="gemini" else settings.anthropic_api_key if settings.model_provider.lower()=="anthropic" else settings.model_base_url)),"persistent_memory":True,"device_bridge":"queue_ready","android_connected":online,"tools":[x["function"]["name"] for x in TOOLS],"note":"A fila de comandos requer o aplicativo Android com o serviço de ponte ativo."}
