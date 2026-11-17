Place the custom Porcupine Android keyword model at:
app/src/main/assets/bruce_android.ppn

Also add a preference UI field for Picovoice access key before testing. The model must be generated for the exact phrase BRUCE, pt-BR pronunciation and Android platform using the Picovoice Console. The current scaffold is not installable/production-ready until that binary model is supplied and Gradle compilation succeeds.

Android 14+ restricts starting microphone foreground services from the background. Start monitoring from the visible app while it is foregrounded, accept the system permissions, and keep the persistent notification visible. Force-stop, reboot, OEM battery restrictions, and lock-screen behavior vary by device. Do not promise wake-word availability after force-stop.
