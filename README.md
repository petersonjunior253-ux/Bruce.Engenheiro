# BRUCE — Assistente pessoal

BRUCE é um projeto de assistente pessoal próprio, com cliente Android nativo, API privada e inferência conectável a modelos compatíveis com OpenAI. O objetivo é evoluir para uma experiência de voz contínua, memória pessoal controlável e automações Android com autorização explícita.

## Estado real do projeto

| Camada | Implementado | Pendente / precisa de validação |
|---|---|---|
| Android | Chat nativo, API privada, Vosk pt-BR offline, serviço em primeiro plano, ponte de comandos, leitor de notificações, acessibilidade para controles de tela e ferramentas básicas de arquivos | Ativar permissões no Samsung e testar microfone, acessibilidade, arquivos e notificações fisicamente |
| API | FastAPI hospedada no Vercel, autenticação Bearer, memória SQLite persistida em Blob privado, histórico, memória, fila de comandos, status de execução e voz neural Edge TTS | Configurar endpoint do modelo de IA acessível pela nuvem; evoluir armazenamento para Postgres antes de multiusuário |
| IA | Tool calling compatível com servidores OpenAI-compatible, ferramentas reais Android, Ollama local para execução local | A hospedagem ainda não tem endpoint de modelo configurado; a API responde health, mas chat exige um modelo alcançável |
| Voz | Palavra de ativação offline Vosk no Android; TTS neural pt-BR via API quando conectado; fallback para TTS Android | A qualidade neural e o reconhecimento offline precisam de teste real no Samsung |
| Web | Interface neural minimalista, conversa, voz, configuração da API e confirmação de ações do dispositivo | Teste final no navegador e configuração do token pelo proprietário |

**API hospedada:** https://bruce-personal-api-petersonjunior253-8756s-projects.vercel.app  
**Interface web:** https://bruce-preview-six.vercel.app

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
