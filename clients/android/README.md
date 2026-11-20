# Legacy Android client

This directory is a legacy prototype and is not the active BRUCE APK build target.

The active native Android application lives in the repository root at `app/` (package `com.bruce.assistant`). GitHub Actions builds that project with the root Gradle settings.

The active app includes:
- Vosk Portuguese wake-word recognition using the bundled `vosk-model-small-pt-0.3` model.
- A user-started foreground microphone service with a persistent notification.
- Android command bridge, notification listener, accessibility service, and file tools.

Do not build or distribute an APK from this legacy directory.
