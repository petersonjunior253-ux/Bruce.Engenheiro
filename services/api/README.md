# API própria do BRUCE

Esta API é o backend do assistente. Ela **não exige a API do ChatGPT nem uma chave da OpenAI**.

## Motor padrão: Ollama

Instale Ollama no computador/servidor que executará o motor de IA e baixe um modelo adequado à memória e ao desempenho do hardware. Por exemplo:

```bash
ollama pull llama3.2
ollama serve
```

A URL padrão configurada é `http://127.0.0.1:11434/v1`. O processo da API precisa conseguir acessar esse endereço. Se a API estiver em um container, ajuste a URL para o endereço de rede do host Ollama; `127.0.0.1` dentro do container aponta para o próprio container.

## Instalação

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
```

Edite `.env`:
- `BRUCE_API_KEY`: segredo longo para autenticar o app BRUCE.
- `BRUCE_MODEL_BASE_URL`: endpoint do motor de IA.
- `BRUCE_MODEL_NAME`: nome exato de um modelo disponível no motor.
- `BRUCE_MODEL_API_KEY`: opcional; deixe vazio para Ollama local sem autenticação.

Inicie em desenvolvimento:

```bash
uvicorn main:app --host 0.0.0.0 --port 8787
```

Não exponha a API diretamente à internet sem HTTPS, autenticação forte, rate limiting e firewall. Para produção, use uma URL HTTPS e mantenha a chave do motor apenas no servidor.

## Endpoints

- `GET /health` — estado não autenticado, sem revelar segredos.
- `GET /v1/status` — configuração do motor (autenticado).
- `POST /v1/chat` — conversa com histórico persistente.
- `GET /v1/conversations` e `GET /v1/conversations/{id}`.
- `POST /v1/memories`, `GET /v1/memories`, `DELETE /v1/memories/{id}`.

Todas as rotas `/v1` exigem `Authorization: Bearer <BRUCE_API_KEY>`.

## Sobre compatibilidade

O gateway usa o formato de mensagens `/chat/completions` para conversar com motores que implementam esse formato. Isso é somente compatibilidade de protocolo; o modelo padrão é Ollama, não um modelo ChatGPT.
