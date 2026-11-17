from __future__ import annotations
import hashlib,hmac,json,os,secrets,sqlite3,time
from pathlib import Path
from typing import Literal,Any
import httpx
from fastapi import Depends,FastAPI,Header,HTTPException,Query
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from pydantic_settings import BaseSettings,SettingsConfigDict
import edge_tts

class Settings(BaseSettings):
 model_config=SettingsConfigDict(env_prefix="BRUCE_",env_file=".env",extra="ignore")
 api_key:str="development-only-change-me"
 model_base_url:str="http://127.0.0.1:11434/v1"
 model_api_key:str=""
 model_name:str="llama3.2"
 system_prompt:str="Você é BRUCE, assistente pessoal privado do usuário. Responda em português brasileiro, seja inteligente, direto, natural e proativo. Nunca afirme que executou algo sem confirmação do dispositivo. Para ações críticas, peça autorização explícita. Use ferramentas reais quando disponíveis."
 max_context_messages:int=80
 max_output_tokens:int=4096
 database_path:str="./data/bruce.sqlite3"
 device_online_seconds:int=90
settings=Settings()
db=Path(settings.database_path);db.parent.mkdir(parents=True,exist_ok=True)
app=FastAPI(title="BRUCE Personal Intelligence API",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=os.getenv("BRUCE_ALLOWED_ORIGINS","https://bruce-preview-six.vercel.app,https://bruce-preview-petersonjunior253-8756s-projects.vercel.app,http://localhost:5173,http://127.0.0.1:5173").split(","),allow_credentials=False,allow_methods=["GET","POST","PATCH","DELETE"],allow_headers=["Authorization","Content-Type"])

def connect():
 c=sqlite3.connect(db);c.row_factory=sqlite3.Row;return c
def init_db():
 with connect() as c:
  c.execute("CREATE TABLE IF NOT EXISTS conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY AUTOINCREMENT,conversation_id TEXT NOT NULL,role TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS memories(id INTEGER PRIMARY KEY AUTOINCREMENT,category TEXT NOT NULL,content TEXT NOT NULL,created_at INTEGER NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS devices(id TEXT PRIMARY KEY,name TEXT NOT NULL,platform TEXT NOT NULL,last_seen INTEGER NOT NULL,metadata TEXT NOT NULL DEFAULT '{}')")
  c.execute("CREATE TABLE IF NOT EXISTS device_commands(id TEXT PRIMARY KEY,device_id TEXT NOT NULL,tool TEXT NOT NULL,args TEXT NOT NULL,status TEXT NOT NULL,created_at INTEGER NOT NULL,result TEXT)")
  c.execute("CREATE INDEX IF NOT EXISTS idx_messages ON messages(conversation_id,id)")
  c.execute("CREATE INDEX IF NOT EXISTS idx_commands ON device_commands(device_id,status,created_at)")
  c.commit()
@app.on_event("startup")
def startup():init_db()
def auth(authorization:str|None=Header(default=None)):
 if not settings.api_key or settings.api_key=="development-only-change-me":raise HTTPException(503,"Configure BRUCE_API_KEY no servidor.")
 if not authorization or not hmac.compare_digest(authorization,"Bearer "+settings.api_key):raise HTTPException(401,"Token privado inválido.")
class Message(BaseModel):
 role:Literal["user","assistant"];content:str=Field(min_length=1,max_length=100000)
class ChatRequest(BaseModel):
 conversation_id:str|None=None;messages:list[Message]=Field(min_length=1,max_length=100)
class MemoryRequest(BaseModel):
 category:str=Field(default="geral",max_length=60);content:str=Field(min_length=1,max_length=12000)
class DeviceRegistration(BaseModel):
 device_id:str=Field(min_length=6,max_length=100);name:str="BRUCE Android";platform:str="android";metadata:dict[str,Any]={}
class CommandResult(BaseModel):
 status:Literal["completed","failed","denied"];result:dict[str,Any]={}
class VoiceRequest(BaseModel):
 text:str=Field(min_length=1,max_length=12000)
 voice:str="pt-BR-AntonioNeural"
