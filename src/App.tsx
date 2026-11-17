import { useCallback, useEffect, useRef, useState } from "react";
import {
  AudioLines, Plus, Search, Settings2, PanelLeftClose, PanelLeftOpen, Mic, MicOff,
  Send, Paperclip, Volume2, VolumeX, Brain, MessageSquare, Trash2, Pencil,
  Check, X, ShieldCheck, Wifi, WifiOff, Sparkles, ChevronDown, Command,
  Bell, Globe2, MoreHorizontal, Square, LoaderCircle, CircleHelp
} from "lucide-react";

type Role = "assistant" | "user";
type Message = { role: Role; text: string; created_at?: number };
type Conversation = { id: string; title: string; updated_at: number };
type Memory = { id: number; category: string; content: string; created_at: number };
type RecognitionResult = { 0: { transcript: string }; isFinal: boolean };
type RecognitionEvent = { resultIndex: number; results: ArrayLike<RecognitionResult> };
type Recognition = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: RecognitionEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null; start: () => void; stop: () => void;
};
type SpeechWindow = Window & { SpeechRecognition?: new () => Recognition; webkitSpeechRecognition?: new () => Recognition };

const API_URL_KEY = "bruce_api_url";
const API_TOKEN_KEY = "bruce_api_token";
const welcome: Message = { role: "assistant", text: "Estou aqui. Sou BRUCE, seu assistente pessoal. Posso conversar, ajudar a planejar e organizar suas ideias. Conecte sua API privada nas configurações para ativar o modelo de inteligência." };

