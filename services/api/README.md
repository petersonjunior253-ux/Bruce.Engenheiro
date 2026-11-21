# BRUCE API

API privada do assistente BRUCE, construída em FastAPI. O motor principal é Google Gemini via API oficial, com suporte alternativo a Anthropic e servidores OpenAI-compatible, como Ollama. A chave do modelo permanece exclusivamente no servidor.

## API hospedada

- Endpoint: `https://bruce-personal-api-petersonjunior253-8756s-projects.vercel.app`
- Runtime: FastAPI no Vercel Functions.
- Autenticação: Bearer token privado.
- Memória: SQLite persistido em armazenamento privado Vercel Blob (snapshot por requisição; adequada ao uso pessoal inicial, ainda não substitui PostgreSQL transacional em cenário multiusuário/concorrrente).
- Voz neural: rota `POST /v1/voice` com Edge TTS pt-BR; depende de conectividade externa e pode recorrer à voz local do Android.
- Modelo principal: Google Gemini pela API oficial (`gemini-3.8-flash`). A Vercel precisa ter `BRUCE_GEMINI_API_KEY` configurada como segredo. O endereço local `127.0.0.1` não funciona a partir da API hospedada.

## Execução local

Na pasta `services/api`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.2
```

Para usar Gemini, configure `BRUCE_API_KEY`, `BRUCE_MODEL_PROVIDER=gemini`, `BRUCE_MODEL_NAME=gemini-3.8-flash` e `BRUCE_GEMINI_API_KEY` no ambiente do servidor. Para usar Ollama local, configure `BRUCE_MODEL_PROVIDER=openai-compatible`, `BRUCE_MODEL_BASE_URL=http://127.0.0.1:11434/v1`, `BRUCE_MODEL_NAME=llama3.2` e `BRUCE_API_KEY`.

Rotas privadas exigem `Authorization: Bearer SEU_TOKEN`.

## Inferência própria

- Ollama local: `BRUCE_MODEL_BASE_URL=http://127.0.0.1:11434/v1`, `BRUCE_MODEL_NAME=llama3.2`; chave vazia.
- Gemini: `BRUCE_MODEL_PROVIDER=gemini`, `BRUCE_GEMINI_API_KEY` e `BRUCE_MODEL_NAME=gemini-3.8-flash`.
- Anthropic: `BRUCE_MODEL_PROVIDER=anthropic`, `BRUCE_ANTHROPIC_API_KEY` e o nome do modelo configurado.
- Outro servidor compatível: `BRUCE_MODEL_PROVIDER=openai-compatible`, URL base, nome exato do modelo e chave apenas no servidor.
- Nunca coloque chave de provedor no Android, navegador, repositório ou logs.
- Para conectar Ollama local à API hospedada, será necessário expor o endpoint com um túnel privado seguro ou hospedar API e modelo na mesma rede.

## Rotas

| Método | Rota | Uso |
|---|---|---|
| GET | `/health` | Estado da API, modelo e armazenamento privado |
| POST | `/v1/chat` | Conversa e despacho de ferramentas |
| POST | `/v1/voice` | Geração de voz neural pt-BR |
| POST | `/v1/device/register` | Registrar Android |
| GET | `/v1/device/commands` | Buscar comandos pendentes |
| GET | `/v1/device/commands/{id}` | Consultar resultado de ação |
| POST | `/v1/device/commands/{id}/result` | Confirmar resultado do Android |
| GET | `/v1/device/status` | Estado dos dispositivos |
| GET/POST/DELETE | `/v1/memories` | Memória pessoal |
| GET/POST/PATCH | `/v1/tasks` | Tarefas e rotina persistentes |
| GET/DELETE | `/v1/conversations` | Histórico de conversas |
| GET | `/v1/capabilities` | Ferramentas disponíveis |

## Ferramentas pessoais

- `create_task`, `list_tasks` e `complete_task`: registrar, consultar e concluir tarefas de rotina, estudos, treino e metas.
- `save_memory`, `list_memories` e `delete_memory`: memória pessoal persistente, com gravação somente de informações não sensíveis e autorizadas.

## Ferramentas Android

- Abrir aplicativos e listar aplicativos instalados.
- Ler texto visível da tela, tocar em controles por texto, digitar em campo focado, rolar e voltar/início (requer acessibilidade).
- Listar e ler arquivos de texto e criar arquivos novos sem sobrescrever (requer acesso a todos os arquivos).
- Ler notificações ativas (requer Notification Access).
- Criar notificação local, abrir seletor de arquivos, criar evento no calendário via tela de confirmação, configurar alarme e abrir configurações.
- Ações que alteram dados abrem confirmação nativa quando disponível. O BRUCE não deve alegar sucesso sem confirmação do dispositivo.

## Permissões Android

O usuário habilita no próprio Samsung:
1. Microfone e notificações para o aplicativo.
2. Acessibilidade: BRUCE Device Control.
3. Acesso a notificações: BRUCE Notification Access.
4. Acesso a todos os arquivos, se quiser gestão de arquivos pelo BRUCE.

O Android não permite conceder essas permissões silenciosamente por uma API externa. O app abre as telas corretas; o proprietário precisa confirmar.

## Limites conhecidos

- O Gradle baixa e inclui o modelo Vosk pequeno de português no APK durante a compilação; o serviço de escuta ainda precisa de validação física no Samsung.
- Voz neural usa Edge TTS online; offline, o app recorre ao mecanismo TTS do Android.
- A hospedagem precisa receber `BRUCE_GEMINI_API_KEY` como variável secreta para habilitar a conversa Gemini.
- A persistência Blob+SQLite é para uso pessoal inicial; antes de multiusuário ou alto volume, migrar para Postgres e autenticação por dispositivo.
- Não existe controle irrestrito de todo o Android: algumas telas, apps bancários e áreas protegidas bloqueiam automação por segurança do sistema.
