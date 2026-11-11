"""Vitrina Quilín: revisa qué modelos del line up faltan libres en Quilín y los pide a KAR en Roma.

Plan aprobado: OS/work/vitrina-automatica (handshake, scavenge y mapping del 05-11-2026).
- Por defecto es ENSAYO: lee APC y Roma y dice qué pediría. Solo escribe en Roma con --escribir.
- Un cupo falta si no hay ningún auto "Disponible" (Estado AutoPro) de ese modelo en Quilín.
- "Ya pedido": solicitud PENDIENTE de Miguel hacia Quilín cuyo chasis sigue en la bodega KAR.
- Se pide el auto de KAR con más días en bodega; si Roma dice "ya se encuentra tomado", el siguiente.
- Landtrek, Rifter y C5 Aircross no se piden solos (test car); se pueden dictar con --dictar.
- Nunca escribe a nadie ni muestra costo, margen, bono ni precio de compra.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import actualizar_stock_apc as apc  # noqa: E402  (lector del xls de APC)

ROMA_ENV = Path(r"C:\Proyectos\vigia-roma\.env")
CTRL = "/php/controller/controller.trasladoNoVenta.php"
DESTINO_QUILIN = "52"   # STOCK CITROEN QUILIN (también para Peugeot)
ORIGEN_KAR = "53"       # KAR-LOGISTICS
TIPO_VITRINA = "28"     # Traslado Bodega a Vitrina
MARCA_ROMA = {"PEUGEOT": "16", "CITROEN": "21"}
ESTADOS_DEALER_PEDIBLES = ("DISPONIBLE", "EN REVISION")  # primero DISPONIBLE


@dataclass(frozen=True)
class Modelo:
    nombre: str
    marca: str
    roma: str
    apc: tuple[str, ...]
    cupo: str | None  # None = excepción: solo se pide si Miguel lo dicta


MODELOS = [
    Modelo("208", "PEUGEOT", "105", ("208", "nuevo 208"), "208"),
    Modelo("2008", "PEUGEOT", "108", ("2008", "nuevo 2008"), "2008"),
    Modelo("308", "PEUGEOT", "107", ("308", "nuevo 308"), "308"),
    Modelo("3008", "PEUGEOT", "109", ("3008", "nuevo 3008"), "3008"),
    Modelo("5008", "PEUGEOT", "110", ("5008", "nuevo 5008"), "5008"),
    Modelo("Partner", "PEUGEOT", "112", ("partner", "nueva partner"), "Partner"),
    Modelo("Traveller", "PEUGEOT", "114", ("traveller",), "Traveller"),
    Modelo("Boxer", "PEUGEOT", "115", ("boxer",), "Jumper o Boxer"),
    Modelo("Expert", "PEUGEOT", "113", ("expert",), "Jumpy o Expert"),
    Modelo("Rifter", "PEUGEOT", "111", ("rifter",), None),
    Modelo("Landtrek", "PEUGEOT", "161", ("landtrek",), None),
    Modelo("C3", "CITROEN", "239", ("c3",), "C3"),
    Modelo("C4", "CITROEN", "241", ("c4",), "C4"),
    Modelo("C3 Aircross", "CITROEN", "1554", ("c3 aircross", "new c3 aircross"), "C3 Aircross"),
    Modelo("Berlingo Multispace", "CITROEN", "1490", ("berlingo vp", "berlingo multispace"), "Berlingo Multispace"),
    Modelo("Berlingo", "CITROEN", "244", ("berlingo vu", "berlingo"), "Berlingo"),
    Modelo("Basalt", "CITROEN", "1565", ("basalt",), "Basalt"),
    Modelo("Spacetourer", "CITROEN", "1492", ("spacetourer",), "Spacetourer"),
    Modelo("Jumper", "CITROEN", "1555", ("jumper",), "Jumper o Boxer"),
    Modelo("Jumpy", "CITROEN", "1493", ("jumpy",), "Jumpy o Expert"),
    Modelo("C5 Aircross", "CITROEN", "775", ("c5", "c5 aircross"), None),
]
CUPOS = list(dict.fromkeys(m.cupo for m in MODELOS if m.cupo))  # 16 cupos, en orden
_POR_APC = {(m.marca, a): m for m in MODELOS for a in m.apc}


def _norm(texto: str) -> str:
    return re.sub(r"\s+", " ", str(texto or "").strip().lower())


def modelo_de(fila: dict) -> Modelo | None:
    marca = _norm(fila.get("Marca")).upper().replace("Ë", "E")
    return _POR_APC.get((marca, _norm(fila.get("Modelo"))))


def _dias(fila: dict) -> int:
    try:
        return int(str(fila.get("Días Stock") or "0").strip())
    except ValueError:
        return 0


def en_kar(fila: dict) -> bool:
    return str(fila.get("Bodega", "")).strip().upper() == "KAR-LOGISTICS"


def pedibles_kar(kar: list[dict]) -> list[dict]:
    """Autos en la bodega KAR que se pueden pedir: Disponible en AutoPro, primero Dealer DISPONIBLE, más días primero."""
    filas = [f for f in kar if en_kar(f) and _norm(f.get("Estado AutoPro")) == "disponible"
             and str(f.get("Estado Dealer", "")).strip().upper() in ESTADOS_DEALER_PEDIBLES]
    return sorted(filas, key=lambda f: (ESTADOS_DEALER_PEDIBLES.index(str(f["Estado Dealer"]).strip().upper()), -_dias(f)))


def vin_de(fila: dict) -> str:
    return str(fila.get("Numero Chasis") or fila.get("Numero VIN") or "").strip().upper()


@dataclass
class Cupo:
    nombre: str
    estado: str  # "libre" | "ya pedido" | "pedir" | "no hay en KAR"
    libres: list[dict] = field(default_factory=list)
    pedido_previo: dict | None = None
    candidatos: list[dict] = field(default_factory=list)


def cruzar(quilin: list[dict], kar: list[dict], solicitudes: list[dict]) -> tuple[list[Cupo], list[str]]:
    """Cruce puro (sin red). Devuelve los 16 cupos y los modelos que APC trae con un nombre desconocido."""
    revisar = quilin + [f for f in kar if en_kar(f)]
    desconocidos = sorted({f"{f.get('Marca')} {f.get('Modelo')}" for f in revisar if f.get("Modelo") and modelo_de(f) is None})
    kar_por_vin = {vin_de(f): f for f in kar if en_kar(f)}
    pedibles = pedibles_kar(kar)
    pendientes = {}
    for s in solicitudes:
        if str(s.get("EstadoTxt", "")).upper() != "PENDIENTE" or "QUILIN" not in str(s.get("BodegaDestino", "")).upper():
            continue
        fila = kar_por_vin.get(str(s.get("vin", "")).strip().upper())
        m = modelo_de(fila) if fila else None
        if m and m.cupo and m.cupo not in pendientes:
            pendientes[m.cupo] = {**s, "_fila": fila}
    cupos = []
    for nombre in CUPOS:
        libres = [f for f in quilin if (m := modelo_de(f)) and m.cupo == nombre and _norm(f.get("Estado AutoPro")) == "disponible"]
        if libres:
            cupos.append(Cupo(nombre, "libre", libres=libres)); continue
        if nombre in pendientes:
            cupos.append(Cupo(nombre, "ya pedido", pedido_previo=pendientes[nombre])); continue
        cands = [f for f in pedibles if (m := modelo_de(f)) and m.cupo == nombre]
        cupos.append(Cupo(nombre, "pedir" if cands else "no hay en KAR", candidatos=cands))
    return cupos, desconocidos


def candidatos_dictado(texto: str, kar: list[dict]) -> tuple[str, list[dict]]:
    """'2008 GT' -> autos de 2008 en KAR cuya versión o color contiene GT. 'Aircross' solo = C5 Aircross."""
    t = _norm(texto)
    if t == "aircross" or t.startswith("aircross "):
        t = "c5 " + t
    elegido, resto = None, ""
    for m in sorted(MODELOS, key=lambda m: -max(len(a) for a in m.apc)):
        for alias in sorted(m.apc, key=len, reverse=True):
            if t == alias or t.startswith(alias + " "):
                elegido, resto = m, t[len(alias):].strip(); break
        if elegido:
            break
    if not elegido:
        return texto, []
    palabras = resto.split()
    cands = [f for f in pedibles_kar(kar) if modelo_de(f) == elegido
             and all(p in _norm(f"{f.get('Versión')} {f.get('Color Exterior')}") for p in palabras)]
    return f"{elegido.nombre} {resto}".strip(), cands


class RomaRaro(RuntimeError):
    """Roma respondió algo que no es una lista: no se sigue pidiendo a ciegas."""


class Roma:
    def __init__(self):
        import requests
        from urllib.parse import urljoin
        from dotenv import dotenv_values
        env = dotenv_values(ROMA_ENV)
        if not env.get("ROMA_URL"):
            raise RuntimeError(f"Falta ROMA_URL en {ROMA_ENV}")
        self._url = lambda p: urljoin(env["ROMA_URL"], p)
        self.s = requests.Session(); self.s.headers["X-Requested-With"] = "XMLHttpRequest"
        d = self.s.post(self._url("/php/controller/controller.session.php"), data={
            "session_email": env["ROMA_USER"], "session_pass": env["ROMA_PASSWORD"], "action": "sessionOpen"}, timeout=30).json()
        self.u = json.dumps([{"usuario": d[0]["usuario"], "cookie": d[0]["cookie"]}])

    def post(self, datos: dict) -> list:
        r = self.s.post(self._url(CTRL), data={**datos, "usuario": self.u}, timeout=60)
        r.encoding = "utf-8"
        if not r.text.lstrip().startswith("["):
            raise RomaRaro(f"{datos['action']}: Roma respondió algo inesperado")
        return r.json()

    def solicitudes(self) -> list[dict]:
        return self.post({"FILTRO_bodegasOrigen": "null", "FILTRO_bodegasDestino": "null", "FILTRO_sol": "null",
                          "FILTRO_estado": "null", "btn_misPendientes": "0", "action": "ListarRegistros"})

    def crear(self, fila: dict) -> dict:
        m = modelo_de(fila); vin = vin_de(fila)
        res = self.post({"fecha_traslado": dt.date.today().isoformat(), "tiposol": TIPO_VITRINA,
                         "marca": MARCA_ROMA[m.marca], "sucursal_origen": ORIGEN_KAR, "sucursal_destino": DESTINO_QUILIN,
                         "cajon": vin[-8:], "vin": vin, "modelo_generico": m.roma, "modelo_txt": "",
                         "detalle": "vitrina", "action": "CrearSolTrasladoNoVenta"})
        return res[0] if res else {}


def pedir(nombre: str, candidatos: list[dict], crear, escribir: bool) -> dict:
    """Prueba los candidatos en orden hasta que Roma acepte uno. `crear` recibe la fila y devuelve la respuesta de Roma."""
    if not escribir:
        return {"nombre": nombre, "resultado": "se pediría", "fila": candidatos[0], "tomados": []}
    tomados, otros = [], []
    for fila in candidatos:
        r = crear(fila)
        if str(r.get("type")) == "1":
            return {"nombre": nombre, "resultado": "pedido", "fila": fila, "tomados": tomados, "otros": otros}
        msg = str(r.get("message", ""))
        (tomados if "tomado" in msg.lower() else otros).append((vin_de(fila), msg))
    return {"nombre": nombre, "resultado": "ninguno entró", "fila": None, "tomados": tomados, "otros": otros}


def _auto(f: dict) -> str:
    return f"{f.get('Versión') or f.get('Modelo')} · {str(f.get('Color Exterior') or '').title()} · {vin_de(f)} · {_dias(f)} días en KAR"


def bloque(cupos: list[Cupo], pedidos: list[dict], desconocidos: list[str], escribir: bool, numeros: dict, falla: str = "") -> str:
    libres = [c for c in cupos if c.estado == "libre"]
    lineas = [f"VITRINA QUILÍN · {len(libres)} de {len(cupos)} modelos con auto libre en el local."]
    verbo = "Pedido hoy a KAR" if escribir else "ENSAYO · se pediría a KAR"
    hechos = [p for p in pedidos if p["fila"] is not None]
    if hechos:
        lineas.append(f"{verbo}:")
        for p in hechos:
            nro = f" · solicitud {numeros[vin_de(p['fila'])]}" if vin_de(p["fila"]) in numeros else ""
            lineas.append(f"- {p['nombre']}: {_auto(p['fila'])}{nro}")
    fallidos = [p for p in pedidos if p["fila"] is None]
    if fallidos:
        lineas.append("No se pudo pedir (todos los chasis ya tomados por otra solicitud):")
        lineas += [f"- {p['nombre']}" for p in fallidos]
    ya = [c for c in cupos if c.estado == "ya pedido"]
    if ya:
        lineas.append("Ya pedido (el auto sigue en KAR):")
        lineas += [f"- {c.nombre}: solicitud {c.pedido_previo.get('ID')} del {str(c.pedido_previo.get('FechaCreacion', ''))[:10]}" for c in ya]
    no_hay = [c.nombre for c in cupos if c.estado == "no hay en KAR"]
    if no_hay:
        lineas.append("Falta en el local y no hay en KAR: " + ", ".join(no_hay) + ".")
    if desconocidos:
        lineas.append("Modelos que no reconozco (no se cruzaron): " + ", ".join(desconocidos) + ".")
    if falla:
        lineas.append(f"Ojo: {falla}")
    return "\n".join(lineas)


def _ultimo(patron: str, carpeta: Path) -> Path:
    archivos = sorted(carpeta.glob(patron), key=lambda p: p.stat().st_mtime)
    if not archivos:
        raise RuntimeError(f"No encontré descargas {patron} en {carpeta}")
    return archivos[-1]


def leer_descargas() -> tuple[list[dict], list[dict]]:
    quilin, kar = [], []
    for marca in ("peugeot", "citroen"):
        quilin += apc.leer_export(_ultimo(f"quilin-{marca}-*.xls", apc.DESCARGAS / "quilin"))
        kar += apc.leer_export(_ultimo(f"stock-apc-{marca}-*.xls", apc.DESCARGAS))
    return quilin, kar


def correr(escribir: bool, dictado: list[str] | None = None, roma: Roma | None = None,
           descargas: tuple[list[dict], list[dict]] | None = None) -> str:
    quilin, kar = descargas or leer_descargas()
    roma = roma or Roma()
    cupos, desconocidos = cruzar(quilin, kar, roma.solicitudes())
    pedidos, falla = [], ""
    if dictado:
        objetivos = [candidatos_dictado(t, kar) for t in dictado]
        cupos_sin_kar = [n for n, c in objetivos if not c]
        objetivos = [(n, c) for n, c in objetivos if c]
    else:
        objetivos = [(c.nombre, c.candidatos) for c in cupos if c.estado == "pedir"]
        cupos_sin_kar = []
    try:
        for nombre, cands in objetivos:
            pedidos.append(pedir(nombre, cands, roma.crear, escribir))
    except RomaRaro as e:
        falla = f"{e}. Se detuvo para no pedir a ciegas; lo que falta se intenta mañana."
    numeros = {}
    if escribir and any(p["resultado"] == "pedido" for p in pedidos):
        numeros = {str(s.get("vin", "")).upper(): s.get("ID") for s in roma.solicitudes()}
    if not dictado:
        return bloque(cupos, pedidos, desconocidos, escribir, numeros, falla)
    lineas = ["VITRINA QUILÍN · pedido dictado por Miguel" + ("" if escribir else " (ENSAYO)")]
    for p in pedidos:
        if p["fila"] is None:
            lineas.append(f"- {p['nombre']}: no entró, todos los chasis ya tomados por otra solicitud")
        else:
            nro = f" · solicitud {numeros[vin_de(p['fila'])]}" if vin_de(p["fila"]) in numeros else ""
            lineas.append(f"- {p['nombre']}: {'pedido' if escribir else 'se pediría'} {_auto(p['fila'])}{nro}")
    lineas += [f"- {n}: no hay en KAR" for n in cupos_sin_kar]
    if falla:
        lineas.append(f"Ojo: {falla}")
    return "\n".join(lineas)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--escribir", action="store_true", help="crea las solicitudes en Roma (sin esto es ensayo)")
    ap.add_argument("--dictar", help='pedidos de Miguel separados por coma, ej. "2008 GT, Expert, Aircross"')
    a = ap.parse_args()
    dictado = [x.strip() for x in a.dictar.split(",") if x.strip()] if a.dictar else None
    print(correr(a.escribir, dictado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
