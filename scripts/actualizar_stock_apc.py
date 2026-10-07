"""actualizar_stock_apc.py — baja el stock físico desde APC (AutoProCloud) y rehace stock.html.

Uso:
    python scripts\\actualizar_stock_apc.py                 # baja de APC y muestra el resumen (ensayo)
    python scripts\\actualizar_stock_apc.py --aplicar       # además reescribe el bloque `fisico` de stock.html
    python scripts\\actualizar_stock_apc.py --ver           # con el navegador a la vista (para mirar la prueba)
    python scripts\\actualizar_stock_apc.py --archivos a.xls b.xls   # no entra a APC, usa exports ya bajados

    python scripts\\actualizar_stock_apc.py --publicar     # baja, escribe stock.html y lo sube (tarea diaria 07:30)

--publicar sube SOLO stock.html y no usa publicar.ps1 (que necesita Node). Corta si aparece un
campo que no sea vin/version/color/sucursal/bodega, o si las unidades caen más de 40% contra lo
publicado (señal de que APC exportó a medias). GitHub valida la sintaxis en cada push.
Excepción acordada con Miguel el 07-10-2026: el stock se publica solo; el Deal (plata) sigue a mano.

Credenciales: C:\\Proyectos\\app-deal\\apc.env (FUERA del repo; nunca se sube):
    APC_USUARIO=correo@pompeyo.cl
    APC_CLAVE=...
    APC_EMPRESA=POMPEYO CARRASCO SPA     (opcional: texto tal cual aparece en el menú)
    APC_SUCURSAL=                        (opcional)
    APC_MODULO=                          (opcional)

Reglas (igual que con Roma): APC es SOLO LECTURA. El script solo usa pantallas y botones
observados el 06-10-2026 y solo hace clic en los de la lista BOTONES_PERMITIDOS. La pantalla
de stock tiene botones que mueven inventario ("Genera Ajuste de Salida", "Entrega a Cliente",
"Cambiar estado"): nunca se tocan.

El export de APC trae costo, margen y bono por unidad. Nada de eso llega a stock.html (que es
público): solo modelo, versión, color, sucursal, bodega y VIN. Los .xls crudos quedan en
C:\\Proyectos\\app-deal\\apc-descargas, fuera del repo.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = REPO.parent                                  # C:\Proyectos\app-deal
ENV_FILE = BASE / "apc.env"
DESCARGAS = BASE / "apc-descargas"
STOCK_HTML = REPO / "stock.html"

# wordpressMode=1 es como entra Miguel (iframe de autoprocloud.com/mi-cuenta). Sin él, el
# JS de APC manda Optional3='null' y la lista de Módulo llega vacía (visto 06-10-2026).
LOGIN_URL = "https://provider.autoprocloud.com/mc/mobile/msignin.aspx?wordpressMode=1"
STOCK_URL = "https://appspsa-cl.autoprocloud.com//vcl/dms_vehiculo/showdms_vehiculotable.aspx"

P = "ctl00$PageContent$"
MARCAS = {"peugeot": "114", "citroen": "30"}        # valores del filtro Marca observados
CONDICION_NUEVOS_FLOOR_PLAN = "1"
ESTADO_DISPONIBLE = f"{P}id_Estado_VehiculoFilter$2"

# Únicos botones de la pantalla de stock que el script puede apretar.
BOTON_BUSCAR = "#ctl00_PageContent_GoButton__Button"
BOTON_EXCEL = "#ctl00_PageContent_Dms_VehiculoExportExcelButton"
BOTONES_PERMITIDOS = {BOTON_BUSCAR, BOTON_EXCEL}

# Estado Dealer que cuenta como stock vendible. El resto (RESCILIACION, JUDICIAL, DONANTE,
# EN TALLER...) se informa en el resumen pero no se muestra a los vendedores.
ESTADOS_DEALER_OK = {"DISPONIBLE"}

NS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def log(msg: str) -> None:
    print(msg, flush=True)


# ---------------------------------------------------------------- credenciales
def leer_env() -> dict:
    if not ENV_FILE.exists():
        ENV_FILE.write_text(
            "APC_USUARIO=\nAPC_CLAVE=\nAPC_EMPRESA=\nAPC_SUCURSAL=\nAPC_MODULO=\n", encoding="utf-8"
        )
        sys.exit(f"Creé {ENV_FILE}. Ábrelo, escribe tu usuario y clave de APC y vuelve a correr.")
    env = {}
    for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
        if "=" in linea and not linea.lstrip().startswith("#"):
            k, v = linea.split("=", 1)
            env[k.strip()] = v.strip()
    if not env.get("APC_USUARIO") or not env.get("APC_CLAVE"):
        sys.exit(f"Falta APC_USUARIO o APC_CLAVE en {ENV_FILE}.")
    return env


# ---------------------------------------------------------------- APC
def clic(page, selector: str, **kw):
    if selector not in BOTONES_PERMITIDOS:
        raise RuntimeError(f"Botón no permitido: {selector}")
    page.click(selector, **kw)


def elegir_combo(page, combo: str, texto: str | None) -> str:
    """Elige empresa/sucursal/módulo en el login (combos jQuery Mobile)."""
    # Las listas se llenan por AJAX: esperar a que haya al menos una opción real.
    try:
        page.wait_for_function(
            """c => [...document.querySelectorAll('#' + c + ' option')]
                     .some(o => o.value && !['--PLEASE_SELECT--', '--ANY--'].includes(o.value))""",
            arg=combo, timeout=30000,
        )
    except Exception:
        pass  # se informa abajo con las opciones que haya
    opciones = page.eval_on_selector_all(
        f"#{combo} option", "os => os.map(o => [o.value, o.textContent.trim()])"
    )
    validas = [o for o in opciones if o[0] not in ("", "--PLEASE_SELECT--", "--ANY--")]
    if texto:
        elegida = next((o for o in validas if o[1].upper() == texto.upper()), None)
        if not elegida:
            raise RuntimeError(f"'{texto}' no está en {combo}. Opciones: {[o[1] for o in validas]}")
    elif len(validas) == 1:
        elegida = validas[0]
    else:
        actual = page.eval_on_selector(f"#{combo}", "s => s.value")
        elegida = next((o for o in validas if o[0] == actual), None)
        if not elegida:
            raise RuntimeError(
                f"Hay varias opciones en {combo} y no sé cuál usar: {[o[1] for o in validas]}. "
                f"Escribe la correcta en apc.env."
            )
    page.evaluate(
        "([c, v]) => { const s = $('#' + c); s.val(v); try { s.selectmenu('refresh'); } catch (e) {} s.change(); }",
        [combo, elegida[0]],
    )
    return elegida[1]


def cerrar_aviso(page) -> None:
    """Cierra el popup 'Información' del login si quedó abierto (solo es un aviso, no hace nada)."""
    page.evaluate("() => { try { $('#ControlPopup').popup('close'); } catch (e) {} }")
    page.wait_for_timeout(300)


def entrar(page, env: dict) -> None:
    log("1. Entrando a APC...")
    page.goto(LOGIN_URL, wait_until="networkidle")
    page.fill("#TxtUsername", env["APC_USUARIO"])
    page.fill("#TxtPassword", env["APC_CLAVE"])
    page.evaluate("() => $('#LoginOk').trigger('click')")
    page.wait_for_function(
        """() => document.querySelector('#control02')?.style.display === 'block'
              || document.querySelector('#ControlUniqueSession-popup.ui-popup-active')
              || document.querySelector('#ControlPopup-popup.ui-popup-active')""",
        timeout=45000,
    )
    paso_clave = page.evaluate("() => document.querySelector('#control02')?.style.display === 'block'")
    if not paso_clave and page.is_visible("#ControlUniqueSession-popup.ui-popup-active"):
        texto = page.inner_text("#UniqueSessionText")
        raise RuntimeError(f"APC dice que ya hay una sesión abierta: {texto.strip()} — ciérrala y vuelve a correr.")
    if not paso_clave:
        raise RuntimeError(f"APC rechazó el ingreso: {page.inner_text('#validText').strip()}")
    cerrar_aviso(page)

    empresa = elegir_combo(page, "business", env.get("APC_EMPRESA"))
    sucursal = elegir_combo(page, "branch", env.get("APC_SUCURSAL"))
    modulo = elegir_combo(page, "module", env.get("APC_MODULO"))
    log(f"   empresa={empresa} · sucursal={sucursal} · módulo={modulo}")
    cerrar_aviso(page)
    with page.expect_navigation(timeout=60000):
        page.evaluate("() => $('#LoginOk').trigger('click')")
    page.wait_for_load_state("networkidle")
    log(f"   dentro: {page.url.split('?')[0]}")


def postback(page, accion):
    """Los filtros de APC a veces recargan la página entera y a veces solo un pedazo
    (UpdatePanel de ASP.NET). Se espera a que termine cualquiera de los dos."""
    accion()
    page.wait_for_timeout(800)
    page.wait_for_load_state("load", timeout=90000)
    page.wait_for_function(
        """() => !(window.Sys && Sys.WebForms && Sys.WebForms.PageRequestManager
                   && Sys.WebForms.PageRequestManager.getInstance().get_isInAsyncPostBack())""",
        timeout=90000,
    )
    page.wait_for_load_state("networkidle", timeout=90000)


def bajar_marca(page, marca: str, destino: Path) -> tuple[Path, int | None]:
    log(f"2. Stock {marca.upper()}...")
    page.goto(STOCK_URL, wait_until="networkidle")
    if "dms_vehiculo" not in page.url:
        raise RuntimeError(f"No llegué a la pantalla de stock (quedé en {page.url}).")

    sel = lambda n: f'[name="{P}{n}"]'
    if page.eval_on_selector(sel("TipoConsultaDropDownList"), "s => s.value") != "1":
        postback(page, lambda: page.select_option(sel("TipoConsultaDropDownList"), "1"))
    # APC deja Sucursal = la del login (ej. CITROEN QUILIN). El stock se quiere de TODAS.
    if page.eval_on_selector(sel("id_SucursalFilter"), "s => s.value") != "--PLEASE_SELECT--":
        postback(page, lambda: page.select_option(sel("id_SucursalFilter"), "--PLEASE_SELECT--"))
    if page.eval_on_selector(sel("id_MarcaFilter"), "s => s.value") != MARCAS[marca]:
        postback(page, lambda: page.select_option(sel("id_MarcaFilter"), MARCAS[marca]))
    page.select_option(sel("id_Condicion_VehiculoFilter"), CONDICION_NUEVOS_FLOOR_PLAN)
    # Estado AutoPro: solo "Disponible"
    for cb in page.query_selector_all(f'input[type=checkbox][name^="{P}id_Estado_VehiculoFilter$"]'):
        quiero = cb.get_attribute("name") == ESTADO_DISPONIBLE
        if cb.is_checked() != quiero:
            cb.set_checked(quiero)
    postback(page, lambda: clic(page, BOTON_BUSCAR))

    m = re.search(r"(\d+)\s*Elementos", page.inner_text("body"))
    en_pantalla = int(m.group(1)) if m else None
    filtros = page.evaluate(
        """n => ['id_SucursalFilter', 'id_MarcaFilter', 'id_Condicion_VehiculoFilter']
                 .map(f => document.querySelector(`[name="${n}${f}"]`).selectedOptions[0].text.trim())""",
        P,
    )
    log(f"   filtros: sucursal={filtros[0]} · marca={filtros[1]} · condición={filtros[2]}")
    log(f"   APC muestra {en_pantalla} elementos")
    if not en_pantalla:
        raise RuntimeError("APC no devolvió unidades con esos filtros; no exporto un archivo vacío.")

    with page.expect_download(timeout=120000) as d:
        clic(page, BOTON_EXCEL)
    archivo = destino / f"stock-apc-{marca}-{dt.datetime.now():%Y%m%d-%H%M}.xls"
    d.value.save_as(archivo)
    log(f"   bajado: {archivo.name}")
    return archivo, en_pantalla


def bajar_de_apc(ver: bool) -> dict:
    from playwright.sync_api import sync_playwright

    env = leer_env()
    DESCARGAS.mkdir(exist_ok=True)
    salida = {}
    with sync_playwright() as pw:
        nav = pw.chromium.launch(headless=not ver, slow_mo=250 if ver else 0)
        ctx = nav.new_context(accept_downloads=True, locale="es-CL")
        page = ctx.new_page()
        page.on("dialog", lambda dlg: dlg.dismiss())  # cualquier "¿está seguro?" se cancela
        try:
            entrar(page, env)
            for marca in MARCAS:
                salida[marca] = bajar_marca(page, marca, DESCARGAS)
        except Exception:
            foto = DESCARGAS / f"error-{dt.datetime.now():%Y%m%d-%H%M}.png"
            page.screenshot(path=str(foto), full_page=True)
            log(f"   (pantallazo del error: {foto})")
            raise
        finally:
            ctx.close()
            nav.close()
    return salida


# ---------------------------------------------------------------- export -> datos
def leer_export(ruta: Path) -> list[dict]:
    """El 'xls' de APC es SpreadsheetML 2003 (XML). Devuelve una fila por unidad."""
    filas = []
    for row in ET.parse(ruta).getroot().iter(NS + "Row"):
        vals = []
        for c in row.findall(NS + "Cell"):
            idx = c.get(NS + "Index")
            if idx:
                vals += [""] * (int(idx) - 1 - len(vals))
            d = c.find(NS + "Data")
            vals.append((d.text or "").strip() if d is not None else "")
        filas.append(vals)
    cab = filas[0]
    for col in ("Marca", "Modelo", "Versión", "Color Exterior", "Numero VIN", "Estado Dealer"):
        if col not in cab:
            raise RuntimeError(f"{ruta.name}: falta la columna '{col}'. ¿Cambió el export de APC?")
    return [dict(zip(cab, f)) for f in filas[1:] if any(f)]


def armar_fisico(unidades: list[dict]) -> tuple[dict, collections.Counter]:
    fisico = {"peugeot": [], "citroen": []}
    fuera = collections.Counter()
    grupos = collections.defaultdict(list)
    for u in unidades:
        marca = u["Marca"].lower().replace("ë", "e")
        if marca not in fisico:
            fuera[f"otra marca: {u['Marca']}"] += 1
            continue
        if u["Estado Dealer"].upper() not in ESTADOS_DEALER_OK:
            fuera[f"{u['Marca']} · {u['Estado Dealer']}"] += 1
            continue
        grupos[(marca, u["Modelo"])].append({   # SOLO estos campos: nada de costos ni margen
            "vin": u["Numero VIN"],
            "version": u["Versión"],
            "color": u["Color Exterior"],
            "sucursal": u.get("Sucursal", ""),
            "bodega": u.get("Bodega", ""),
        })
    for (marca, modelo), det in sorted(grupos.items(), key=lambda kv: (kv[0][0], kv[0][1].upper())):
        det.sort(key=lambda x: (x["version"], x["color"], x["vin"]))
        fisico[marca].append({"modelo": modelo, "n": len(det), "det": det})
    return fisico, fuera


def escribir_stock_html(fisico: dict, fecha: str) -> None:
    html = STOCK_HTML.read_text(encoding="utf-8")
    nuevo = "const fisico = " + json.dumps(fisico, ensure_ascii=False, separators=(",", ":")) + ";\n"
    html, n = re.subn(r"const fisico = \{.*?\};\n", lambda _: nuevo, html, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError("No encontré el bloque `const fisico = {...};` en stock.html.")
    html, n = re.subn(r"(Última actualización: <b>)[^<]*(</b>)", rf"\g<1>{fecha}\g<2>", html, count=1)
    if n != 1:
        raise RuntimeError("No encontré 'Última actualización' en stock.html.")
    STOCK_HTML.write_text(html, encoding="utf-8", newline="")


# ---------------------------------------------------------------- publicar
CAMPOS_PUBLICOS = {"vin", "version", "color", "sucursal", "bodega"}


def git(*args: str) -> str:
    import subprocess
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} falló:\n{r.stdout}{r.stderr}")
    return r.stdout.strip()


def total_publicado() -> int:
    """Unidades del bloque fisico que hay HOY en GitHub (para detectar una bajada a medias)."""
    html = git("show", "HEAD:stock.html")
    m = re.search(r"const fisico = (\{.*?\});\n", html, flags=re.S)
    d = json.loads(m.group(1))
    return sum(x["n"] for marca in d.values() for x in marca)


def publicar(fisico: dict, mensaje: str) -> None:
    """Sube SOLO stock.html. Controles: sin campos de costo, sin caída brusca de unidades."""
    for marca in fisico.values():
        for grupo in marca:
            for u in grupo["det"]:
                if set(u) != CAMPOS_PUBLICOS:
                    raise RuntimeError(f"Campos no permitidos en stock.html: {set(u) - CAMPOS_PUBLICOS}")
    nuevo = sum(x["n"] for marca in fisico.values() for x in marca)
    antes = total_publicado()
    if antes and nuevo < antes * 0.6:
        raise RuntimeError(f"Bajó de {antes} a {nuevo} unidades de un día para otro (>40%). "
                           f"No publico: revisar a mano por si APC exportó a medias.")
    git("pull", "--ff-only", "origin", "main")
    if not git("status", "--porcelain", "--", "stock.html"):
        log("Sin cambios en el stock respecto de lo publicado. Nada que subir.")
        return
    git("commit", "-m", mensaje, "--", "stock.html")
    git("push", "origin", "main")
    log(f"Publicado ({antes} -> {nuevo} unidades). En vivo en ~1 min: "
        "https://miguelcastroyevenes-glitch.github.io/mi-app/stock.html")


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description="Stock físico desde APC -> stock.html")
    ap.add_argument("--aplicar", action="store_true", help="reescribe stock.html (sin esto, solo ensayo)")
    ap.add_argument("--publicar", action="store_true", help="escribe stock.html y lo sube a GitHub (solo ese archivo)")
    ap.add_argument("--ver", action="store_true", help="muestra el navegador mientras trabaja")
    ap.add_argument("--archivos", nargs="+", type=Path, help="usar exports ya bajados en vez de entrar a APC")
    a = ap.parse_args()

    if a.archivos:
        archivos = {p.name: (p, None) for p in a.archivos}
    else:
        archivos = bajar_de_apc(a.ver)

    unidades = []
    log("3. Leyendo exports...")
    for nombre, (ruta, en_pantalla) in archivos.items():
        filas = leer_export(ruta)
        aviso = ""
        if en_pantalla is not None and en_pantalla != len(filas):
            aviso = f"  <-- OJO: APC mostraba {en_pantalla}"
        log(f"   {ruta.name}: {len(filas)} unidades{aviso}")
        unidades += filas

    fisico, fuera = armar_fisico(unidades)
    tot = {m: sum(x["n"] for x in fisico[m]) for m in fisico}
    log(f"\nStock físico vendible: {tot['peugeot']} Peugeot · {tot['citroen']} Citroën")
    for m in fisico:
        log(f"  {m}: " + ", ".join(f"{x['modelo']} {x['n']}" for x in fisico[m]))
    if fuera:
        log("Fuera de la página (no DISPONIBLE u otra marca): " + ", ".join(f"{k} {v}" for k, v in fuera.items()))

    if a.aplicar or a.publicar:
        escribir_stock_html(fisico, dt.date.today().strftime("%d-%m-%Y"))
        log("\nstock.html actualizado.")
        if a.publicar:
            publicar(fisico, f"stock APC: corte del {dt.date.today():%d-%m-%Y} "
                             f"({sum(x['n'] for x in fisico['peugeot'])} P · {sum(x['n'] for x in fisico['citroen'])} C)")
    else:
        log("\nENSAYO: stock.html no se tocó. Agrega --aplicar para escribirlo.")


if __name__ == "__main__":
    main()
