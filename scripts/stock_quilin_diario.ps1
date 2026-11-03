# stock_quilin_diario.ps1 — lo corre el Programador de tareas ("Stock Quilin conteo diario", 09:00).
# Saca de APC el stock de Peugeot Quilin y Citroen Quilin y lo envia al equipo para el conteo fisico.
# Si falla, a Miguel le llega un correo de aviso por Gmail (pieza 3.2, Tanda 1; ya no depende de
# Outlook) y ademas queda un aviso en el Escritorio ("STOCK QUILIN NO SE ENVIO.txt").

$base   = "C:\Proyectos\app-deal"
$repo   = Join-Path $base "mi-app"
$log    = Join-Path $base "apc-descargas\quilin\ultima-corrida.log"
$aviso  = Join-Path ([Environment]::GetFolderPath("Desktop")) "STOCK QUILIN NO SE ENVIO.txt"
$python = "C:\Users\Migue\AppData\Local\Programs\Python\Python312\python.exe"
$laboratorio = "C:\Proyectos\laboratorio-ia"

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
    # Con codigo distinto de 0 el .py ya aviso por correo; aqui solo falta el caso en que
    # termino bien pero el envio al equipo no quedo registrado.
    if ($codigo -eq 0) {
        $avisador = Join-Path (Join-Path $laboratorio 'lab') 'aviso_cli.py'
        & $python $avisador --tarea "Stock Quilin (envio al equipo)" --detalle "termino sin error pero no quedo registrado el envio" --log $log 2>&1 | ForEach-Object { "$_" } | Out-File $log -Append -Encoding utf8
    }
    @"
El stock de Quilin para el conteo NO se envio hoy ($(Get-Date -Format 'dd-MM-yyyy HH:mm')).
A Miguel le debio llegar un correo de aviso; si no llego, el motivo esta en el detalle.

Detalle: $log
Para reintentar a mano:  python C:\Proyectos\app-deal\mi-app\scripts\stock_quilin_diario.py
"@ | Out-File $aviso -Encoding utf8
}
exit $codigo
