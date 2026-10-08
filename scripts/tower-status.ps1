# What is running Nova on this machine, and how it was started.
# Run with (no shifted characters, so it can be typed over remote desktop):
#   powershell -executionpolicy bypass -file scripts\tower-status.ps1

$listener = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($listener) { "port 8000 is owned by PID $($listener.OwningProcess)" } else { "nothing is listening on port 8000" }

Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='uv.exe' OR Name='uvicorn.exe'" |
    Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine |
    Format-List
