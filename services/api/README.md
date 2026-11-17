# BRUCE API

FastAPI privada para chat, histórico e memória. Não depende automaticamente de ChatGPT nem de assinatura ChatGPT. Chama um endpoint de inferência compatível com `/v1/chat/completions`.

## Execução local

Na pasta `services/api`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.2
```

Configure no terminal (use um token aleatório e privado):

```powershell
$env:BRUCE_API_KEY = "COLOQUE_UM_TOKEN_LONGO_E_ALEATORIO"
$env:BRUCE_MODEL_BASE_URL = "http://127.0.0.1:11434/v1"
$env:BRUCE_MODEL_NAME = "llama3.2"
uvicorn main:app --host 0.0.0.0 --port 8000
```

Verifique `GET /health`. Rotas privadas exigem `Authorization: Bearer SEU_TOKEN`.

## Inferência própria

- Ollama local: `BRUCE_MODEL_BASE_URL=http://127.0.0.1:11434/v1`; `BRUCE_MODEL_NAME=llama3.2`; chave normalmente vazia.
- Outro servidor compatível: informe URL base e nome exato do modelo. Se exigir credencial, configure `BRUCE_MODEL_API_KEY` apenas no servidor.
- Nunca coloque chave de provedor no Android, navegador, repositório ou logs.

**Atenção:** `127.0.0.1` aponta para a própria máquina onde a API roda. Uma API hospedada na nuvem não alcança automaticamente o Ollama instalado no computador. API e modelo precisam estar na mesma máquina, numa rede privada alcançável, ou usar um endpoint de inferência hospedado.

## Rotas

| Método | Rota | Uso |
|---|---|---|
| GET | `/health` | Estado básico |
| POST | `/v1/chat` | Conversar com o modelo |
| GET | `/v1/conversations` | Listar conversas |
| GET | `/v1/conversations/{id}` | Ler mensagens |
| PATCH | `/v1/conversations/{id}` | Renomear conversa |
| DELETE | `/v1/conversations/{id}` | Apagar conversa |
| GET | `/v1/memories` | Listar memórias |
| POST | `/v1/memories` | Salvar memória |
| DELETE | `/v1/memories/{id}` | Apagar memória |
| GET | `/v1/capabilities` | Consultar capacidades declaradas |

## Segurança antes de publicar

A implementação atual usa um token Bearer compartilhado e SQLite. Antes de exposição pública, adicionar HTTPS, rate limiting, tokens individuais por dispositivo com revogação, limites de payload, auditoria sem conteúdo sensível, retenção configurável e testes de segurança. CORS não substitui autenticação.

## Evolução planejada

1. Testes automatizados de autenticação, chat, histórico, memória e falhas do provedor.
2. Migrações e PostgreSQL para produção multi-instância.
3. Streaming de tokens e cancelamento.
4. Ferramentas com schemas, allowlist, confirmação e auditoria.
5. STT/TTS streaming desacoplados do modelo de linguagem.
6. Gestão de dispositivos, notificações e ações Android com permissões nativas.
