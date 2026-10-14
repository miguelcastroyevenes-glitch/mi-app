# Respaldo y publicación — cómo se usa

Clon de trabajo: `C:\Proyectos\app-deal\mi-app` (fuera de OneDrive, a propósito).
Respaldos: `C:\Proyectos\app-deal\respaldos`.

> **Por qué fuera de OneDrive.** OneDrive sincroniza también la carpeta `.git`. Si sincroniza
> a medias mientras git escribe, el repo queda corrupto; y si editas desde dos equipos genera
> `index-copia en conflicto.html`, que es exactamente cómo aparecieron las copias viejas
> congeladas en v18. El respaldo lo hace `respaldo.ps1`, no OneDrive.

## Instalación (una vez)

```powershell
mkdir C:\Proyectos\app-deal
cd C:\Proyectos\app-deal
git clone https://github.com/miguelcastroyevenes-glitch/mi-app.git
mkdir respaldos
cd mi-app
git config core.autocrlf false    # los HTML no deben cambiar de saltos de línea
```

Node hace falta solo para validar (`npx esbuild`). Si `node -v` no responde, instalar Node 20 LTS.

Cuando esto funcione, la carpeta vieja de OneDrive (`app deal\mi-app`) se archiva o se borra,
para que no queden dos clones editables.

## Los tres comandos

| Comando | Para qué |
|---|---|
| `.\scripts\respaldo.ps1` | Respaldo local. No toca GitHub. Se puede correr cuando sea. |
| `.\scripts\validar.ps1` | Chequea la sintaxis de las dos apps. Cero riesgo. |
| `python scripts\actualizar_catalogo.py --carpeta <carpeta del mes> --mes <mes> --anio <año>` | Carga mensual del catálogo (4 marcas, B2B, UTM, versión). Sin `--aplicar` es ensayo. Ver `MANTENCION.md`. |
| `.\scripts\publicar.ps1 -Mensaje "v29: catálogo octubre"` | Respaldo → pull → validar → subir versión → commit → push. |
| `python scripts\actualizar_stock_apc.py --publicar` | Baja el stock físico de APC (Peugeot + Citroën), rehace `stock.html` y sube **solo ese archivo**. Corre solo todos los días a las 07:30. Credenciales en `C:\Proyectos\app-deal\apc.env` (fuera del repo). Con `--ver` se mira el navegador; sin `--publicar` es ensayo. |
| `python scripts\actualizar_zonal.py --publicar` | Pestaña "Stock de marca (zonal)": lee de Outlook (solo lectura) el último correo con "stock" de Benjamín Bastian (Citroën) y Cristian Zurita (Peugeot), guarda el Excel en `files\Zonal` y actualiza la pestaña. Sin planilla nueva o solo con foto, esa marca no cambia. Corre en la misma tarea de las 07:30. Nunca retrocede a un corte más viejo que el publicado. |
| `python scripts\actualizar_asignacion.py --aplicar` | Pestañas "Asignación de marca" y "Pre inscritas". Lee las planillas del Drive bajadas a `files\Asignacion` (`asignacion-<marca>-<fecha Drive>.xlsx` y `preinscritas-<fecha>.csv`). **Solo la pestaña más nueva** de cada marca: al cerrar el mes esas unidades pasan a Stock físico. Saca lo que ya está en APC. Pre inscritas sin RUT ni nombres (el repo es público). Sin `--aplicar` es ensayo; después se publica con `-SinSubirVersion`. |

Ensayo sin publicar nada:
```powershell
.\scripts\publicar.ps1 -Mensaje "prueba" -Ensayo
```

> **Ojo (desde v31, 13-10-2026):** el Deal tiene un panel "📦 Stock disponible" que **lee `stock.html`**
> (las líneas `const fisico = …;`, `const asignacion`, `const asignacionMeta`, `const preinscritas`,
> `const preinscritasMeta` y `const zonal`, una por línea). Si un script cambia ese formato, el panel
> deja de mostrar stock sin dar error. Los nombres de versión se emparejan en `fichas()` de `index.html`.

