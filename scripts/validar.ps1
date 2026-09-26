# validar.ps1 — chequea la sintaxis de las dos apps antes de publicar.
# Uso:  .\scripts\validar.ps1
# Salida: "OK" por app, o el error de sintaxis con linea. Codigo de salida 1 si algo falla.

$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$tmp  = Join-Path $env:TEMP "validar-mi-app"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$fallo = $false

function Extraer-Script {
    param($archivo, $salida)
    # Saca el contenido del ULTIMO bloque <script ...> ... </script> del HTML.
    $texto = Get-Content -Raw -Encoding UTF8 $archivo
    $m = [regex]::Matches($texto, '(?s)<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>')
    if ($m.Count -eq 0) { throw "No encontre bloque <script> inline en $archivo" }
    $cuerpo = $m[$m.Count - 1].Groups[1].Value
    Set-Content -Path $salida -Value $cuerpo -Encoding UTF8
    return $cuerpo.Length
}

function Chequear {
    param($archivo, $ext, $loader)
    $nombre = Split-Path -Leaf $archivo
    Write-Host "-> $nombre " -NoNewline
    $jsx = Join-Path $tmp ("app" + $ext)
    $largo = Extraer-Script (Join-Path $repo $archivo) $jsx
    $descarte = Join-Path $tmp ("descarte" + $ext + ".out")
    $salida = & npx --yes esbuild $jsx "--loader:$ext=$loader" "--outfile=$descarte" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FALLA" -ForegroundColor Red
        Write-Host $salida
        $script:fallo = $true
    } else {
        Write-Host "OK ($largo chars)" -ForegroundColor Green
    }
}

Chequear "index.html" ".jsx" "jsx"   # Deal Final: React + Babel, JSX inline
Chequear "stock.html" ".js"  "js"    # Stock Pompeyo: JS plano

if ($fallo) { Write-Host "`nHAY ERRORES DE SINTAXIS. No publicar." -ForegroundColor Red; exit 1 }
Write-Host "`nSintaxis OK en las dos apps." -ForegroundColor Green
Write-Host "Ojo: sintaxis valida NO es calculo correcto. Probar en el navegador igual." -ForegroundColor Yellow
