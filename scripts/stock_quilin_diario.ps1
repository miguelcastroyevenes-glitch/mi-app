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
    # Si Python fallo antes de llegar a su manejador (por ejemplo, al cargar el modulo),
    # el envoltorio hace un intento de respaldo por el mismo aviso del laboratorio.
    $avisoIntentado = Select-String -Path $log -Pattern "AVISO_SOLICITADO_LABORATORIO" -Quiet
    if ($codigo -ne 0 -and -not $avisoIntentado) {
        $avisador = Join-Path (Join-Path $laboratorio 'lab') 'aviso_cli.py'
        & $python $avisador --tarea "Stock Quilin (conteo diario)" --detalle "El programa de Python termino antes de activar su aviso interno; revisar el registro." --log $log 2>&1 | ForEach-Object { "$_" } | Out-File $log -Append -Encoding utf8
    }
    # Si terminó bien pero no quedó anotado el envío diario al equipo, también avisa.
    if ($codigo -eq 0) {
        $avisador = Join-Path (Join-Path $laboratorio 'lab') 'aviso_cli.py'
        & $python $avisador --tarea "Stock Quilin (envio al equipo)" --detalle "termino sin error pero no quedo registrado el envio" --log $log 2>&1 | ForEach-Object { "$_" } | Out-File $log -Append -Encoding utf8
    }
    $avisoConfirmado = Select-String -Path $log -Pattern "AVISO_ENVIADO_LABORATORIO|AVISO_ENVIADO" -Quiet
    if ($avisoConfirmado) {
        $estadoCorreo = "El registro confirma que el aviso se envio."
    } else {
        $estadoCorreo = "El registro no confirma que el aviso se haya enviado; revisa el detalle."
    }
    @"
El stock de Quilin para el conteo NO se envio hoy ($(Get-Date -Format 'dd-MM-yyyy HH:mm')).
$estadoCorreo

Detalle: $log
Para reintentar a mano:  python C:\Proyectos\app-deal\mi-app\scripts\stock_quilin_diario.py
"@ | Out-File $aviso -Encoding utf8
}
exit $codigo
