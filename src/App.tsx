import { useCallback, useEffect, useRef, useState } from "react";
import {
  Activity, AudioLines, Bell, BookOpen, Brain, CalendarDays, CheckCircle2,
  ChevronRight, CircleDollarSign, Command, Dumbbell, FileText, History,
  Home, Languages, Mic, MicOff, Plus, Send, Settings, ShieldCheck,
  Sparkles, Target, Volume2, X, LoaderCircle, Menu
} from "lucide-react";

type Message = { role: "user" | "assistant"; text: string };
type Section = "Início" | "Rotina" | "Treinos" | "Estudos" | "Metas" | "Evolução";
type Recognition = { lang:string; continuous:boolean; interimResults:boolean; onresult:((e:any)=>void)|null; onerror:((e:any)=>void)|null; onend:(()=>void)|null; start:()=>void; stop:()=>void };
type SpeechWindow = Window & { SpeechRecognition?: new()=>Recognition; webkitSpeechRecognition?: new()=>Recognition };
const API_DEFAULT = "https://bruce-personal-api-petersonjunior253-8756s-projects.vercel.app";
const API_KEY = "bruce_api_url";
const TOKEN_KEY = "bruce_api_token";
const nav: {name:Section; icon:any; prompt:string}[] = [
  {name:"Início",icon:Home,prompt:"Vamos organizar minhas prioridades de hoje."},
  {name:"Rotina",icon:CalendarDays,prompt:"Ajude-me a organizar minha rotina de hoje e os próximos dias."},
  {name:"Treinos",icon:Dumbbell,prompt:"Quero registrar e planejar meus treinos."},
  {name:"Estudos",icon:BookOpen,prompt:"Quero organizar meus estudos e meu progresso."},
  {name:"Metas",icon:Target,prompt:"Vamos revisar minhas metas e definir próximos passos."},
  {name:"Evolução",icon:Activity,prompt:"Faça uma revisão da minha evolução e dos meus hábitos."}
];

