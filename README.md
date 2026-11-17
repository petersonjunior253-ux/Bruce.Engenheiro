# BRUCE — Assistente pessoal

BRUCE é um projeto de assistente pessoal próprio, com cliente Android nativo, API privada e inferência conectável a modelos compatíveis com OpenAI. O objetivo é evoluir para uma experiência de voz contínua, memória pessoal controlável e automações Android com autorização explícita.

## Estado real do projeto

| Camada | Implementado no repositório | Ainda precisa ser feito/testado |
|---|---|---|
| Android | App Kotlin/Compose com chat nativo, conexão HTTPS privada, serviço foreground, wake word Vosk offline em português e TTS do Android | Teste em Samsung/Android 14, TTS neural próprio, ações Android e diálogo contínuo robusto |
| API | FastAPI, autenticação Bearer, SQLite, chat compatível com API OpenAI, histórico e memória persistente | Deploy HTTPS, gestão de dispositivos/usuários, limites, observabilidade e testes automatizados |
| IA | Adaptador de endpoint compatível; padrão local Ollama `http://127.0.0.1:11434/v1`, modelo `llama3.2` | Escolha/benchmark de modelo, roteamento, ferramentas e avaliação de qualidade |
| Voz | Reconhecimento de palavra-chave offline no Android e voz TTS do dispositivo | STT/TTS neural de alta qualidade, streaming, interrupção e conversa full-duplex |
| Automações | Serviço Android preparado para receber comandos de voz | Camada de ferramentas com permissões, confirmação e registro de execução |
| Web/PWA | Workspace React/Vite com histórico, chat, configurações, memória editável, reconhecimento de voz no navegador e palavra BRUCE enquanto a página está aberta | Conectar a API hospedada, testar em navegadores reais, notificações push e voz neural própria |

**Não considere uma capacidade pronta apenas porque existe uma tela ou endpoint.** A coluna de implementação é código presente; a segunda coluna é trabalho pendente. A interface web atual está publicada em https://bruce-preview-six.vercel.app.

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
3. Inicie Ollama e baixe um modelo: `ollama pull llama3.2`.
4. Configure `BRUCE_API_KEY` com um token longo e aleatório.
5. Execute a API a partir de `services/api`: `uvicorn main:app --host 0.0.0.0 --port 8000`.

O endereço `127.0.0.1` só aponta para a própria máquina que executa a API. Se a API estiver na nuvem, não consegue alcançar automaticamente o Ollama instalado no PC; é necessário hospedar o modelo em uma rede/endereço alcançável ou manter API e modelo na mesma máquina.

## APK

Abra GitHub Actions, execute o workflow de build Android e baixe o artefato `BRUCE-Android-APK`.

## Segurança e limites

- Não comitar tokens, chaves, senhas, gravações, banco pessoal ou arquivos `.env`.
- A API atual usa um único token de dispositivo compartilhado; antes de abrir para internet, implementar tokens por dispositivo, rotação/revogação, rate limiting e TLS.
- SQLite é adequado para desenvolvimento/instância única; para escala multi-instância, migrar para PostgreSQL.
- O serviço de microfone não deve prometer escuta permanente após reinicialização: Android limita o início de serviços de microfone em segundo plano.
