import { useEffect, useRef, useState } from "react";
import { AudioLines, Command, Mic, MicOff, Send, Settings2, Volume2, VolumeX, Wifi, WifiOff } from "lucide-react";

type Message = { role: "assistant" | "user"; text: string };
type SpeechRecognitionResult = { 0: { transcript: string }; isFinal: boolean };
type SpeechRecognitionEvent = { resultIndex: number; results: ArrayLike<SpeechRecognitionResult> };
type SpeechRecognitionLike = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};
type SpeechWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};

const welcome: Message = {
  role: "assistant",
  text: "Olá. Sou o BRUCE, sua interface pessoal de assistência. Posso conversar por texto ou voz. A conexão com o modelo de inteligência será configurada na próxima etapa.",
};

export default function App() {
  const [messages, setMessages] = useState<Message[]>([welcome]);
  const [input, setInput] = useState("");
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [status, setStatus] = useState("Interface local pronta");
  const [wakeEnabled, setWakeEnabled] = useState(false);
  const recognition = useRef<SpeechRecognitionLike | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => () => {
    recognition.current?.stop();
    window.speechSynthesis?.cancel();
  }, []);

  const speak = (text: string) => {
    if (!voiceEnabled || !("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "pt-BR";
    utterance.rate = 1;
    utterance.onstart = () => setSpeaking(true);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  const sendMessage = (raw: string) => {
    const text = raw.trim();
    if (!text) return;
    setMessages((current) => [...current, { role: "user", text }]);
    setInput("");
    const response = "Recebi sua mensagem. Esta primeira versão já oferece a interface e os controles de voz. Na próxima etapa, conectaremos com segurança o mecanismo de inteligência do ChatGPT, sem expor credenciais no navegador.";
    window.setTimeout(() => {
      setMessages((current) => [...current, { role: "assistant", text: response }]);
      speak(response);
    }, 350);
  };

  const startListening = () => {
    const SpeechRecognition = (window as SpeechWindow).SpeechRecognition || (window as SpeechWindow).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setStatus("Reconhecimento de voz indisponível neste navegador");
      return;
    }
    if (recognition.current) recognition.current.stop();
    const engine = new SpeechRecognition();
    engine.lang = "pt-BR";
    engine.continuous = false;
    engine.interimResults = false;
    engine.onresult = (event) => {
      const transcript = Array.from(event.results).slice(event.resultIndex).map((result) => result[0].transcript).join(" ");
      if (transcript) sendMessage(transcript);
    };
    engine.onerror = (event) => {
      setStatus("Microfone: " + event.error);
      setListening(false);
    };
    engine.onend = () => {
      setListening(false);
      setStatus("Interface local pronta");
    };
    recognition.current = engine;
    try {
      engine.start();
      setListening(true);
      setStatus("Ouvindo você…");
    } catch {
      setStatus("Não foi possível iniciar o microfone");
      setListening(false);
    }
  };

  const stopListening = () => {
    recognition.current?.stop();
    setListening(false);
    setStatus("Microfone pausado");
  };

  const toggleWake = () => {
    setWakeEnabled((value) => !value);
    setStatus(wakeEnabled
      ? "Ativação contínua desativada"
      : "Modo de demonstração: a página precisa permanecer aberta; não é uma wake word em segundo plano");
  };

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark"><AudioLines size={19} /></div><div><strong>BRUCE</strong><span>PERSONAL AI</span></div></div>
        <div className="top-status"><span className="status-dot" /> SISTEMA PRONTO</div>
        <button className="icon-button" aria-label="Configurações" title="Configurações"><Settings2 size={19} /></button>
      </header>

      <section className="hero">
        <div className={`core-wrap ${listening ? "is-listening" : ""} ${speaking ? "is-speaking" : ""}`}>
          <div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orbit orbit-three" />
          <div className="core-glow" />
          <div className="core"><div className="core-inner"><AudioLines size={42} strokeWidth={1.25} /></div></div>
          <span className="core-label">{listening ? "OUVINDO" : speaking ? "RESPONDENDO" : "BRUCE ONLINE"}</span>
        </div>
        <p className="eyebrow">SEU ASSISTENTE PESSOAL</p>
        <h1>Como posso ajudar?</h1>
        <p className="subtitle">Converse comigo. Estou aqui para transformar suas ideias em ação.</p>
        <div className="voice-actions">
          <button className={`primary-voice ${listening ? "active" : ""}`} onClick={listening ? stopListening : startListening}>
            {listening ? <MicOff size={19} /> : <Mic size={19} />}{listening ? "Parar de ouvir" : "Falar com BRUCE"}
          </button>
          <button className={`secondary-voice ${wakeEnabled ? "enabled" : ""}`} onClick={toggleWake}>
            <AudioLines size={17} /> {wakeEnabled ? "Modo demonstração ligado" : "Ativação BRUCE"}
          </button>
        </div>
        <p className="microphone-note"><Wifi size={13} /> {status}</p>
      </section>

      <section className="conversation">
        <div className="conversation-head"><div><span className="eyebrow">CONVERSA</span><h2>Sua sessão</h2></div><span className="local-tag"><span className="status-dot" /> Interface local</span></div>
        <div className="messages">
          {messages.map((message, index) => <article className={`message ${message.role}`} key={index}>
            <div className="avatar">{message.role === "assistant" ? <AudioLines size={16} /> : "Você"}</div>
            <div className="message-body"><span>{message.role === "assistant" ? "BRUCE" : "VOCÊ"}</span><p>{message.text}</p></div>
          </article>)}
          <div ref={bottomRef} />
        </div>
        <form className="composer" onSubmit={(event) => { event.preventDefault(); sendMessage(input); }}>
          <input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Escreva sua mensagem para o BRUCE…" aria-label="Mensagem" />
          <button className="send-button" type="submit" disabled={!input.trim()} aria-label="Enviar"><Send size={18} /></button>
        </form>
        <div className="composer-foot"><span><Command size={12} /> Enter para enviar</span><button onClick={() => { setVoiceEnabled((value) => !value); if (voiceEnabled) window.speechSynthesis?.cancel(); }}><span>{voiceEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}</span> Voz {voiceEnabled ? "ativada" : "desativada"}</button></div>
      </section>

      <footer><span>BRUCE · PERSONAL INTELLIGENCE SYSTEM</span><span>PROTÓTIPO DE VOZ · V0.1</span></footer>
    </main>
  );
}