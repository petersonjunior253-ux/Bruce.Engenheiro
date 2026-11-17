# BRUCE architecture

## Product principle

BRUCE is the personalized interface and device companion. ChatGPT remains the intended intelligence experience through a secure model-provider connection; BRUCE does not claim to recreate or enlarge a proprietary neural model.

## Runtime

1. Local wake-word detector runs on the device.
2. After detecting BRUCE, the native companion opens the assistant experience or starts an explicitly authorized capture session.
3. Speech recognition transcribes the user's command.
4. The client sends text to the authenticated BRUCE API.
5. API retrieves conversation history and saved memory, then calls the configured model provider.
6. The answer returns to the client for display and text-to-speech.

## Security boundaries

- Model provider credentials stay on the server.
- Device API token is separate from provider key.
- No arbitrary shell execution from model output.
- Sensitive actions require user confirmation.
- Wake-word detection is local; raw microphone audio is not uploaded by the wake listener.
- Public deployment requires TLS, rate limiting, abuse controls, secret rotation and a production database.

## Context

Long context is limited by the chosen model's actual context window. BRUCE stores conversations and explicit memories, then selects a bounded recent window. Future retrieval-augmented memory can search older conversation segments. Storage does not itself expand a model's context capacity or intelligence.
