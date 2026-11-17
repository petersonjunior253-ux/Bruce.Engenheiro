# BRUCE — Assistente pessoal Android

Projeto nativo Android do BRUCE, com interface neural escura e foco em interação por voz.

## O que já está no código
- Interface Android nativa em Jetpack Compose, com núcleo neural animado.
- Reconhecimento offline da palavra de ativação **BRUCE** usando Vosk em português.
- Serviço de microfone em primeiro plano, com notificação persistente e ação para desativar.
- Captura de uma frase falada após a palavra de ativação.
- Respostas faladas locais para comandos básicos (hora, data e identidade).
- Permissões explícitas de microfone, notificações, serviço de microfone e internet.
- Workflow GitHub Actions para compilar e publicar o APK de teste como artefato.

## Gerar APK
Abra a aba **Actions**, escolha **Build BRUCE APK**, abra a execução concluída e baixe o artefato **BRUCE-Android-APK**.

## Limites conhecidos desta versão
Esta ainda é uma versão de engenharia. A detecção da palavra e o fluxo de captura de fala estão no código, mas precisam ser testados no aparelho real (incluindo Samsung/Android 14). Não declare o BRUCE como assistente completo até concluir esses testes.

A conversa com um modelo de IA na nuvem, memória pessoal sincronizada, chamadas a ferramentas, automações, notificações inteligentes e diálogo contínuo ainda não estão conectados. A assinatura do ChatGPT não fornece automaticamente acesso à API para um aplicativo externo; uma integração de IA exige um backend seguro com credencial de API, sem embutir segredos no APK nem no repositório.

## Android 14 e execução em segundo plano
O microfone é mantido por um serviço em primeiro plano, visível por uma notificação. O serviço deve ser iniciado quando o aplicativo estiver visível e as permissões forem concedidas. As regras do Android 14 restringem iniciar serviços de microfone a partir do segundo plano; por isso, não se promete inicialização automática após reinicialização do telefone. O usuário pode parar a escuta pela ação na notificação.

## Segurança
Não comitar chaves de API, tokens, senhas, dados pessoais ou gravações. Nenhuma conversa de voz é enviada a um servidor nesta versão; reconhecimento de fala e respostas básicas são locais.
