"""Vigilante ENSAYO del conteo físico de Stock Quilín.

Nunca abre APC ni escribe en Roma.  Una ejecución procesa a lo más una respuesta.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

MIGUEL = "miguel.castro@pompeyo.cl"
ASUNTO_BASE = "Stock Quilín para conteo ·"
RAIZ = Path(__file__).resolve().parents[2]  # carpeta app-deal (o la copia de trabajo)
SALIDA = RAIZ / "apc-descargas" / "quilin"
ESTADO = SALIDA / "vigilante_trabajados.json"
LOG = SALIDA / "vigilante.log"
ORIGINAL = Path(r"C:\Proyectos\app-deal\apc-descargas\quilin")
VIGIA = Path(r"C:\Proyectos\vigia-roma")
IMAGENES = {".jpeg", ".jpg", ".png", ".heic"}


def registrar(texto: str) -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    LOG.open("a", encoding="utf-8").write(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {texto}\n")


def cargar_estado() -> dict:
    if not ESTADO.exists():
        return {"trabajados": [], "avisos": []}
    datos = json.loads(ESTADO.read_text(encoding="utf-8"))
    return {"trabajados": datos.get("trabajados", []), "avisos": datos.get("avisos", [])}


def guardar_estado(datos: dict, simular: bool) -> None:
    if not simular:
        ESTADO.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def fecha_asunto(asunto: str) -> str | None:
    m = re.search(r"(\d{2}-\d{2}-\d{4})", asunto or "")
    if not m:
        return None
    try:
        dt.datetime.strptime(m.group(1), "%d-%m-%Y")
        return m.group(1)
    except ValueError:
        return None


def es_respuesta_valida(correo: dict) -> bool:
    asunto = correo.get("subject", "")
    return (asunto.startswith(("Re:", "RE:")) and ASUNTO_BASE in asunto
            and correo.get("sender", "").lower() == MIGUEL
            and any(a.get("extension", "").lower() in IMAGENES and not a.get("hidden")
                    and not a.get("inline") for a in correo.get("attachments", [])))


def seleccionar_respuestas(correos: list[dict], trabajados: set[str]) -> list[dict]:
    """Deduplica Bandeja/Enviados por fecha; un RV/FW no cumple el asunto."""
    resultado, vistas = [], set()
    for correo in correos:
        fecha = fecha_asunto(correo.get("subject", ""))
        if fecha and fecha not in vistas and fecha not in trabajados and es_respuesta_valida(correo):
            resultado.append(correo)
            vistas.add(fecha)
    return resultado


def debe_avisar(hora: str, robot_hoy: bool, hay_foto: bool, aviso_ya: bool) -> bool:
    return hora >= "12:00" and robot_hoy and not hay_foto and not aviso_ya


def reservar_aviso(estado: dict, fecha: dt.date, hora: str, robot_hoy: bool, hay_foto: bool) -> bool:
    """Reserva el aviso antes del envío para que una corrida posterior no lo repita."""
    clave = fecha.isoformat()
    if not debe_avisar(hora, robot_hoy, hay_foto, clave in estado["avisos"]):
        return False
    estado["avisos"].append(clave)
    return True


def validar_destinatarios(destinatarios: list[str]) -> None:
    if destinatarios != [MIGUEL]:
        raise RuntimeError("El vigilante solo puede escribir a miguel.castro@pompeyo.cl.")


def procesos_apc_corriendo() -> bool:
    try:
        salida = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Select-Object -ExpandProperty CommandLine"],
            text=True, errors="replace",
        )
    except Exception as exc:
        registrar(f"No se pudo revisar procesos Python: {exc}")
        return False
    texto = salida.lower()
    return "actualizar_stock_apc.py" in texto or "stock_quilin_diario.py" in texto


def smtp_remitente(item) -> str:
    try:
        usuario = item.Sender.GetExchangeUser()
        if usuario and usuario.PrimarySmtpAddress:
            return str(usuario.PrimarySmtpAddress).lower()
    except Exception:
        pass
    try:
        return str(item.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x39FE001E")).lower()
    except Exception as exc:
        raise RuntimeError(f"No se pudo resolver la dirección real del remitente: {exc}") from exc


def adjuntos_foto(item) -> list:
    fotos = []
    for i in range(1, item.Attachments.Count + 1):
        adj = item.Attachments.Item(i)
        nombre = str(adj.FileName)
        if Path(nombre).suffix.lower() not in IMAGENES:
            continue
        try:
            oculto = bool(adj.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x7FFE000B"))
        except Exception:
            oculto = False
        if oculto or (str(getattr(adj, "ContentId", "")) and str(getattr(adj, "ContentId", "")) in str(item.HTMLBody)):
            continue
        fotos.append(adj)
    return fotos


def correos_outlook(desde: dt.date) -> tuple[list[dict], bool]:
    try:
        import win32com.client
        app = win32com.client.Dispatch("Outlook.Application")
        ns = app.GetNamespace("MAPI")
    except Exception as exc:
        raise RuntimeError(f"Outlook clásico no está abierto o no respondió: {exc}") from exc
    correos, robot_hoy = [], False
    for carpeta_id in (6, 5):  # Inbox, Sent Items
        carpeta = ns.GetDefaultFolder(carpeta_id)
        # Restrict acota a los días pedidos; algunos elementos raros de la bandeja
        # fallan al leer sus campos ("Interfaz no compatible") y se saltan.
        items = carpeta.Items.Restrict(f"[ReceivedTime] >= '{desde.strftime('%d-%m-%Y')} 00:00'")
        for item in items:
            try:
                if item.Class != 43:
                    continue
                recibido = item.ReceivedTime
            except Exception:
                continue
            if not recibido or recibido.date() < desde:
                continue
            asunto = str(item.Subject or "")
            fotos = adjuntos_foto(item)
            if (not asunto.startswith(("Re:", "RE:")) and ASUNTO_BASE in asunto
                    and any(Path(str(a.FileName)).suffix.lower() == ".xlsx" for a in [item.Attachments.Item(j) for j in range(1, item.Attachments.Count + 1)])):
                if fecha_asunto(asunto) == dt.date.today().strftime("%d-%m-%Y"):
                    robot_hoy = True
            if asunto.startswith(("Re:", "RE:")) and ASUNTO_BASE in asunto:
                correos.append({"subject": asunto, "sender": smtp_remitente(item), "attachments": [
                    {"extension": Path(str(a.FileName)).suffix, "hidden": False, "inline": False, "object": a} for a in fotos], "item": item})
    return correos, robot_hoy


def leer_foto(foto: Path) -> dict:
    from anthropic import Anthropic
    from dotenv import dotenv_values
    llave = dotenv_values(r"C:\Proyectos\asistente-ventas\.env").get("ANTHROPIC_API_KEY", "")
    if not llave:
        raise RuntimeError("No hay llave de IA en C:\\Proyectos\\asistente-ventas\\.env.")
    pedido = '''Lee la columna REV LOCAL (la última) de esta hoja de conteo, fila por fila.
Devuelve por cada código impreso: marca X, vacio o dudosa. X solo si es clara; todo lo que no sea una X clara es dudosa. Nunca inventes códigos. Responde SOLO JSON: {"filas":[{"codigo":"...","marca":"X|vacio|dudosa"}]}'''
    tipo = "image/png" if foto.suffix.lower() == ".png" else "image/jpeg"
    respuesta = Anthropic(api_key=llave, max_retries=2, timeout=120).messages.create(model="claude-opus-5-5", max_tokens=8000, messages=[{"role":"user","content":[{"type":"image","source":{"type":"base64","media_type":tipo,"data":base64.standard_b64encode(foto.read_bytes()).decode()}},{"type":"text","text":pedido}]}])
    texto = "".join(b.text for b in respuesta.content if b.type == "text").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(texto)


def excel_del_dia(fecha: str) -> Path:
    iso = dt.datetime.strptime(fecha, "%d-%m-%Y").strftime("%Y-%m-%d")
    esperado = ORIGINAL / f"Stock Quilin conteo {iso}.xlsx"
    if esperado.exists():
        return esperado
    hallados = list(ORIGINAL.glob(f"*{iso}*.xlsx"))
    if len(hallados) == 1:
        registrar(f"Excel con nombre distinto: {hallados[0].name}")
        return hallados[0]
    raise RuntimeError(f"No se encontró el Excel del conteo {iso} en {ORIGINAL}.")


def leer_autos_excel(ruta: Path) -> tuple[dict[str, dict], object]:
    from openpyxl import load_workbook
    wb = load_workbook(ruta)
    ws = wb.active
    encabezados = {str(ws.cell(4, c).value or "").strip(): c for c in range(1, ws.max_column + 1)}
    if "REV LOCAL" not in encabezados:
        raise RuntimeError("El Excel no tiene la columna REV LOCAL en la fila 4.")
    codigo_col = next((c for n, c in encabezados.items() if "interno" in n.lower() or "digo" in n.lower()), None)  # encabezado real: "Cód. interno"
    if not codigo_col:
        raise RuntimeError("El Excel no tiene una columna de código interno.")
    autos = {}
    for fila in range(5, ws.max_row + 1):
        codigo = str(ws.cell(fila, codigo_col).value or "").strip()
        if codigo:
            autos[codigo] = {"fila": fila, "modelo": str(ws.cell(fila, encabezados.get("Modelo", 1)).value or ""), "rev": encabezados["REV LOCAL"]}
    return autos, wb


def marcar_excel(wb, autos: dict, xs: list[str], clasificaciones: dict, fecha: str) -> Path:
    ws = wb.active
    ws.cell(4, 11, "Resultado")
    for codigo in xs:
        auto = autos[codigo]
        ws.cell(auto["fila"], auto["rev"], "X")
        ws.cell(auto["fila"], 11, clasificaciones[codigo]["resultado"])
    SALIDA.mkdir(parents=True, exist_ok=True)
    destino = SALIDA / f"Stock Quilin conteo {dt.datetime.strptime(fecha, '%d-%m-%Y'):%Y-%m-%d} REV LOCAL.xlsx"
    wb.save(destino)
    return destino


def elegir_venta(ventas_lista: list[dict], codigo: str) -> dict | None:
    """La venta del auto por chasis: nunca la ANULADA; primero facturada, luego vigente."""
    candidatas = [v for v in ventas_lista if str(v.get("Vin") or "").strip().upper().endswith(codigo.upper())
                  and "ANULAD" not in str(v.get("EstadoVenta") or "").upper()]
    for clave in ("FACTUR", "VIGENTE"):
        elegida = next((v for v in candidatas if clave in str(v.get("EstadoVenta") or "").upper()), None)
        if elegida:
            return elegida
    return candidatas[0] if candidatas else None


def tiene_acta(respuesta_archivos) -> bool:
    """getInfoArchivos_venta trae [tipos, archivos]; tipos siempre lista el acta, solo cuentan los archivos subidos."""
    if not isinstance(respuesta_archivos, list) or len(respuesta_archivos) < 2:
        raise RuntimeError("getInfoArchivos_venta no trajo la forma [tipos, archivos].")
    archivos = respuesta_archivos[1]
    if isinstance(archivos, str):
        archivos = json.loads(archivos) if archivos.strip() else []
    return any(str(a.get("ArchivoTipoID")) == "32" for a in archivos or [])


def ultima_entrega(solicitudes: list[dict]) -> dict | None:
    """La "Entrega Vehículo" más reciente manda: una rechazada puede aprobarse después (VJ011267, 21 y 26-10-2026)."""
    entregas = [s for s in solicitudes if str(s.get("Tipo") or "").upper().startswith("ENTREGA VEH")]
    return max(entregas, key=lambda s: str(s.get("FechaCreacion") or ""), default=None)


def estado_sin_acta(entrega: dict | None, pedir_respuestas) -> str:
    if not entrega:
        return "sin acta · entrega nunca pedida"
    estado = str(entrega.get("Estado") or "").upper()
    if "RECHAZ" in estado:
        respuestas = pedir_respuestas(str(entrega.get("ID") or ""))
        motivo = next((str(r.get("Comentario") or "").strip() for r in respuestas
                       if "RECHAZ" in str(r.get("Accion") or "").upper()), "")
        return f"sin acta · entrega rechazada: {motivo}" if motivo else "sin acta · entrega rechazada: TODO: preguntar"
    if "CONFIRM" in estado:
        return "sin acta · entrega aprobada"
    return f"sin acta · entrega {estado.lower() or 'sin estado'}"


def clasificar_roma(codigos: list[str]) -> dict:
    """Solo acciones observadas: sesión, ListarRegistros, archivos y solicitudes."""
    sys.path.insert(0, str(VIGIA))
    from scraper import _controlador, _pedir_lista, abrir_sesion
    from inteligencia import ventas
    sesion, usuario = abrir_sesion()
    try:
        ventas_lista = []
        for desde, hasta in ventas.meses("2026-05-01", dt.date.today().isoformat()):
            ventas_lista.extend(ventas.pedir(sesion, usuario, desde, hasta))
        u = json.loads(usuario)[0]
        solicitudes_url = _controlador("controller.solicitudes.php")

        def pedir_respuestas(sid: str) -> list:
            if not sid: raise RuntimeError("La solicitud rechazada no trajo ID.")
            return _pedir_lista(sesion, solicitudes_url, {"solicitudID": sid, "usuario": usuario, "action": "SolicitudGetInfoRespuestas"}, 120)

        resultado = {}
        for codigo in codigos:
            venta = elegir_venta(ventas_lista, codigo)
            if not venta:
                resultado[codigo] = {"resultado": "sin venta en Roma", "vendedor": ""}; continue
            vid = str(venta.get("ID") or "")
            if not vid: raise RuntimeError("ListarRegistros no trajo identificador de venta utilizable.")
            vendedor = str(venta.get("nombre_Vendedor") or "")
            extra = " · venta de Miguel" if "MIGUEL" in vendedor.upper() else ""
            archivos = _pedir_lista(sesion, _controlador("controller.ventas.php"), {"id": vid, "usuario": str(u["usuario"]), "cookie_vt": u["cookie"], "url": "Venta.html", "action": "getInfoArchivos_venta"}, 120)
            if tiene_acta(archivos):
                resultado[codigo] = {"resultado": "con acta" + extra, "vendedor": vendedor, "venta": vid}; continue
            solicitudes = _pedir_lista(sesion, solicitudes_url, {"id": vid, "usuario": usuario, "url": "Venta.html", "action": "getSolicitudesxReferencia"}, 120)
            resultado[codigo] = {"resultado": estado_sin_acta(ultima_entrega(solicitudes), pedir_respuestas) + extra, "vendedor": vendedor, "venta": vid}
        return resultado
    finally:
        sesion.close()


def imprimir_envio(asunto: str, cuerpo: str) -> None:
    validar_destinatarios([MIGUEL]); print(f"Para: {MIGUEL}\nAsunto: {asunto}\n{cuerpo}")


def enviar_correo_nuevo(asunto: str, cuerpo: str, excel: Path | None = None) -> None:
    import win32com.client
    app = win32com.client.Dispatch("Outlook.Application")
    nuevo = app.CreateItem(0)
    nuevo.To = MIGUEL
    nuevo.CC = ""
    nuevo.BCC = ""
    nuevo.Subject = asunto
    nuevo.Body = cuerpo
    if excel is not None:
        nuevo.Attachments.Add(str(excel))
    validar_destinatarios([MIGUEL])
    nuevo.Send()


def enviar_resultado(correo, asunto: str, cuerpo: str, excel: Path) -> None:
    """Responde en el hilo; si falla, crea un correo nuevo solo a Miguel."""
    try:
        respuesta = correo.Reply()
        respuesta.To = MIGUEL
        respuesta.CC = ""
        respuesta.BCC = ""
        respuesta.Subject = asunto
        respuesta.Body = cuerpo
        respuesta.Attachments.Add(str(excel))
        validar_destinatarios([MIGUEL])
        respuesta.Send()
    except Exception as exc:
        registrar(f"Falló Reply(); se enviará correo nuevo: {exc}")
        enviar_correo_nuevo(asunto, cuerpo, excel)


def filtrar_lectura(lectura: dict, autos: dict) -> tuple[set[str], set[str], list[str]]:
    """Conserva solamente códigos presentes en el Excel y separa X de dudas."""
    marcas, dudosas, ignorados = set(), set(), []
    for fila in lectura.get("filas", []):
        codigo = str(fila.get("codigo", "")).strip()
        marca = str(fila.get("marca", "")).lower()
        if codigo not in autos:
            ignorados.append(codigo)
        elif marca == "x":
            marcas.add(codigo)
        elif marca != "vacio":
            dudosas.add(codigo)
    return marcas, dudosas, ignorados


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--simular", action="store_true"); ap.add_argument("--desde"); ap.add_argument("--foto", type=Path); ap.add_argument("--fecha"); ap.add_argument("--hora"); ap.add_argument("--marcas"); ap.add_argument("--dudosas")
    a = ap.parse_args()
    if (a.desde or a.foto or a.hora or a.marcas or a.dudosas) and not a.simular: raise RuntimeError("Las opciones de prueba requieren --simular.")
    estado = cargar_estado(); hoy = dt.date.today(); fecha = a.fecha
    try:
        if procesos_apc_corriendo(): registrar("No hizo nada: robot APC corriendo."); return 0
        item = None
        if a.foto:
            if not fecha: raise RuntimeError("--foto requiere --fecha.")
            foto = a.foto
        else:
            desde = dt.datetime.strptime(a.desde, "%d-%m-%Y").date() if a.desde else hoy - dt.timedelta(days=1)
            correos, robot_hoy = correos_outlook(desde)
            elegidas = seleccionar_respuestas(correos, set(estado["trabajados"]))
            hay_foto = any(
                fecha_asunto(correo["subject"]) == hoy.strftime("%d-%m-%Y")
                and es_respuesta_valida(correo)
                for correo in correos
            )
            if not elegidas:
                hora = a.hora or dt.datetime.now().strftime("%H:%M")
                if reservar_aviso(estado, hoy, hora, robot_hoy, hay_foto):
                    asunto = f"ENSAYO · Falta la foto del conteo de hoy · {hoy:%d-%m-%Y}"; cuerpo = "Falta la foto del conteo de hoy. Es un ensayo."
                    if a.simular: imprimir_envio(asunto, cuerpo)
                    else:
                        guardar_estado(estado, False)
                        enviar_correo_nuevo(asunto, cuerpo)
                registrar("No encontró respuesta con foto."); print("No encontró respuesta con foto."); return 0
            elegido = elegidas[0]; fecha = fecha_asunto(elegido["subject"]); item = elegido["item"]
            adj = max(elegido["attachments"], key=lambda x: getattr(x["object"], "Size", 0))["object"]
            foto = SALIDA / str(adj.FileName); SALIDA.mkdir(parents=True, exist_ok=True); adj.SaveAsFile(str(foto))
        excel = excel_del_dia(fecha); autos, wb = leer_autos_excel(excel)
        lectura = {"filas": []} if a.marcas else leer_foto(foto)
        marcas = set((a.marcas or "").split(",")) - {""}; dudosas = set((a.dudosas or "").split(",")) - {""}
        lectura_marcas, lectura_dudosas, ignorados = filtrar_lectura(lectura, autos)
        marcas.update(lectura_marcas)
        dudosas.update(lectura_dudosas)
        clasificaciones = clasificar_roma(sorted(marcas)) if marcas else {}
        marcado = marcar_excel(wb, autos, sorted(marcas), clasificaciones, fecha)
        lineas = [f"Autos con X: {len(marcas)}"] + [f"- {c}: {autos[c]['modelo']} · {clasificaciones[c]['vendedor']} · {clasificaciones[c]['resultado']}" for c in sorted(marcas)]
        if dudosas: lineas += ["Te pregunto por estos autos:", *[f"- {c}" for c in sorted(dudosas)]]
        lineas += ["Es un ensayo: no se tocó APC ni se escribió a ningún vendedor."]
        asunto = f"ENSAYO · Stock realizado y cuadrado · {fecha}"; cuerpo = "\n".join(lineas)
        if a.simular: imprimir_envio(asunto, cuerpo); print(f"Excel: {marcado}")
        else:
            estado["trabajados"].append(fecha)
            guardar_estado(estado, False)
            enviar_resultado(item, asunto, cuerpo, marcado)
        registrar(f"Ensayo {fecha}: X={len(marcas)}, dudosas={len(dudosas)}, ignorados={ignorados}")
        return 0
    except Exception as exc:
        registrar(f"Error: {exc}"); print(f"Error: {exc}", file=sys.stderr); return 1


if __name__ == "__main__":
    raise SystemExit(main())
