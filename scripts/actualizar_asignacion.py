"""actualizar_asignacion.py — pestañas "Asignación de marca" y "Pre inscritas" de stock.html desde el Drive.

Uso:
    python scripts\\actualizar_asignacion.py                 # ensayo: lee files\\Asignacion y muestra el resumen
    python scripts\\actualizar_asignacion.py --aplicar       # además reescribe el bloque `asignacion` de stock.html

De dónde sale (visto el 13-10-2026):
  - "Asignacion Peugeot" y "Asignacion Citroen" (Google Sheets de la marca, compartidas con Miguel).
    Una pestaña por mes, la más nueva primero. Las columnas cambian de nombre de un mes a otro,
    por eso se buscan por contenido (VIN, Modelo/Vehicle Description, Color, Entrega, CAT/Sucursal).
  - Se descargan como .xlsx a C:\\Proyectos\\app-deal\\files\\Asignacion (fuera del repo, que es
    público) con nombre asignacion-<marca>-<aaaa-mm-dd>.xlsx. La fecha del nombre es la del archivo
    en el Drive (última modificación), y es la que se muestra en la página.

Reglas:
  - Se lee SOLO la pestaña más nueva de cada marca (Miguel, 13-10-2026): la jefa la carga ~2 veces al
    mes con lo que compra a Stellantis, y al cerrar el mes esas unidades pasan a Stock físico (APC).
    Las pestañas de meses anteriores ya no cuentan.
  - Si la pestaña más nueva no es del mes en curso (aún no cargan el mes), la página lo avisa.
  - Unidad "En APC" o cuyo VIN ya está en Stock físico: se saca (ya está en la otra pestaña).
  - Con NV / CAT / sucursal escrita: queda "tomada" con ese texto. Sin nada: "Libre".
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
CARPETA = REPO.parent / "files" / "Asignacion"
STOCK_HTML = REPO / "stock.html"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


def limpio(s) -> str:
    if isinstance(s, float) and s.is_integer():
        s = int(s)
    return re.sub(r"\s+", " ", str(s or "")).strip()


def col(cab: list[str], *claves: str) -> int | None:
    for i, c in enumerate(cab):
        if any(k in c.lower() for k in claves):
            return i
    return None


def leer_pestana(ws) -> list[dict]:
    filas = list(ws.iter_rows(values_only=True))
    if not filas:
        return []
    cab = [limpio(c) for c in filas[0]]
    i_vin = col(cab, "vin")
    i_mod = col(cab, "modelo", "vehicle description", "cdc eds")
    i_col = col(cab, "color")
    i_ent = col(cab, "entrega", "disponibilidad")
    i_cat = col(cab, "cat")
    i_suc = col(cab, "sucursal")
    if i_vin is None or i_mod is None:
        return []
    usadas = {i for i in (i_vin, i_mod, i_col, i_ent, i_cat, i_suc) if i is not None}
    if i_cat is None and i_suc is None:                     # a veces la columna de NV viene sin título
        libres = [i for i in range(len(cab)) if i not in usadas and not cab[i]]
        i_cat = libres[-1] if libres else None
    out = []
    for f in filas[1:]:
        g = lambda i: limpio(f[i]) if i is not None and i < len(f) else ""
        vin = g(i_vin).upper()
        if len(vin) != 17:
            continue
        modelo, entrega = g(i_mod), g(i_ent)
        if modelo and modelo == entrega:                   # error de la planilla: modelo = fecha
            modelo = "Modelo sin informar (ver planilla)"
        nv = " ".join(x for x in (g(i_cat), g(i_suc)) if x)
        out.append({"vin": vin, "entrega": entrega, "version": modelo, "color": g(i_col).upper(), "nv": nv})
    return out


def vins_fisico(html: str) -> set[str]:
    i = html.index("const fisico = ") + len("const fisico = ")
    fis = json.JSONDecoder().raw_decode(html[i:])[0]
    return {d["vin"].upper() for m in sum(fis.values(), []) for d in m["det"]}


def ultima_planilla(marca: str) -> Path:
    archivos = sorted(CARPETA.glob(f"asignacion-{marca}-*.xlsx"))
    if not archivos:
        raise SystemExit(f"No hay planilla de {marca} en {CARPETA}")
    return archivos[-1]


SUCURSALES = ("MOVICENTER", "PLAZA SUR", "QUILIN", "IRARRAZAVAL", "EGAÑA", "BILBAO", "ARAUCO",
              "PROFESSIONAL", "CAM")


def tomada_por(texto: str) -> str:
    """El repo es público: de "MOVICENTER 12.345.678-9 / NOMBRE" solo sale "Tomada · MOVICENTER".
    Nunca RUT ni nombres de clientes."""
    t = texto.upper()
    suc = next((s for s in SUCURSALES if re.search(rf"\b{s}\b", t)), None)
    return f"Tomada · {suc.title() if suc != 'CAM' else 'CAM'}" if suc else "Tomada"


def leer_preinscritas() -> tuple[list, dict]:
    """Planilla "Unidades Pre Inscritas TM" (Drive), guardada como preinscritas-<aaaa-mm-dd>.csv (;)."""
    archivos = sorted(CARPETA.glob("preinscritas-*.csv"))
    if not archivos:
        raise SystemExit(f"No hay planilla de pre inscritas en {CARPETA}")
    ruta = archivos[-1]
    grupos = collections.defaultdict(list)
    for linea in ruta.read_text(encoding="utf-8").splitlines()[1:]:
        anio, modelo, version, color, codigo, vin, ppu, precio, nv = (limpio(x) for x in linea.split(";"))
        if len(vin) != 17:
            continue
        grupos[f"{modelo} · año {anio}"].append({
            "vin": vin, "info": f"{version} - Código {codigo} - PPU {ppu} - {precio}",
            "color": color.upper(), "nv": tomada_por(nv) if nv else ""})
    lista = [{"modelo": m, "n": len(us), "det": us} for m, us in sorted(grupos.items(), reverse=True)]
    f = re.search(r"(\d{4})-(\d{2})-(\d{2})", ruta.name)
    return lista, {"fecha": f"{f[3]}-{f[2]}-{f[1]}"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Asignación de marca desde las planillas del Drive")
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()

    html = STOCK_HTML.read_text(encoding="utf-8")
    en_fisico = vins_fisico(html)
    asignacion, meta = {}, {}
    for marca in ("peugeot", "citroen"):
        ruta = ultima_planilla(marca)
        wb = openpyxl.load_workbook(ruta, data_only=True)
        hojas = wb.sheetnames[:1]                          # solo el mes en curso
        vistos, unidades, sacadas = set(), [], 0
        for h in hojas:
            for u in leer_pestana(wb[h]):
                if u["vin"] in vistos:
                    continue
                vistos.add(u["vin"])
                if "apc" in u["nv"].lower() or u["vin"] in en_fisico:
                    sacadas += 1
                    continue
                u["mes"] = h
                unidades.append(u)
        grupos = collections.defaultdict(list)
        for u in unidades:
            grupos[u["version"]].append(u)
        asignacion[marca] = [{"modelo": m, "n": len(us), "det": us}
                             for m, us in sorted(grupos.items(), key=lambda kv: (-len(kv[1]), kv[0]))]
        fecha = re.search(r"(\d{4})-(\d{2})-(\d{2})", ruta.name)
        mes_hoy = MESES[dt.date.today().month - 1]
        meta[marca] = {"fecha": f"{fecha[3]}-{fecha[2]}-{fecha[1]}", "pestana": hojas[0],
                       "al_dia": hojas[0].lower().startswith(mes_hoy)}
        libres = sum(1 for u in unidades if not u["nv"])
        aviso = "" if meta[marca]["al_dia"] else f"  ⚠ aún no cargan {mes_hoy}"
        print(f"{marca}: pestaña {hojas[0]} · {len(unidades)} unidades ({libres} libres, "
              f"{len(unidades) - libres} tomadas) · {sacadas} ya en APC/Stock físico{aviso}")

    bloque = (f"const asignacion = {json.dumps(asignacion, ensure_ascii=False)};\n"
              f"const asignacionMeta = {json.dumps(meta, ensure_ascii=False)};")
    nuevo = re.sub(r"const asignacion = .*?;\n(const asignacionMeta = .*?;\n)?",
                   lambda _: bloque + "\n", html, count=1, flags=re.S)

    pre, pre_meta = leer_preinscritas()
    n = sum(m["n"] for m in pre)
    libres = sum(1 for m in pre for u in m["det"] if not u["nv"])
    print(f"pre inscritas: planilla del {pre_meta['fecha']} · {n} unidades ({libres} libres, {n - libres} tomadas)")
    bloque = (f"const preinscritas = {json.dumps(pre, ensure_ascii=False)};\n"
              f"const preinscritasMeta = {json.dumps(pre_meta, ensure_ascii=False)};")
    nuevo = re.sub(r"const preinscritas = .*?;\n(const preinscritasMeta = .*?;\n)?",
                   lambda _: bloque + "\n", nuevo, count=1, flags=re.S)
    if not a.aplicar:
        print("\nENSAYO: stock.html no se tocó. Agrega --aplicar para escribirlo.")
        return
    STOCK_HTML.write_text(nuevo, encoding="utf-8", newline="")
    print("\nstock.html actualizado (pestaña Asignación de marca).")


if __name__ == "__main__":
    main()