Cambio que toca solo `stock.html` (no corresponde subir `APP_VERSION` del Deal):
```powershell
.\scripts\publicar.ps1 -Mensaje "stock: corte del 03-10" -SinSubirVersion
```

`publicar.ps1` **pide confirmación** antes del push y corta si el respaldo, el pull o la
validación fallan. La regla de `MANTENCION.md` sigue en pie: sintaxis válida no es cálculo
correcto — hay que abrir la app en el navegador igual.

## Qué deja el respaldo

```
C:\Proyectos\app-deal\respaldos\
├── bundles\
│   └── mi-app-2026-09-26.bundle      <- repo completo, todo el historial, 1 archivo
└── 2026-09-26_1830\
    ├── index.html
    ├── stock.html
    ├── MANTENCION.md
    └── ESTADO.txt                    <- commit, APP_VERSION y cambios sin commitear
```

Conserva 30 días de copias planas y los últimos 12 bundles.

## Restaurar

Un archivo suelto, desde la copia plana:
```powershell
copy C:\Proyectos\app-deal\respaldos\2026-09-26_1830\index.html C:\Proyectos\app-deal\mi-app\
```

El repo entero desde un bundle (si GitHub no está o el clon se corrompió):
```powershell
cd C:\Proyectos\app-deal
git clone respaldos\bundles\mi-app-2026-09-26.bundle mi-app-recuperado
```

Volver a una versión anterior sin perder el historial:
```powershell
git log --oneline          # ubicar el commit bueno
git revert <commit-malo>   # revert, nunca reset --hard sobre algo ya publicado
```

## Automatizar el respaldo diario (Programador de tareas)

Una vez, en PowerShell **como administrador**:

```powershell
$acc = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Proyectos\app-deal\mi-app\scripts\respaldo.ps1"'
$dis = New-ScheduledTaskTrigger -Daily -At 8:15am
$cfg = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable:$false
Register-ScheduledTask -TaskName "Respaldo app deal" -Action $acc -Trigger $dis -Settings $cfg `
  -Description "Respaldo diario de Deal Final y Stock Pompeyo"
```

Probar sin esperar al otro día:
```powershell
Start-ScheduledTask -TaskName "Respaldo app deal"
Get-ScheduledTaskInfo -TaskName "Respaldo app deal"   # LastTaskResult 0 = OK
```

**El respaldo se automatiza; el publicar no** — salvo el stock (acordado 07-10-2026): `stock.html` no calcula plata y su script corta solo si algo se ve raro (campos de costo, caída de más de 40% en unidades). El Deal sigue igual: Publicar mueve plata de verdad y necesita que
alguien haya mirado la app en el navegador. `publicar.ps1` se corre a mano, siempre.

## Red de seguridad en GitHub

`.github/workflows/validar.yml` valida la sintaxis de las dos apps en cada push a `main`.
Si queda en rojo, el commit tiene un problema de sintaxis. **Avisa, no bloquea**: GitHub Pages
publica igual, así que si sale rojo hay que arreglarlo o revertir al tiro.

## Stock Quilín para el conteo físico (correo diario 09:00)

`stock_quilin_diario.py` saca de APC el stock de PEUGEOT QUILIN y CITROEN QUILIN (Estado AutoPro
Disponible + Facturado + Vendido), lo une en un Excel de una hoja horizontal y lo envía desde el
Outlook de Miguel a Miguel, los 4 vendedores (`vigia-roma/vendedores.json`) y los `EXTRA` de
`C:\Proyectos\app-deal\stock_quilin.env`. Si falla, escribe solo a Miguel.

- Tarea: "Stock Quilin conteo diario", 09:00, corre `stock_quilin_diario.ps1`. Necesita Outlook clásico abierto.
- Registro: `C:\Proyectos\app-deal\apc-descargas\quilin\ultima-corrida.log` (los Excel quedan ahí mismo).
- Probar sin enviar: `python scripts\stock_quilin_diario.py --ensayo` · solo a Miguel: `--solo-miguel`.
- Por qué existe y qué decidió Miguel: `C:\Proyectos\app-deal\handshake_stock-quilin-diario.md`.