export default function App() {
  const [section,setSection]=useState<Section>("Início");
  const [apiUrl,setApiUrl]=useState(localStorage.getItem(API_KEY)||API_DEFAULT);
  const [token,setToken]=useState(sessionStorage.getItem(TOKEN_KEY)||"");
  const [draftUrl,setDraftUrl]=useState(apiUrl),[draftToken,setDraftToken]=useState(token);
  const [settings,setSettings]=useState(false),[sidebarOpen,setSidebarOpen]=useState(false);
  const [messages,setMessages]=useState<Message[]>([]);
  const [input,setInput]=useState("");
  const [conversationId,setConversationId]=useState<string|null>(null);
  const [busy,setBusy]=useState(false),[listening,setListening]=useState(false),[speaking,setSpeaking]=useState(false);
  const [connected,setConnected]=useState(false),[model,setModel]=useState("Gemini 3.8 Flash");
  const [deviceOnline,setDeviceOnline]=useState(false),[tasks,setTasks]=useState<any[]>([]),[error,setError]=useState("");
  const listRef=useRef<HTMLDivElement>(null),recognition=useRef<Recognition|null>(null);

  const request=useCallback(async(path:string,init:RequestInit={})=>{
    if(!apiUrl||!token)throw new Error("Conecte o BRUCE à API privada nas configurações.");
    const response=await fetch(apiUrl.replace(/\/$/,"")+path,{...init,headers:{"Content-Type":"application/json",Authorization:"Bearer "+token,...(init.headers||{})}});
    const data=await response.json().catch(()=>({}));
    if(!response.ok)throw new Error(data.detail||"Falha na API ("+response.status+").");
    return data;
  },[apiUrl,token]);

  const refreshStatus=useCallback(async()=>{
    try {
      const response=await fetch(apiUrl.replace(/\/$/,"")+"/health");
      if(!response.ok)throw Error();
      const data=await response.json();
      setConnected(Boolean(data.model_configured));
      setModel(data.model_provider==="Gemini"?(data.model_configured?(data.model_name||"Gemini"):"Gemini · chave pendente"):"Gemini · aguardando configuração");
    } catch {setConnected(false);}
    if(token){
      try {const devices=await request("/v1/device/status");setDeviceOnline(Array.isArray(devices)&&devices.some((d:any)=>d.online));}
      catch {setDeviceOnline(false);}
      try {const rows=await request("/v1/tasks?status=pending");setTasks(Array.isArray(rows)?rows:[]);}
      catch {setTasks([]);}
    } else setDeviceOnline(false);
  },[apiUrl,token,request]);

  useEffect(()=>{void refreshStatus();},[refreshStatus]);
  useEffect(()=>{listRef.current?.scrollTo({top:listRef.current.scrollHeight,behavior:"smooth"});},[messages,busy]);
  useEffect(()=>()=>{recognition.current?.stop();window.speechSynthesis?.cancel();},[]);

  const speak=useCallback((text:string)=>{
    if(!("speechSynthesis" in window))return;
    window.speechSynthesis.cancel();
    const utterance=new SpeechSynthesisUtterance(text);
    utterance.lang="pt-BR";utterance.rate=.96;utterance.pitch=1;
    utterance.onstart=()=>setSpeaking(true);
    utterance.onend=()=>setSpeaking(false);
    utterance.onerror=()=>setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  },[]);

  const send=async(raw:string)=>{
    const prompt=raw.trim();
    if(!prompt||busy)return;
    setInput("");setError("");
    setMessages(current=>[...current,{role:"user",text:prompt}]);
    if(!token){setMessages(current=>[...current,{role:"assistant",text:"Estou pronto para conversar. Falta apenas conectar o token privado da API nas configurações."}]);return;}
    setBusy(true);
    try{
      const data=await request("/v1/chat",{method:"POST",body:JSON.stringify({conversation_id:conversationId,messages:[{role:"user",content:prompt}]})});
      if(data.conversation_id)setConversationId(data.conversation_id);
      let answer=String(data.message||"Não recebi uma resposta válida.");
      const actions=Array.isArray(data.queued_actions)?data.queued_actions:[];
      if(actions.length){
        const results=await Promise.all(actions.map(async(action:any)=>{
          for(let i=0;i<15;i++){
            await new Promise(resolve=>window.setTimeout(resolve,1200));
            try{
              const state=await request("/v1/device/commands/"+encodeURIComponent(String(action.id)));
              if(state.status==="completed")return "Ação confirmada pelo celular.";
              if(state.status==="failed"||state.status==="denied")return "Ação não concluída: "+String(state.result?.error||"falha no dispositivo");
            }catch{}
          }
          return "Comando enviado; ainda aguardando confirmação do celular.";
        }));
        answer+="\n\n"+results.join("\n");
      }
      setMessages(current=>[...current,{role:"assistant",text:answer}]);
      if(data.model_provider==="Gemini")setModel(data.model||"Gemini");
      speak(answer);void refreshStatus();
    }catch(e){const message=e instanceof Error?e.message:"Erro inesperado";setError(message);setMessages(current=>[...current,{role:"assistant",text:"Não consegui concluir agora: "+message}]);}
    finally{setBusy(false);}
  };

  const startVoice=()=>{
    const C=(window as SpeechWindow).SpeechRecognition||(window as SpeechWindow).webkitSpeechRecognition;
    if(!C){setError("Este navegador não oferece reconhecimento de voz. Use o microfone do aplicativo Android BRUCE.");return;}
    recognition.current?.stop();
    const r=new C();r.lang="pt-BR";r.continuous=false;r.interimResults=false;
    r.onresult=e=>{const text=Array.from(e.results).map((item:any)=>item[0].transcript).join(" ").trim();if(text)void send(text);};
    r.onerror=e=>{setError("Não consegui acessar o microfone: "+e.error);setListening(false);};
    r.onend=()=>setListening(false);
    recognition.current=r;
    try{r.start();setListening(true);setError("");}catch{setError("Não foi possível iniciar o microfone.");}
  };
  const stopVoice=()=>{recognition.current?.stop();setListening(false);};

  const saveSettings=()=>{
    const url=draftUrl.trim().replace(/\/$/,""),key=draftToken.trim();
    if(!url||!key){setError("Informe o endereço da API e o token privado.");return;}
    if(!url.startsWith("https://")&&!url.includes("localhost")&&!url.includes("127.0.0.1")){setError("Use HTTPS para conexões externas.");return;}
    localStorage.setItem(API_KEY,url);sessionStorage.setItem(TOKEN_KEY,key);
    setApiUrl(url);setToken(key);setSettings(false);
  };
  const quick=(prompt:string)=>{setSection("Início");void send(prompt);};

  return <main className="app-shell">
    <aside className={"sidebar "+(sidebarOpen?"sidebar-open":"")}>
      <div className="sidebar-brand"><div className="brand-emblem">W</div><div><strong>PROTOCOLO</strong><b>BRUCE WAYNE</b><small>DISCIPLINA · FOCO · EVOLUÇÃO</small></div><button className="mobile-close" onClick={()=>setSidebarOpen(false)}><X/></button></div>
      <div className="sidebar-label">ASSISTENTE PESSOAL</div>
      <nav className="side-nav">
        {nav.map(item=>{const Icon=item.icon;return <button key={item.name} className={section===item.name?"selected":""} onClick={()=>{setSection(item.name);setSidebarOpen(false);if(item.name!=="Início")setInput(item.prompt);}}><Icon size={17}/><span>{item.name}</span>{section===item.name&&<i/>}</button>;})}
      </nav>
      <div className="sidebar-spacer"/>
      <div className="sidebar-system"><div className="system-heading"><span className={connected?"live-dot":"off-dot"}/><b>{connected?"Sistema conectado":"Aguardando conexão"}</b></div><small>{model}</small><div className="system-divider"/><div className="system-heading"><span className={deviceOnline?"live-dot":"off-dot"}/><b>{deviceOnline?"Android conectado":"Android desconectado"}</b></div><small>Voz e automações do dispositivo</small></div>
      <button className="sidebar-profile" onClick={()=>{setDraftUrl(apiUrl);setDraftToken(token);setSettings(true);}}><div className="profile-avatar">PJ</div><div><b>Meu BRUCE</b><small>Configurações pessoais</small></div><Settings size={16}/></button>
    </aside>

    <section className="workspace">
      <header className="topbar">
        <button className="mobile-menu" onClick={()=>setSidebarOpen(true)}><Menu/></button>
        <div className="welcome"><div className="eyebrow">SEU ASSISTENTE PESSOAL</div><h1>{section==="Início"?"Olá. Vamos começar?":section}</h1><p>{section==="Início"?"Estou aqui para ajudar você a pensar, planejar e agir.":"Vamos trabalhar em "+section.toLowerCase()+", passo a passo."}</p></div>
        <div className="top-actions"><button className="language-chip"><Languages size={15}/> Português <span>⌄</span></button><button className="icon-button" aria-label="Notificações" onClick={()=>setError("As notificações do BRUCE serão exibidas aqui quando estiverem conectadas.")}><Bell size={18}/></button><button className="icon-button" aria-label="Configurações" onClick={()=>{setDraftUrl(apiUrl);setDraftToken(token);setSettings(true);}}><Settings size={18}/></button></div>
      </header>

      <div className="dashboard-grid">
        <section className="assistant-column">
          <div className="assistant-stage">
            <div className={"assistant-orb "+(busy?"thinking":listening?"listening":speaking?"speaking":"")}>
              <div className="orb-ring ring-a"/><div className="orb-ring ring-b"/><div className="orb-ring ring-c"/>
              <div className="orb-core"><AudioLines size={43} strokeWidth={1.25}/></div>
              <span className="orb-particle p1"/><span className="orb-particle p2"/><span className="orb-particle p3"/>
            </div>
            <div className="assistant-greeting"><span className="online-pulse"/><b>{busy?"BRUCE está pensando":listening?"Estou ouvindo você":speaking?"Estou respondendo":connected?"BRUCE está ativado":"BRUCE está aguardando conexão"}</b></div>
            <h2>{section==="Início"?"Como posso ajudar você hoje?":"O que vamos fazer em "+section.toLowerCase()+"?"}</h2>
            <p className="assistant-subtitle">Converse naturalmente. Eu ajudo a transformar suas ideias em ações.</p>
          </div>

          {messages.length>0&&<div className="chat-history" ref={listRef}>
            {messages.slice(-8).map((m,i)=><article className={"chat-message "+m.role} key={i}><div className="message-avatar">{m.role==="assistant"?"B":"PJ"}</div><div><label>{m.role==="assistant"?"BRUCE":"VOCÊ"}</label><p>{m.text}</p>{m.role==="assistant"&&<button className="listen-answer" onClick={()=>speak(m.text)}><Volume2 size={13}/> Ouvir resposta</button>}</div></article>)}
            {busy&&<div className="typing"><LoaderCircle size={15}/> BRUCE está organizando a resposta…</div>}
          </div>}

          <div className="composer-wrap">
            <form className="composer" onSubmit={e=>{e.preventDefault();void send(input);}}>
              <button type="button" className="composer-tool" title="Anexos" onClick={()=>setError("O envio de arquivos será habilitado na próxima etapa.")}><Plus size={19}/></button>
              <input value={input} onChange={e=>setInput(e.target.value)} placeholder="Fale com o BRUCE..." aria-label="Mensagem para BRUCE"/>
              <button type="button" className={"mic-button "+(listening?"active":"")} onClick={listening?stopVoice:startVoice} aria-label="Falar">{listening?<MicOff size={19}/>:<Mic size={19}/>}</button>
              <button type="submit" className="send-button" disabled={!input.trim()||busy} aria-label="Enviar"><Send size={17}/></button>
            </form>
            <div className="composer-hint"><span><ShieldCheck size={13}/> Suas informações permanecem privadas</span><span>Ativação por voz em segundo plano no app Android</span></div>
          </div>

          <div className="quick-actions">
            <button onClick={()=>quick("Bruce, organize minha rotina de hoje.")}><CalendarDays/><span>Organizar rotina</span></button>
            <button onClick={()=>quick("Bruce, registre meu treino de hoje.")}><Dumbbell/><span>Registrar treino</span></button>
            <button onClick={()=>quick("Bruce, monte um plano de estudos para mim.")}><BookOpen/><span>Planejar estudos</span></button>
            <button onClick={()=>quick("Bruce, vamos revisar minhas metas.")}><Target/><span>Revisar metas</span></button>
          </div>
        </section>

        <aside className="right-rail">
          <section className="rail-card system-card"><div className="card-title"><div><span className="card-kicker">NÚCLEO PESSOAL</span><h3>Status do sistema</h3></div><Activity size={18}/></div>
            <div className="status-row"><span className={connected?"live-dot":"off-dot"}/><div><b>Inteligência Gemini</b><small>{connected?model:"Aguardando chave de API"}</small></div><span className="status-text">{connected?"ONLINE":"PENDENTE"}</span></div>
            <div className="status-row"><span className={deviceOnline?"live-dot":"off-dot"}/><div><b>Dispositivo Android</b><small>{deviceOnline?"Ponte de comandos conectada":"Ative a ponte no aplicativo"}</small></div><span className="status-text">{deviceOnline?"ONLINE":"OFFLINE"}</span></div>
            <div className="status-row"><span className={token?"live-dot":"off-dot"}/><div><b>Memória pessoal</b><small>Contexto e histórico privado</small></div><span className="status-text">{token?"API":"CONFIG"}</span></div>
            <button className="card-link" onClick={()=>{setDraftUrl(apiUrl);setDraftToken(token);setSettings(true);}}>Configurar sistema <ChevronRight size={15}/></button>
          </section>

          <section className="rail-card"><div className="card-title"><div><span className="card-kicker">ORGANIZAÇÃO</span><h3>Próximas atividades</h3></div><CalendarDays size={18}/></div>
            {tasks.length>0?<div className="task-list">{tasks.slice(0,5).map(task=><div className="task-row" key={task.id}><button className="task-check" title="Concluir tarefa" onClick={async()=>{try{await request("/v1/tasks/"+encodeURIComponent(task.id),{method:"PATCH",body:JSON.stringify({status:"completed"})});await refreshStatus();}catch(e){setError(e instanceof Error?e.message:"Não foi possível concluir a tarefa.");}}}><CheckCircle2 size={15}/></button><div><b>{task.title}</b><small>{task.category}{task.due_at?" · "+task.due_at.replace("T"," "):""}</small></div></div>)}<button className="card-link" onClick={()=>quick("Bruce, mostre todas as minhas tarefas pendentes.")}>Ver todas as tarefas <ChevronRight size={14}/></button></div>:<div className="empty-activities"><div className="empty-icon"><CalendarDays size={20}/></div><p>Vamos preencher sua agenda juntos.</p><small>Peça ao BRUCE para planejar sua rotina e organizar seus compromissos.</small><button onClick={()=>quick("Bruce, me ajude a montar minha rotina semanal.")}>Planejar rotina <ChevronRight size={14}/></button></div>}
          </section>

          <section className="rail-card memory-card"><div className="card-title"><div><span className="card-kicker">CONTEXTO CONTÍNUO</span><h3>Memória e evolução</h3></div><Brain size={18}/></div>
            <p>O BRUCE usa o contexto disponível para manter conversas mais úteis e consistentes.</p>
            <div className="memory-tags"><span><Sparkles size={12}/> Personalização</span><span><ShieldCheck size={12}/> Privacidade</span></div>
          </section>

          <section className="voice-note"><div className="voice-note-icon"><AudioLines size={20}/></div><div><b>Fale apenas “Bruce”</b><p>Ative a escuta no aplicativo Android para chamar o assistente sem abrir a tela.</p></div></section>
        </aside>
      </div>
      <footer className="workspace-footer"><span>PROTOCOLO BRUCE WAYNE</span><span>INTELIGÊNCIA PESSOAL · VOZ · AUTOMAÇÃO</span><span className={connected?"footer-online":"footer-offline"}>{connected?"● NÚCLEO ONLINE":"● CONEXÃO PENDENTE"}</span></footer>
    </section>

    {settings&&<div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)setSettings(false);}}><section className="settings-modal"><div className="modal-heading"><div><span className="card-kicker">CONFIGURAÇÃO DO NÚCLEO</span><h2>Conexão privada</h2></div><button onClick={()=>setSettings(false)}><X/></button></div><p>Informe o endereço da API BRUCE e o token privado do dispositivo. A chave do Gemini deve permanecer configurada apenas no servidor.</p><label>URL DA API<input value={draftUrl} onChange={e=>setDraftUrl(e.target.value)} placeholder="https://sua-api.vercel.app"/></label><label>TOKEN PRIVADO<input type="password" value={draftToken} onChange={e=>setDraftToken(e.target.value)} placeholder="Token privado do dispositivo"/></label><div className="secure-hint"><ShieldCheck size={16}/> Nunca cole aqui sua chave do Google Gemini.</div><div className="modal-actions"><button className="secondary" onClick={()=>{localStorage.removeItem(API_KEY);sessionStorage.removeItem(TOKEN_KEY);setToken("");setSettings(false);}}>Desconectar</button><button className="primary" onClick={saveSettings}>Salvar conexão</button></div></section></div>}
    {error&&<div className="toast-error">{error}<button onClick={()=>setError("")}><X size={14}/></button></div>}
  </main>;
}
