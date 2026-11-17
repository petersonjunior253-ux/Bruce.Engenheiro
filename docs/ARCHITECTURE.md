# BRUCE architecture

## Product principle

BRUCE is an independent personal assistant with its own API, orchestration layer, memory and device tools. It does **not** use the ChatGPT product or require the OpenAI API. The model backend is replaceable and may be a locally hosted Ollama model or another independently selected inference service.

“OpenAI-compatible” describes an HTTP request format supported by some model servers; it does not mean the OpenAI service is being used. Provider credentials, when needed, stay exclusively on the server.

## Shared experience: Android + Protocolo Bruce Wayne site

The Android application and the original Protocolo Bruce Wayne website are two clients of the same BRUCE intelligence:

- Android owns local wake-word detection, microphone capture, speech recognition, speech output and Android device tools.
- The website keeps its original interface, personal workspaces and browser experience.
- Both clients must use the same authenticated API, conversation identifiers and canonical memory store.
- The API performs model routing, context assembly, memory retrieval, tool selection, authorization and execution tracking.

The site must call the BRUCE API through an authenticated same-origin server-side proxy. The BRUCE API token must never be sent to browser JavaScript.

## Runtime

1. Android performs local detection of the wake word **BRUCE**. The raw wake-listener audio is not uploaded.
2. After activation, Android captures the user's command and transcribes it locally where possible.
3. The Android client or website sends the text to the authenticated BRUCE API.
4. The API verifies the client, loads the conversation and authorized memory, and selects the configured model backend.
5. The model may answer directly or request a registered tool.
6. Android actions are queued for the registered device; the device reports the actual result.
7. The response is returned to the requesting client for display and/or text-to-speech.

## Model independence

- No OpenAI API key is required.
- Ollama is supported through its OpenAI-compatible HTTP interface.
- Other independently hosted or selected model endpoints may be configured server-side.
- The production API must report model readiness accurately. A successful deployment or healthy API process does not prove that an inference model is reachable.
- When no model is configured, the API may support deterministic offline commands but must clearly report that free-form AI conversation is unavailable.

## Security boundaries

- Model-provider credentials and the BRUCE device token stay server-side or in Android secure storage, respectively.
- The website's proxy must validate a Better Auth session and restrict access to the configured owner account until per-user authorization is implemented.
- No arbitrary shell execution from model output.
- Sensitive, external, financial or irreversible actions require explicit confirmation.
- Wake-word detection is local; raw microphone audio is not uploaded by the wake listener.
- Public deployment requires TLS, rate limiting, abuse controls, secret rotation and a production database.
- The current BRUCE API's single shared device token and global memory store are for one owner's private use only. They are not multi-user isolation.

## Context and memory

Conversation history and explicit memories are stored separately. The API selects a bounded, relevant context window for each request. Storage does not itself expand a model's context capacity or intelligence. The Android and website clients must not maintain competing canonical memories; they must use one shared, access-controlled persistence layer.
