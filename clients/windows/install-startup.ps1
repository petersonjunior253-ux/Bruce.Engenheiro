$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Here ".venv\Scripts\pythonw.exe"
$Script = Join-Path $Here "bruce_wake.py"
if (-not (Test-Path $Python)) {
  throw "Ambiente virtual não encontrado. Crie .venv e instale requirements.txt primeiro."
}
if (-not (Test-Path (Join-Path $Here ".env"))) {
  throw "Crie o arquivo .env e configure a chave Picovoice e o modelo bruce_windows.ppn."
}
$Action = New-ScheduledTaskAction -Execute $Python -Argument $Script -WorkingDirectory $Here
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Days 0)
Register-ScheduledTask -TaskName "BRUCE Voice Assistant" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Detector local da palavra BRUCE" -Force | Out-Null
Write-Host "Tarefa criada. O detector iniciará no próximo login. Para iniciar agora:"
Write-Host "Start-ScheduledTask -TaskName 'BRUCE Voice Assistant'"
