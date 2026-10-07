# stock_diario.ps1 — lo corre el Programador de tareas ("Stock APC diario", 07:30).
# Baja el stock de APC y publica stock.html. Deja el detalle en apc-descargas\ultima-corrida.log
# y, si falla, un aviso en el Escritorio ("STOCK APC NO SE ACTUALIZO.txt") con el motivo.

$base   = "C:\Proyectos\app-deal"
$repo   = Join-Path $base "mi-app"
$log    = Join-Path $base "apc-descargas\ultima-corrida.log"
$aviso  = Join-Path ([Environment]::GetFolderPath("Desktop")) "STOCK APC NO SE ACTUALIZO.txt"
$python = "C:\Users\Migue\AppData\Local\Programs\Python\Python312\python.exe"

New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$env:PYTHONIOENCODING = "utf-8"
Set-Location $repo

"=== $(Get-Date -Format 'dd-MM-yyyy HH:mm') ===" | Out-File $log -Encoding utf8
cmd /c "`"$python`" scripts\actualizar_stock_apc.py --publicar >> `"$log`" 2>&1"
$codigo = $LASTEXITCODE

if ($codigo -eq 0) {
    if (Test-Path $aviso) { Remove-Item $aviso -Confirm:$false }
} else {
    $motivo = (Get-Content $log -Encoding utf8 | Where-Object { $_ -match "Error|rror:" } | Select-Object -Last 1)
    @"
El stock de APC NO se actualizo hoy ($(Get-Date -Format 'dd-MM-yyyy HH:mm')).
La pagina sigue mostrando el corte anterior.

Motivo: $motivo

Causas tipicas:
- Tenias APC abierto a esa hora (APC permite una sola sesion).
- Cambiaste la clave de APC: actualizala en C:\Proyectos\app-deal\apc.env
- APC estaba caido.

Detalle completo: $log
Pantallazo del error (si lo hay): C:\Proyectos\app-deal\apc-descargas\
Para reintentar a mano:  python C:\Proyectos\app-deal\mi-app\scripts\actualizar_stock_apc.py --publicar
"@ | Out-File $aviso -Encoding utf8
}
exit $codigo
