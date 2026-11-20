# BRUCE — Assistente pessoal

BRUCE é um assistente pessoal com interface conversacional, API privada, integração principal com Google Gemini e cliente Android nativo para ativação offline por voz e automações autorizadas.

## Estado real do projeto

| Camada | Implementado | Pendente / precisa de validação |
|---|---|---|
| Android | Chat nativo, API privada, Vosk pt-BR offline, serviço em primeiro plano, ponte de comandos, leitor de notificações, acessibilidade para controles de tela e ferramentas básicas de arquivos | Ativar permissões no Samsung e testar microfone, acessibilidade, arquivos e notificações fisicamente |
| API | FastAPI hospedada no Vercel, autenticação Bearer, memória SQLite persistida em Blob privado, histórico, fila de comandos, voz neural Edge TTS e suporte ao Gemini com function calling | Configurar `BRUCE_GEMINI_API_KEY` como segredo na Vercel; evoluir armazenamento para Postgres antes de multiusuário |
| IA | Google Gemini via API oficial, function calling e ferramentas Android; alternativas Anthropic e OpenAI-compatible/Ollama | A chave Gemini ainda precisa ser configurada no servidor para habilitar conversa livre |
| Voz | Palavra de ativação offline Vosk no Android; TTS neural pt-BR via API quando conectado; fallback para TTS Android | A qualidade neural e o reconhecimento offline precisam de teste real no Samsung |
| Web | Painel BRUCE WAYNE com navegação, conversa, entrada por voz, ações rápidas e status de conexão | Validar no preview; reconhecimento de voz do navegador é somente enquanto a página está ativa |

**API hospedada:** https://bruce-personal-api-petersonjunior253-8756s-projects.vercel.app  
**Interface web anterior:** https://bruce-preview-six.vercel.app
**Nova interface (preview):** será disponibilizada pelo projeto Vercel `bruce-personal-ui` após o build da branch

O armazenamento persistente usa um Blob privado na região de São Paulo e mantém um snapshot SQLite para o uso pessoal inicial. Isso evita perder memória a cada execução serverless, mas ainda não é uma arquitetura transacional multiusuário.

## Princípios do BRUCE

- Independente da API da OpenAI/ChatGPT. O backend pode usar Ollama local ou qualquer servidor de inferência compatível.
- Segredos ficam no servidor; nunca inserir chave de provedor no APK, HTML ou Git.
- Memória visível, editável e apagável pelo proprietário.
- Autonomia gradual: ações reversíveis e locais podem ser automatizadas após configuração; ações sensíveis, externas, financeiras ou irreversíveis exigem aprovação.
- Microfone e escuta em segundo plano sempre visíveis e controláveis pelo usuário, respeitando as restrições do Android.
- O assistente informa quando não tem acesso, ferramenta ou confirmação de uma ação.

## API local

Consulte [services/api/README.md](services/api/README.md).

Resumo:
1. Instale Python 3.11+.
2. Instale dependências: `pip install -r services/api/requirements.txt`.
3. Configure `BRUCE_API_KEY` e `BRUCE_GEMINI_API_KEY` como segredos no servidor.
4. Use `BRUCE_MODEL_PROVIDER=gemini` e `BRUCE_MODEL_NAME=gemini-3.8-flash`.
5. Para execução local alternativa, inicie Ollama e configure `BRUCE_MODEL_PROVIDER=openai-compatible`, `BRUCE_MODEL_BASE_URL` e `BRUCE_MODEL_NAME`.
6. Execute a API a partir de `services/api`: `uvicorn main:app --host 0.0.0.0 --port 8000`.

O endereço `127.0.0.1` só aponta para a própria máquina que executa a API. Se a API estiver na nuvem, não consegue alcançar automaticamente o Ollama instalado no PC; é necessário hospedar o modelo em uma rede/endereço alcançável ou manter API e modelo na mesma máquina.

## APK

Abra GitHub Actions, execute o workflow de build Android e baixe o artefato `BRUCE-Android-APK`.

## Segurança e limites

- Não comitar tokens, chaves, senhas, gravações, banco pessoal ou arquivos `.env`.
- A API atual usa um único token de dispositivo compartilhado; antes de abrir para internet, implementar tokens por dispositivo, rotação/revogação, rate limiting e TLS.
- SQLite é adequado para desenvolvimento/instância única; para escala multi-instância, migrar para PostgreSQL.
- O serviço de microfone não deve prometer escuta permanente após reinicialização: Android limita o início de serviços de microfone em segundo plano.