export default function App() {
  const [apiUrl, setApiUrl] = useState(localStorage.getItem(API_URL_KEY) || "");
  const [token, setToken] = useState(sessionStorage.getItem(API_TOKEN_KEY) || "");
  const [messages, setMessages] = useState<Message[]>([welcome]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [input, setInput] = useState("");
  const [sidebar, setSidebar] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [memoryDraft, setMemoryDraft] = useState("");
  const [memoryCategory, setMemoryCategory] = useState("preferência");
  const [busy, setBusy] = useState(false);
  const [listening, setListening] = useState(false);
  const [wakeEnabled, setWakeEnabled] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [status, setStatus] = useState("Configure sua API privada");
  const [connected, setConnected] = useState(false);
  const [modelName, setModelName] = useState("Modelo próprio");
  const [language, setLanguage] = useState("pt-BR");
  const [search, setSearch] = useState("");
  const [draftUrl, setDraftUrl] = useState(apiUrl);
  const [draftToken, setDraftToken] = useState(token);
  const [error, setError] = useState("");
  const [mobileMenu, setMobileMenu] = useState(false);
  const recognition = useRef<Recognition | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wakeArmed = useRef(false);
  const wakeActive = useRef(false);

  const request = useCallback(async (path: string, init: RequestInit = {}) => {
    if (!apiUrl || !token) throw new Error("Configure a URL e o token privado da API BRUCE.");
    const response = await fetch(apiUrl.replace(/\/$/, "") + path, {
      ...init,
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + token, ...(init.headers || {}) }
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "Falha na API (" + response.status + ")");
    return data;
  }, [apiUrl, token]);

  const refreshConversations = useCallback(async () => {
    try { setConversations(await request("/v1/conversations")); } catch { /* API may be offline */ }
  }, [request]);

  const refreshMemories = useCallback(async () => {
    try { setMemories(await request("/v1/memories")); } catch (e) { setError(e instanceof Error ? e.message : "Falha ao carregar memória"); }
  }, [request]);

  const checkConnection = useCallback(async () => {
    if (!apiUrl || !token) { setConnected(false); setStatus("Configure sua API privada"); return; }
    try {
      const health = await fetch(apiUrl.replace(/\/$/, "") + "/health");
      if (!health.ok) throw new Error("API indisponível");
      const data = await health.json();
      setConnected(true);
      setModelName(data.model_name || (data.model_configured ? "Modelo conectado" : "Modelo não configurado"));
      setStatus(data.model_configured ? "Núcleo conectado" : "API online · configure o modelo");
      void refreshConversations();
    } catch {
      setConnected(false); setStatus("Não foi possível alcançar a API");
    }
  }, [apiUrl, token, refreshConversations]);

  useEffect(() => { void checkConnection(); }, [checkConnection]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);
  useEffect(() => () => { recognition.current?.stop(); window.speechSynthesis?.cancel(); }, []);

  const speak = useCallback((text: string) => {
    if (!voiceEnabled || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = language; utterance.rate = 0.96; utterance.pitch = 0.92;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  }, [voiceEnabled, language]);

  const newConversation = () => {
    recognition.current?.stop(); setListening(false); setWakeEnabled(false);
    setConversationId(null); setMessages([welcome]); setError(""); setInput("");
    inputRef.current?.focus();
  };

  const loadConversation = async (id: string) => {
    try {
      const data = await request("/v1/conversations/" + encodeURIComponent(id));
      setConversationId(id);
      setMessages((data.messages || []).map((m: { role: Role; content: string; created_at: number }) => ({ role: m.role, text: m.content, created_at: m.created_at })));
      setMobileMenu(false);
    } catch (e) { setError(e instanceof Error ? e.message : "Não foi possível abrir a conversa"); }
  };

  const sendMessage = async (raw: string) => {
    const text = raw.trim();
    if (!text || busy) return;
    setInput(""); setError("");
    setMessages(current => [...current, { role: "user", text }]);
    if (!apiUrl || !token) {
      const warning = "Ainda não estou conectado à sua API. Abra Configurações e informe o endereço HTTPS e o token privado do BRUCE.";
      setMessages(current => [...current, { role: "assistant", text: warning }]);
      speak(warning); setError("API não configurada"); return;
    }
    setBusy(true); setStatus("Pensando…");
    try {
      const data = await request("/v1/chat", {
        method: "POST",
        body: JSON.stringify({ conversation_id: conversationId, messages: [{ role: "user", content: text }] })
      });
      if (data.conversation_id) setConversationId(data.conversation_id);
      const answer = String(data.message || "Não recebi uma resposta válida do modelo.");
      setMessages(current => [...current, { role: "assistant", text: answer }]);
      setModelName(data.model || "Modelo ativo");
      setStatus("Pronto");
      speak(answer);
      void refreshConversations();
    } catch (e) {
      const reason = e instanceof Error ? e.message : "Erro desconhecido";
      setError(reason); setStatus("Falha na inteligência");
      setMessages(current => [...current, { role: "assistant", text: "Não consegui concluir sua solicitação: " + reason }]);
    } finally { setBusy(false); }
  };

  const saveConnection = async () => {
    const url = draftUrl.trim().replace(/\/$/, "");
    const secret = draftToken.trim();
    if (!url || !secret) { setError("Informe a URL e o token privado."); return; }
    if (!url.startsWith("https://") && !url.includes("localhost") && !url.includes("127.0.0.1")) {
      setError("Use HTTPS para conexões fora do ambiente local."); return;
    }
    setApiUrl(url); setToken(secret);
    localStorage.setItem(API_URL_KEY, url); sessionStorage.setItem(API_TOKEN_KEY, secret);
    setSettingsOpen(false); setError("Conexão salva neste navegador.");
    setTimeout(() => setError(""), 3500);
  };

  const startListening = (wakeMode = false) => {
    const Constructor = (window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition;
    if (!Constructor) { setError("Este navegador não oferece reconhecimento de voz. Use Chrome ou o app Android."); return; }
    recognition.current?.stop();
    const engine = new Constructor();
    engine.lang = language; engine.continuous = wakeMode; engine.interimResults = true;
    engine.onresult = event => {
      const transcript = Array.from(event.results).slice(event.resultIndex).map(r => r[0].transcript).join(" ").trim();
      if (!transcript) return;
      if (wakeMode) {
        const match = transcript.match(/\bbruce\b[,.!\s]*(.*)/i);
        if (match) {
          const command = match[1].trim();
          wakeArmed.current = true;
          setWakeEnabled(false); setListening(false);
          engine.stop();
          if (command) void sendMessage(command);
          else {
            speak("Estou aqui. Pode falar.");
            setTimeout(() => startListening(false), 900);
          }
        }
      } else if (Array.from(event.results).some(r => r.isFinal)) {
        void sendMessage(transcript);
      }
    };
    engine.onerror = event => { setListening(false); setWakeEnabled(false); setStatus("Microfone: " + event.error); };
    engine.onend = () => {
      if (wakeMode && wakeArmed.current) { wakeArmed.current = false; return; }
      setListening(false);
      if (wakeMode && wakeActive.current) {
        try { engine.start(); setListening(true); } catch { setWakeEnabled(false); }
      }
    };
    recognition.current = engine;
    try { engine.start(); setListening(true); setWakeEnabled(wakeMode); wakeActive.current = wakeMode; setStatus(wakeMode ? "Aguardando a palavra BRUCE…" : "Ouvindo você…"); }
    catch { setListening(false); setWakeEnabled(false); setError("Não foi possível iniciar o microfone."); }
  };

  const stopListening = () => {
    wakeArmed.current = true;
    recognition.current?.stop(); setListening(false); setWakeEnabled(false); wakeActive.current = false; setStatus("Microfone pausado");
  };

  const saveMemory = async () => {
    if (!memoryDraft.trim()) return;
    try {
      await request("/v1/memories", { method: "POST", body: JSON.stringify({ category: memoryCategory, content: memoryDraft.trim() }) });
      setMemoryDraft(""); await refreshMemories();
    } catch (e) { setError(e instanceof Error ? e.message : "Falha ao salvar memória"); }
  };

  const deleteMemory = async (id: number) => {
    try { await request("/v1/memories/" + id, { method: "DELETE" }); await refreshMemories(); }
    catch (e) { setError(e instanceof Error ? e.message : "Falha ao apagar memória"); }
  };

  const deleteConversation = async (id: string) => {
    if (!window.confirm("Apagar esta conversa permanentemente?")) return;
    try {
      await request("/v1/conversations/" + id, { method: "DELETE" });
      if (conversationId === id) newConversation();
      await refreshConversations();
    } catch (e) { setError(e instanceof Error ? e.message : "Falha ao apagar conversa"); }
  };

  const filtered = conversations.filter(c => c.title.toLowerCase().includes(search.toLowerCase()));

  return <div className="app-shell">
    {sidebar && <aside className="sidebar">
      <div className="side-brand"><div className="brand-symbol"><AudioLines size={19}/></div><div><b>BRUCE</b><small>PERSONAL INTELLIGENCE</small></div><button className="ghost icon-only side-collapse" onClick={() => setSidebar(false)} aria-label="Recolher menu"><PanelLeftClose size={17}/></button></div>
      <button className="new-chat" onClick={newConversation}><Plus size={17}/> Nova conversa <span>⌘ K</span></button>
      <div className="side-search"><Search size={15}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar conversas"/></div>
      <div className="side-label">ESPAÇO PESSOAL</div>
      <button className="side-link" onClick={() => { setMemoryOpen(true); void refreshMemories(); }}><Brain size={16}/> Memória</button>
      <button className="side-link" onClick={() => setSettingsOpen(true)}><Settings2 size={16}/> Configurações</button>
      <div className="history-label"><span>RECENTES</span><MoreHorizontal size={15}/></div>
      <div className="history-list">{filtered.map(c => <div className={"history-row " + (conversationId === c.id ? "selected" : "")} key={c.id}><button onClick={() => void loadConversation(c.id)}><MessageSquare size={15}/><span>{c.title || "Nova conversa"}</span></button><button className="history-delete" aria-label="Apagar conversa" onClick={() => void deleteConversation(c.id)}><Trash2 size={13}/></button></div>)}</div>
      <div className="side-bottom"><div className="connection-card"><span className={"connection-indicator " + (connected ? "online" : "")}/><div><b>{connected ? "API conectada" : "API desconectada"}</b><small>{connected ? modelName : "Configure sua inteligência"}</small></div><button className="ghost icon-only" onClick={() => setSettingsOpen(true)}><Settings2 size={15}/></button></div><div className="privacy-note"><ShieldCheck size={13}/> Sua inteligência. Seus dados. Seu controle.</div></div>
    </aside>}

    <main className="main-area">
      <header className="topbar">
        <div className="top-left">{!sidebar && <button className="ghost icon-only" onClick={() => setSidebar(true)}><PanelLeftOpen size={18}/></button>}<span className="workspace-title">Assistente</span><span className="model-pill"><span className="model-dot"/>{modelName}<ChevronDown size={13}/></span></div>
        <div className="top-right"><span className="live-status"><i className={connected ? "online" : ""}/>{connected ? "ONLINE" : "OFFLINE"}</span><button className="ghost icon-only" title="Idioma" onClick={() => setLanguage(language === "pt-BR" ? "en-US" : "pt-BR")}><Globe2 size={17}/></button><button className="ghost icon-only" title="Memória" onClick={() => { setMemoryOpen(true); void refreshMemories(); }}><Brain size={17}/></button><button className="ghost icon-only" title="Configurações" onClick={() => setSettingsOpen(true)}><Settings2 size={17}/></button></div>
      </header>

      <section className="chat-stage">
        {messages.length <= 1 && !conversationId ? <div className="welcome-screen">
          <div className="welcome-orb"><div className="orb-ring ring-a"/><div className="orb-ring ring-b"/><div className="orb-core"><AudioLines size={34}/></div><div className="orb-particle p-a"/><div className="orb-particle p-b"/></div>
          <div className="welcome-kicker"><Sparkles size={13}/> SEU ASSISTENTE PESSOAL</div>
          <h1>O que vamos<br/><em>resolver hoje?</em></h1>
          <p>Inteligência, voz e automação em um só lugar.</p>
          <div className="suggestion-grid">
            <button onClick={() => void sendMessage("Organize meu dia considerando estudos, treino e descanso.")}><span><Command size={16}/></span><b>Organizar meu dia</b><small>Planejamento e rotina</small></button>
            <button onClick={() => void sendMessage("Me ajude a estudar programação com um plano prático.")}><span><Brain size={16}/></span><b>Aprender algo</b><small>Estudos e desenvolvimento</small></button>
            <button onClick={() => void sendMessage("Ajude-me a estruturar e priorizar meus projetos.")}><span><Sparkles size={16}/></span><b>Desenvolver projeto</b><small>Ideias em execução</small></button>
          </div>
        </div> : <div className="message-list">{messages.map((m, i) => <article className={"chat-message " + m.role} key={i}><div className="message-avatar">{m.role === "assistant" ? <AudioLines size={16}/> : "P"}</div><div className="message-content"><div className="message-meta">{m.role === "assistant" ? "BRUCE" : "VOCÊ"} <span>{m.created_at ? new Date(m.created_at * 1000).toLocaleTimeString() : ""}</span></div><div className="message-text">{m.text}</div>{m.role === "assistant" && <div className="message-tools"><button onClick={() => speak(m.text)} title="Ouvir resposta"><Volume2 size={14}/></button><button onClick={() => navigator.clipboard?.writeText(m.text)} title="Copiar resposta"><Command size={13}/></button></div>}</div></article>)}{busy && <div className="thinking"><LoaderCircle size={16}/> BRUCE está pensando…</div>}<div ref={bottomRef}/></div>}
      </section>

      <div className="composer-wrap">
        {error && <div className="inline-notice"><CircleHelp size={14}/>{error}<button onClick={() => setError("")}><X size={13}/></button></div>}
        <form className="composer" onSubmit={e => { e.preventDefault(); void sendMessage(input); }}>
          <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} placeholder="Pergunte qualquer coisa ao BRUCE…" aria-label="Mensagem para BRUCE"/>
          <div className="composer-actions"><button type="button" className={"composer-icon " + (listening ? "active" : "")} title="Ativação por voz" onClick={() => listening ? stopListening() : startListening(false)}>{listening ? <MicOff size={18}/> : <Mic size={18}/>}</button><button type="submit" className="send-action" disabled={!input.trim() || busy}><Send size={17}/></button></div>
        </form>
        <div className="composer-bottom"><div><button onClick={() => setVoiceEnabled(v => !v)}>{voiceEnabled ? <Volume2 size={13}/> : <VolumeX size={13}/>} Voz {voiceEnabled ? "ativa" : "silenciada"}</button><span className="dot-separator"/> <span>{status}</span></div><button className={wakeEnabled ? "wake-active" : ""} onClick={() => listening && wakeEnabled ? stopListening() : startListening(true)}><AudioLines size={13}/> {wakeEnabled ? "BRUCE ouvindo" : "Ativar palavra BRUCE"}</button></div>
      </div>
      <footer className="app-footer"><span>BRUCE PESSOAL · IA INDEPENDENTE</span><span>Verifique ações importantes antes de confirmar.</span></footer>
    </main>

    {settingsOpen && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setSettingsOpen(false); }}><section className="settings-panel"><div className="panel-heading"><div><small>CONFIGURAÇÃO DO SISTEMA</small><h2>Conexão privada</h2></div><button className="ghost icon-only" onClick={() => setSettingsOpen(false)}><X size={18}/></button></div><p className="panel-copy">Conecte sua própria API. A chave do provedor de IA permanece no servidor; aqui entra apenas o token privado do dispositivo.</p><label>ENDEREÇO HTTPS DA API<input value={draftUrl} onChange={e => setDraftUrl(e.target.value)} placeholder="https://sua-api.com"/></label><label>TOKEN PRIVADO DO BRUCE<input type="password" value={draftToken} onChange={e => setDraftToken(e.target.value)} placeholder="Token do dispositivo"/></label><div className="security-callout"><ShieldCheck size={17}/><span>Não coloque sua chave de provedor aqui. Use somente o token de acesso do BRUCE.</span></div><div className="panel-actions"><button className="button-muted" onClick={() => setSettingsOpen(false)}>Cancelar</button><button className="button-primary" onClick={() => void saveConnection()}><Check size={15}/> Salvar conexão</button></div><button className="text-danger" onClick={() => { localStorage.removeItem(API_URL_KEY); sessionStorage.removeItem(API_TOKEN_KEY); setApiUrl(""); setToken(""); setDraftUrl(""); setDraftToken(""); setConnected(false); setSettingsOpen(false); }}>Desconectar e limpar credenciais deste navegador</button></section></div>}

    {memoryOpen && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setMemoryOpen(false); }}><section className="settings-panel memory-panel"><div className="panel-heading"><div><small>CONTEXTO PESSOAL</small><h2>Memória do BRUCE</h2></div><button className="ghost icon-only" onClick={() => setMemoryOpen(false)}><X size={18}/></button></div><p className="panel-copy">Informações salvas aqui podem ser usadas como contexto nas conversas. Você controla o que fica armazenado.</p><div className="memory-form"><select value={memoryCategory} onChange={e => setMemoryCategory(e.target.value)}><option>preferência</option><option>rotina</option><option>objetivo</option><option>projeto</option><option>pessoal</option></select><textarea value={memoryDraft} onChange={e => setMemoryDraft(e.target.value)} placeholder="Ex.: Prefiro respostas diretas e instruções práticas…"/><button className="button-primary" onClick={() => void saveMemory()} disabled={!memoryDraft.trim()}><Plus size={15}/> Salvar memória</button></div><div className="memory-list">{memories.map(m => <article key={m.id}><div><small>{m.category.toUpperCase()}</small><p>{m.content}</p></div><button className="ghost icon-only" title="Apagar memória" onClick={() => void deleteMemory(m.id)}><Trash2 size={15}/></button></article>)}{memories.length === 0 && <div className="empty-memory">Nenhuma memória salva ainda.</div>}</div></section></div>}
  </div>;
}
