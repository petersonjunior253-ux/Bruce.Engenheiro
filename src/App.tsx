import { useEffect, useRef, useState } from "react";
import { AudioLines, Command, Mic, MicOff, Send, Settings2, Volume2, VolumeX, Wifi } from "lucide-react";

type Message = { role: "assistant" | "user"; text: string };
type SpeechRecognitionResult = { 0: { transcript: string }; isFinal: boolean };
type SpeechRecognitionEvent = { resultIndex: number; results: ArrayLike<SpeechRecognitionResult> };
type SpeechRecognitionLike = {
  lang: string; continuous: boolean; interimResults: boolean;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null; start: () => void; stop: () => void;
};
type SpeechWindow = Window & { SpeechRecognition?: new () => SpeechRecognitionLike; webkitSpeechRecognition?: new () => SpeechRecognitionLike };

const welcome: Message = { role: "assistant", text: "Olá. Sou BRUCE, sua interface pessoal. Configure a conexão segura com sua API nas configurações para conversar com o modelo de inteligência." };

export default function App() {
  const [messages, setMessages] = useState<Message[]>([welcome]);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [status, setStatus] = useState("Interface pronta · configure a API");
  const [busy, setBusy] = useState(false);
  const [apiUrl, setApiUrl] = useState(localStorage.getItem("bruce_api_url") || "");
  const [apiToken, setApiToken] = useState(localStorage.getItem("bruce_api_token") || "");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const recognition = useRef<SpeechRecognitionLike | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => () => { recognition.current?.stop(); window.speechSynthesis?.cancel(); }, []);

  const configure = () => {
    const url = window.prompt("URL HTTPS da API BRUCE (ex.: https://api.seudominio.com)", apiUrl);
    if (url === null) return;
    const token = window.prompt("Token de acesso BRUCE (não é a chave do provedor de IA)", apiToken);
    if (token === null) return;
    setApiUrl(url.trim().replace(/\/$/, ""));
    setApiToken(token.trim());
    localStorage.setItem("bruce_api_url", url.trim().replace(/\/$/, ""));
    localStorage.setItem("bruce_api_token", token.trim());
    setConversationId(null);
    setStatus("Configuração salva neste navegador");
  };

  const speak = (text: string) => {
    if (!voiceEnabled || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "pt-BR"; utterance.rate = 1;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const sendMessage = async (raw: string) => {
    const text = raw.trim();
    if (!text || busy) return;
    const next = [...messages, { role: "user" as const, text }];
    setMessages(next); setInput("");
    if (!apiUrl || !apiToken) {
      const warning = "Ainda não estou conectado ao modelo. Abra as configurações e informe a URL HTTPS da API BRUCE e o token de dispositivo. A chave do provedor de IA deve ficar somente no servidor.";
      setMessages((current) => [...current, { role: "assistant", text: warning }]);
      speak(warning); setStatus("API não configurada"); return;
    }
    setBusy(true); setStatus("Consultando o núcleo de inteligência…");
    try {
      const response = await fetch(apiUrl + "/v1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: "Bearer " + apiToken },
        body: JSON.stringify({
          conversation_id: conversationId,
          messages: [{ role: "user", content: text }]
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Falha na API (" + response.status + ")");
      if (data.conversation_id) setConversationId(data.conversation_id);
      const answer = String(data.message || "O modelo retornou uma resposta vazia.");
      setMessages((current) => [...current, { role: "assistant", text: answer }]);
      speak(answer); setStatus("Conectado · " + (data.model || "modelo ativo"));
    } catch (error) {
      const reason = error instanceof Error ? error.message : "Erro desconhecido";
      setMessages((current) => [...current, { role: "assistant", text: "Não consegui acessar a inteligência: " + reason }]);
      setStatus("Falha de conexão");
    } finally { setBusy(false); }
  };

  const startListening = () => {
    const SpeechRecognition = (window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition;
    if (!SpeechRecognition) { setStatus("Reconhecimento de voz indisponível neste navegador"); return; }
    recognition.current?.stop();
    const engine = new SpeechRecognition();
    engine.lang = "pt-BR"; engine.continuous = false; engine.interimResults = false;
    engine.onresult = (event) => {
      const transcript = Array.from(event.results).slice(event.resultIndex).map((result) => result[0].transcript).join(" ");
      if (transcript) void sendMessage(transcript);
    };
    engine.onerror = (event) => { setStatus("Microfone: " + event.error); setListening(false); };
    engine.onend = () => setListening(false);
    recognition.current = engine;
    try { engine.start(); setListening(true); setStatus("Ouvindo você…"); }
    catch { setStatus("Não foi possível iniciar o microfone"); setListening(false); }
  };
  const stopListening = () => { recognition.current?.stop(); setListening(false); setStatus("Microfone pausado"); };

  return <main className="shell">
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><AudioLines size={19} /></div><div><strong>BRUCE</strong><span>PERSONAL AI</span></div></div>
      <div className="top-status"><span className="status-dot" /> SISTEMA PRONTO</div>
      <button className="icon-button" aria-label="Configurar conexão" title="Configurar conexão" onClick={configure}><Settings2 size={19} /></button>
    </header>
    <section className="hero">
      <div className={`core-wrap ${listening ? "is-listening" : ""} ${speaking ? "is-speaking" : ""}`}>
        <div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" /><div className="core-glow" />
        <div className="core"><div className="core-inner"><AudioLines size={42} strokeWidth={1.25} /></div></div>
        <span className="core-label">{listening ? "OUVINDO" : speaking ? "RESPONDENDO" : busy ? "PROCESSANDO" : "BRUCE ONLINE"}</span>
      </div>
      <p className="eyebrow">SEU ASSISTENTE PESSOAL</p><h1>Como posso ajudar?</h1>
      <p className="subtitle">Converse comigo. Estou aqui para transformar suas ideias em ação.</p>
      <div className="voice-actions">
        <button className={`primary-voice ${listening ? "active" : ""}`} onClick={listening ? stopListening : startListening}>
          {listening ? <MicOff size={19} /> : <Mic size={19} />}{listening ? "Parar de ouvir" : "Falar com BRUCE"}
        </button>
        <button className="secondary-voice" onClick={configure}><Settings2 size={17} /> Configurar inteligência</button>
      </div>
      <p className="microphone-note"><Wifi size={13} /> {status}</p>
    </section>
    <section className="conversation">
      <div className="conversation-head"><div><span className="eyebrow">CONVERSA</span><h2>Sua sessão</h2></div><span className="local-tag"><span className="status-dot" /> {apiUrl ? "API configurada" : "Aguardando API"}</span></div>
      <div className="messages">{messages.map((message, index) => <article className={`message ${message.role}`} key={index}>
        <div className="avatar">{message.role === "assistant" ? <AudioLines size={16} /> : "Você"}</div>
        <div className="message-body"><span>{message.role === "assistant" ? "BRUCE" : "VOCÊ"}</span><p>{message.text}</p></div>
      </article>)}<div ref={bottomRef} /></div>
      <form className="composer" onSubmit={(event) => { event.preventDefault(); void sendMessage(input); }}>
        <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Escreva sua mensagem para o BRUCE…" aria-label="Mensagem" />
        <button className="send-button" type="submit" disabled={!input.trim() || busy} aria-label="Enviar"><Send size={18} /></button>
      </form>
      <div className="composer-foot"><span><Command size={12} /> Enter para enviar</span><button onClick={() => { setVoiceEnabled((value) => !value); if (voiceEnabled) window.speechSynthesis?.cancel(); }}><span>{voiceEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}</span> Voz {voiceEnabled ? "ativada" : "desativada"}</button></div>
    </section>
    <footer><span>BRUCE · PERSONAL INTELLIGENCE SYSTEM</span><span>VOICE + AI · V0.2</span></footer>
  </main>;
}
