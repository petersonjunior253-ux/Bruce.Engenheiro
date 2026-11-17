# BRUCE Android client — implementation plan

The Android client must be a native Kotlin application, not a webpage pretending to listen in the background.

Required implementation:
- Android foreground service with a persistent notification while microphone monitoring is active.
- On-device custom BRUCE wake-word model and explicit microphone permission.
- User-visible start/stop controls and clear recording indicator.
- Audio capture begins only after local wake detection; no always-on audio upload.
- Android 14+ microphone foreground-service declarations and permission flow.
- Optional assistant-role integration through VoiceInteractionService, subject to Android default-assistant selection and device support.

This directory intentionally does not claim a working Android listener yet. A tested custom model and native APK build are required before activation can be considered operational.
