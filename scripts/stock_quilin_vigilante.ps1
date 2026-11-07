# Ejecuta una sola vez el vigilante; la tarea programada se registra por separado.
$repo = Split-Path -Parent $PSScriptRoot
$python = "C:\Users\Migue\AppData\Local\Programs\Python\Python312\python.exe"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $repo
& $python scripts\stock_quilin_vigilante.py
exit $LASTEXITCODE
