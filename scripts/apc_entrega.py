"""Entrega Cliente en APC, acotada a autos previamente confirmados en Roma.

Este módulo sólo puede seleccionar una fila y cambiarla a ``Entregado`` (67).
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actualizar_stock_apc as apc

P = apc.P
FILA = f'[name="{P}Dms_VehiculoTableControlRepeater$ctl00$Dms_VehiculoRecordRowSelection"]'
BOTON_ENTREGA = "#ctl00_PageContent_Dms_VehiculoEntregaClienteButton"


def _elegir_sucursal(page, texto: str | None) -> None:
    sel = f'[name="{P}id_SucursalFilter"]'
    if texto is None:
        valor = "--PLEASE_SELECT--"
    else:
        opciones = page.eval_on_selector_all(f"{sel} option", "os => os.map(o => [o.value, o.textContent.trim()])")
        valor = next((v for v, t in opciones if t.upper() == texto.upper()), None)
        if valor is None:
            raise RuntimeError(f"No existe la sucursal {texto!r} en APC.")
    if page.eval_on_selector(sel, "s => s.value") != valor:
        apc.postback(page, lambda: page.select_option(sel, valor))


def _buscar(page, codigo: str, marca: str) -> tuple[str, object | None]:
    """Busca en todas las sucursales y devuelve el estado sólo de la fila del código."""
    page.goto(apc.STOCK_URL, wait_until="networkidle")
    if "dms_vehiculo" not in page.url:
        raise RuntimeError(f"No llegué a stock APC (quedé en {page.url}).")
    sel = f'[name="{P}TipoConsultaDropDownList"]'
    if page.eval_on_selector(sel, "s => s.value") != "1":
        apc.postback(page, lambda: page.select_option(sel, "1"))
    _elegir_sucursal(page, None)  # TODAS: no leer estados de filtros o etiquetas globales.
    page.fill(f'[name="{P}Codigo_InternoFilter"]', codigo)
    apc.postback(page, lambda: page.click(apc.BOTON_BUSCAR))
    filas = page.query_selector_all(f'[name$="Dms_VehiculoRecordRowSelection"]')
    candidatas = []
    for fila in filas:
        texto = fila.evaluate("c => c.closest('tr').innerText")
        if codigo.upper() in texto.upper():
            candidatas.append((fila, texto))
    if len(candidatas) != 1:
        return ("no se encontró" if not candidatas else "falló: más de una fila para el código"), None
    fila, texto = candidatas[0]
    estado = next((e for e in ("Entregado Cliente", "Facturado", "Vendido", "Disponible")
                    if e.upper() in texto.upper()), "sin estado")
    return estado, fila


def _acta_sigue_confirmada(codigo: str) -> bool:
    # Importación tardía evita un ciclo: el vigilante llama a este módulo sólo al ejecutar.
    from stock_quilin_vigilante import clasificar_roma
    dato = clasificar_roma([codigo]).get(codigo, {})
    return str(dato.get("resultado", "")).startswith("con acta")


def _marca_de(entrada) -> tuple[str, str]:
    if isinstance(entrada, str):
        return entrada, "TODAS"
    if isinstance(entrada, dict):
        return str(entrada["codigo"]), str(entrada.get("marca") or "TODAS")
    return str(entrada[0]), str(entrada[1] if len(entrada) > 1 else "TODAS")


def entregar_en_apc(codigos_marca, hacer: bool) -> dict[str, str]:
    """Confirma Roma y APC antes de entregar; retorna un resultado por código.

    ``hacer=False`` abre APC y reporta exactamente lo que se haría, sin cambiar nada.
    """
    autos = [_marca_de(x) for x in codigos_marca]
    resultados: dict[str, str] = {}
    if not autos:
        return resultados
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=True)
        ctx = nav.new_context(locale="es-CL")
        page = ctx.new_page()
        page.on("dialog", lambda d: d.accept())
        try:
            apc.entrar(page, apc.leer_env())
            for codigo, marca in autos:
                try:
                    # Debe ser inmediatamente antes del cambio, no la clasificación anterior.
                    if not _acta_sigue_confirmada(codigo):
                        resultados[codigo] = "falló: el acta ya no está confirmada en Roma"
                        continue
                    estado, fila = _buscar(page, codigo, marca)
                    if estado == "Entregado Cliente":
                        resultados[codigo] = "ya estaba entregado"; continue
                    if fila is None:
                        resultados[codigo] = estado; continue
                    if estado != "Facturado":
                        resultados[codigo] = f"no está en Facturado: {estado}"; continue
                    if not hacer:
                        resultados[codigo] = "se marcaría (simulación)"; continue
                    comentario = f"Conteo físico Quilín {dt.date.today():%d-%m-%Y}: auto no está en el local, acta firmada en Roma"
                    for _ in range(2):
                        # La lectura de Roma va pegada al acto de marcar, también al reintento.
                        if not _acta_sigue_confirmada(codigo):
                            resultados[codigo] = "falló: el acta ya no está confirmada en Roma"
                            break
                        estado, fila = _buscar(page, codigo, marca)
                        if estado == "Entregado Cliente": break
                        if estado != "Facturado" or fila is None: break
                        fila.check()
                        page.click(BOTON_ENTREGA)
                        page.wait_for_timeout(3000)
                        pop = next((f for pg in ctx.pages for f in pg.frames if "PopupEntregaVehiculo" in f.url), None)
                        if pop is None: continue
                        pop.wait_for_load_state("networkidle")
                        pop.select_option(f'[name="{P}id_Estado_Unidad"]', "67")
                        for nombre, valor in pop.eval_on_selector_all("textarea, input[type=text]", "es => es.map(e => [e.name, e.value])"):
                            if "omentario" in nombre and not str(valor).strip():
                                pop.fill(f'[name="{nombre}"]', comentario)
                        pop.click("#ctl00_PageContent_SaveButton__Button")
                        page.wait_for_timeout(5000)
                    if codigo not in resultados:
                        estado, _ = _buscar(page, codigo, marca)
                        resultados[codigo] = "marcado" if estado == "Entregado Cliente" else f"falló: después de guardar quedó en {estado}"
                except Exception as exc:
                    resultados[codigo] = f"falló: {exc}"
        finally:
            ctx.close(); nav.close()
    return resultados
