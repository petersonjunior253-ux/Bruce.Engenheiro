# BRUCE — Assistente pessoal independente

BRUCE é um assistente pessoal próprio, com aplicativo Android, serviço de ativação por voz e API/backend controlados pelo proprietário.

## Inteligência independente

BRUCE **não utiliza a API da OpenAI nem a API do ChatGPT por padrão**. A API do BRUCE é o backend deste projeto. Ela se conecta a um motor de IA configurado pelo proprietário.

O primeiro motor recomendado é **Ollama**, executando um modelo aberto no computador/servidor que hospeda a API. A API também pode apontar para outros servidores de inferência compatíveis com o formato de chat. O protocolo compatível é apenas o formato de comunicação; não significa que o serviço seja da OpenAI.

## Componentes

- `app/`: aplicativo Android nativo com detecção local da palavra BRUCE.
- `services/api/`: API própria, autenticação do dispositivo, histórico e memória SQLite.
- `src/`: interface web/PWA.
- `clients/`: clientes e protótipos adicionais.
- `.github/workflows/`: compilação automatizada do APK.

## Como a inteligência funciona

1. O aplicativo reconhece a palavra BRUCE localmente.
2. A fala do usuário é transcrita.
3. O app envia o texto para a API privada BRUCE por HTTPS.
4. A API carrega histórico e memórias salvas.
5. A API consulta o modelo configurado no servidor (Ollama por padrão).
6. A resposta volta ao app e é falada em português.

A capacidade de raciocínio depende do modelo selecionado e do hardware disponível. Uma API própria não cria, sozinha, um modelo neural: ela controla autenticação, memória, contexto, ferramentas e conexão com o motor de IA.

## Configuração inicial do backend

Veja [services/api/README.md](services/api/README.md) e copie `.env.example` para `.env`. Defina uma chave longa para `BRUCE_API_KEY`, escolha um modelo instalado no Ollama e mantenha qualquer credencial exclusivamente no servidor.

**Nunca coloque chaves de provedor, tokens ou senhas no APK, no frontend ou no Git.**

## Estado de desenvolvimento

O projeto possui uma base Android com wake-word local e uma API com histórico e memória persistentes. A integração ponta a ponta com um modelo próprio ainda depende de hospedar a API, disponibilizar o motor de IA e configurar o app com URL HTTPS e token de dispositivo. O APK precisa ser validado no aparelho Samsung real.
