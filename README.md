# BRUCE — Personal AI Assistant

BRUCE is an independent personal-assistant experience for Windows and Android, using ChatGPT as its intended intelligence provider and a custom voice-first interface.

## Current milestone

This repository starts with a responsive web prototype:
- dark neural-core interface and assistant status;
- text conversation interface;
- browser speech recognition when supported and explicitly started by the user;
- speech synthesis for spoken responses;
- a visible microphone/listening state and stop control.

## Important capability boundaries

- The browser prototype does **not** listen while the browser is closed, the device is locked, or the operating system is using another app.
- Browser speech recognition support varies by browser and device.
- The prototype does not yet connect to ChatGPT. A ChatGPT API integration requires an API key and separate API billing; a ChatGPT subscription does not automatically provide API credentials.
- Never put API keys in frontend code. A future backend must keep secrets server-side.
- Native Android and Windows clients are required for a dependable BRUCE wake-word service. Android background microphone behavior is subject to OS permissions and foreground-service restrictions.

## Run locally

Requirements: Node.js 20+.

```bash
npm install
npm run dev
```

## Planned architecture

- `apps/web`: responsive assistant UI and browser voice prototype.
- `apps/windows`: planned Windows companion with local wake-word detection.
- `apps/android`: planned Android companion with an explicitly enabled foreground voice service.
- `services/api`: planned secure backend for model calls, device pairing, preferences and action approvals.

## Privacy and safety

Wake-word detection should run locally. Audio should only be sent for transcription after activation and user consent. The assistant must request confirmation before sensitive, external, financial or irreversible actions.
