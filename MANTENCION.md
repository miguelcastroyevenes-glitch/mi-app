# Deal Final — guía de mantención

Referencia para actualizar la app mes a mes. `index.html` es un archivo único, sin build:
React 18 + Babel standalone por CDN, JSX inline. Lo usan 4 vendedores desde el celular para
cerrar deals reales, y no tiene tests. Cada edición mueve plata de verdad.

- **Repo:** https://github.com/miguelcastroyevenes-glitch/mi-app (branch `main`)
- **En vivo:** https://miguelcastroyevenes-glitch.github.io/mi-app/
- **Clon local:** `C:\Users\miguel.acastro\OneDrive - pompeyo.cl\app deal\mi-app`

> ⚠️ **Ojo con la carpeta.** Existe una copia de `index.html` en
> `Documentos\nueva app\.preview-deal\` que está **congelada en v18** y pertenece a otro
> repo (`renovaciones-app`, el Next.js de clientes/gestiones). Editar esa copia por error
> publica una app sin Permiso de Circulación ni Impuesto Verde. Hay otra copia suelta en
> `OneDrive\files\index.html` que tampoco sirve. La única buena es `app deal\mi-app`.

---

## Flujo obligatorio para cualquier edición

1. `git pull` en el clon local. Nunca asumir el estado del archivo desde una sesión anterior.
2. Leer el `index.html` real y **verificar `APP_VERSION`** antes de editar.
3. Si algo de lo que pide el usuario no calza con lo que dice el código, **parar y preguntar**.
   No forzar el cambio para que calce con una descripción vieja.
4. Editar solo lo que corresponde al pedido.
5. **Validar el JSX.** `npx esbuild index.html` falla por el `<!DOCTYPE html>`. Lo que sirve:
   extraer el texto entre `<script type="text/babel">` y `</script>` a un `.jsx` y correr
   `npx esbuild archivo.jsx --loader:.jsx=jsx --outfile=NUL`. Cero salida = sintaxis OK.
6. Probar en el navegador de verdad. Sintaxis válida no es lo mismo que cálculo correcto.
7. Subir `APP_VERSION` a `"AAAA-MM-DD · vN"`, con N tomado del archivo, no de la memoria.
8. `git add`, commit con mensaje descriptivo, `git push` a `main`. Confirmar que el push pasó.

---

## Actualización mensual del catálogo

Las listas llegan a `Documentos\quilin\precios\<MES AÑO>\`. Son una por marca, más
`Lista de Descuentos B2B <mes>.xlsx` para los tramos de flota.

### Reglas de IVA — el error más común

| Campo | Pasajeros | Comerciales |
|---|---|---|
| `pl` (precio lista) | con IVA | **con IVA** |
| `bono` | con IVA | **con IVA** |
| `aporteRed`, `aporteSte`, `aporteFin` | con IVA | **NETOS** |
| bloque `b2b` completo | — | **NETOS** |

En comerciales la app calcula `ivaBono = bono − (aporteRed + aporteSte + aporteFin)`.
Chequeo rápido: la suma de los aportes × 1,19 tiene que dar el bono. Si no da, algún campo
quedó en la unidad equivocada.

### Aporte Red = tope CE

`aporteRed` es siempre **2,5% del precio lista neto**. Sirve para validar cualquier fila:
para el Leapmotor B10 REEV, `25.990.000 × 0,025 = 649.750`. Y siempre
`aporteRed + aporteSte (+ aporteFin) = bono` (neto en comerciales).

### Tramos B2B (solo comerciales)

Los porcentajes **no** salen de la lista de precios sino de la planilla de descuentos B2B,
en la pestaña de la marca. Cada modelo ocupa tres filas: `Total`, `Stellantis` y `RED`.
Mapeo de columnas verificado contra el Berlingo, que ya estaba cargado:

| Col | Significado | Campo en la app |
|---|---|---|
| 3 | margen fijo | `margenFijo` |
| 5 | Tramo 1 Professional | `t1.pct` / `t1.steProf` / `t1.redProf` |
| 6 | Tramo 2 Professional | `t2.*Prof` |
| 7 | Tramo 1 No Professional | `t1.*NoProf` |
| 8 | Tramo 2 No Professional | `t2.*NoProf` |
| 9 | Grandes Cuentas | `gc.*` |

Validación: `redProf + steProf = pct`, y `plSinIva × (1 − pct) = precio`. Pompeyo está
configurado como `professional` (constante `CONCESIONARIO_B2B`).

### Marca nueva

1. Agregar la llave al final de `CATALOGO_LOCAL`. Si la marca no tiene comerciales, **no
   poner la llave `Comerciales`** — el selector de tipo se arma desde las llaves existentes
   y ofrecer un botón vacío confunde al vendedor.
2. Agregar el color en `C` y la entrada en `MARCA_COLOR`. Nada más: el header, las tarjetas
   de marca y los títulos de familia leen todos de ahí.
3. El selector de marcas se acomoda solo (una fila hasta 3 marcas, 2×2 de 4 en adelante).

Colores en uso: Peugeot `#0f2b5b`, Citroën `#c4161c`, Leapmotor `#166534`, Opel `#1e40af`.
El azul de Opel es más brillante que el de Peugeot a propósito — `#0f2b5b` es casi negro y
en pantalla de celular los dos botones se confundían.

