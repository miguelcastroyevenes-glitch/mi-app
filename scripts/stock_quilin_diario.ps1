# stock_quilin_diario.ps1 — lo corre el Programador de tareas ("Stock Quilin conteo diario", 09:00).
# Saca de APC el stock de Peugeot Quilin y Citroen Quilin y lo envia al equipo para el conteo fisico.
# Si falla, el script le escribe solo a Miguel. Si ni siquiera puede escribir (Outlook cerrado),
# deja un aviso en el Escritorio ("STOCK QUILIN NO SE ENVIO.txt").

$base   = "C:\Proyectos\app-deal"
$repo   = Join-Path $base "mi-app"
$log    = Join-Path $base "apc-descargas\quilin\ultima-corrida.log"
$aviso  = Join-Path ([Environment]::GetFolderPath("Desktop")) "STOCK QUILIN NO SE ENVIO.txt"
$python = "C:\Users\Migue\AppData\Local\Programs\Python\Python312\python.exe"

New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$env:PYTHONIOENCODING = "utf-8"
Set-Location $repo

"=== $(Get-Date -Format 'dd-MM-yyyy HH:mm') ===" | Out-File $log -Encoding utf8
cmd /c "`"$python`" scripts\stock_quilin_diario.py >> `"$log`" 2>&1"
$codigo = $LASTEXITCODE

$envio = Select-String -Path $log -Pattern "Enviado a" -Quiet
if ($codigo -eq 0 -and $envio) {
    if (Test-Path $aviso) { Remove-Item $aviso -Confirm:$false }
} elseif (-not $envio) {
    @"
El stock de Quilin para el conteo NO se envio hoy ($(Get-Date -Format 'dd-MM-yyyy HH:mm')),
y tampoco se pudo mandar el correo de aviso (Outlook cerrado o sin conexion).

Detalle: $log
Para reintentar a mano:  python C:\Proyectos\app-deal\mi-app\scripts\stock_quilin_diario.py
"@ | Out-File $aviso -Encoding utf8
}
exit $codigo
