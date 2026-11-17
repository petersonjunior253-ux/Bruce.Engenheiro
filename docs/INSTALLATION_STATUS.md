# Installation and test status

## What is in the repository
- Web UI with a 3D-style neural core and text-to-speech / browser speech recognition controls.
- Secure model-provider gateway API with conversation and explicit-memory persistence.
- Windows Porcupine local wake-word listener scaffold.
- Android Kotlin foreground-service wake-word scaffold.
- Android debug APK build workflow.

## Required before a working voice wake test
1. Generate a custom Porcupine keyword model for the phrase BRUCE, Portuguese pronunciation, and each target platform (Windows .ppn and Android .ppn).
2. Obtain a Picovoice AccessKey and configure it locally. The key is not embedded in source control.
3. Android: place the Android model at `clients/android/app/src/main/assets/bruce_android.ppn`, install the APK, grant microphone and notification permissions, and start monitoring while the app is visible.
4. Windows: place the Windows model at `clients/windows/models/bruce_windows.ppn`, configure its .env and run the listener. Use the startup installer only after a successful manual test.
5. Configure and deploy the API with a real model-provider key and model ID. Store provider credentials only as server environment variables.
6. Configure the frontend/device with the API HTTPS URL and a separate BRUCE device token.

## Not yet verified
No APK has been built or installed in a physical device in this repository session. No custom keyword model or provider secret was supplied. Android lock-screen wake behavior, OEM battery behavior, Windows microphone permissions, API provider compatibility, and end-to-end latency still require device tests.

## Security
Do not commit .env files, provider keys, device tokens, or custom model assets that contain account-bound secrets. Rotate any credential that is accidentally committed.