---

## Impuesto Verde y Permiso de Circulación

Ambos se pagan al inscribir el auto nuevo, así que los dos usan `VALOR_UTM`, que es la
**UTM del mes en curso** (no la de enero: esa aplica a la renovación anual). **Hay que
subirla cada mes.** Septiembre 2026 = `71721`.

### Impuesto Verde

Tabla `IMPUESTO_VERDE`, indexada por **CIT**, con `{rend, nox}`. Fórmula del SII:

```
[(35 / rendimiento urbano) + (120 × NOx)] × (precioNeto × 0,00000006)
```

El resultado va en UTM, se **redondea a 2 decimales** y recién ahí se pasa a pesos. Ese
redondeo es lo que hace que calce exacto con la calculadora del SII.

- El factor de NOx es **120**, no 60.
- Eléctricos: `rend` queda en 0 y la función corta devolviendo 0 (exentos por ley).
- Los furgones solo están exentos sobre **2.000 kg** de carga. El Combo (907 kg) y el
  Berlingo/Partner **sí pagan**.

**De dónde salen `rend` y `nox`:** del CSV oficial `VehiculosHomologados.csv` (Ministerio
de Transporte / SII), columnas `Rendimiento Urbano (Km/l)` y `Nox (gr/Km)`. Miguel lo tiene
en `Downloads`. Se busca por CIT exacto.

> **Si un CIT del catálogo nuevo no está en la tabla, el impuesto sale $0 en silencio.**
> Al cargar una marca o modelo nuevo hay que cruzar todos los CIT contra el CSV y confirmar
> que calzaron todos. Varias versiones comparten CIT (mismo informe técnico) — es normal
> tener menos llaves que modelos.

### Permiso de Circulación

Escala progresiva acumulativa del Art. 12 letra a) del DL 3.063, sobre la tasación en UTM
(`precioNeto / VALOR_UTM`): **1% / 2% / 3% / 4% / 4,5%** en los tramos 0-60 / 60-120 /
120-250 / 250-400 / 400+. Piso legal de 0,5 UTM. Prorrateo de auto nuevo:
`mesesRestantes = (12 − mesCompra) + 1`, incluyendo el mes en curso.

Discrepancia conocida: contra un permiso real de Las Condes queda un gap de ~1,4%, que se
explica por el valor de UTM usado, no por la escala ni el prorrateo.

---

## Trampas conocidas

- **`store:{...}` es data muerta.** La función Store se eliminó en v10 cuando terminó la
  campaña. Los sub-objetos `store` siguen en `CATALOGO_LOCAL` (y se siguen cargando al
  actualizar el catálogo, por consistencia), pero **ningún código los lee**: el bono
  adicional STORE no se muestra ni se calcula. Si se quiere de vuelta hay que reconstruir
  la feature; el código original está en el commit `6ebc55c`.
- **Llaves por modelo, byte a byte.** Las tablas auxiliares que van por nombre de modelo
  (`PUSH_VIN`, `PROX_MES`) tienen que calzar con `auto.modelo` exactamente, incluidos
  dobles espacios accidentales del catálogo. Un desajuste no da error: la feature
  simplemente no aparece.
- **Números chilenos.** Usar siempre el helper `parsePesos()`, nunca `parseInt()` crudo:
  el punto es separador de miles.
- **Campañas con fecha.** `PUSH_VIN` y `PROX_MES` tienen su propio gate de vigencia. Al
  vencer se vacían (`vigencia:""`), no se borra el bloque.
- **El catálogo va embebido a propósito.** `SCRIPT_URL` (Google Sheets) queda vacío: la app
  tiene que funcionar 100% offline en el celular del vendedor.
- **En Windows, `git commit -m` con here-string se rompe** si el mensaje trae paréntesis;
  PowerShell parte el texto y git lo lee como rutas. Usar `git commit -F archivo.txt`.
- **No hay Python real en esta máquina** (solo el stub de la Store). Para leer los Excel:
  Node + `xlsx` (SheetJS).

---

## Invariantes de negocio

No derivables leyendo el código — Miguel las fijó explícitamente:

1. **Márgenes:** 9% pasajeros, 10% comerciales. Descuento recomendado máximo 4%; el tope
   duro es el margen completo.
2. **Gastos ROMA:** $204.500 fijos por vehículo, en la cascada de utilidad
   (margen bruto → −CE → −Pompeyo → −ROMA → margen neto).
3. **El desglose del bono no se colapsa nunca.** Aporte Red en naranjo `#b45309`,
   Stellantis en azul `#2563eb`, Financiera en violeta `#7c3aed`. El vendedor necesita cada
   línea por separado para configurar ROMA/APC.
4. **Separación APC:** BONOS (plata de afuera: Stellantis + Financiera + Zonal) vs
   DESCUENTO (margen de la casa: CE 2,5% + Descuento Pompeyo). No mezclar.
5. **El Descuento Pompeyo se ingresa en pesos**, no en porcentaje. El % es solo referencia
   e incluye el CE: `totalDadoPct = descPompeyoPct + 2,5%`.
6. **No romper:** localStorage (prefijo `df_`), el flujo de reabrir un deal cerrado, ni el
   botón de compartir con `navigator.share()` y su fallback a portapapeles.
