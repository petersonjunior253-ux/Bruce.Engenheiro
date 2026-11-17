# Arquitetura BRUCE — IA independente

## Princípio
BRUCE é um produto independente. A API BRUCE é o backend e o proprietário escolhe o motor neural. A configuração inicial aponta para Ollama local. Não há dependência obrigatória da OpenAI ou da API do ChatGPT.

## Fluxo
1. Detector de palavra-chave executa localmente no Android.
2. O app captura a fala após a ativação.
3. A fala é convertida em texto no dispositivo/serviço Android.
4. O app envia texto para a API BRUCE autenticada por HTTPS.
5. A API carrega histórico e memórias do SQLite.
6. A API consulta o modelo configurado (Ollama por padrão).
7. A resposta retorna ao app para fala em português.

## Responsabilidades
- App Android: voz, interface, permissões, notificações e ações no dispositivo.
- API BRUCE: autenticação, histórico, memória, contexto, roteamento de modelo e ferramentas futuras.
- Motor de IA: geração e raciocínio, conforme o modelo escolhido e os recursos de hardware.

## Segurança
- Chave do motor de IA somente no servidor.
- Token do dispositivo separado da chave do motor.
- HTTPS em produção.
- Ações sensíveis, externas, financeiras ou irreversíveis exigem confirmação.
- Nenhuma saída do modelo pode ser executada como shell arbitrário.
- Detecção da palavra-chave é local; o áudio do detector não é enviado à API.

## Limites
A memória persistente recupera contexto, mas não amplia o limite nativo de contexto do modelo. A qualidade e velocidade dependem do modelo, quantização, RAM, GPU/CPU e hardware do host.
