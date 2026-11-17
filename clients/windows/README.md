# BRUCE Windows Wake Client

This client continuously detects the custom wake word locally while the process is running. It does not stream microphone audio to a server.

## Prerequisites

1. Windows 10/11 and Python 3.10+.
2. Create a Picovoice account and obtain an access key.
3. Train/download a custom Porcupine keyword model for the phrase **BRUCE**, Portuguese pronunciation, and your Windows architecture at https://console.picovoice.ai/.
4. Put the resulting `.ppn` file at `models/bruce_windows.ppn`.
5. Copy `.env.example` to `.env` and configure the access key.

## Install and run

```powershell
cd clients/windows
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
py bruce_wake.py
```

Windows must grant microphone permission to the desktop app. Keep the process running; this script is not yet installed as a Windows service or startup task. It currently prints the wake event and optionally launches a configured local command. It does not yet launch a ChatGPT voice session automatically.

## Important

A custom keyword model is required. A generic package cannot guarantee recognition of BRUCE without the trained model. The wake listener must be explicitly installed and started by the user.
