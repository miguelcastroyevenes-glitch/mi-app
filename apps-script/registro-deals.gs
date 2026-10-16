// Deal Final · guarda cada deal cerrado en esta planilla y lo entrega por su número.
//
// Se publica como aplicación web: "Ejecutar como: yo" y "Quién tiene acceso: cualquier persona".
// La planilla sigue siendo privada de Miguel. Esta es la única puerta, y solo deja dos cosas:
// guardar un deal (devuelve su número) o leer UN deal por su número. No hay forma de listar todos.
// El número son 6 letras al azar, así que no se puede adivinar el de otro deal.

const LETRAS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"; // sin O/0 ni I/1/L para que no se confundan
const COL_NUMERO = 21; // U
const COL_CODIGO = 22; // V

function hoja_() {
  return SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
}

function responder_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

// Un texto que empieza con = + - @ la planilla lo toma como fórmula; se le antepone ' para que quede como texto.
function texto_(v) {
  const s = v == null ? "" : String(v);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function numero_(v) {
  const n = Number(v);
  return isFinite(n) ? n : 0;
}

function nuevoNumero_() {
  let s = "";
  for (let i = 0; i < 6; i++) s += LETRAS[Math.floor(Math.random() * LETRAS.length)];
  return s;
}

function buscarFila_(sh, numero) {
  const filas = sh.getLastRow() - 1;
  if (filas < 1) return null;
  const cel = sh.getRange(2, COL_NUMERO, filas, 1).createTextFinder(numero).matchEntireCell(true).findNext();
  return cel ? cel.getRow() : null;
}

// Guardar: la app manda el deal (para las columnas que se leen) y su código corto (para rearmarlo).
function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const body = JSON.parse(e.postData.contents);
    const d = body.deal || {};
    const codigo = String(body.codigo || "");
    if (!/^2[zj][A-Za-z0-9_-]+$/.test(codigo) || codigo.length > 4000) return responder_({ ok: false, error: "codigo" });

    const sh = hoja_();
    if (sh.getRange(1, COL_NUMERO).getValue() === "") sh.getRange(1, COL_NUMERO, 1, 2).setValues([["Número", "Código"]]);

    let numero;
    do { numero = nuevoNumero_(); } while (buscarFila_(sh, numero));

    const ahora = new Date();
    const pago = d.modoVenta === "flota" ? "Flota " + String(d.tramoFlota || "").toUpperCase() : d.formaPago;
    sh.appendRow([
      Utilities.formatDate(ahora, "America/Santiago", "dd-MM-yyyy"),
      Utilities.formatDate(ahora, "America/Santiago", "HH:mm"),
      texto_(d.vendedor), texto_(d.cliente), texto_(d.marca), texto_(d.modelo), texto_(d.cit), texto_(pago),
      numero_(d.precioLista), numero_(d.bonoTotal), numero_(d.descPompeyo), numero_(d.bonoZonal),
      numero_(d.precioAuto), numero_(d.totalDoc), numero_(d.totalAcc), numero_(d.totalCliente),
      numero_(d.margenNeto), numero_(d.comisionCredito), numero_(d.utilidadProxy), numero_(d.utilidadPct),
      numero, codigo,
    ]);
    return responder_({ ok: true, numero: numero });
  } catch (err) {
    return responder_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

// Leer: ?n=ABC234 devuelve el código corto de ese deal. Cualquier otra cosa devuelve ok:false.
function doGet(e) {
  const numero = String((e && e.parameter && e.parameter.n) || "").toUpperCase();
  if (!/^[A-Z0-9]{6}$/.test(numero)) return responder_({ ok: false });
  const sh = hoja_();
  const fila = buscarFila_(sh, numero);
  if (!fila) return responder_({ ok: false });
  return responder_({ ok: true, codigo: String(sh.getRange(fila, COL_CODIGO).getValue()) });
}
