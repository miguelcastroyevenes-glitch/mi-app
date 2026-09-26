# publicar.ps1 — publica las dos apps a main con respaldo y validacion previos.
# Uso:
#   .\scripts\publicar.ps1 -Mensaje "v29: catalogo octubre Peugeot"
#   .\scripts\publicar.ps1 -Mensaje "stock: corte del 03-10" -SinSubirVersion
#   .\scripts\publicar.ps1 -Mensaje "prueba" -Ensayo        <- no commitea ni sube, solo muestra
#
# Orden: respaldo -> pull -> validar sintaxis -> subir APP_VERSION -> commit -> push.
# Si cualquier paso falla, corta y NO publica.

param(
    [Parameter(Mandatory = $true)][string]$Mensaje,
    [switch]$SinSubirVersion,   # usar cuando el cambio es solo de stock.html
    [switch]$Ensayo             # simula: valida y muestra el diff, sin commit ni push
)

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

function Paso($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }

# --- 1. Respaldo ANTES de tocar nada ---
Paso 1 "Respaldo local"
& "$PSScriptRoot\respaldo.ps1"
if ($LASTEXITCODE -ne 0) { throw "El respaldo fallo. Corto aqui: no publico sin respaldo." }

# --- 2. Traer lo que haya en GitHub ---
Paso 2 "git pull (nunca asumir el estado del archivo)"
$rama = git rev-parse --abbrev-ref HEAD
git pull --ff-only origin $rama
if ($LASTEXITCODE -ne 0) { throw "El pull no fue limpio. Resolver a mano antes de seguir." }

# --- 3. Validar sintaxis de las dos apps ---
Paso 3 "Validacion de sintaxis"
& "$PSScriptRoot\validar.ps1"
if ($LASTEXITCODE -ne 0) { throw "Sintaxis invalida. No se publica." }

# --- 4. Subir APP_VERSION leyendo N del archivo, no de memoria ---
if (-not $SinSubirVersion) {
    Paso 4 "Subiendo APP_VERSION"
    $html = Get-Content -Raw -Encoding UTF8 "$repo\index.html"
    $m = [regex]::Match($html, 'APP_VERSION\s*=\s*"(\d{4}-\d{2}-\d{2}) · v(\d+)"')
    if (-not $m.Success) { throw "No pude leer APP_VERSION de index.html. Revisar a mano." }
    $vieja = $m.Value
    $nueva = 'APP_VERSION = "{0} · v{1}"' -f (Get-Date -Format "yyyy-MM-dd"), ([int]$m.Groups[2].Value + 1)
    Write-Host "  $vieja  ->  $nueva"
    if (-not $Ensayo) {
        $html = $html.Remove($m.Index, $m.Length).Insert($m.Index, $nueva)
        Set-Content "$repo\index.html" -Value $html -Encoding UTF8 -NoNewline
    }
} else {
    Paso 4 "APP_VERSION sin cambios (-SinSubirVersion)"
}

# --- 5. Que se va a publicar ---
Paso 5 "Cambios a publicar"
git status --short
git diff --stat

if ($Ensayo) {
    Write-Host "`nENSAYO: no commitee ni subi nada. Quitar -Ensayo para publicar de verdad." -ForegroundColor Yellow
    exit 0
}

if (-not (git status --porcelain)) { Write-Host "`nNo hay nada que publicar." -ForegroundColor Yellow; exit 0 }

$r = Read-Host "`nPublicar a '$rama'? (s/N)"
if ($r -ne "s") { Write-Host "Cancelado. Los cambios quedan en el disco." -ForegroundColor Yellow; exit 0 }

# --- 6. Commit y push. Mensaje por archivo: en Windows -m se rompe con parentesis. ---
Paso 6 "Commit y push"
$msgFile = Join-Path $env:TEMP "commit-mi-app.txt"
Set-Content $msgFile -Value $Mensaje -Encoding UTF8
git add -A
git commit -F $msgFile
if ($LASTEXITCODE -ne 0) { throw "El commit fallo." }

foreach ($espera in 0, 2, 4, 8, 16) {
    if ($espera -gt 0) { Write-Host "  reintento en ${espera}s..."; Start-Sleep -Seconds $espera }
    git push -u origin $rama
    if ($LASTEXITCODE -eq 0) { break }
}
if ($LASTEXITCODE -ne 0) { throw "El push fallo despues de 5 intentos. El commit esta local: reintentar con git push." }

Write-Host "`nPublicado. En vivo en ~1 min:" -ForegroundColor Green
Write-Host "  Deal  : https://miguelcastroyevenes-glitch.github.io/mi-app/"
Write-Host "  Stock : https://miguelcastroyevenes-glitch.github.io/mi-app/stock.html"
Write-Host "Abrir con Ctrl+F5 y confirmar la version en pantalla." -ForegroundColor Yellow