TOOLS=[
 {"type":"function","function":{"name":"open_app","description":"Abrir um aplicativo instalado no Android do usuário pelo nome ou pacote.","parameters":{"type":"object","properties":{"package_name":{"type":"string"},"app_name":{"type":"string"}},"required":["package_name"]}}},
 {"type":"function","function":{"name":"create_calendar_event","description":"Criar um evento no calendário Android. O aplicativo mostrará a tela de confirmação antes de salvar.","parameters":{"type":"object","properties":{"title":{"type":"string"},"start_iso":{"type":"string"},"end_iso":{"type":"string"},"description":{"type":"string"}},"required":["title","start_iso"]}}},
 {"type":"function","function":{"name":"open_file_picker","description":"Abrir seletor nativo de arquivos para o usuário escolher um documento.","parameters":{"type":"object","properties":{"mime_type":{"type":"string"}}}}},
 {"type":"function","function":{"name":"create_notification","description":"Mostrar uma notificação local no Android.","parameters":{"type":"object","properties":{"title":{"type":"string"},"message":{"type":"string"}},"required":["title","message"]}}},
 {"type":"function","function":{"name":"set_alarm","description":"Abrir o relógio Android para configurar um alarme.","parameters":{"type":"object","properties":{"hour":{"type":"integer"},"minute":{"type":"integer"},"message":{"type":"string"}},"required":["hour","minute"]}}},
 {"type":"function","function":{"name":"open_device_settings","description":"Abrir uma página de configurações Android solicitada pelo usuário.","parameters":{"type":"object","properties":{"section":{"type":"string","enum":["settings","wifi","bluetooth","sound","display","apps","accessibility","notifications"]}},"required":["section"]}}},
 {"type":"function","function":{"name":"get_device_info","description":"Consultar informações básicas do dispositivo conectado.","parameters":{"type":"object","properties":{} } }},
 {"type":"function","function":{"name":"list_installed_apps","description":"Listar aplicativos instalados e visíveis no Android.","parameters":{"type":"object","properties":{} } }},\n {"type":"function","function":{"name":"list_notifications","description":"Ler notificações ativas do Android. Requer que o usuário habilite o acesso a notificações do BRUCE nas configurações do sistema.","parameters":{"type":"object","properties":{} } }}
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
def health():
 return {"status":"ok","service":"BRUCE Personal Intelligence API","model_configured":bool(settings.model_name),"model_name":settings.model_name,"model_provider":"OpenAI-compatible","database":"sqlite","device_tools":True,"time":int(time.time())}
@app.post("/v1/chat",dependencies=[Depends(auth)])
async def chat(p:ChatRequest):
 now=int(time.time());cid=p.conversation_id or secrets.token_hex(12)
 with connect() as c:
  c.execute("INSERT OR IGNORE INTO conversations VALUES(?,?,?,?)",(cid,"Nova conversa",now,now))
  old=c.execute("SELECT role,content FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT ?",(cid,settings.max_context_messages)).fetchall()
  for m in p.messages:c.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(cid,m.role,m.content,now))
  title=p.messages[0].content.strip()[:72] or "Nova conversa"
  c.execute("UPDATE conversations SET updated_at=?,title=CASE WHEN title='Nova conversa' THEN ? ELSE title END WHERE id=?",(now,title,cid));c.commit()
 with connect() as c:mem=c.execute("SELECT category,content FROM memories ORDER BY id DESC LIMIT 30").fetchall()
 with connect() as c:devices=c.execute("SELECT id,name,last_seen FROM devices WHERE last_seen>=?",(now-settings.device_online_seconds,)).fetchall()
 context=settings.system_prompt
 if mem:context+="\n\nMemórias do usuário:\n"+"\n".join(f"- [{x['category']}] {x['content']}" for x in mem)
 if devices:context+="\n\nUm dispositivo Android está conectado e pode receber comandos por ferramentas. Use-as somente quando o usuário pedir uma ação concreta. O aplicativo Android exige confirmação em ações que alteram dados."
 else:context+="\n\nNenhum dispositivo Android está conectado agora. Não diga que executou ações no aparelho."
 messages=[{"role":"system","content":context}]+[{"role":x["role"],"content":x["content"]} for x in reversed(old)]+[{"role":m.role,"content":m.content} for m in p.messages]
 body={"model":settings.model_name,"messages":messages,"max_tokens":settings.max_output_tokens,"tools":TOOLS,"tool_choice":"auto"}
 headers={"Content-Type":"application/json"}
 if settings.model_api_key:headers["Authorization"]="Bearer "+settings.model_api_key
 try:
  async with httpx.AsyncClient(timeout=httpx.Timeout(150,connect=15)) as client:
   r=await client.post(settings.model_base_url.rstrip("/")+"/chat/completions",headers=headers,json=body);r.raise_for_status();data=r.json()
  choice=data["choices"][0]["message"];answer=choice.get("content") or ""
  calls=choice.get("tool_calls") or []
 except httpx.HTTPStatusError as e:raise HTTPException(502,f"Provedor de IA retornou HTTP {e.response.status_code}.")
 except (httpx.HTTPError,KeyError,ValueError) as e:raise HTTPException(502,"Não foi possível consultar o modelo configurado.")
 queued=[]
 if calls and devices:
  did=devices[0]["id"]
  for call in calls:
   fn=call.get("function",{});name=fn.get("name")
   if name not in {x["function"]["name"] for x in TOOLS}:continue
   try:args=json.loads(fn.get("arguments") or "{}")
   except ValueError:args={}
   command_id=secrets.token_hex(12)
   with connect() as c:c.execute("INSERT INTO device_commands(id,device_id,tool,args,status,created_at) VALUES(?,?,?,?,?,?)",(command_id,did,name,json.dumps(args,ensure_ascii=False),"queued",now));c.commit()
   queued.append({"id":command_id,"tool":name,"args":args})
  if queued and not answer:answer="Recebi seu pedido e enviei a ação ao BRUCE no celular. Vou confirmar o resultado assim que o dispositivo responder."
 elif calls and not devices:
  answer=(answer+"\n\nNo momento, seu Android não está conectado ao núcleo BRUCE.").strip()
 if not answer:answer="Não recebi uma resposta válida do modelo."
 with connect() as c:c.execute("INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",(cid,"assistant",answer,int(time.time())));c.commit()
 return {"conversation_id":cid,"message":answer,"model":settings.model_name,"queued_actions":queued}
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
 return {"assistant":"BRUCE","chat":True,"persistent_memory":True,"device_bridge":"queue_ready","android_connected":online,"tools":[x["function"]["name"] for x in TOOLS],"note":"A fila de comandos requer o aplicativo Android com o serviço de ponte ativo."}
