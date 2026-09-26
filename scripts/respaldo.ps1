# respaldo.ps1 — respaldo local de las dos apps. No toca el repo ni GitHub.
# Uso:  .\scripts\respaldo.ps1
#
# Deja dos cosas en C:\Proyectos\app-deal\respaldos:
#   1. bundles\mi-app-AAAA-MM-DD.bundle  -> repo COMPLETO con todo el historial (1 archivo)
#   2. AAAA-MM-DD_HHmm\                  -> copia plana de index.html y stock.html
# Conserva los ultimos 30 dias de carpetas planas y los ultimos 12 bundles.

param(
    [string]$Destino = "C:\Proyectos\app-deal\respaldos",
    [int]$DiasCopias = 30,
    [int]$MaxBundles = 12
)

$ErrorActionPreference = "Stop"
$repo  = Split-Path -Parent $PSScriptRoot
$sello = Get-Date -Format "yyyy-MM-dd_HHmm"
$dia   = Get-Date -Format "yyyy-MM-dd"

New-Item -ItemType Directory -Force -Path $Destino, "$Destino\bundles" | Out-Null

# --- 1. Bundle: el repo entero en un archivo. Esto es el respaldo que importa. ---
$bundle = "$Destino\bundles\mi-app-$dia.bundle"
Write-Host "Creando bundle de todo el historial..."
git -C $repo bundle create $bundle --all
if ($LASTEXITCODE -ne 0) { throw "git bundle fallo" }
git -C $repo bundle verify $bundle | Out-Null
if ($LASTEXITCODE -ne 0) { throw "El bundle quedo corrupto" }
$mb = [math]::Round((Get-Item $bundle).Length / 1MB, 1)
Write-Host "  OK  $bundle ($mb MB, verificado)" -ForegroundColor Green

# --- 2. Copia plana: los HTML sueltos, para abrir sin git si todo lo demas falla. ---
$carpeta = "$Destino\$sello"
New-Item -ItemType Directory -Force -Path $carpeta | Out-Null
Copy-Item "$repo\index.html", "$repo\stock.html", "$repo\MANTENCION.md" $carpeta

# Anota en que commit y version quedo este respaldo.
$commit  = git -C $repo rev-parse --short HEAD
$rama    = git -C $repo rev-parse --abbrev-ref HEAD
$sucio   = git -C $repo status --porcelain
$mv = [regex]::Match((Get-Content -Raw -Encoding UTF8 "$repo\index.html"), 'APP_VERSION\s*=\s*"([^"]+)"')
$version = if ($mv.Success) { $mv.Groups[1].Value } else { "(no pude leerla)" }
@"
Respaldo      : $sello
Rama / commit : $rama / $commit
APP_VERSION   : $version
Cambios sin commitear al momento del respaldo:
$(if ($sucio) { $sucio } else { "  (ninguno, el arbol estaba limpio)" })
"@ | Set-Content "$carpeta\ESTADO.txt" -Encoding UTF8

Write-Host "  OK  $carpeta  (index.html, stock.html, MANTENCION.md, ESTADO.txt)" -ForegroundColor Green
if ($sucio) { Write-Host "  AVISO: habia cambios sin commitear. Quedaron en la copia plana." -ForegroundColor Yellow }

# --- 3. Limpieza de respaldos viejos ---
Get-ChildItem $Destino -Directory |
    Where-Object { $_.Name -match '^\d{4}-\d{2}-\d{2}_\d{4}$' -and $_.CreationTime -lt (Get-Date).AddDays(-$DiasCopias) } |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force; Write-Host "  purgado $($_.Name)" -ForegroundColor DarkGray }

Get-ChildItem "$Destino\bundles" -Filter *.bundle |
    Sort-Object LastWriteTime -Descending | Select-Object -Skip $MaxBundles |
    ForEach-Object { Remove-Item $_.FullName -Force; Write-Host "  purgado $($_.Name)" -ForegroundColor DarkGray }

Write-Host "`nRespaldo listo en $Destino" -ForegroundColor Green
