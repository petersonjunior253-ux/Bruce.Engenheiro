# BRUCE installation and validation status

## Active implementation
- Web dashboard in `src/App.tsx` and `src/styles.css`: BRUCE WAYNE navigation, conversational area, voice input while the page is active, quick routine prompts, API/device status, and task list.
- Private FastAPI backend in `services/api/main.py`: Gemini provider, function calling, SQLite persistence in private Blob, task CRUD, memory CRUD, Android command queue, and Edge TTS.
- Active native Android app in `app/` (package `com.bruce.assistant`): Vosk wake-word service, foreground microphone service, Android command bridge, notification listener, accessibility service, and file tools.
- The legacy `clients/android/` directory is not the active APK target.

## Voice activation
- The active Android app uses the official `vosk-model-small-pt-0.3` model, downloaded automatically by Gradle and packaged under the asset path `model-pt`.
- Model source: https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip (31 MB, Apache 2.0).
- User must open BRUCE, grant microphone and notification permissions, and tap **ATIVAR BRUCE · VOZ OFFLINE** while the app is visible.
- After activation, the foreground service and persistent notification allow wake-word listening while the activity is not on screen.
- Android 14+ restricts starting a microphone foreground service from the background. Do not promise automatic microphone start after reboot or force-stop; the user may need to activate it again.

## Required server configuration
1. Set `BRUCE_API_KEY` to a strong private device token.
2. Set `BRUCE_MODEL_PROVIDER=gemini`.
3. Set `BRUCE_MODEL_NAME=gemini-3.8-flash`.
4. Set `BRUCE_GEMINI_API_KEY` as a Vercel secret (never in Git, APK, or browser code).
5. Confirm `/health` reports `model_provider=Gemini` and `model_configured=true`.

## Validation completed in the current code branch
- Python syntax compilation passed for `services/api/main.py`.
- Vite production build passed (TypeScript + Vite).
- Local API smoke test passed for health/Gemini configuration, task create/list/complete, and memory save/read.
- The actual Gemini network call still requires a real Google API key.
- Android APK compilation and physical-device wake-word testing still need to run through GitHub Actions and a Samsung device.

## Known platform limits
- Browser speech recognition is not a background wake-word service; it works only while the page is active.
- Android foreground microphone monitoring must be user-started with permission and a visible persistent notification.
- Force-stop, reboot, OEM battery management, and microphone policy can interrupt listening.
- The current API token is a single-device private token. Before public multi-user access, implement user-scoped data, per-device credentials, pairing, revocation, and rate limits.
