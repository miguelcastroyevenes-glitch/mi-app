#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tutor.py — Caja de herramientas determinística del Tutor de IA Agéntica.

El tutor es, a propósito, un ejemplo didáctico de agente:

  * CONTEXTO     → curriculo/malla.json (qué se estudia) y base/ (fuentes y fichas).
  * HERRAMIENTAS → este archivo: comandos que el LLM invoca en vez de «calcular de memoria».
  * MEMORIA      → progreso/estado.json, progreso/tarjetas.json y progreso/bitacora.md.
  * EVALUACIÓN   → aprobar-semana (evidencia + rúbrica con umbral), repetición espaciada y `validar`.

Regla de diseño: lo que tiene que pasar siempre lo hace el código (fechas, racha, repasos
vencidos, qué toca hoy, si una evidencia tiene forma mínima, si la rúbrica alcanza el
umbral). El LLM explica, pregunta, puntúa cada criterio con evidencia y da feedback.

Reglas de investigacion/03 que este código hace cumplir:
  * sesiones micro 15 / estándar 30 / laboratorio 75 min;
  * racha SEMANAL: piso de 3 sesiones o 60 min (cierre de mes: 2 o 30), 1 comodín al mes,
    una semana fallida se repara con 2 sesiones (o el piso) la semana siguiente, pausas congelan;
  * retorno: 1–2 días no se menciona · 3–6 reentrada · 7+ reinicio limpio (sin contar días perdidos);
  * semana de cierre de mes = modo mantenimiento (sin contenido nuevo);
  * bitácora de una fila por sesión con si-entonces; parking de ideas.
Y de investigacion/01: la aprobación la decide el código (rúbrica 0–3, mínimo 2 por criterio)
y cada etapa cierra con un checkpoint sin IA.

Solo biblioteca estándar de Python 3 (>= 3.9).

Fechas inyectables para pruebas:  --hoy AAAA-MM-DD   o   TUTOR_HOY=AAAA-MM-DD
Raíz inyectable (simulación/tests): --raiz RUTA      o   TUTOR_RAIZ=RUTA
Progreso en otra carpeta (p. ej. un repo privado): --progreso RUTA o TUTOR_PROGRESO=RUTA
"""
from __future__ import annotations

import argparse
import calendar
import html
import json
import math
import os
import re
import sys
import unicodedata
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

VERSION = "1.1.0"
RAIZ_DEFECTO = Path(__file__).resolve().parent.parent
ZONA_HORARIA = "America/Santiago"
NOMBRE_SKILL = "tutor-ia-agentica"

# --- Lo que la malla (malla-curricular.html) exige. `validar` lo hace cumplir. ---
ETAPAS_MALLA = {
    1: {"semanas": (1, 3), "horas": 24},
    2: {"semanas": (4, 6), "horas": 28},
    3: {"semanas": (7, 10), "horas": 36},
    4: {"semanas": (11, 14), "horas": 34},
    5: {"semanas": (15, 19), "horas": 40},
    6: {"semanas": (20, 24), "horas": 48},
}
PROYECTOS_MALLA = {
    3: "AI Opportunity Map",
    6: "Sales Intelligence Agent",
    10: "Tool-Using Agent",
    14: "AI Sales Team",
    19: "Agent QA Lab",
    24: "Capstone",
}
FIN_DE_ETAPA = {v["semanas"][1] for v in ETAPAS_MALLA.values()}  # 3, 6, 10, 14, 19, 24
TOTAL_SEMANAS = 24
SEMANA_FIN = TOTAL_SEMANAS + 1  # semana_actual == 25 ⇒ programa completado
HORAS_TOTALES_MALLA = 210
TOLERANCIA_HORAS_TOTAL = 5
TOLERANCIA_HORAS_ETAPA = 1

CAMPOS_SEMANA = (
    "semana", "etapa", "titulo", "objetivo", "conceptos", "lectura", "laboratorio",
    "entregable", "evidencia_de_dominio", "preguntas_de_repaso", "horas", "version_micro",
)
CAMPOS_FUENTE = ("id", "titulo", "autor", "anio", "url", "idioma", "tipo", "nivel",
                 "minutos", "acceso", "etapas", "semanas", "nucleo", "por_que")

MODOS = {"micro": 15, "estandar": 30, "lab": 75}
TIPOS_SESION = ("micro", "estandar", "lab", "repaso", "produccion")
LOGRADO = ("si", "parcial", "no")
TOPE_LAB_MINUTOS = 145  # 2 h + una extensión de 25 min decidida explícitamente

CONFIG_DEFECTO = {
    "piso_sesiones": 3,
    "piso_minutos": 60,
    "piso_cierre_sesiones": 2,
    "piso_cierre_minutos": 30,
    "comodines_por_mes": 1,
    "sesiones_para_reparar": 2,
    "dias_cierre_mes": 7,
    "dias_por_semana_de_contenido": 10,  # calendario honesto: 24 semanas ≈ 8 meses
    # 03: «jueves a domingo tiene poco tiempo». Esos días no cuentan como «días fuera» (0 = lunes).
    "dias_de_baja_disponibilidad": [3, 4, 5, 6],
}

CRITERIOS = {
    "entregable": "El entregable de la semana existe y cumple lo pedido.",
    "explicacion": "Explica sin mirar: 3 = correcto + cuándo NO aplica + ejemplo propio.",
    "recuperacion": "Responde sin mirar las preguntas de repaso de la semana.",
    "sin_ia": ("Checkpoint sin IA de la etapa: quiz cerrado, bug-hunt cronometrado o explicar "
               "su propio código línea a línea, sin asistencia."),
}
UMBRAL_RUBRICA = 2
ESCALA_RUBRICA = "0 no hay · 1 insuficiente · 2 suficiente · 3 sólido (mínimo 2 en cada criterio)"

EF_INICIAL = 2.5
EF_MINIMO = 1.3
INTERVALO_MAXIMO = 120

FRASES_DISPARO = ("sesión de hoy", "tutor", "estudiemos", "repaso", "retomar", "cómo voy")
SECCIONES_SKILL = ("Protocolo de sesión", "SIEMPRE", "NUNCA", "Modo sin archivos")
MARCA_INTEGRAR = "<!-- INTEGRAR: reglas del tutor (03) y reglas no negociables (01) -->"
MARCA_PENDIENTE = "Pendiente de integración"

DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

ESCALA_CALIDAD = ("5 perfecta sin dudar · 4 bien con alguna duda · 3 bien con esfuerzo · "
                  "2 mal, pero la reconocí al ver la respuesta · 1 mal · 0 en blanco")


class ErrorTutor(Exception):
    """Error esperable, con mensaje para Miguel (no un bug)."""


# ---------------------------------------------------------------------------
# Rutas y utilidades
# ---------------------------------------------------------------------------
class Rutas:
    def __init__(self, raiz: Path | str, progreso: Path | str | None = None):
        self.raiz = Path(raiz).resolve()
        self.malla = self.raiz / "curriculo" / "malla.json"
        self.fuentes = self.raiz / "base" / "fuentes.json"
        self.fichas = self.raiz / "base" / "fichas"
        self.progreso = Path(progreso).resolve() if progreso else self.raiz / "progreso"
        self.estado = self.progreso / "estado.json"
        self.tarjetas = self.progreso / "tarjetas.json"
        self.bitacora = self.progreso / "bitacora.md"
        self.panel = self.progreso / "panel.html"
        self.skill_dir = self.raiz / ".claude" / "skills" / NOMBRE_SKILL
        self.skill = self.skill_dir / "SKILL.md"
        self.dist = self.raiz / "dist"
        self.investigacion = self.raiz / "investigacion"

    def rel(self, ruta: Path) -> str:
        try:
            return str(Path(ruta).resolve().relative_to(self.raiz))
        except ValueError:
            return str(ruta)


def resolver_rutas(raiz: str | None = None, progreso: str | None = None) -> Rutas:
    """Con --raiz explícito, el progreso vive dentro de esa raíz salvo --progreso (así la
    simulación y los tests nunca tocan el progreso real aunque exista TUTOR_PROGRESO)."""
    if raiz:
        return Rutas(raiz, progreso)
    return Rutas(os.environ.get("TUTOR_RAIZ") or RAIZ_DEFECTO, progreso or os.environ.get("TUTOR_PROGRESO"))


def parse_fecha(texto, campo: str = "fecha") -> date:
    try:
        return date.fromisoformat(str(texto).strip())
    except (ValueError, TypeError):
        raise ErrorTutor(f"Fecha inválida en {campo}: «{texto}». Usa AAAA-MM-DD.")


def fecha_hoy(valor: str | None = None) -> date:
    """--hoy > TUTOR_HOY > fecha actual en Chile (zona America/Santiago)."""
    texto = valor or os.environ.get("TUTOR_HOY")
    if texto:
        return parse_fecha(texto, "--hoy / TUTOR_HOY")
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo(ZONA_HORARIA)).date()
    except Exception:  # sin base de zonas horarias: fecha local del sistema
        return date.today()


def fecha_corta(d: date) -> str:
    return f"{DIAS[d.weekday()]} {d.day:02d}-{MESES[d.month - 1]}-{d.year}"


def formato_minutos(m: float) -> str:
    m = int(round(m))
    if m < 60:
        return f"{m} min"
    h, r = divmod(m, 60)
    return f"{h} h {r:02d} min" if r else f"{h} h"


def normalizar(texto: str) -> str:
    """minúsculas y sin tildes, para comparar texto libre."""
    t = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in t if not unicodedata.combining(c)).lower()


def leer_json(ruta: Path):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def escribir_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, ruta)


def id_tarjeta_malla(semana: int, i: int) -> str:
    return f"s{semana:02d}-p{i}"


def lunes_de(d: date) -> date:
    return d - timedelta(days=d.weekday())


def ultimo_dia_mes(d: date) -> int:
    return calendar.monthrange(d.year, d.month)[1]


def criterios_semana(n: int) -> list[str]:
    base = ["entregable", "explicacion", "recuperacion"]
    return base + (["sin_ia"] if n in FIN_DE_ETAPA else [])


# ---------------------------------------------------------------------------
# Contexto: malla, fuentes y fichas
# ---------------------------------------------------------------------------
def cargar_malla(rutas: Rutas) -> dict:
    if not rutas.malla.exists():
        raise ErrorTutor(f"No existe {rutas.rel(rutas.malla)}.")
    try:
        return leer_json(rutas.malla)
    except json.JSONDecodeError as e:
        raise ErrorTutor(f"curriculo/malla.json no es JSON válido: {e}")


def semanas_de(malla: dict) -> dict:
    return {s["semana"]: s for s in malla.get("semanas", [])
            if isinstance(s, dict) and isinstance(s.get("semana"), int)}


def etapa_de(malla: dict, numero) -> dict:
    for e in malla.get("etapas", []):
        if isinstance(e, dict) and e.get("numero") == numero:
            return e
    return {"numero": numero, "nombre": f"Etapa {numero}"}


def leer_lista_fuentes(rutas: Rutas):
    """Lista de fuentes de base/fuentes.json, o None si el archivo aún no existe."""
    if not rutas.fuentes.exists():
        return None
    datos = leer_json(rutas.fuentes)
    if isinstance(datos, dict):
        datos = datos.get("fuentes", [])
    if not isinstance(datos, list):
        raise ErrorTutor("base/fuentes.json debe ser una lista de fuentes (o {\"fuentes\": [...]}).")
    return datos


def indice_fuentes(lista) -> dict:
    return {f["id"]: f for f in (lista or []) if isinstance(f, dict) and isinstance(f.get("id"), str)}


RE_TITULO_PREGUNTAS = re.compile(r"^##\s+preguntas\s+de\s+pr[aá]ctica\s*:?\s*$", re.I)
RE_P = re.compile(r"^[-*]\s*P\s*:\s*(.*)$")
RE_R = re.compile(r"^(?:[-*]\s*)?R\s*:\s*(.*)$")


def parsear_ficha(texto: str) -> dict:
    """Extrae los pares P/R de la sección «## Preguntas de práctica» de una ficha.

    Formato esperado:
        ## Preguntas de práctica
        - P: pregunta
          R: respuesta
    """
    en_seccion = False
    encontrada = False
    pares, errores = [], []
    actual, campo = None, None

    def cerrar():
        if actual is not None:
            pares.append(actual)

    for i, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if RE_TITULO_PREGUNTAS.match(s):
            en_seccion, encontrada = True, True
            continue
        if en_seccion and re.match(r"^#{1,2}\s", s):
            en_seccion = False
            continue
        if not en_seccion or not s or s.startswith("#"):
            continue
        m = RE_P.match(s)
        if m:
            cerrar()
            actual, campo = {"pregunta": m.group(1).strip(), "respuesta": "", "linea": i}, "pregunta"
            continue
        m = RE_R.match(s)
        if m:
            if actual is None:
                errores.append(f"línea {i}: «R:» sin una «P:» antes")
                continue
            if actual["respuesta"]:
                errores.append(f"línea {i}: segunda «R:» para la misma pregunta")
            actual["respuesta"] = m.group(1).strip()
            campo = "respuesta"
            continue
        if actual is not None and campo:
            actual[campo] = (actual[campo] + " " + s).strip()
    cerrar()

    preguntas = []
    for par in pares:
        if not par["pregunta"]:
            errores.append(f"línea {par['linea']}: «P:» vacía")
        elif not par["respuesta"]:
            errores.append(f"línea {par['linea']}: la pregunta no tiene «R:»")
        else:
            preguntas.append((par["pregunta"], par["respuesta"]))
    return {"encontrada": encontrada, "preguntas": preguntas, "errores": errores}


def cargar_fichas(rutas: Rutas) -> dict:
    fichas = {}
    if rutas.fichas.is_dir():
        for ruta in sorted(rutas.fichas.glob("*.md")):
            info = parsear_ficha(ruta.read_text(encoding="utf-8"))
            info["ruta"] = ruta
            fichas[ruta.stem] = info
    return fichas


def catalogo_preguntas(malla: dict, fichas: dict) -> dict:
    """Todas las tarjetas posibles: id → {origen, semana|ficha, pregunta, respuesta}."""
    cat = {}
    for n, s in sorted(semanas_de(malla).items()):
        for i, q in enumerate(s.get("preguntas_de_repaso") or [], 1):
            if isinstance(q, dict):
                cat[id_tarjeta_malla(n, i)] = {"origen": "malla", "semana": n,
                                               "pregunta": q.get("pregunta", ""),
                                               "respuesta": q.get("respuesta", "")}
    for fid, info in sorted(fichas.items()):
        for i, (p, r) in enumerate(info.get("preguntas", []), 1):
            cat[f"f-{fid}-p{i}"] = {"origen": "ficha", "ficha": fid, "semana": None,
                                    "pregunta": p, "respuesta": r}
    return cat


# ---------------------------------------------------------------------------
# Memoria: estado, tarjetas y bitácora
# ---------------------------------------------------------------------------
def estado_inicial(hoy: date) -> dict:
    return {
        "version": 2,
        "estudiante": "Miguel Ángel",
        "creado": hoy.isoformat(),
        "semana_actual": 1,
        "aprobaciones": [],
        "rechazos": [],
        "sesiones": [],
        "retornos": [],
        "pausas": [],
        "parking": [],
        "config": dict(CONFIG_DEFECTO),
    }


def tarjetas_iniciales() -> dict:
    return {"version": 1, "algoritmo": "SM-2 simplificado (calidad 0-5)", "tarjetas": {}}


COLUMNAS_BITACORA = ("Fecha", "Sem.", "Formato", "Objetivo", "Logrado", "Aprendí", "Duda",
                     "Recuperación", "Si-entonces")
ENCABEZADO_BITACORA = (
    "# Bitácora de estudio — IA Agéntica\n\n"
    "Una fila por sesión o evento. La escribe `herramientas/tutor.py`; no la edites a mano.\n\n"
    "| " + " | ".join(COLUMNAS_BITACORA) + " |\n"
    "|" + "---|" * len(COLUMNAS_BITACORA) + "\n"
)


def _celda(texto) -> str:
    return str(texto if texto not in (None, "") else "—").replace("|", "/").replace("\n", " ").strip()


class Contexto:
    """Todo lo que el tutor necesita saber, cargado de disco."""

    def __init__(self, rutas: Rutas, hoy: date):
        self.rutas = rutas
        self.hoy = hoy
        self.malla = cargar_malla(rutas)
        self.semanas = semanas_de(self.malla)
        try:
            self.lista_fuentes = leer_lista_fuentes(rutas)
        except (json.JSONDecodeError, ErrorTutor):
            self.lista_fuentes = None
        self.fuentes = indice_fuentes(self.lista_fuentes) if self.lista_fuentes is not None else None
        self.fichas = cargar_fichas(rutas)
        self.catalogo = catalogo_preguntas(self.malla, self.fichas)
        self.estado_existia = rutas.estado.exists()
        self.estado = leer_json(rutas.estado) if self.estado_existia else estado_inicial(hoy)
        for clave, defecto in estado_inicial(hoy).items():
            self.estado.setdefault(clave, defecto)
        self.config = {**CONFIG_DEFECTO, **(self.estado.get("config") or {})}
        self.tarjetas = leer_json(rutas.tarjetas) if rutas.tarjetas.exists() else tarjetas_iniciales()
        self.tarjetas.setdefault("tarjetas", {})

    @property
    def semana_actual(self) -> int:
        return int(self.estado.get("semana_actual", 1))

    @property
    def terminado(self) -> bool:
        return self.semana_actual >= SEMANA_FIN

    def semana(self, n: int | None = None) -> dict:
        n = n or min(self.semana_actual, TOTAL_SEMANAS)
        return self.semanas.get(n, {})

    def guardar(self, panel: bool = True) -> None:
        escribir_json(self.rutas.estado, self.estado)
        escribir_json(self.rutas.tarjetas, self.tarjetas)
        if not self.rutas.bitacora.exists():
            self.rutas.bitacora.write_text(ENCABEZADO_BITACORA, encoding="utf-8")
        if panel:
            self.rutas.panel.write_text(generar_panel(self), encoding="utf-8")

    def fila_bitacora(self, semana, formato, objetivo="", logrado="", aprendi="", duda="",
                      recuperacion="", si_entonces="") -> None:
        self.rutas.progreso.mkdir(parents=True, exist_ok=True)
        if not self.rutas.bitacora.exists():
            self.rutas.bitacora.write_text(ENCABEZADO_BITACORA, encoding="utf-8")
        celdas = [self.hoy.isoformat(), semana, formato, objetivo, logrado, aprendi, duda, recuperacion, si_entonces]
        with open(self.rutas.bitacora, "a", encoding="utf-8") as f:
            f.write("| " + " | ".join(_celda(c) for c in celdas) + " |\n")


# ---------------------------------------------------------------------------
# Repetición espaciada (SM-2 simplificado)
# ---------------------------------------------------------------------------
def nueva_tarjeta(hoy: date) -> dict:
    return {"activada": hoy.isoformat(), "proxima": (hoy + timedelta(days=1)).isoformat(),
            "intervalo": 0, "repeticiones": 0, "ef": EF_INICIAL, "historial": []}


def aplicar_sm2(tarjeta: dict, calidad: int, hoy: date) -> dict:
    """Actualiza una tarjeta según la calidad de la respuesta (0-5).

    calidad < 3  → se reinicia: vuelve mañana.
    calidad >= 3 → intervalos 1, 3 y luego intervalo × facilidad (EF).
    EF sube con respuestas fáciles y baja con las difíciles (mínimo 1,3).
    """
    if isinstance(calidad, bool) or not isinstance(calidad, int) or not 0 <= calidad <= 5:
        raise ErrorTutor(f"La calidad debe ser un entero de 0 a 5 (recibí «{calidad}»). Escala: {ESCALA_CALIDAD}.")
    t = dict(tarjeta)
    ef = float(t.get("ef", EF_INICIAL))
    reps = int(t.get("repeticiones", 0))
    intervalo_previo = intervalo = int(t.get("intervalo", 0))
    if calidad < 3:
        reps, intervalo = 0, 1
    else:
        if reps == 0:
            intervalo = 1
        elif reps == 1:
            intervalo = 3
        else:
            intervalo = max(intervalo + 1, int(round(intervalo * ef)))
        reps += 1
    ef = max(EF_MINIMO, round(ef + 0.1 - (5 - calidad) * (0.08 + (5 - calidad) * 0.02), 4))
    intervalo = min(intervalo, INTERVALO_MAXIMO)
    t.update(ef=ef, repeticiones=reps, intervalo=intervalo, ultima=hoy.isoformat(),
             proxima=(hoy + timedelta(days=intervalo)).isoformat())
    t["historial"] = list(t.get("historial", [])) + [
        {"fecha": hoy.isoformat(), "calidad": calidad, "intervalo_previo": intervalo_previo}]
    return t


def tarjetas_vencidas(tarjetas: dict, hoy: date) -> list[str]:
    items = []
    for tid, t in tarjetas.get("tarjetas", {}).items():
        try:
            prox = date.fromisoformat(t.get("proxima", ""))
        except ValueError:
            continue
        if prox <= hoy:
            items.append((prox, tid))
    return [tid for _, tid in sorted(items)]


CAJAS = ("Nueva", "1 día", "3 días", "1 semana", "1 mes", "Dominada")


def caja(t: dict) -> str:
    """Caja tipo Leitner para mostrar el avance de una tarjeta."""
    if not t.get("historial"):
        return "Nueva"
    i = int(t.get("intervalo", 0))
    if i <= 1:
        return "1 día"
    if i <= 3:
        return "3 días"
    if i <= 7:
        return "1 semana"
    if i <= 30:
        return "1 mes"
    return "Dominada"


def metricas_recuperacion(tarjetas: dict, hoy: date) -> dict:
    """% de aciertos (calidad ≥ 3). Metas de 03: ≥80% a 1 semana y ≥70% a 1 mes."""
    hist = [h for t in tarjetas.get("tarjetas", {}).values() for h in t.get("historial", [])]

    def pct(items):
        return round(100 * sum(1 for h in items if h.get("calidad", 0) >= 3) / len(items)) if items else None

    recientes = []
    for h in hist:
        try:
            if date.fromisoformat(h["fecha"]) > hoy - timedelta(days=30):
                recientes.append(h)
        except (KeyError, ValueError):
            continue
    a_semana = [h for h in hist if h.get("intervalo_previo", 0) >= 7]
    a_mes = [h for h in hist if h.get("intervalo_previo", 0) >= 30]
    return {"ultimos_30_dias": pct(recientes), "n_30_dias": len(recientes),
            "a_1_semana": pct(a_semana), "n_1_semana": len(a_semana),
            "a_1_mes": pct(a_mes), "n_1_mes": len(a_mes)}


def activar_tarjetas(ctx: Contexto, ids, hoy: date) -> list[str]:
    nuevas = []
    for tid in ids:
        if tid in ctx.catalogo and tid not in ctx.tarjetas["tarjetas"]:
            ctx.tarjetas["tarjetas"][tid] = nueva_tarjeta(hoy)
            nuevas.append(tid)
    return nuevas


def ids_tarjetas_semana(ctx: Contexto, n: int) -> list[str]:
    return [tid for tid, c in ctx.catalogo.items() if c["origen"] == "malla" and c["semana"] == n]


def ids_tarjetas_ficha(ctx: Contexto, fid: str) -> list[str]:
    return [tid for tid, c in ctx.catalogo.items() if c["origen"] == "ficha" and c["ficha"] == fid]


# ---------------------------------------------------------------------------
# Racha semanal con comodín (investigacion/03, §5)
# ---------------------------------------------------------------------------
def es_semana_de_cierre(lunes: date, dias_cierre: int = CONFIG_DEFECTO["dias_cierre_mes"]) -> bool:
    """Semana de cierre de mes: la que contiene la mayoría de los últimos `dias_cierre` días de un mes
    (con 7 días, exactamente una semana por mes)."""
    n = 0
    for k in range(7):
        d = lunes + timedelta(days=k)
        if d.day > ultimo_dia_mes(d) - dias_cierre:
            n += 1
    return 2 * n > dias_cierre


def mes_de_semana(lunes: date):
    jueves = lunes + timedelta(days=3)  # convención ISO: la semana pertenece al mes de su jueves
    return (jueves.year, jueves.month)


def _dias_en_pausa(lunes: date, pausas) -> int:
    n = 0
    for k in range(7):
        d = lunes + timedelta(days=k)
        if any(desde <= d <= hasta for desde, hasta in pausas):
            n += 1
    return n


def _pausas_de(estado: dict):
    out = []
    for p in estado.get("pausas", []):
        try:
            out.append((date.fromisoformat(p["desde"]), date.fromisoformat(p["hasta"])))
        except (KeyError, ValueError, TypeError):
            continue
    return out


def calcular_racha(sesiones, hoy: date, config: dict | None = None, pausas=()) -> dict:
    """Racha = semanas (lunes a domingo) seguidas cumpliendo el piso.

    * Piso: 3 sesiones o 60 min (semana de cierre de mes: 2 sesiones o 30 min).
    * Semana fallida: se REPARA si la semana siguiente tiene ≥ 2 sesiones (o cumple el piso); si no, la cubre el
      comodín del mes (1 por mes); si tampoco, la racha se corta.
    * Semanas con ≥ 4 días de pausa declarada (vacaciones) son neutras: ni suman ni cortan.
    * La semana en curso solo suma si ya cumplió el piso; si no, sigue abierta (no corta).
    `sesiones` es una lista de (fecha, minutos).
    """
    cfg = {**CONFIG_DEFECTO, **(config or {})}
    ses = [(f, m) for f, m in sesiones if f <= hoy and m > 0]
    por_semana = {}
    for f, m in ses:
        s = por_semana.setdefault(lunes_de(f), [0, 0])
        s[0] += 1
        s[1] += m

    def info(lunes: date) -> dict:
        n_ses, mins = por_semana.get(lunes, [0, 0])
        cierre = es_semana_de_cierre(lunes, cfg["dias_cierre_mes"])
        piso_s = cfg["piso_cierre_sesiones"] if cierre else cfg["piso_sesiones"]
        piso_m = cfg["piso_cierre_minutos"] if cierre else cfg["piso_minutos"]
        return {"lunes": lunes.isoformat(), "sesiones": n_ses, "minutos": mins, "cierre": cierre,
                "piso_sesiones": piso_s, "piso_minutos": piso_m,
                "piso_ok": n_ses >= piso_s or mins >= piso_m,
                "pausa": _dias_en_pausa(lunes, pausas) >= 4, "estado": None}

    lunes_hoy = lunes_de(hoy)
    res = {"actual": 0, "mejor": 0, "estado": "sin_iniciar", "semanas": [],
           "comodin_disponible": True, "semana_en_curso": None}
    if not ses:
        w = info(lunes_hoy)
        w["estado"] = "pausa" if w["pausa"] else "en_curso"
        res["semana_en_curso"] = w
        return res
    infos = []
    d = lunes_de(min(f for f, _ in ses))
    while d <= lunes_hoy:
        infos.append(info(d))
        d += timedelta(weeks=1)
    usados: dict = {}
    actual = mejor = 0
    ultimo = len(infos) - 1
    for i, w in enumerate(infos):
        if w["piso_ok"]:
            w["estado"] = "cumplida"
            actual += 1
        elif w["pausa"]:
            w["estado"] = "pausa"
        elif i == ultimo:
            w["estado"] = "en_curso"
        else:
            sig = infos[i + 1]
            mes = mes_de_semana(date.fromisoformat(w["lunes"]))
            if sig["sesiones"] >= cfg["sesiones_para_reparar"] or sig["piso_ok"]:
                w["estado"] = "reparada"
            elif i + 1 == ultimo and not sig["pausa"]:
                w["estado"] = "por_reparar"
            elif usados.get(mes, 0) < cfg["comodines_por_mes"]:
                usados[mes] = usados.get(mes, 0) + 1
                w["estado"] = "comodin"
            else:
                w["estado"] = "rota"
                actual = 0
        mejor = max(mejor, actual)
    mes_actual = mes_de_semana(lunes_hoy)
    res.update(actual=actual, mejor=mejor, semanas=infos, semana_en_curso=infos[-1],
               estado="activa" if actual > 0 else "en_cero",
               comodin_disponible=usados.get(mes_actual, 0) < cfg["comodines_por_mes"])
    return res


def sesiones_de_estado(estado: dict) -> list:
    out = []
    for s in estado.get("sesiones", []):
        try:
            out.append((date.fromisoformat(s["fecha"]), int(s.get("minutos", 0))))
        except (ValueError, KeyError, TypeError):
            continue
    return out


def fechas_estudio(estado: dict) -> list[date]:
    return [f for f, m in sesiones_de_estado(estado) if m > 0]


def racha_de(ctx: Contexto) -> dict:
    return calcular_racha(sesiones_de_estado(ctx.estado), ctx.hoy, ctx.config, _pausas_de(ctx.estado))


def texto_falta_piso(w: dict) -> str:
    if w["piso_ok"]:
        return "piso cumplido"
    faltan_s = max(0, w["piso_sesiones"] - w["sesiones"])
    faltan_m = max(0, w["piso_minutos"] - w["minutos"])
    return f"faltan {faltan_s} sesión(es) o {faltan_m} min para el piso"


# ---------------------------------------------------------------------------
# Retomar sin culpa (investigacion/03, §3)
# ---------------------------------------------------------------------------
def dias_sin_estudiar(estado: dict, hoy: date, libres=()):
    """Días de estudio PLANIFICADOS sin estudiar desde la última sesión (hasta hoy, inclusive).

    Los días de baja disponibilidad (por defecto jueves a domingo, según 03) no cuentan: un
    fin de semana largo en la sucursal no es un «retorno». Devuelve None si no hay sesiones.
    """
    fechas = [f for f in fechas_estudio(estado) if f <= hoy]
    if not fechas:
        return None
    ultima = max(fechas)
    libres = set(libres or ())
    return sum(1 for k in range(1, (hoy - ultima).days + 1)
               if (ultima + timedelta(days=k)).weekday() not in libres)


def dias_fuera(ctx: "Contexto"):
    return dias_sin_estudiar(ctx.estado, ctx.hoy, ctx.config.get("dias_de_baja_disponibilidad", ()))


def en_pausa_declarada(estado: dict, hoy: date) -> bool:
    return any(desde <= hoy <= hasta for desde, hasta in _pausas_de(estado))


def pausa_reciente(estado: dict, hoy: date) -> bool:
    """¿Hubo una pausa declarada que terminó hace poco (≤ 7 días)?"""
    return any(hasta < hoy <= hasta + timedelta(days=7) for _, hasta in _pausas_de(estado))


def ancla_reinicio(hoy: date):
    """03: ancla al próximo lunes o al inicio de mes si está a ≤ 3 días; si no, parte ya."""
    candidatos = []
    if hoy.weekday() != 0:
        candidatos.append((lunes_de(hoy) + timedelta(days=7), "el lunes"))
    primero_mes = date(hoy.year + (hoy.month == 12), hoy.month % 12 + 1, 1)
    if hoy.day != 1:
        candidatos.append((primero_mes, "el inicio de mes"))
    candidatos = [(d, q) for d, q in candidatos if (d - hoy).days <= 3]
    return min(candidatos) if candidatos else (hoy, "hoy")


def protocolo_retomar(dias, hoy: date | None = None, pausa_declarada: bool = False) -> dict:
    """Protocolo de retorno. Nunca castiga ni cuenta días perdidos: re-engancha."""
    if dias is None:
        return {"codigo": "inicio", "titulo": "Primer día", "modo": "estandar",
                "mensaje": "Aún no hay sesiones registradas. Hoy empieza la semana 1: una sola cosa, bien hecha.",
                "pasos": ["Lee el objetivo de la semana 1 (tutor.py hoy).",
                          "Sesión estándar de 30 min, o micro de 15 si hoy no da.",
                          "Cierra con registrar y un si-entonces: así el tutor sabe dónde quedaste."]}
    if dias <= 2:
        return {"codigo": "al_dia", "titulo": "Al día", "modo": "estandar",
                "mensaje": "No hay nada que retomar ni que comentar: sesión normal. La recuperación ya incluye lo pendiente.",
                "pasos": ["tutor.py hoy y adelante."]}
    if dias <= 6:
        return {"codigo": "reentrada", "titulo": "Reentrada", "modo": "micro",
                "mensaje": "Se retoma el hilo, no el tiempo. Hoy, micro de reentrada.",
                "pasos": ["Dónde quedamos: tu última nota y tu si-entonces (abajo).",
                          "3 preguntas fáciles-medias, sin mirar (abajo).",
                          "El paso que ya estaba definido, en versión micro (tutor.py hoy --micro).",
                          "Replanifica QUITANDO, no apilando: esta semana basta con el piso."]}
    fecha, que = ancla_reinicio(hoy or date.today())
    pasos = []
    if que != "hoy":
        pasos.append(f"Ancla el reinicio a {que} ({fecha.isoformat()}): parte ahí con arranque fuerte. "
                     "Hasta entonces, nada obligatorio.")
    else:
        pasos.append("Parte hoy mismo; no esperes al lunes.")
    if not pausa_declarada:
        pasos.append("Pregunta: ¿qué lo cortó: tiempo, energía o interés? Tiempo → baja el piso. "
                     "Energía → solo micro por una semana. Interés → proyecto aplicado a tu sucursal.")
    pasos += ["Prueba de nivel: 8 preguntas sin mirar (abajo); el tutor muestra cada respuesta después.",
              "La primera sesión termina con algo funcionando (la versión micro de la semana en curso).",
              "Las fechas se mueven; nunca se comprimen. Lo aprobado sigue aprobado."]
    return {"codigo": "reinicio", "titulo": "Reinicio limpio", "modo": "estandar",
            "mensaje": ("Volviste, que es lo que importa. Nada de lo aprobado se pierde; "
                        "hoy se re-engancha con una prueba corta y algo funcionando."),
            "pasos": pasos, "ancla": fecha.isoformat()}


# ---------------------------------------------------------------------------
# Evidencia y rúbrica (la aprobación la decide el código)
# ---------------------------------------------------------------------------
RE_URL = re.compile(r"https?://[^\s<>\"'«»]+", re.I)
RE_CONSUMO = re.compile(
    r"\b(vi|lei|mire|revise|escuche|termine|complete|avance|estudie|repase|entendi|comprendi|"
    r"ya lo (vi|lei|se)|me lo se|lo tengo claro)\b")
VERBOS_DEMOSTRACION = (
    "explique", "construi", "implemente", "respondi", "presente", "demostre", "cree", "escribi",
    "programe", "arme", "entregue", "disene", "calcule", "medi", "probe", "ejecute", "defendi",
    "resolvi", "corregi", "dibuje", "redacte", "configure", "conecte", "entreviste", "grabe",
    "subi", "publique", "desarrolle", "analice", "compare", "clasifique", "evalue", "ataque",
    "documente", "modifique", "agregue", "trace", "valide", "integre", "instrumente", "hice",
)
RE_DEMOSTRACION = re.compile(r"\b(" + "|".join(VERBOS_DEMOSTRACION) + r")\b")
LARGO_MINIMO_DESCRIPCION = 60


def _candidatos_ruta(texto: str) -> list[str]:
    tokens = []
    for tok in re.split(r"\s+", texto):
        tok = tok.strip("\"'«»()[]{},;:").rstrip(".")
        if not tok or RE_URL.match(tok):
            continue
        if "/" in tok or re.search(r"\.[A-Za-z0-9]{1,5}$", tok):
            tokens.append(tok)
    return tokens


def _existe_ruta(tok: str, rutas: Rutas):
    p = Path(tok).expanduser()
    bases = [None] if p.is_absolute() else [rutas.raiz, rutas.raiz.parent, Path.cwd()]
    for base in bases:
        cand = p if base is None else base / p
        if cand.exists():
            return cand
    return None


def evaluar_evidencia(texto: str, es_proyecto: bool, rutas: Rutas):
    """Forma mínima de la evidencia. Devuelve (ok, tipo, motivo); tipo ∈ {archivo, url, descripcion}.

    Sin evidencia no hay avance; «vi el contenido» no es evidencia; las semanas de proyecto
    exigen el artefacto (ruta existente o URL). La calidad la puntúa la rúbrica.
    """
    t = (texto or "").strip()
    if not t:
        return False, None, ("Falta la evidencia. Avanzas cuando puedes demostrarlo: "
                             "indica la ruta del artefacto, una URL o qué demostraste y con qué resultado.")
    urls = RE_URL.findall(t)
    candidatos = _candidatos_ruta(t)
    existentes = [c for c in candidatos if _existe_ruta(c, rutas)]
    faltantes = [c for c in candidatos if c not in existentes]
    tipo = "archivo" if existentes else ("url" if urls else "descripcion")
    if tipo == "descripcion":
        pista = f" (no encontré: {', '.join(faltantes[:3])})" if faltantes else ""
        if es_proyecto:
            return False, tipo, ("Semana de proyecto: la evidencia tiene que ser el artefacto — ruta a un "
                                 "archivo que exista en el repo o una URL (repo, demo, video)" + pista + ".")
        norm = normalizar(t)
        demo = RE_DEMOSTRACION.search(norm)
        if RE_CONSUMO.search(norm) and not demo:
            return False, tipo, (f"«{t[:60]}» describe consumo, no dominio. «Vi el contenido» no aprueba "
                                 "una semana: di qué explicaste, construiste o respondiste, y con qué resultado.")
        if len(t) < LARGO_MINIMO_DESCRIPCION:
            return False, tipo, (f"Evidencia demasiado vaga ({len(t)} caracteres; mínimo "
                                 f"{LARGO_MINIMO_DESCRIPCION}). Describe qué demostraste y el resultado, "
                                 "o entrega una ruta o URL" + pista + ".")
        if not demo:
            return False, tipo, ("No se ve una demostración. Usa un verbo de acción (expliqué, construí, "
                                 "respondí, presenté…) y di con qué resultado.")
    return True, tipo, ""


def parsear_rubrica(texto: str | None) -> dict:
    """«entregable=3,explicacion=2,recuperacion=3» → dict. Lanza ErrorTutor si el formato es inválido."""
    if not texto or not texto.strip():
        return {}
    out = {}
    for parte in re.split(r"[,;\s]+", texto.strip()):
        if not parte:
            continue
        m = re.fullmatch(r"([a-z_]+)\s*[=:]\s*(\d)", normalizar(parte))
        if not m:
            raise ErrorTutor(f"Rúbrica mal escrita en «{parte}». Formato: entregable=3,explicacion=2,recuperacion=3")
        clave, valor = m.group(1), int(m.group(2))
        if clave not in CRITERIOS:
            raise ErrorTutor(f"Criterio desconocido «{clave}». Válidos: {', '.join(CRITERIOS)}")
        if not 0 <= valor <= 3:
            raise ErrorTutor(f"«{clave}» debe ir de 0 a 3 ({ESCALA_RUBRICA}).")
        out[clave] = valor
    return out


def evaluar_rubrica(rubrica: dict, n: int):
    """Devuelve (ok, motivo). Todos los criterios de la semana, cada uno ≥ UMBRAL_RUBRICA."""
    requeridos = criterios_semana(n)
    faltan = [c for c in requeridos if c not in rubrica]
    if faltan:
        return False, (f"Falta puntuar: {', '.join(faltan)}. Criterios de la semana {n}: "
                       f"{', '.join(requeridos)} (tutor.py rubrica {n}).")
    bajos = [c for c in requeridos if rubrica[c] < UMBRAL_RUBRICA]
    if bajos:
        detalle = "; ".join(f"{c}: {CRITERIOS[c]}" for c in bajos)
        return False, (f"No alcanza el umbral (mínimo {UMBRAL_RUBRICA} en cada criterio): "
                       f"{', '.join(f'{c}={rubrica[c]}' for c in bajos)}. Qué se espera → {detalle}")
    return True, ""


# ---------------------------------------------------------------------------
# Acciones que modifican la memoria
# ---------------------------------------------------------------------------
def inferir_tipo(minutos: int) -> str:
    if minutos <= 20:
        return "micro"
    if minutos <= 50:
        return "estandar"
    return "lab"


def recuperacion_del_dia(ctx: Contexto) -> str:
    hoy = ctx.hoy.isoformat()
    notas = [h["calidad"] for t in ctx.tarjetas["tarjetas"].values() for h in t.get("historial", [])
             if h.get("fecha") == hoy]
    return f"{sum(1 for q in notas if q >= 3)}/{len(notas)}" if notas else ""


def registrar_sesion(ctx: Contexto, minutos: int, nota: str, tipo: str | None = None,
                     evidencia: str | None = None, leido=(), semana: int | None = None,
                     objetivo: str | None = None, logrado: str | None = None,
                     duda: str | None = None, si_entonces: str | None = None) -> dict:
    if isinstance(minutos, bool) or not isinstance(minutos, int) or not 1 <= minutos <= 600:
        raise ErrorTutor("--minutos debe ser un entero entre 1 y 600.")
    nota = (nota or "").strip()
    if not nota:
        raise ErrorTutor("La nota es obligatoria: 1 línea de qué aprendiste o hiciste (es lo que te "
                         "permite retomar rápido la próxima vez).")
    tipo = tipo or inferir_tipo(minutos)
    if tipo not in TIPOS_SESION:
        raise ErrorTutor(f"--tipo debe ser uno de: {', '.join(TIPOS_SESION)}.")
    if logrado is not None:
        logrado = normalizar(logrado).strip()
        if logrado not in LOGRADO:
            raise ErrorTutor("--logrado debe ser si, parcial o no.")
    tope = min(ctx.semana_actual, TOTAL_SEMANAS)
    semana = semana or tope
    if not 1 <= semana <= tope:
        raise ErrorTutor(f"--semana debe estar entre 1 y {tope} (no puedes registrar en una semana futura).")
    avisos = []
    leido = [x.strip() for x in leido if x and x.strip()]
    for fid in leido:
        if ctx.fuentes is not None and fid not in ctx.fuentes:
            avisos.append(f"La fuente «{fid}» no existe en base/fuentes.json (se registra igual).")
    if evidencia and not RE_URL.match(evidencia.strip()) and not _existe_ruta(evidencia.strip(), ctx.rutas):
        avisos.append(f"No encontré el archivo de evidencia «{evidencia}» (se registra igual).")
    if minutos > TOPE_LAB_MINUTOS:
        avisos.append("Sesión de más de 2 h: la próxima vez aplica el tope (2 h + una extensión de 25 min "
                      "decidida explícitamente) y registra el punto de reanudación.")
    datos = ctx.semana(semana)
    objetivo = (objetivo or "").strip() or datos.get("objetivo", "")
    recuperacion = recuperacion_del_dia(ctx)
    sesion = {"fecha": ctx.hoy.isoformat(), "minutos": minutos, "tipo": tipo, "semana": semana,
              "nota": nota, "objetivo": objetivo}
    for clave, valor in (("logrado", logrado), ("duda", duda), ("si_entonces", si_entonces),
                         ("recuperacion", recuperacion)):
        if valor and str(valor).strip():
            sesion[clave] = str(valor).strip()
    if evidencia:
        sesion["evidencia"] = evidencia.strip()
    if leido:
        sesion["leido"] = leido
    ctx.estado["sesiones"].append(sesion)
    nuevas = []
    for fid in leido:
        nuevas += activar_tarjetas(ctx, ids_tarjetas_ficha(ctx, fid), ctx.hoy)
    etiqueta = {"micro": "Micro", "estandar": "Estándar", "lab": "Laboratorio", "repaso": "Repaso",
                "produccion": "Producción"}[tipo]
    aprendi = nota + (f" (evidencia: {evidencia})" if evidencia else "") + (f" (leído: {', '.join(leido)})" if leido else "")
    ctx.fila_bitacora(semana, f"{etiqueta} {formato_minutos(minutos)}", objetivo, logrado or "", aprendi,
                      duda or "", recuperacion, si_entonces or "")
    ctx.guardar()
    return {"sesion": sesion, "avisos": avisos, "tarjetas_nuevas": nuevas}


def aprobar_semana(ctx: Contexto, n: int, evidencia: str, rubrica: str | dict | None = None,
                   test_out: bool = False) -> dict:
    actual = ctx.semana_actual
    if ctx.terminado:
        raise ErrorTutor("El programa ya está completo: las 24 semanas están aprobadas.")
    if not 1 <= n <= TOTAL_SEMANAS:
        raise ErrorTutor(f"La semana debe estar entre 1 y {TOTAL_SEMANAS}.")
    if n < actual:
        raise ErrorTutor(f"La semana {n} ya está aprobada. La semana en curso es la {actual}.")
    aprobs = ctx.estado["aprobaciones"]
    if aprobs and ctx.hoy < parse_fecha(aprobs[-1]["fecha"]):
        raise ErrorTutor("La fecha de aprobación no puede ser anterior a la última aprobación.")
    puntajes = rubrica if isinstance(rubrica, dict) else parsear_rubrica(rubrica)

    def rechazar(motivo: str):
        ctx.estado["rechazos"].append({"semana": n, "fecha": ctx.hoy.isoformat(),
                                       "evidencia": (evidencia or "").strip(), "rubrica": puntajes,
                                       "motivo": motivo})
        ctx.fila_bitacora(n, "AÚN NO se aprueba", f"Aprobar semana {n} con: {(evidencia or '(vacía)').strip()}",
                          "no", f"Qué falta: {motivo}", "", "", "Cerrar la brecha y volver a demostrar")
        ctx.guardar()
        raise ErrorTutor("Aún no. " + motivo)

    if n > actual:
        rechazar(f"La semana en curso es la {actual}. Las semanas se aprueban en orden: "
                 f"primero demuestra la semana {actual}.")
    datos = ctx.semana(n)
    es_proyecto = bool(datos.get("proyecto")) or n in PROYECTOS_MALLA
    ok, tipo, motivo = evaluar_evidencia(evidencia, es_proyecto, ctx.rutas)
    if not ok:
        rechazar(motivo)
    ok, motivo = evaluar_rubrica(puntajes, n)
    if not ok:
        rechazar(motivo)
    registro = {"semana": n, "fecha": ctx.hoy.isoformat(), "evidencia": evidencia.strip(),
                "tipo_evidencia": tipo, "rubrica": {c: puntajes[c] for c in criterios_semana(n)},
                "modalidad": "test-out" if test_out else "normal"}
    if es_proyecto:
        registro["proyecto"] = (datos.get("proyecto") or {}).get("nombre", PROYECTOS_MALLA.get(n))
    aprobs.append(registro)
    ctx.estado["semana_actual"] = n + 1
    nuevas = activar_tarjetas(ctx, ids_tarjetas_semana(ctx, n), ctx.hoy)
    for fid in datos.get("lectura") or []:
        nuevas += activar_tarjetas(ctx, ids_tarjetas_ficha(ctx, fid), ctx.hoy)
    rub = ", ".join(f"{c}={v}" for c, v in registro["rubrica"].items())
    ctx.fila_bitacora(n, "APROBADA" + (" (test-out)" if test_out else ""), datos.get("objetivo", ""), "si",
                      f"Evidencia ({tipo}): {evidencia.strip()}" + (f" · Proyecto: {registro['proyecto']}" if es_proyecto else ""),
                      "", f"Rúbrica: {rub}", "")
    ctx.guardar()
    return {"registro": registro, "tarjetas_nuevas": nuevas}


def calificar_tarjeta(ctx: Contexto, tid: str, calidad: int) -> dict:
    if tid not in ctx.catalogo:
        raise ErrorTutor(f"No existe la tarjeta «{tid}». Formato: s01-p2 (semana 1, pregunta 2) o f-<ID>-p1.")
    if tid not in ctx.tarjetas["tarjetas"]:
        raise ErrorTutor(f"La tarjeta «{tid}» aún no está activa (se activa al aprobar su semana "
                         "o al registrar la lectura con --leido).")
    t = aplicar_sm2(ctx.tarjetas["tarjetas"][tid], calidad, ctx.hoy)
    ctx.tarjetas["tarjetas"][tid] = t
    ctx.guardar()
    return t


def registrar_retorno(ctx: Contexto, dias, codigo: str) -> bool:
    if codigo not in ("reentrada", "reinicio"):
        return False
    hoy = ctx.hoy.isoformat()
    if any(r.get("fecha") == hoy for r in ctx.estado["retornos"]):
        return False
    ctx.estado["retornos"].append({"fecha": hoy, "dias_fuera": dias, "protocolo": codigo})
    ctx.fila_bitacora(min(ctx.semana_actual, TOTAL_SEMANAS), "RETORNO", f"Protocolo: {codigo}", "",
                      "Volviste. Eso es lo que cuenta.")
    ctx.guardar()
    return True


def declarar_pausa(ctx: Contexto, hasta: date, motivo: str) -> dict:
    if hasta < ctx.hoy:
        raise ErrorTutor("--hasta no puede ser anterior a hoy.")
    if (hasta - ctx.hoy).days > 60:
        raise ErrorTutor("Una pausa declarada dura como máximo 60 días; si es más larga, declárala de nuevo al volver.")
    p = {"desde": ctx.hoy.isoformat(), "hasta": hasta.isoformat(), "motivo": (motivo or "pausa").strip()}
    ctx.estado["pausas"].append(p)
    ctx.fila_bitacora(min(ctx.semana_actual, TOTAL_SEMANAS), "PAUSA DECLARADA",
                      f"Hasta {p['hasta']}", "", p["motivo"], "", "", "La racha queda congelada")
    ctx.guardar()
    return p


def agregar_parking(ctx: Contexto, idea: str) -> dict:
    idea = (idea or "").strip()
    if not idea:
        raise ErrorTutor("La idea está vacía.")
    item = {"fecha": ctx.hoy.isoformat(), "idea": idea, "semana": min(ctx.semana_actual, TOTAL_SEMANAS)}
    ctx.estado["parking"].append(item)
    ctx.guardar()
    return item


# ---------------------------------------------------------------------------
# Plan del día (investigacion/03, §1)
# ---------------------------------------------------------------------------
PASOS = {
    "entender": {"modo": "estandar", "nombre": "Entender"},
    "entender-2": {"modo": "estandar", "nombre": "Entender (segunda pasada)"},
    "construir": {"modo": "lab", "nombre": "Construir"},
    "construir-mas": {"modo": "lab", "nombre": "Construir (continuación)"},
    "cerrar": {"modo": "estandar", "nombre": "Cerrar el laboratorio"},
    "demostrar": {"modo": "estandar", "nombre": "Demostrar"},
    "micro": {"modo": "micro", "nombre": "Micro"},
    "reentrada": {"modo": "micro", "nombre": "Reentrada"},
    "reinicio": {"modo": "estandar", "nombre": "Reinicio limpio"},
    "mantenimiento": {"modo": "micro", "nombre": "Mantenimiento (cierre de mes)"},
    "mantener": {"modo": "micro", "nombre": "Mantener (programa completo)"},
}


def sesiones_de_semana(estado: dict, n: int) -> list:
    return [s for s in estado.get("sesiones", []) if s.get("semana") == n]


def elegir_paso(estado: dict, n: int, modo: str | None = None, dias_fuera=None,
                hoy: date | None = None, config: dict | None = None):
    """Decide el paso de hoy. Devuelve (clave_paso, motivo)."""
    cfg = {**CONFIG_DEFECTO, **(config or {})}
    if n >= SEMANA_FIN:
        return "mantener", "programa completo"
    ses = sesiones_de_semana(estado, n)
    teoria = sum(1 for s in ses if s.get("tipo") == "estandar")
    lab = sum(1 for s in ses if s.get("tipo") == "lab")
    if modo == "micro":
        return "micro", "elegiste modo micro"
    if modo is None:
        if dias_fuera is not None and dias_fuera >= 7:
            return "reinicio", "vuelves después de un tiempo: reinicio limpio"
        if dias_fuera is not None and dias_fuera >= 3:
            return "reentrada", "micro de reentrada para retomar el hilo"
        if hoy is not None and es_semana_de_cierre(lunes_de(hoy), cfg["dias_cierre_mes"]):
            if not estado.get("sesiones"):
                return "micro", "semana de cierre de mes: primer contacto suave, en versión micro"
            return "mantenimiento", "semana de cierre de mes: sin contenido nuevo"
    if modo == "lab":
        return ("construir" if lab == 0 else "construir-mas"), f"{lab} laboratorio(s) hechos en esta semana de contenido"
    if modo == "estandar":
        if teoria == 0:
            return "entender", "primera sesión estándar de la semana"
        if teoria == 1:
            return ("cerrar", "ya hay laboratorio: toca cerrarlo") if lab else ("entender-2", "aún sin laboratorio")
        return "demostrar", "teoría y cierre hechos: toca demostrar"
    # Ritmo de 03: lunes estándar (entender) · martes lab (construir) · miércoles estándar (cerrar) · demostrar.
    if teoria == 0:
        return "entender", "semana nueva: primero entender"
    if lab == 0:
        return "construir", "conceptos vistos: toca construir"
    if teoria == 1:
        return "cerrar", "laboratorio empezado: cerrarlo y dejar el entregable"
    return "demostrar", "laboratorio cerrado: toca demostrar para avanzar"


def _mitades(lista: list):
    k = math.ceil(len(lista) / 2)
    return lista[:k], lista[k:]


def lecturas_de(ctx: Contexto, datos: dict) -> list[dict]:
    leidas = {fid for s in ctx.estado.get("sesiones", []) for fid in s.get("leido", [])}
    out = []
    for fid in datos.get("lectura") or []:
        f = (ctx.fuentes or {}).get(fid, {})
        out.append({"id": fid, "titulo": f.get("titulo", "(no está en base/fuentes.json)"),
                    "autor": f.get("autor"), "minutos": f.get("minutos"), "url": f.get("url"),
                    "acceso": f.get("acceso"), "nucleo": bool(f.get("nucleo")), "leida": fid in leidas,
                    "ficha": ctx.rutas.rel(ctx.fichas[fid]["ruta"]) if fid in ctx.fichas else None})
    return out


def quedamos_en(ctx: Contexto) -> str:
    ses = ctx.estado.get("sesiones", [])
    if not ses:
        return "partimos con la semana 1"
    u = ses[-1]
    txt = u.get("nota", "")
    if u.get("duda"):
        txt += f" · duda pendiente: {u['duda']}"
    return txt


def ultimo_si_entonces(ctx: Contexto) -> str:
    for s in reversed(ctx.estado.get("sesiones", [])):
        if s.get("si_entonces"):
            return s["si_entonces"]
    return ""


def seleccion_diagnostico(ctx: Contexto, cantidad: int, faciles: bool = False) -> list[str]:
    """Preguntas para reentrada (fáciles-medias) o prueba de nivel (vencidas + últimas semanas)."""
    tarjetas = ctx.tarjetas.get("tarjetas", {})
    if faciles:
        orden = sorted(tarjetas, key=lambda t: (-float(tarjetas[t].get("ef", EF_INICIAL)), t))
    else:
        orden = tarjetas_vencidas(ctx.tarjetas, ctx.hoy)
        for n in reversed([a["semana"] for a in ctx.estado.get("aprobaciones", [])]):
            orden += [t for t in ids_tarjetas_semana(ctx, n) if t not in orden]
    if len(orden) < cantidad:
        orden += [t for t in ids_tarjetas_semana(ctx, min(ctx.semana_actual, TOTAL_SEMANAS)) if t not in orden]
    return [t for t in orden if t in ctx.catalogo][:cantidad]


def plan_de_hoy(ctx: Contexto, modo: str | None = None) -> dict:
    n = ctx.semana_actual
    dias = dias_fuera(ctx)
    paso, motivo = elegir_paso(ctx.estado, n, modo, dias, ctx.hoy, ctx.config)
    vencidas = tarjetas_vencidas(ctx.tarjetas, ctx.hoy)
    modo_paso = PASOS[paso]["modo"]
    # El reinicio no cuenta como teoría de la semana (si no, se saltaría «Entender»).
    tipo_registro = "repaso" if paso == "reinicio" else modo_paso
    plan = {"fecha": ctx.hoy.isoformat(), "semana": n, "paso": paso,
            "nombre_paso": PASOS[paso]["nombre"], "modo": modo_paso, "minutos": MODOS[modo_paso],
            "tipo_registro": tipo_registro,
            "motivo": motivo, "repasos_vencidos": vencidas, "bloques": [], "lecturas": [],
            "terminado": ctx.terminado, "quedamos_en": quedamos_en(ctx),
            "si_entonces_anterior": ultimo_si_entonces(ctx)}
    k_rec = 5 if modo_paso == "micro" else 3
    primer_dia = not ctx.estado.get("sesiones")
    if vencidas:
        primero = f"responde sin mirar: «{ctx.catalogo.get(vencidas[0], {}).get('pregunta', '')}»"
    elif primer_dia:
        primero = "lee el objetivo en voz alta y nombra un caso de tu sucursal donde aplicaría"
    else:
        primero = "di en una frase qué recuerdas de tu última sesión"
    plan["primero"] = primero
    if paso == "mantener":
        plan["hoy"] = "mantener lo aprendido y avanzar el piloto del capstone"
        plan["bloques"] = [(2, "Arranque"), (6, f"Recuperación: {min(len(vencidas), 5)} repaso(s) → tutor.py repaso"),
                           (5, "Un paso del piloto del capstone (roadmap 30/60/90)"), (2, "Registro")]
        return plan
    datos = ctx.semana(n)
    plan.update(titulo=datos.get("titulo", ""), objetivo=datos.get("objetivo", ""),
                etapa=datos.get("etapa"), version_micro=datos.get("version_micro", ""),
                lecturas=lecturas_de(ctx, datos))
    plan["hoy"] = datos.get("objetivo", "")
    arranque = f"Arranque: quedamos en «{plan['quedamos_en']}»; hoy: {PASOS[paso]['nombre']}"
    if vencidas:
        recuperar = f"Recuperación: {min(len(vencidas), k_rec)} pregunta(s) sin mirar → tutor.py repaso --limite {k_rec}"
    elif primer_dia:
        recuperar = "Línea base: di en 3 frases qué sabes hoy de agentes, sin buscar nada (sirve para medir tu avance)"
    else:
        recuperar = "Recuperación: explica sin mirar lo último que aprendiste (no hay tarjetas vencidas)"
    c1, c2 = _mitades(datos.get("conceptos") or [])
    ids_semana = ids_tarjetas_semana(ctx, n)
    cierre = (f"Cierre: tutor.py registrar --minutos {MODOS[modo_paso]} --tipo {tipo_registro} --nota \"...\" "
              "--si-entonces \"Si es [día/hora] y [ancla], entonces abro el tutor y [primera acción]\"")
    pendientes = [l for l in plan["lecturas"] if not l["leida"]]
    if paso in ("entender", "entender-2"):
        foco = c1 if paso == "entender" else (c2 or c1)
        plan["bloques"] = [
            (2, arranque), (5, recuperar),
            (3, f"Gancho: el tutor plantea un caso de tu sucursal sobre «{foco[0] if foco else ''}» y tú predices qué pasa"),
            (14, "Hacer: explica con tus palabras y un ejemplo propio → " + " | ".join(foco)
             + (f" (lectura: {pendientes[0]['id']})" if pendientes else "")
             + (". Después, sin mirar: " + ", ".join(ids_semana) if paso == "entender-2" else "")),
            (3, "Explicar: explícaselo a tu vendedor más nuevo en 3 frases"),
            (3, cierre)]
    elif paso in ("construir", "construir-mas"):
        b1 = ("Construir: " + datos.get("laboratorio", "")) if paso == "construir" else \
            ("Sigue construyendo lo que falta para: " + datos.get("entregable", ""))
        plan["bloques"] = [
            (7, arranque + " · " + recuperar), (25, b1), (5, "Pausa sin pantalla"),
            (25, "Construir y probar: deja funcionando la versión mínima"),
            (8, "Demo y explicación: muéstrale al tutor qué funciona y por qué; él pregunta «¿qué pasa si…?»"),
            (5, cierre + " (tope del laboratorio: 2 h)")]
    elif paso == "cerrar":
        plan["bloques"] = [
            (2, arranque), (5, recuperar),
            (3, "Gancho: ¿qué fallaría si mañana lo usa un vendedor de tu equipo? Predice antes de probar"),
            (14, "Cierra el laboratorio y deja el entregable: " + datos.get("entregable", "")
             + (" · Conceptos que aún no explicaste: " + " | ".join(c2) if c2 else "")),
            (3, "Explicar: 3 frases para tu vendedor más nuevo sobre lo que construiste"),
            (3, cierre)]
    elif paso == "demostrar":
        plan["bloques"] = [
            (2, arranque), (5, recuperar),
            (15, "Demuestra: " + datos.get("evidencia_de_dominio", "")),
            (5, f"Evaluación con rúbrica, en contexto aparte: tutor.py rubrica {n} (0–3; mínimo 2 en cada criterio)"),
            (3, f"Registra primero (tutor.py registrar ... --semana {n}) y, si pasa: tutor.py aprobar-semana {n} "
                f"--evidencia \"<ruta, URL o qué demostraste>\" --rubrica \"{','.join(c + '=?' for c in criterios_semana(n))}\"")]
        rech = [r for r in ctx.estado.get("rechazos", []) if r.get("semana") == n]
        if rech:
            plan["ultimo_rechazo"] = rech[-1]["motivo"]
    elif paso == "micro":
        plan["bloques"] = [(2, arranque), (6, recuperar), (5, "Micro-paso: " + datos.get("version_micro", "")),
                           (2, "Registro: tutor.py registrar --minutos 15 --tipo micro --nota \"...\"")]
    elif paso == "reentrada":
        faciles = seleccion_diagnostico(ctx, 3, faciles=True)
        plan["preguntas"] = faciles
        plan["bloques"] = [(2, f"Dónde quedamos: {plan['quedamos_en']}"),
                           (6, "3 preguntas fáciles-medias sin mirar: " + (", ".join(faciles) or "las de la semana")),
                           (5, "El paso ya definido, en micro: " + datos.get("version_micro", "")),
                           (2, "Registro, y replanificar QUITANDO: esta semana basta con el piso")]
    elif paso == "reinicio":
        prueba = seleccion_diagnostico(ctx, 8)
        plan["preguntas"] = prueba
        plan["bloques"] = [(3, "¿Qué lo cortó: tiempo, energía o interés? (ajusta el plan con la respuesta)"),
                           (10, "Prueba de nivel, 8 preguntas sin mirar: " + (", ".join(prueba) or "las de la semana")),
                           (14, "Algo funcionando hoy: " + datos.get("version_micro", "")),
                           (3, cierre)]
    elif paso == "mantenimiento":
        plan["hoy"] = "mantener lo aprendido durante el cierre de mes (sin contenido nuevo)"
        plan["bloques"] = [(2, arranque), (6, recuperar),
                           (5, "Cuaderno de fricciones: 1 línea sobre qué tarea del cierre de hoy podría hacer un agente"),
                           (2, "Registro: tutor.py registrar --minutos 15 --tipo micro --nota \"fricción: ...\"")]
    return plan


# ---------------------------------------------------------------------------
# Resumen de estado
# ---------------------------------------------------------------------------
def nivel_actual(malla: dict, aprobadas) -> str | None:
    nivel = None
    for e in sorted(malla.get("etapas", []), key=lambda e: e.get("numero", 0)):
        ini, fin = e.get("semanas", [0, 0])
        if all(s in aprobadas for s in range(ini, fin + 1)):
            nivel = e.get("nivel") or f"Etapa {e.get('numero')}"
        else:
            break
    return nivel


def proyeccion(ctx: Contexto) -> dict:
    """Calendario honesto: ritmo real si hay datos; si no, el nominal de 03 (≈ 8 meses)."""
    aprobs = ctx.estado.get("aprobaciones", [])
    nominal = ctx.config["dias_por_semana_de_contenido"]
    ritmo_real = None
    fechas = fechas_estudio(ctx.estado)
    if len(aprobs) >= 2 and fechas:
        dias = (parse_fecha(aprobs[-1]["fecha"]) - min(fechas)).days
        ritmo_real = max(1.0, dias / len(aprobs))
    ritmo = ritmo_real or nominal
    restantes = TOTAL_SEMANAS - len(aprobs)
    out = {"ritmo_dias_por_semana": round(ritmo, 1), "ritmo_real": ritmo_real is not None,
           "termino_programa": (ctx.hoy + timedelta(days=round(restantes * ritmo))).isoformat() if restantes else None,
           "termino_etapa": None, "etapa": None}
    if not ctx.terminado:
        e = etapa_de(ctx.malla, ctx.semana().get("etapa"))
        fin = e.get("semanas", [0, ctx.semana_actual])[1]
        faltan = fin - ctx.semana_actual + 1
        out.update(etapa=e.get("numero"), termino_etapa=(ctx.hoy + timedelta(days=round(faltan * ritmo))).isoformat())
    return out


def minutos_en_semana_calendario(estado: dict, hoy: date) -> int:
    lunes = lunes_de(hoy)
    return sum(m for f, m in sesiones_de_estado(estado) if lunes <= f <= hoy)


def resumen(ctx: Contexto) -> dict:
    n = ctx.semana_actual
    datos = ctx.semana(n)
    aprobadas = [a["semana"] for a in ctx.estado.get("aprobaciones", [])]
    racha = racha_de(ctx)
    dias = dias_fuera(ctx)
    vencidas = tarjetas_vencidas(ctx.tarjetas, ctx.hoy)
    paso, motivo = elegir_paso(ctx.estado, n, None, dias, ctx.hoy, ctx.config)
    fechas = fechas_estudio(ctx.estado)
    etapas = []
    for e in ctx.malla.get("etapas", []):
        ini, fin = e.get("semanas", [0, 0])
        etapas.append({"numero": e.get("numero"), "nombre": e.get("nombre"), "nivel": e.get("nivel"),
                       "aprobadas": sum(1 for s in range(ini, fin + 1) if s in aprobadas), "total": fin - ini + 1})
    etapa_actual = etapa_de(ctx.malla, datos.get("etapa")) if not ctx.terminado else {}
    return {
        "fecha": ctx.hoy.isoformat(),
        "semana_actual": n,
        "terminado": ctx.terminado,
        "titulo": datos.get("titulo", "") if not ctx.terminado else "Programa completado",
        "etapa": datos.get("etapa") if not ctx.terminado else 6,
        "nombre_etapa": etapa_actual.get("nombre", ""),
        "objetivo": datos.get("objetivo", "") if not ctx.terminado else "",
        "nivel": nivel_actual(ctx.malla, aprobadas),
        "proximo_nivel": etapa_actual.get("nivel"),
        "aprobadas": aprobadas,
        "porcentaje": round(100 * len(aprobadas) / TOTAL_SEMANAS),
        "etapas": etapas,
        "racha": racha,
        "dias_sin_estudiar": dias,
        "dias_calendario_sin_estudiar": dias_sin_estudiar(ctx.estado, ctx.hoy),
        "toca_retomar": dias is not None and dias >= 3,
        "en_pausa_declarada": en_pausa_declarada(ctx.estado, ctx.hoy),
        "ultima_sesion": max(fechas).isoformat() if fechas else None,
        "quedamos_en": quedamos_en(ctx),
        "si_entonces": ultimo_si_entonces(ctx),
        "repasos_vencidos": vencidas,
        "tarjetas_activas": len(ctx.tarjetas.get("tarjetas", {})),
        "recuperacion": metricas_recuperacion(ctx.tarjetas, ctx.hoy),
        "paso_siguiente": PASOS[paso]["nombre"],
        "modo_siguiente": PASOS[paso]["modo"],
        "motivo_paso": motivo,
        "semana_calendario": racha["semana_en_curso"],
        "minutos_semana": minutos_en_semana_calendario(ctx.estado, ctx.hoy),
        "minutos_totales": sum(m for _, m in sesiones_de_estado(ctx.estado)),
        "proyeccion": proyeccion(ctx),
        "parking": len(ctx.estado.get("parking", [])),
        "rechazos": len(ctx.estado.get("rechazos", [])),
        "retornos": len(ctx.estado.get("retornos", [])),
    }


# ---------------------------------------------------------------------------
# Bloque de estado (continuidad con claude.ai, modo sin archivos)
# ---------------------------------------------------------------------------
INICIO_BLOQUE = "<<<ESTADO-TUTOR v1"
FIN_BLOQUE = "ESTADO-TUTOR>>>"


def bloque_estado(ctx: Contexto) -> str:
    r = resumen(ctx)
    rc = r["racha"]
    w = r["semana_calendario"]
    lineas = [
        INICIO_BLOQUE,
        f"fecha: {r['fecha']}",
        f"semana_actual: {r['semana_actual']}",
        f"titulo: {r['titulo']}",
        f"nivel: {r['nivel'] or '-'}",
        f"aprobadas: {', '.join(map(str, r['aprobadas'])) or '-'}",
        f"paso_siguiente: {r['paso_siguiente']}",
        f"racha_semanal: {rc['actual']} (mejor {rc['mejor']}) · comodín del mes: "
        f"{'disponible' if rc['comodin_disponible'] else 'usado'}",
        f"esta_semana: {w['sesiones']} sesión(es), {w['minutos']} min · {texto_falta_piso(w)}",
        f"quedamos_en: {r['quedamos_en']}",
        f"si_entonces: {r['si_entonces'] or '-'}",
        f"repasos_vencidos: {', '.join(r['repasos_vencidos'][:10]) or '-'}",
        f"ideas_en_parking: {r['parking']}",
        "# Eventos de esta conversación (una línea por evento; formato exacto):",
        "# sesion: AAAA-MM-DD | minutos | micro/estandar/lab | lo que aprendió | si-entonces",
        "# calificacion: AAAA-MM-DD | id_tarjeta | 0-5",
        "# leido: AAAA-MM-DD | id_fuente",
        "# parking: AAAA-MM-DD | idea",
        "# aprobada: AAAA-MM-DD | semana | entregable=3,explicacion=2,recuperacion=3[,sin_ia=2] | evidencia",
        FIN_BLOQUE,
    ]
    return "\n".join(lineas)


def importar_bloque(ctx_factory, texto: str) -> dict:
    """Aplica los eventos de un bloque pegado desde claude.ai. `ctx_factory(fecha)` crea un Contexto."""
    eventos = []
    for num, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        m = re.match(r"^(sesion|calificacion|leido|parking|aprobada)\s*:\s*(.+)$", s, re.I)
        if not m:
            continue
        partes = [p.strip() for p in m.group(2).split("|")]
        tipo = m.group(1).lower()
        try:
            fecha = parse_fecha(partes[0], f"línea {num}")
        except ErrorTutor as e:
            eventos.append((date.min, num, "error", str(e)))
            continue
        eventos.append((fecha, num, tipo, partes[1:]))
    eventos.sort(key=lambda e: (e[0], e[1]))
    resultado = {"aplicados": [], "omitidos": [], "errores": []}
    for fecha, num, tipo, datos in eventos:
        if tipo == "error":
            resultado["errores"].append(datos)
            continue
        ctx = ctx_factory(fecha)
        try:
            if tipo == "sesion":
                if len(datos) < 3:
                    raise ErrorTutor("sesion necesita: minutos | tipo | lo que aprendió [| si-entonces]")
                minutos, tipo_s, nota = int(datos[0]), normalizar(datos[1]).strip(), datos[2]
                si_ent = datos[3] if len(datos) > 3 else None
                if any(s.get("fecha") == fecha.isoformat() and s.get("minutos") == minutos and s.get("nota") == nota
                       for s in ctx.estado["sesiones"]):
                    resultado["omitidos"].append(f"línea {num}: sesión ya registrada")
                    continue
                registrar_sesion(ctx, minutos, nota, tipo_s, si_entonces=si_ent)
                resultado["aplicados"].append(f"sesión {fecha} ({minutos} min)")
            elif tipo == "calificacion":
                tid, calidad = datos[0], int(datos[1])
                hist = ctx.tarjetas["tarjetas"].get(tid, {}).get("historial", [])
                if any(h.get("fecha") == fecha.isoformat() and h.get("calidad") == calidad for h in hist):
                    resultado["omitidos"].append(f"línea {num}: calificación ya aplicada")
                    continue
                calificar_tarjeta(ctx, tid, calidad)
                resultado["aplicados"].append(f"calificación {tid}={calidad}")
            elif tipo == "leido":
                fid = datos[0]
                nuevas = activar_tarjetas(ctx, ids_tarjetas_ficha(ctx, fid), fecha)
                ctx.guardar()
                resultado["aplicados"].append(f"lectura {fid} ({len(nuevas)} tarjetas)")
            elif tipo == "parking":
                idea = " | ".join(datos)
                if any(p.get("idea") == idea for p in ctx.estado["parking"]):
                    resultado["omitidos"].append(f"línea {num}: idea ya anotada")
                    continue
                agregar_parking(ctx, idea)
                resultado["aplicados"].append("idea al parking")
            elif tipo == "aprobada":
                if len(datos) < 3:
                    raise ErrorTutor("aprobada necesita: semana | rúbrica | evidencia")
                n, rub, evidencia = int(datos[0]), datos[1], " | ".join(datos[2:])
                if n < ctx.semana_actual:
                    resultado["omitidos"].append(f"línea {num}: semana {n} ya aprobada")
                    continue
                aprobar_semana(ctx, n, evidencia, rub)
                resultado["aplicados"].append(f"semana {n} aprobada")
        except (ErrorTutor, ValueError, IndexError) as e:
            resultado["errores"].append(f"línea {num}: {e}")
    return resultado


# ---------------------------------------------------------------------------
# Integración con la base de conocimiento (agente 2)
# ---------------------------------------------------------------------------
def proponer_lecturas(malla: dict, lista_fuentes, maximo: int = 4) -> dict:
    fuentes = [f for f in (lista_fuentes or []) if isinstance(f, dict) and isinstance(f.get("id"), str)]
    propuesta = {}
    for n in range(1, TOTAL_SEMANAS + 1):
        cands = [f for f in fuentes if n in (f.get("semanas") or [])]
        cands.sort(key=lambda f: (not f.get("nucleo", False),
                                  f.get("minutos") if isinstance(f.get("minutos"), (int, float)) else 999,
                                  f["id"]))
        propuesta[n] = [f["id"] for f in cands[:maximo]]
    return propuesta


# ---------------------------------------------------------------------------
# Panel HTML autocontenido: «Hoja de Combate del aprendizaje»
# ---------------------------------------------------------------------------
CSS_PANEL = """
:root{color-scheme:light;
 --plano:#f9f9f7;--tarjeta:#ffffff;--tinta:#0b0b0b;--tinta2:#52514e;--tinta3:#6f6d67;
 --linea:#e1e0d9;--borde:rgba(11,11,11,.10);--acento:#2a78d6;--acento-suave:#e3eefc;--acento-medio:#9ec5f4;
 --ok-texto:#006300;--aviso:#fab219;--critico:#d03b3b;--neutro:#eeede8;--rayado:#a9a79e;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --plano:#0d0d0d;--tarjeta:#1f1f1e;--tinta:#ffffff;--tinta2:#c3c2b7;--tinta3:#a3a199;
 --linea:#2c2c2a;--borde:rgba(255,255,255,.10);--acento:#3987e5;--acento-suave:#17263a;--acento-medio:#1c5cab;
 --ok-texto:#0ca30c;--aviso:#fab219;--critico:#e66767;--neutro:#2c2c2a;--rayado:#6b6a64;}}
:root[data-theme="dark"]{color-scheme:dark;
 --plano:#0d0d0d;--tarjeta:#1f1f1e;--tinta:#ffffff;--tinta2:#c3c2b7;--tinta3:#a3a199;
 --linea:#2c2c2a;--borde:rgba(255,255,255,.10);--acento:#3987e5;--acento-suave:#17263a;--acento-medio:#1c5cab;
 --ok-texto:#0ca30c;--aviso:#fab219;--critico:#e66767;--neutro:#2c2c2a;--rayado:#6b6a64;}
*{box-sizing:border-box}
body{margin:0;background:var(--plano);color:var(--tinta);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1080px;margin:0 auto;padding:20px 16px 48px}
header{display:flex;flex-wrap:wrap;gap:4px 16px;align-items:baseline;justify-content:space-between;margin-bottom:12px}
h1{font-size:20px;margin:0}
h2{font-size:15px;margin:0 0 12px}
.sub{color:var(--tinta2);font-size:13px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));margin-top:12px}
.kpis{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,170px),1fr));margin:12px 0}
.card{background:var(--tarjeta);border:1px solid var(--borde);border-radius:12px;padding:16px;min-width:0}
.kpi .lab{color:var(--tinta2);font-size:13px}
.kpi .val{font-size:28px;font-weight:650;line-height:1.2}
.kpi .det{color:var(--tinta3);font-size:12px}
.hero .num{font-size:48px;font-weight:650;line-height:1.05}
.hero p{margin:6px 0}
.chip{display:inline-block;padding:1px 8px;border-radius:999px;background:var(--acento-suave);font-size:12px;border:1px solid var(--borde);margin-right:4px}
ol,ul{padding-left:20px;margin:0}
li{margin:4px 0}
.etapa{margin:10px 0}
.etapa .cab{display:flex;justify-content:space-between;gap:8px;font-size:13px;color:var(--tinta2)}
.semanas{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.sem{position:relative;width:30px;height:30px;border-radius:6px;display:grid;place-items:center;font-size:12px;
 border:1px solid var(--linea);background:var(--tarjeta);color:var(--tinta2);font-variant-numeric:tabular-nums}
.sem.ok{background:var(--acento);border-color:var(--acento);color:#fff}
.sem.curso{border:2px solid var(--acento);color:var(--tinta);font-weight:650}
.sem.proy::after{content:"";position:absolute;right:-3px;top:-3px;width:9px;height:9px;border-radius:50%;
 background:var(--aviso);box-shadow:0 0 0 2px var(--tarjeta)}
.leyenda{display:flex;flex-wrap:wrap;gap:6px 12px;font-size:12px;color:var(--tinta2);margin-top:10px}
.leyenda span{display:inline-flex;align-items:center;gap:4px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block;border:1px solid var(--borde)}
.tira{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:4px}
.wk{display:flex;flex-direction:column;align-items:center;gap:2px;min-width:0}
.wk .c{width:100%;aspect-ratio:1;max-width:34px;border-radius:6px;display:grid;place-items:center;font-size:13px;font-weight:650;
 background:var(--neutro);color:var(--tinta2);border:1px solid var(--borde)}
.wk .c.cumplida{background:var(--acento);color:#fff;border-color:var(--acento)}
.wk .c.reparada{background:var(--acento-medio);color:var(--tinta)}
.wk .c.comodin{background:repeating-linear-gradient(45deg,var(--rayado) 0 2px,transparent 2px 6px),var(--neutro);color:var(--tinta)}
.wk .c.rota{background:var(--tarjeta);border:2px solid var(--critico);color:var(--critico)}
.wk .c.en_curso,.wk .c.por_reparar{background:var(--tarjeta);border:2px dashed var(--acento);color:var(--tinta)}
.wk .c.pausa{background:var(--neutro);color:var(--tinta3)}
.wk .f{font-size:10px;color:var(--tinta3);white-space:nowrap}
.barras{display:flex;align-items:flex-end;gap:10px;height:130px;border-bottom:1px solid var(--linea);margin-top:22px}
.barra{flex:1;position:relative;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0}
.barra .b{width:min(24px,100%);background:var(--acento);border-radius:4px 4px 0 0;min-height:2px}
.barra .v{font-size:11px;color:var(--tinta2);margin-bottom:2px}
.barra .piso{position:absolute;left:12%;right:12%;border-top:2px solid var(--tinta2)}
.ejes{display:flex;gap:10px;margin-top:4px}
.ejes span{flex:1;text-align:center;font-size:11px;color:var(--tinta3);min-width:0}
.hbar{display:grid;grid-template-columns:78px 1fr 32px;gap:8px;align-items:center;margin:6px 0;font-size:13px}
.hbar .f{height:12px;background:var(--acento);border-radius:0 4px 4px 0;min-width:2px;display:block}
.hbar .n{text-align:right;color:var(--tinta2);font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--linea);vertical-align:top}
th{color:var(--tinta2);font-weight:600}
td.num{font-variant-numeric:tabular-nums}
.ok-t{color:var(--ok-texto);white-space:nowrap}
.ev{color:var(--tinta2);word-break:break-word}
details summary{cursor:pointer;color:var(--tinta2);font-size:13px}
.tabla-scroll{overflow-x:auto}
footer{margin-top:24px;color:var(--tinta3);font-size:12px}
td.est{white-space:nowrap}
@media (max-width:600px){.hero .num{font-size:40px}.wk .f.alt{visibility:hidden}.desc{display:none}.ev{word-break:break-all}}
"""

ESTADOS_SEMANA = {
    "cumplida": ("✓", "Piso cumplido"),
    "reparada": ("R", "Reparada (2 sesiones la semana siguiente)"),
    "comodin": ("C", "Cubierta con el comodín del mes"),
    "pausa": ("P", "Pausa declarada"),
    "rota": ("✗", "Racha cortada"),
    "en_curso": ("…", "En curso"),
    "por_reparar": ("R?", "Por reparar esta semana"),
}


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _pct(v) -> str:
    return "—" if v is None else f"{v}%"


def generar_panel(ctx: Contexto) -> str:
    r = resumen(ctx)
    hoy = ctx.hoy
    racha = r["racha"]
    aprob = {a["semana"]: a for a in ctx.estado.get("aprobaciones", [])}
    n = r["semana_actual"]
    plan = plan_de_hoy(ctx)
    proy = r["proyeccion"]
    rec = r["recuperacion"]
    w = r["semana_calendario"]

    partes = [f"""<header><h1>Hoja de Combate del aprendizaje</h1>
<div class="sub">IA Agéntica · {_esc(ctx.estado.get('estudiante', ''))} · actualizado {_esc(fecha_corta(hoy))}</div></header>"""]
    if r["terminado"]:
        partes.append('<div class="card hero"><div class="sub">Programa</div><div class="num">24/24</div>'
                      '<p>Programa completado. Nivel: AI Business Builder. Mantén los repasos y pilotea tu capstone.</p></div>')
    else:
        ritmo = f"ritmo {'real' if proy['ritmo_real'] else 'nominal'}: {proy['ritmo_dias_por_semana']} días por semana de contenido"
        partes.append(
            f'<div class="card hero"><div class="sub">Semana de contenido en curso · Etapa {_esc(r["etapa"])} — '
            f'{_esc(r["nombre_etapa"])} · rumbo a nivel {_esc(r["proximo_nivel"])}</div>'
            f'<div class="num">Semana {n} <span class="sub">de {TOTAL_SEMANAS}</span></div>'
            f'<p><strong>{_esc(r["titulo"])}</strong></p>'
            f'<p><span class="chip">Objetivo</span>{_esc(r["objetivo"])}</p>'
            f'<p><span class="chip">Quedamos en</span>{_esc(plan["quedamos_en"])}</p>'
            f'<p><span class="chip">Próximo paso</span>{_esc(plan["nombre_paso"])} · {_esc(formato_minutos(plan["minutos"]))} · '
            f'Primero: {_esc(plan["primero"])}</p>'
            f'<p class="sub">Término estimado de la etapa: {_esc(proy["termino_etapa"])} · del programa: '
            f'{_esc(proy["termino_programa"])} ({_esc(ritmo)}).</p></div>')

    kpis = [
        ("Semanas aprobadas", f"{len(r['aprobadas'])}/{TOTAL_SEMANAS}",
         f"Nivel: {r['nivel'] or 'en camino a ' + str(r['proximo_nivel'] or '')}"),
        ("Racha semanal", f"{racha['actual']} sem.",
         f"mejor {racha['mejor']} · comodín del mes: {'disponible' if racha['comodin_disponible'] else 'usado'}"),
        ("Esta semana (meta vs. real)", f"{w['sesiones']}/{w['piso_sesiones']} ses.",
         f"{w['minutos']} min · {texto_falta_piso(w)}" + (" · cierre de mes" if w["cierre"] else "")),
        ("Recuperación", _pct(rec["a_1_semana"] if rec["a_1_semana"] is not None else rec["ultimos_30_dias"]),
         f"a 1 semana {_pct(rec['a_1_semana'])} (meta 80%) · a 1 mes {_pct(rec['a_1_mes'])} (meta 70%)"),
        ("Repasos vencidos", str(len(r["repasos_vencidos"])), f"{r['tarjetas_activas']} tarjetas activas"),
    ]
    partes.append('<section class="kpis">' + "".join(
        f'<div class="card kpi"><div class="lab">{_esc(a)}</div><div class="val">{_esc(b)}</div>'
        f'<div class="det">{_esc(c)}</div></div>' for a, b, c in kpis) + "</section>")

    lis = "".join(f"<li><strong>{m} min</strong> · {_esc(t)}</li>" for m, t in plan["bloques"])
    bloque_plan = (f'<div class="card"><h2>Próxima sesión · {_esc(plan["nombre_paso"])} '
                   f'({_esc(formato_minutos(plan["minutos"]))})</h2><ol>{lis}</ol>'
                   + (f'<p class="sub">Si-entonces pendiente: {_esc(plan["si_entonces_anterior"])}</p>'
                      if plan["si_entonces_anterior"] else "") + "</div>")

    filas = []
    for e in ctx.malla.get("etapas", []):
        ini, fin = e.get("semanas", [0, 0])
        chips = []
        for s in range(ini, fin + 1):
            clases, estado_s = ["sem"], "pendiente"
            if s in aprob:
                clases.append("ok")
                estado_s = f"aprobada el {aprob[s]['fecha']}"
            elif s == n:
                clases.append("curso")
                estado_s = "en curso"
            if s in PROYECTOS_MALLA:
                clases.append("proy")
                estado_s += f" · proyecto {PROYECTOS_MALLA[s]}"
            tit = ctx.semanas.get(s, {}).get("titulo", "")
            chips.append(f'<span class="{" ".join(clases)}" title="Semana {s}: {_esc(tit)} ({_esc(estado_s)})">{s}</span>')
        hechas = sum(1 for s in range(ini, fin + 1) if s in aprob)
        filas.append(f'<div class="etapa"><div class="cab"><span>Etapa {e.get("numero")} · {_esc(e.get("nombre"))}'
                     f'{" · " + _esc(e.get("nivel")) if e.get("nivel") else ""}</span>'
                     f'<span>{hechas}/{fin - ini + 1}</span></div><div class="semanas">{"".join(chips)}</div></div>')
    bloque_etapas = ('<div class="card"><h2>Avance por etapa (el nivel se sube solo con evidencia)</h2>' + "".join(filas)
                     + '<div class="leyenda"><span><i class="sw" style="background:var(--acento)"></i>Aprobada</span>'
                       '<span><i class="sw" style="border:2px solid var(--acento)"></i>En curso</span>'
                       '<span><i class="sw"></i>Pendiente</span>'
                       '<span><i class="sw" style="background:var(--aviso);border-radius:50%"></i>Semana de proyecto</span></div></div>')

    por_lunes = {x["lunes"]: x for x in racha["semanas"]}
    lunes_hoy = lunes_de(hoy)
    celdas = []
    for k in range(11, -1, -1):
        lun = lunes_hoy - timedelta(weeks=k)
        x = por_lunes.get(lun.isoformat())
        if x is None and k == 0:
            x = racha["semana_en_curso"]
        if x is None:
            est, sym, txt = "vacia", "", "antes de empezar"
        else:
            est = x["estado"]
            sym, txt = ESTADOS_SEMANA.get(est, ("", est))
            txt += f" · {x['sesiones']} sesión(es), {x['minutos']} min · piso {x['piso_sesiones']} o {x['piso_minutos']} min"
            if x["cierre"]:
                txt += " · cierre de mes"
        celdas.append(f'<div class="wk" title="Semana del {_esc(fecha_corta(lun))}: {_esc(txt)}">'
                      f'<span class="c {est}">{_esc(sym)}</span><span class="f{" alt" if k % 2 else ""}">'
                      f'{lun.day:02d}/{lun.month:02d}</span></div>')
    leyenda_racha = '<div class="leyenda">' + "".join(
        f'<span><i class="sw" style="{estilo}"></i>{_esc(sym)} {_esc(txt)}</span>'
        for sym, txt, estilo in (
            ("✓", "Cumplida", "background:var(--acento)"),
            ("R", "Reparada", "background:var(--acento-medio)"),
            ("C", "Comodín", "background:repeating-linear-gradient(45deg,var(--rayado) 0 2px,transparent 2px 6px),var(--neutro)"),
            ("P", "Pausa", "background:var(--neutro)"),
            ("✗", "Cortada", "border:2px solid var(--critico)"),
            ("…", "En curso", "border:2px dashed var(--acento)"))) + "</div>"
    bloque_racha = ('<div class="card"><h2>Racha semanal (últimas 12 semanas)</h2>'
                    '<p class="sub">Piso: 3 sesiones o 60 min (cierre de mes: 2 o 30). 1 comodín al mes; una semana '
                    'fallida se repara con 2 sesiones (o el piso) la semana siguiente.</p>'
                    f'<div class="tira">{"".join(celdas)}</div>{leyenda_racha}</div>')

    barras, ejes = [], []
    semanas_cal = [lunes_hoy - timedelta(weeks=k) for k in range(7, -1, -1)]
    infos = []
    for l in semanas_cal:
        x = por_lunes.get(l.isoformat())
        if x is None:
            cierre = es_semana_de_cierre(l, ctx.config["dias_cierre_mes"])
            x = {"sesiones": 0, "minutos": 0, "cierre": cierre,
                 "piso_sesiones": ctx.config["piso_cierre_sesiones" if cierre else "piso_sesiones"]}
        infos.append(x)
    tope = max([x["sesiones"] for x in infos] + [x["piso_sesiones"] for x in infos] + [4]) * 1.15
    maximo = max(x["sesiones"] for x in infos)
    for i, (lun, x) in enumerate(zip(semanas_cal, infos)):
        alto = 100 * x["sesiones"] / tope
        piso = 100 * x["piso_sesiones"] / tope
        etiqueta = str(x["sesiones"]) if i == len(infos) - 1 or (maximo and x["sesiones"] == maximo) else ""
        barras.append(f'<div class="barra" title="Semana del {_esc(fecha_corta(lun))}: {x["sesiones"]} sesión(es), '
                      f'{x["minutos"]} min · piso {x["piso_sesiones"]}{" (cierre de mes)" if x.get("cierre") else ""}">'
                      f'<span class="piso" style="bottom:{piso:.1f}%"></span>'
                      f'<span class="v">{_esc(etiqueta)}</span><span class="b" style="height:{alto:.1f}%"></span></div>')
        ejes.append(f"<span>{lun.day:02d}/{lun.month:02d}</span>")
    bloque_barras = ('<div class="card"><h2>Sesiones por semana vs. piso</h2>'
                     '<p class="sub">Barra: sesiones reales. Línea: piso de esa semana (baja en cierre de mes).</p>'
                     f'<div class="barras">{"".join(barras)}</div><div class="ejes">{"".join(ejes)}</div></div>')

    filas_p = []
    for sem, nombre in PROYECTOS_MALLA.items():
        if sem in aprob:
            est = '<span class="ok-t">✓ Aprobado</span>'
            ev = aprob[sem]["evidencia"]
            ev_html = f'<a href="{_esc(ev)}">{_esc(ev)}</a>' if RE_URL.fullmatch(ev.strip()) else _esc(ev)
        elif sem == n:
            est, ev_html = "● En curso", ""
        else:
            est, ev_html = "○ Pendiente", ""
        entreg = ctx.semanas.get(sem, {}).get("entregable", "")
        filas_p.append(f'<tr><td class="num">{sem}</td><td><strong>{_esc(nombre)}</strong><div class="sub desc">{_esc(entreg)}</div></td>'
                       f'<td class="est">{est}</td><td class="ev">{ev_html}</td></tr>')
    bloque_proy = ('<div class="card" style="margin-top:12px"><h2>Proyectos y artefactos</h2><div class="tabla-scroll"><table>'
                   '<thead><tr><th>Sem.</th><th>Proyecto</th><th>Estado</th><th>Evidencia</th></tr></thead>'
                   f'<tbody>{"".join(filas_p)}</tbody></table></div></div>')

    por_caja = {c: 0 for c in CAJAS}
    prox7 = 0
    for t in ctx.tarjetas.get("tarjetas", {}).values():
        por_caja[caja(t)] += 1
        try:
            if hoy < date.fromisoformat(t["proxima"]) <= hoy + timedelta(days=7):
                prox7 += 1
        except (KeyError, ValueError):
            pass
    maxc = max(por_caja.values()) or 1
    hbars = "".join(f'<div class="hbar" title="{_esc(c)}: {v} tarjetas"><span>{_esc(c)}</span><span>'
                    f'<span class="f" style="width:{100 * v / maxc:.1f}%"></span></span><span class="n">{v}</span></div>'
                    for c, v in por_caja.items())
    bloque_rep = (f'<div class="card"><h2>Repasos (repetición espaciada)</h2>'
                  f'<p class="sub">Vencidos hoy: <strong>{len(r["repasos_vencidos"])}</strong> · próximos 7 días: {prox7} · '
                  f'aciertos últimos 30 días: {_pct(rec["ultimos_30_dias"])} ({rec["n_30_dias"]} respuestas).</p>'
                  f'{hbars}<p class="sub">Tarjetas por intervalo, de «Nueva» a «Dominada». Se activan al aprobar cada semana.</p></div>')

    park = ctx.estado.get("parking", [])[-8:]
    items_p = "".join(f'<li>{_esc(p["idea"])} <span class="sub">({_esc(p["fecha"])})</span></li>' for p in reversed(park)) \
        or '<li class="sub">Vacío. Lo nuevo o de moda se anota aquí y no desvía la sesión.</li>'
    ult = list(reversed(ctx.estado.get("sesiones", [])[-6:]))
    items_b = "".join(f'<li><strong>{_esc(s["fecha"])}</strong> · Sem. {_esc(s.get("semana"))} · {_esc(s.get("tipo"))} · '
                      f'{_esc(formato_minutos(s.get("minutos", 0)))}'
                      + (f' · logrado: {_esc(s.get("logrado"))}' if s.get("logrado") else "")
                      + f'<div class="sub">{_esc(s.get("nota", ""))}</div></li>' for s in ult) \
        or '<li class="sub">Sin sesiones todavía. La primera es la más importante.</li>'
    bloque_notas = (f'<div class="card"><h2>Últimas sesiones</h2><ul>{items_b}</ul>'
                    f'<h2 style="margin-top:16px">Parking de ideas</h2><ul>{items_p}</ul></div>')

    filas_t = []
    for s in range(1, TOTAL_SEMANAS + 1):
        d = ctx.semanas.get(s, {})
        est = (f"Aprobada {aprob[s]['fecha']}" if s in aprob else "En curso" if s == n else "Pendiente")
        filas_t.append(f'<tr><td class="num">{s}</td><td class="num">{_esc(d.get("etapa"))}</td><td>{_esc(d.get("titulo"))}</td>'
                       f'<td class="num">{_esc(d.get("horas"))}</td><td>{_esc(est)}</td></tr>')
    bloque_tabla = ('<div class="card" style="margin-top:12px"><details><summary>Ver las 24 semanas en tabla</summary>'
                    '<div class="tabla-scroll"><table><thead><tr><th>Sem.</th><th>Etapa</th><th>Título</th><th>Horas</th>'
                    f'<th>Estado</th></tr></thead><tbody>{"".join(filas_t)}</tbody></table></div></details></div>')

    cuerpo = ("".join(partes)
              + f'<section class="grid">{bloque_plan}{bloque_etapas}</section>'
              + f'<section class="grid">{bloque_racha}{bloque_barras}</section>'
              + bloque_proy
              + f'<section class="grid">{bloque_rep}{bloque_notas}</section>'
              + bloque_tabla
              + f'<footer>Generado por <code>herramientas/tutor.py</code> el {hoy.isoformat()} desde progreso/estado.json '
                'y progreso/tarjetas.json. Se regenera en cada registro; no lo edites a mano.</footer>')
    return ("<!doctype html>\n<html lang=\"es\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>Hoja de Combate</title>\n"
            f"<style>{CSS_PANEL}</style>\n</head>\n<body>\n<main>\n{cuerpo}\n</main>\n</body>\n</html>\n")


# ---------------------------------------------------------------------------
# Validación («recórrelo y confírmalo»)
# ---------------------------------------------------------------------------
class Informe:
    def __init__(self):
        self.items = []  # (nivel, seccion, mensaje)

    def ok(self, sec, msg):
        self.items.append(("OK", sec, msg))

    def aviso(self, sec, msg):
        self.items.append(("AVISO", sec, msg))

    def error(self, sec, msg):
        self.items.append(("ERROR", sec, msg))

    @property
    def errores(self):
        return [i for i in self.items if i[0] == "ERROR"]

    @property
    def avisos(self):
        return [i for i in self.items if i[0] == "AVISO"]


def _parse_frontmatter(texto: str):
    lineas = texto.splitlines()
    if not lineas or lineas[0].strip() != "---":
        return None, "el archivo no empieza con una línea «---» (frontmatter YAML)"
    try:
        fin = next(i for i in range(1, len(lineas)) if lineas[i].strip() == "---")
    except StopIteration:
        return None, "el frontmatter no tiene la línea «---» de cierre"
    campos = {}
    for linea in lineas[1:fin]:
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", linea)
        if not m:
            return None, f"línea de frontmatter no válida: «{linea[:60]}»"
        clave, valor = m.group(1), m.group(2).strip()
        if valor[:1] in "\"'" and valor[-1:] == valor[:1] and len(valor) >= 2:
            valor = valor[1:-1]
        elif ": " in valor or " #" in valor:
            return None, f"el valor de «{clave}» tiene «: » o « #» sin comillas (YAML inválido)"
        campos[clave] = valor
    return campos, None


RE_OBJETIVO_VERBO = re.compile(r"^[a-záéíóúñ]+(ar|er|ir)$", re.I)


def _validar_malla(rutas: Rutas, inf: Informe):
    sec = "Malla"
    try:
        malla = cargar_malla(rutas)
    except ErrorTutor as e:
        inf.error(sec, str(e))
        return None
    etapas = {e.get("numero"): e for e in malla.get("etapas", []) if isinstance(e, dict)}
    if set(etapas) != set(ETAPAS_MALLA):
        inf.error(sec, f"se esperaban las etapas 1–6 y hay: {sorted(k for k in etapas if k is not None)}")
    for num, esp in ETAPAS_MALLA.items():
        e = etapas.get(num)
        if not e:
            continue
        if list(e.get("semanas", [])) != list(esp["semanas"]):
            inf.error(sec, f"etapa {num}: semanas {e.get('semanas')} ≠ {list(esp['semanas'])} de la malla")
        if e.get("horas") != esp["horas"]:
            inf.error(sec, f"etapa {num}: horas declaradas {e.get('horas')} ≠ {esp['horas']} de la malla")
        for campo in ("nombre", "entregable"):
            if not str(e.get(campo, "")).strip():
                inf.error(sec, f"etapa {num}: falta «{campo}»")
        if not e.get("nivel"):
            inf.aviso(sec, f"etapa {num}: sin «nivel» (gamificación)")
    lista = [s for s in malla.get("semanas", []) if isinstance(s, dict)]
    numeros = [s.get("semana") for s in lista]
    if numeros != list(range(1, TOTAL_SEMANAS + 1)):
        faltan = sorted(set(range(1, TOTAL_SEMANAS + 1)) - set(n for n in numeros if isinstance(n, int)))
        extra = [n for n in numeros if n not in range(1, TOTAL_SEMANAS + 1)]
        dup = sorted({n for n in numeros if numeros.count(n) > 1})
        inf.error(sec, f"las semanas deben ser 1..24 consecutivas y en orden (faltan {faltan}, "
                       f"sobran {extra}, duplicadas {dup})")
    elif set(etapas) == set(ETAPAS_MALLA):
        inf.ok(sec, "24 semanas consecutivas (1..24) y 6 etapas con los rangos de la malla")
    errores_campos = 0
    objetivos = {}
    for s in lista:
        n = s.get("semana")
        for campo in CAMPOS_SEMANA:
            if campo not in s:
                inf.error(sec, f"semana {n}: falta el campo «{campo}»")
                errores_campos += 1
                continue
            v = s[campo]
            if campo == "lectura":
                if not isinstance(v, list) or not all(isinstance(x, str) and x.strip() for x in v):
                    inf.error(sec, f"semana {n}: «lectura» debe ser una lista de ids (puede estar vacía)")
                    errores_campos += 1
                continue
            vacio = v is None or (isinstance(v, (str, list, dict)) and not v) or (isinstance(v, str) and not v.strip())
            if vacio:
                inf.error(sec, f"semana {n}: el campo «{campo}» está vacío")
                errores_campos += 1
        etapa = s.get("etapa")
        if etapa in ETAPAS_MALLA and isinstance(n, int):
            ini, fin = ETAPAS_MALLA[etapa]["semanas"]
            if not ini <= n <= fin:
                inf.error(sec, f"semana {n}: dice etapa {etapa}, pero esa etapa cubre las semanas {ini}–{fin}")
        elif "etapa" in s:
            inf.error(sec, f"semana {n}: etapa «{etapa}» no existe")
        conceptos = s.get("conceptos")
        if isinstance(conceptos, list) and (len(conceptos) < 3 or not all(isinstance(c, str) and c.strip() for c in conceptos)):
            inf.error(sec, f"semana {n}: «conceptos» debe tener al menos 3 textos no vacíos")
        preg = s.get("preguntas_de_repaso")
        if isinstance(preg, list) and preg:
            if not 3 <= len(preg) <= 5:
                inf.error(sec, f"semana {n}: debe tener 3–5 preguntas de repaso (tiene {len(preg)})")
            for i, q in enumerate(preg, 1):
                if not isinstance(q, dict) or not str(q.get("pregunta", "")).strip() or not str(q.get("respuesta", "")).strip():
                    inf.error(sec, f"semana {n}, pregunta {i}: necesita «pregunta» y «respuesta» no vacías")
        horas = s.get("horas")
        if "horas" in s and (not isinstance(horas, (int, float)) or isinstance(horas, bool) or horas <= 0):
            inf.error(sec, f"semana {n}: «horas» debe ser un número positivo")
        elif isinstance(horas, (int, float)) and not 4 <= horas <= 14:
            inf.aviso(sec, f"semana {n}: {horas} h está fuera del rango típico de 8–10 h por semana de contenido")
        obj = s.get("objetivo")
        if "objetivo" in s:
            if not isinstance(obj, str):
                inf.error(sec, f"semana {n}: el objetivo debe ser UN texto (no una lista)")
            elif obj.strip():
                o = obj.strip()
                cuerpo = o[:-1] if o[-1:] in ".!?" else o
                primera = re.split(r"[\s,]+", o)[0]
                if "\n" in o or ";" in o or re.search(r"[.!?]\s+\S", cuerpo):
                    inf.error(sec, f"semana {n}: el objetivo debe ser una sola oración (uno, verificable)")
                if not RE_OBJETIVO_VERBO.match(primera):
                    inf.error(sec, f"semana {n}: el objetivo debe partir con un verbo en infinitivo (recibí «{primera}»)")
                if not 20 <= len(o) <= 260:
                    inf.error(sec, f"semana {n}: el objetivo tiene {len(o)} caracteres (esperado 20–260)")
                objetivos.setdefault(normalizar(o), []).append(n)
    for semanas_dup in (v for v in objetivos.values() if len(v) > 1):
        inf.error(sec, f"objetivo repetido en las semanas {semanas_dup}: cada semana tiene su objetivo único")
    if not errores_campos and len(lista) == TOTAL_SEMANAS:
        inf.ok(sec, "todas las semanas tienen sus 12 campos y un objetivo único por semana")
    total = sum(s.get("horas", 0) for s in lista if isinstance(s.get("horas"), (int, float)))
    if abs(total - HORAS_TOTALES_MALLA) > TOLERANCIA_HORAS_TOTAL:
        inf.error(sec, f"las horas suman {total}; la malla dice ~{HORAS_TOTALES_MALLA} (±{TOLERANCIA_HORAS_TOTAL})")
    else:
        inf.ok(sec, f"horas totales: {total:g} (malla: ~{HORAS_TOTALES_MALLA})")
    malas = []
    for num, esp in ETAPAS_MALLA.items():
        suma = sum(s.get("horas", 0) for s in lista if s.get("etapa") == num and isinstance(s.get("horas"), (int, float)))
        if abs(suma - esp["horas"]) > TOLERANCIA_HORAS_ETAPA:
            malas.append(f"etapa {num}: {suma:g} h ≠ {esp['horas']} h")
    if malas:
        inf.error(sec, "horas por etapa no calzan con la malla: " + "; ".join(malas))
    else:
        inf.ok(sec, "horas por etapa calzan con la malla (24/28/36/34/40/48)")
    proy_top = {p.get("semana"): p.get("nombre") for p in malla.get("proyectos", []) if isinstance(p, dict)}
    if proy_top != PROYECTOS_MALLA:
        inf.error(sec, f"lista «proyectos» debe ser exactamente {PROYECTOS_MALLA} (hay {proy_top})")
    prob = []
    for s in lista:
        n = s.get("semana")
        p = s.get("proyecto")
        if n in PROYECTOS_MALLA:
            if not isinstance(p, dict) or p.get("nombre") != PROYECTOS_MALLA[n] or not str(p.get("resultado", "")).strip():
                prob.append(f"semana {n} debe tener proyecto «{PROYECTOS_MALLA[n]}» con resultado")
        elif p:
            prob.append(f"semana {n} tiene un proyecto, pero la malla no pone proyecto ahí")
    for p in prob:
        inf.error(sec, p)
    if not prob and proy_top == PROYECTOS_MALLA:
        inf.ok(sec, "proyectos en las semanas 3, 6, 10, 14, 19 y 24 (cierre de cada etapa)")
    return malla


def _validar_fuentes_y_fichas(rutas: Rutas, malla, inf: Informe):
    sec = "Base de conocimiento"
    lecturas = {}
    for s in (malla or {}).get("semanas", []):
        if isinstance(s, dict) and isinstance(s.get("lectura"), list):
            for fid in s["lectura"]:
                lecturas.setdefault(fid, []).append(s.get("semana"))
    vacias = [s.get("semana") for s in (malla or {}).get("semanas", []) if isinstance(s, dict) and not s.get("lectura")]
    fuentes = None
    try:
        lista = leer_lista_fuentes(rutas)
    except (json.JSONDecodeError, ErrorTutor) as e:
        inf.error(sec, f"base/fuentes.json no se puede leer: {e}")
        lista = None
    if lista is None and not rutas.fuentes.exists():
        inf.aviso(sec, "base/fuentes.json aún no existe (lo entrega el agente 2): no puedo verificar lecturas")
        if lecturas:
            inf.aviso(sec, f"{len(lecturas)} ids en «lectura» quedan sin verificar")
    elif lista is not None:
        fuentes = indice_fuentes(lista)
        ids = [f.get("id") for f in lista if isinstance(f, dict)]
        sin_id = sum(1 for f in lista if not isinstance(f, dict) or not isinstance(f.get("id"), str) or not f.get("id"))
        if sin_id:
            inf.error(sec, f"{sin_id} fuente(s) sin «id» de texto")
        dup = sorted({i for i in ids if i and ids.count(i) > 1})
        if dup:
            inf.error(sec, f"ids de fuente duplicados: {dup}")
        faltan_campos = {}
        for f in lista:
            if isinstance(f, dict):
                for c in CAMPOS_FUENTE:
                    if c not in f:
                        faltan_campos[c] = faltan_campos.get(c, 0) + 1
                for c, rango in (("semanas", range(1, TOTAL_SEMANAS + 1)), ("etapas", range(1, 7))):
                    v = f.get(c)
                    if v is not None and (not isinstance(v, list) or any(x not in rango for x in v)):
                        inf.error(sec, f"fuente «{f.get('id')}»: «{c}» debe ser lista de números válidos (recibí {v})")
        if faltan_campos:
            inf.aviso(sec, "fuentes sin algunos campos: " + ", ".join(f"{c} ({k})" for c, k in sorted(faltan_campos.items())))
        inexistentes = {fid: sem for fid, sem in lecturas.items() if fid not in fuentes}
        for fid, sem in sorted(inexistentes.items()):
            inf.error(sec, f"lectura «{fid}» (semana(s) {sem}) no existe en base/fuentes.json")
        if not inexistentes:
            inf.ok(sec, f"base/fuentes.json: {len(fuentes)} fuentes; todos los ids de «lectura» existen")
        prop = proponer_lecturas(malla or {}, lista)
        no_asignadas = sorted({i for ids_p in prop.values() for i in ids_p if i not in lecturas})
        if no_asignadas:
            inf.aviso(sec, f"{len(no_asignadas)} fuente(s) sugeridas para alguna semana aún no están en «lectura» "
                           "→ python3 herramientas/tutor.py integrar-lecturas --aplicar")
    if vacias:
        inf.aviso(sec, f"{len(vacias)} semana(s) con «lectura» vacía (pendiente integrar la base de conocimiento)")
    if not rutas.fichas.is_dir():
        inf.aviso(sec, "base/fichas/ aún no existe (lo entrega el agente 2)")
        return
    fichas = cargar_fichas(rutas)
    total_p, malas = 0, 0
    for fid, info in fichas.items():
        rel = rutas.rel(info["ruta"])
        if not info["encontrada"]:
            inf.error(sec, f"{rel}: no tiene la sección «## Preguntas de práctica»")
            malas += 1
            continue
        for e in info["errores"]:
            inf.error(sec, f"{rel}: {e}")
        if info["errores"]:
            malas += 1
        if not info["preguntas"]:
            inf.error(sec, f"{rel}: no tiene preguntas parseables (formato «- P: ...» / «  R: ...»)")
            malas += 1
        total_p += len(info["preguntas"])
        if fuentes is not None and fid not in fuentes:
            inf.aviso(sec, f"{rel}: el id «{fid}» no está en base/fuentes.json")
    if fichas and not malas:
        inf.ok(sec, f"{len(fichas)} fichas con {total_p} preguntas de práctica parseables")
    elif not fichas:
        inf.aviso(sec, "base/fichas/ está vacía")
    sin_ficha = sorted(fid for fid in lecturas if fid not in fichas)
    if sin_ficha:
        inf.aviso(sec, f"{len(sin_ficha)} lectura(s) sin ficha en base/fichas/: {', '.join(sin_ficha[:8])}")


def _subcomandos_conocidos() -> set:
    for accion in construir_parser()._actions:  # noqa: SLF001
        if isinstance(accion, argparse._SubParsersAction):  # noqa: SLF001
            return set(accion.choices)
    return set()


def _validar_skill_y_docs(rutas: Rutas, inf: Informe):
    sec = "Skill y documentación"
    if not rutas.skill.exists():
        inf.error(sec, f"no existe {rutas.rel(rutas.skill)}")
        return
    texto = rutas.skill.read_text(encoding="utf-8")
    campos, err = _parse_frontmatter(texto)
    if err:
        inf.error(sec, f"SKILL.md: {err}")
    else:
        nombre = campos.get("name", "")
        desc = campos.get("description", "")
        if nombre != NOMBRE_SKILL:
            inf.error(sec, f"SKILL.md: name debe ser «{NOMBRE_SKILL}» (igual a la carpeta); recibí «{nombre}»")
        elif not re.fullmatch(r"[a-z0-9-]{1,64}", nombre):
            inf.error(sec, "SKILL.md: name solo admite minúsculas, números y guiones (máx. 64)")
        if not desc:
            inf.error(sec, "SKILL.md: falta description")
        else:
            if len(desc) > 1024:
                inf.error(sec, f"SKILL.md: description tiene {len(desc)} caracteres (máx. 1024)")
            if "<" in desc or ">" in desc:
                inf.error(sec, "SKILL.md: description no puede tener «<» ni «>»")
            faltan = [f for f in FRASES_DISPARO if normalizar(f) not in normalizar(desc)]
            if faltan:
                inf.error(sec, f"SKILL.md: la description no incluye las frases de disparo {faltan}")
        extra = set(campos) - {"name", "description", "license", "allowed-tools", "metadata", "version"}
        if extra:
            inf.aviso(sec, f"SKILL.md: claves de frontmatter no estándar: {sorted(extra)}")
        if nombre == NOMBRE_SKILL and desc and len(desc) <= 1024:
            inf.ok(sec, "SKILL.md: frontmatter válido (name + description con frases de disparo)")
    for s in SECCIONES_SKILL:
        if s.lower() not in texto.lower():
            inf.error(sec, f"SKILL.md: falta la sección «{s}»")
    if MARCA_INTEGRAR not in texto:
        inf.error(sec, "SKILL.md: falta el marcador de integración " + MARCA_INTEGRAR)
    elif MARCA_PENDIENTE in texto:
        inf.aviso(sec, "SKILL.md: la sección de reglas 01/03 sigue «Pendiente de integración»")
    conocidos = _subcomandos_conocidos()
    for doc in (rutas.skill, rutas.raiz / "CLAUDE.md", rutas.raiz / "README.md"):
        if doc.exists():
            usados = set(re.findall(r"tutor\.py\s+([a-z][a-z-]*)", doc.read_text(encoding="utf-8")))
            desconocidos = sorted(usados - conocidos)
            if desconocidos:
                inf.error(sec, f"{rutas.rel(doc)} menciona comandos que no existen: {desconocidos}")


def verificar_estado(ctx: Contexto) -> list[str]:
    """Consistencia de la memoria. Devuelve la lista de errores (vacía = OK)."""
    errores = []
    e, hoy = ctx.estado, ctx.hoy
    sa = e.get("semana_actual")
    if not isinstance(sa, int) or not 1 <= sa <= SEMANA_FIN:
        return [f"semana_actual inválida: {sa}"]
    aprobs = e.get("aprobaciones", [])
    semanas_aprob = [a.get("semana") for a in aprobs]
    if semanas_aprob != list(range(1, sa)):
        errores.append(f"aprobaciones {semanas_aprob} no calzan con semana_actual={sa} (deberían ser 1..{sa - 1})")
    fecha_prev = None
    for a in aprobs:
        n = a.get("semana")
        if not str(a.get("evidencia", "")).strip():
            errores.append(f"semana {n} aprobada sin evidencia")
        try:
            f = date.fromisoformat(a.get("fecha", ""))
            if f > hoy:
                errores.append(f"semana {n} aprobada en fecha futura ({f})")
            if fecha_prev and f < fecha_prev:
                errores.append(f"aprobación de la semana {n} con fecha anterior a la previa")
            fecha_prev = f
        except (ValueError, TypeError):
            errores.append(f"semana {n}: fecha de aprobación inválida")
        if n in PROYECTOS_MALLA and a.get("tipo_evidencia") not in ("archivo", "url"):
            errores.append(f"semana de proyecto {n} aprobada sin artefacto (archivo o URL)")
        rub = a.get("rubrica") or {}
        if isinstance(n, int):
            bajos = [c for c in criterios_semana(n) if not isinstance(rub.get(c), int) or rub[c] < UMBRAL_RUBRICA]
            if bajos:
                errores.append(f"semana {n} aprobada sin alcanzar la rúbrica en: {', '.join(bajos)}")
        if a.get("modalidad", "normal") not in ("normal", "test-out"):
            errores.append(f"semana {n}: modalidad inválida ({a.get('modalidad')})")
    for i, s in enumerate(e.get("sesiones", []), 1):
        try:
            f = date.fromisoformat(s.get("fecha", ""))
            if f > hoy:
                errores.append(f"sesión {i}: fecha futura ({f})")
        except (ValueError, TypeError):
            errores.append(f"sesión {i}: fecha inválida")
        m = s.get("minutos")
        if not isinstance(m, int) or isinstance(m, bool) or not 1 <= m <= 600:
            errores.append(f"sesión {i}: minutos inválidos ({m})")
        if s.get("tipo") not in TIPOS_SESION:
            errores.append(f"sesión {i}: tipo inválido ({s.get('tipo')})")
        if s.get("logrado") is not None and s.get("logrado") not in LOGRADO:
            errores.append(f"sesión {i}: «logrado» inválido ({s.get('logrado')})")
        sem = s.get("semana")
        if not isinstance(sem, int) or not 1 <= sem <= min(sa, TOTAL_SEMANAS):
            errores.append(f"sesión {i}: semana {sem} fuera de rango (semana en curso: {sa})")
        if not str(s.get("nota", "")).strip():
            errores.append(f"sesión {i}: sin nota")
    for p in e.get("pausas", []):
        try:
            if date.fromisoformat(p["desde"]) > date.fromisoformat(p["hasta"]):
                errores.append(f"pausa {p}: «desde» posterior a «hasta»")
        except (KeyError, ValueError, TypeError):
            errores.append(f"pausa inválida: {p}")
    for p in e.get("parking", []):
        if not str(p.get("idea", "")).strip():
            errores.append("idea vacía en el parking")
    tarjetas = ctx.tarjetas.get("tarjetas", {})
    for tid, t in tarjetas.items():
        c = ctx.catalogo.get(tid)
        if not c:
            errores.append(f"tarjeta huérfana «{tid}» (no existe en la malla ni en las fichas)")
            continue
        if c["origen"] == "malla" and c["semana"] >= sa:
            errores.append(f"tarjeta «{tid}» activa, pero la semana {c['semana']} aún no se aprueba")
        try:
            if float(t.get("ef", 0)) < EF_MINIMO - 1e-9:
                errores.append(f"tarjeta «{tid}»: facilidad < {EF_MINIMO}")
            if int(t.get("intervalo", -1)) < 0 or int(t.get("repeticiones", -1)) < 0:
                errores.append(f"tarjeta «{tid}»: intervalo/repeticiones negativos")
            prox = date.fromisoformat(t.get("proxima", ""))
            act = date.fromisoformat(t.get("activada", ""))
            if prox < act:
                errores.append(f"tarjeta «{tid}»: próxima revisión antes de activarse")
        except (ValueError, TypeError):
            errores.append(f"tarjeta «{tid}»: campos inválidos")
        for h in t.get("historial", []):
            if not isinstance(h.get("calidad"), int) or not 0 <= h["calidad"] <= 5:
                errores.append(f"tarjeta «{tid}»: calidad inválida en historial")
    for n in range(1, min(sa, SEMANA_FIN)):
        faltan = [tid for tid in ids_tarjetas_semana(ctx, n) if tid not in tarjetas]
        if faltan:
            errores.append(f"semana {n} aprobada pero sus tarjetas no están activas: {faltan}")
    try:
        racha_de(ctx)
    except Exception as ex:  # pragma: no cover - defensivo
        errores.append(f"no se pudo calcular la racha: {ex}")
    return errores


def _validar_estado(rutas: Rutas, hoy: date, inf: Informe):
    sec = "Estado del estudiante"
    if not rutas.estado.exists():
        inf.aviso(sec, f"{rutas.rel(rutas.estado)} no existe todavía (python3 herramientas/tutor.py iniciar)")
        return
    try:
        ctx = Contexto(rutas, hoy)
    except (json.JSONDecodeError, ErrorTutor) as e:
        inf.error(sec, f"no se pudo leer el progreso: {e}")
        return
    errores = verificar_estado(ctx)
    for err in errores:
        inf.error(sec, err)
    if not errores:
        r = resumen(ctx)
        inf.ok(sec, f"estado.json y tarjetas.json consistentes (semana {r['semana_actual']}, "
                    f"{len(r['aprobadas'])} aprobadas, {len(ctx.estado['sesiones'])} sesiones, "
                    f"{r['tarjetas_activas']} tarjetas)")
    if not rutas.bitacora.exists():
        inf.aviso(sec, "progreso/bitacora.md no existe")
    if not rutas.panel.exists():
        inf.aviso(sec, "progreso/panel.html no existe (python3 herramientas/tutor.py panel)")


def validar(rutas: Rutas, hoy: date) -> Informe:
    inf = Informe()
    sec = "Archivos del programa"
    requeridos = ["curriculo/malla.json", "herramientas/tutor.py", "herramientas/simular.py",
                  "tests/test_tutor.py", f".claude/skills/{NOMBRE_SKILL}/SKILL.md", "CLAUDE.md", "README.md"]
    faltan = [r for r in requeridos if not (rutas.raiz / r).exists()]
    for f in faltan:
        inf.error(sec, f"falta {f}")
    if not faltan:
        inf.ok(sec, f"{len(requeridos)}/{len(requeridos)} archivos presentes")
    malla = _validar_malla(rutas, inf)
    _validar_fuentes_y_fichas(rutas, malla, inf)
    _validar_skill_y_docs(rutas, inf)
    _validar_estado(rutas, hoy, inf)
    sec = "Integración con agentes 1–3"
    for nombre, quien in (("01-revision-idea-tutor.md", "agente 1"), ("02-base-de-conocimiento.md", "agente 2"),
                          ("03-reglas-del-tutor.md", "agente 3")):
        if not (rutas.investigacion / nombre).exists():
            inf.aviso(sec, f"investigacion/{nombre} aún no existe ({quien})")
    return inf


# ---------------------------------------------------------------------------
# Salida de texto de cada comando
# ---------------------------------------------------------------------------
def texto_estado(ctx: Contexto) -> str:
    r = resumen(ctx)
    rc = r["racha"]
    w = r["semana_calendario"]
    out = [f"ESTADO · {fecha_corta(ctx.hoy)}"]
    if r["terminado"]:
        out.append("Programa completado: 24/24 semanas aprobadas. Nivel: AI Business Builder.")
    else:
        out.append(f"Semana {r['semana_actual']}/{TOTAL_SEMANAS} · Etapa {r['etapa']} — {r['nombre_etapa']}")
        out.append(f"«{r['titulo']}»")
        out.append(f"Objetivo: {r['objetivo']}")
    barra = "█" * len(r["aprobadas"]) + "░" * (TOTAL_SEMANAS - len(r["aprobadas"]))
    out.append(f"Avance: {len(r['aprobadas'])}/{TOTAL_SEMANAS} semanas de contenido ({r['porcentaje']}%) {barra}")
    out.append("Etapas: " + " · ".join(f"E{e['numero']} {e['aprobadas']}/{e['total']}" for e in r["etapas"])
               + f" · Nivel: {r['nivel'] or '—'}")
    if rc["estado"] == "sin_iniciar":
        out.append("Racha semanal: parte con tu primera semana (piso: 3 sesiones o 60 min).")
    else:
        out.append(f"Racha semanal: {rc['actual']} (mejor {rc['mejor']}) · comodín del mes: "
                   f"{'disponible' if rc['comodin_disponible'] else 'usado'}")
    out.append(f"Esta semana: {w['sesiones']} sesión(es), {w['minutos']} min · {texto_falta_piso(w)}"
               + (" · semana de cierre de mes (piso reducido)" if w["cierre"] else ""))
    if r["en_pausa_declarada"]:
        out.append("Pausa declarada vigente: la racha está congelada.")
    if r["ultima_sesion"]:
        out.append(f"Quedamos en: {r['quedamos_en']} (última sesión: {r['ultima_sesion']})")
    if r["si_entonces"]:
        out.append(f"Si-entonces: {r['si_entonces']}")
    rec = r["recuperacion"]
    out.append(f"Repasos vencidos: {len(r['repasos_vencidos'])} (de {r['tarjetas_activas']} tarjetas) · "
               f"recuperación a 1 semana: {_pct(rec['a_1_semana'])} (meta 80%)")
    if r["parking"]:
        out.append(f"Parking de ideas: {r['parking']} (python3 herramientas/tutor.py parking para verlas)")
    if not r["terminado"]:
        out.append(f"Próximo paso: {r['paso_siguiente']} ({formato_minutos(MODOS[r['modo_siguiente']])}) — {r['motivo_paso']}")
        out.append("  → python3 herramientas/tutor.py hoy")
        p = r["proyeccion"]
        out.append(f"Término estimado: etapa {p['etapa']} el {p['termino_etapa']} · programa el {p['termino_programa']} "
                   f"(ritmo {'real' if p['ritmo_real'] else 'nominal'}: {p['ritmo_dias_por_semana']} días por semana de contenido)")
    if r["toca_retomar"]:
        out.append("Toca retomar el hilo → python3 herramientas/tutor.py retomar")
    return "\n".join(out)


def texto_plan(ctx: Contexto, plan: dict) -> str:
    cab = f"Quedamos en: {plan['quedamos_en']} · Hoy: {plan.get('hoy', '')} · Primero: {plan['primero']}"
    if plan["terminado"]:
        lineas = [f"HOY · {fecha_corta(ctx.hoy)} · Programa completado", cab, "", "PLAN (15 min)"]
        lineas += [f"  [{m:>2} min] {t}" for m, t in plan["bloques"]]
        return "\n".join(lineas)
    etapa = etapa_de(ctx.malla, plan.get("etapa"))
    lineas = [
        f"HOY · {fecha_corta(ctx.hoy)} · Semana {plan['semana']}/{TOTAL_SEMANAS} · Etapa {plan.get('etapa')} — {etapa.get('nombre', '')}",
        f"{plan.get('titulo', '')}",
        f"Paso: {plan['nombre_paso']} · modo {plan['modo']} · {formato_minutos(plan['minutos'])} ({plan['motivo']})",
        "",
        cab,
        "",
        "OBJETIVO ÚNICO DE LA SEMANA",
        f"  {plan.get('objetivo', '')}",
        "",
        "PLAN",
    ]
    lineas += [f"  [{m:>2} min] {t}" for m, t in plan["bloques"]]
    if plan.get("preguntas"):
        lineas += ["", "PREGUNTAS (sin mirar; el tutor muestra la respuesta después)"]
        lineas += [f"  [{t}] {ctx.catalogo[t]['pregunta']}" for t in plan["preguntas"] if t in ctx.catalogo]
    if plan.get("ultimo_rechazo"):
        lineas += ["", "LO QUE FALTÓ LA ÚLTIMA VEZ", f"  {plan['ultimo_rechazo']}"]
    if plan.get("si_entonces_anterior"):
        lineas += ["", f"SI-ENTONCES QUE DEJASTE: {plan['si_entonces_anterior']}"]
    lineas += ["", "LECTURA"]
    if plan["lecturas"]:
        for l in plan["lecturas"]:
            detalle = ", ".join(x for x in (l.get("autor"), f"{l['minutos']} min" if l.get("minutos") else None,
                                            "núcleo" if l.get("nucleo") else None) if x)
            marca = "[leída] " if l["leida"] else ""
            lineas.append(f"  {marca}{l['id']} — {l['titulo']}" + (f" ({detalle})" if detalle else ""))
            if l.get("url"):
                lineas.append(f"      {l['url']}")
            if l.get("ficha"):
                lineas.append(f"      ficha: {l['ficha']}")
        lineas.append("  Al registrar, agrega --leido <ID> para activar sus preguntas de repaso.")
    else:
        lineas.append("  Pendiente de integrar base/fuentes.json en la malla. Hoy trabaja con los conceptos; "
                      "el tutor no inventa fuentes.")
    if plan["paso"] not in ("micro", "reentrada", "mantenimiento"):
        lineas += ["", "SI SOLO TIENES 15 MIN", f"  {plan.get('version_micro', '')}"]
    return "\n".join(lineas)


def texto_retomar(ctx: Contexto, proto: dict) -> str:
    r = resumen(ctx)
    lineas = [f"RETOMAR · {fecha_corta(ctx.hoy)} · {proto['titulo']}", proto["mensaje"], "", "PASOS"]
    lineas += [f"  {i}. {p}" for i, p in enumerate(proto["pasos"], 1)]
    if r["ultima_sesion"]:
        lineas += ["", "DÓNDE QUEDAMOS", f"  {r['quedamos_en']}"]
        if r["si_entonces"]:
            lineas.append(f"  Si-entonces: {r['si_entonces']}")
    if proto["codigo"] in ("reentrada", "reinicio"):
        cantidad, faciles = (3, True) if proto["codigo"] == "reentrada" else (8, False)
        preg = seleccion_diagnostico(ctx, cantidad, faciles)
        if preg:
            titulo = "3 PREGUNTAS FÁCILES-MEDIAS" if faciles else "PRUEBA DE NIVEL (8 preguntas)"
            lineas += ["", f"{titulo} — sin mirar; el tutor muestra la respuesta después"]
            lineas += [f"  [{t}] {ctx.catalogo[t]['pregunta']}" for t in preg]
    if not r["terminado"]:
        p = r["proyeccion"]
        lineas += ["", f"Semana en curso: {r['semana_actual']} — {r['titulo']}",
                   f"Fechas reprogramadas desde hoy: etapa {p['etapa']} el {p['termino_etapa']} · programa el {p['termino_programa']}",
                   f"Modo sugerido hoy: {proto['modo']} → python3 herramientas/tutor.py hoy"]
    return "\n".join(lineas)


def texto_rubrica(ctx: Contexto, n: int) -> str:
    d = ctx.semana(n)
    lineas = [f"RÚBRICA · Semana {n}: {d.get('titulo', '')}",
              f"Escala por criterio: {ESCALA_RUBRICA}.",
              "Evalúa en un contexto aparte (subagente): solo rúbrica, evidencia y clave; sin el historial de la conversación.",
              "", f"Evidencia de dominio: {d.get('evidencia_de_dominio', '')}",
              f"Entregable: {d.get('entregable', '')}", "", "CRITERIOS"]
    for c in criterios_semana(n):
        lineas.append(f"  {c}: {CRITERIOS[c]}")
    lineas += ["", "CLAVE (preguntas de la semana; no se la muestres a Miguel antes de que responda)"]
    for tid in ids_tarjetas_semana(ctx, n):
        lineas.append(f"  [{tid}] {ctx.catalogo[tid]['pregunta']} → {ctx.catalogo[tid]['respuesta']}")
    ejemplo = ",".join(f"{c}=2" for c in criterios_semana(n))
    lineas += ["", f"Aprobar: python3 herramientas/tutor.py aprobar-semana {n} --evidencia \"...\" --rubrica \"{ejemplo}\""]
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def construir_parser() -> argparse.ArgumentParser:
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--hoy", default=argparse.SUPPRESS, help="fecha a usar como hoy (AAAA-MM-DD)")
    comun.add_argument("--raiz", default=argparse.SUPPRESS, help="carpeta del programa (por defecto, la del script)")
    comun.add_argument("--progreso", default=argparse.SUPPRESS, help="carpeta de progreso (por defecto, <raiz>/progreso)")
    p = argparse.ArgumentParser(prog="tutor.py", description="Tutor de IA Agéntica: herramientas determinísticas.")
    p.add_argument("--hoy", default=None, help="fecha a usar como hoy (AAAA-MM-DD); también TUTOR_HOY")
    p.add_argument("--raiz", default=None, help="carpeta del programa; también TUTOR_RAIZ")
    p.add_argument("--progreso", default=None, help="carpeta de progreso; también TUTOR_PROGRESO")
    p.add_argument("--version", action="version", version=f"tutor.py {VERSION}")
    sub = p.add_subparsers(dest="comando", metavar="comando")

    s = sub.add_parser("estado", parents=[comun], help="dónde vas, racha, próxima tarea y repasos vencidos")
    s.add_argument("--json", action="store_true", help="salida en JSON (para el LLM)")

    s = sub.add_parser("hoy", parents=[comun], help="arma el plan de la sesión de hoy")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--micro", dest="modo", action="store_const", const="micro", help="15 min")
    g.add_argument("--estandar", dest="modo", action="store_const", const="estandar", help="30 min")
    g.add_argument("--lab", dest="modo", action="store_const", const="lab", help="75 min de laboratorio")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("repaso", parents=[comun], help="tarjetas vencidas (solo preguntas)")
    s.add_argument("--limite", type=int, default=5)
    s.add_argument("--todas", action="store_true")
    s.add_argument("--json", action="store_true")

    s = sub.add_parser("respuesta", parents=[comun], help="muestra la respuesta de una tarjeta (después de intentar)")
    s.add_argument("id_tarjeta")

    s = sub.add_parser("calificar", parents=[comun], help="califica una tarjeta 0-5 (repetición espaciada)")
    s.add_argument("id_tarjeta")
    s.add_argument("calidad", type=int)

    s = sub.add_parser("registrar", parents=[comun], help="registra una sesión (una fila de bitácora)")
    s.add_argument("--minutos", type=int, required=True)
    s.add_argument("--nota", required=True, help="lo que aprendiste o hiciste (1 línea)")
    s.add_argument("--tipo", choices=TIPOS_SESION)
    s.add_argument("--objetivo", help="objetivo de la sesión (por defecto, el de la semana)")
    s.add_argument("--logrado", help="si, parcial o no")
    s.add_argument("--duda")
    s.add_argument("--si-entonces", dest="si_entonces", help="«Si es [día/hora] y [ancla], entonces abro el tutor y [acción]»")
    s.add_argument("--evidencia")
    s.add_argument("--leido", action="append", default=[], help="id de fuente leída (repetible)")
    s.add_argument("--semana", type=int)

    s = sub.add_parser("rubrica", parents=[comun], help="criterios, escala y clave para evaluar una semana")
    s.add_argument("semana", type=int, nargs="?")

    s = sub.add_parser("aprobar-semana", parents=[comun], help="aprueba la semana en curso SOLO con evidencia y rúbrica")
    s.add_argument("semana", type=int)
    s.add_argument("--evidencia", required=True)
    s.add_argument("--rubrica", required=True, help="entregable=3,explicacion=2,recuperacion=3[,sin_ia=2]")
    s.add_argument("--test-out", dest="test_out", action="store_true", help="convalidación: ya lo dominaba")

    sub.add_parser("retomar", parents=[comun], help="protocolo de retorno sin culpa")

    s = sub.add_parser("pausa", parents=[comun], help="declara una pausa (vacaciones): congela la racha")
    s.add_argument("--hasta", required=True)
    s.add_argument("--motivo", default="vacaciones")

    s = sub.add_parser("parking", parents=[comun], help="anota una idea para después (sin idea: las lista)")
    s.add_argument("idea", nargs="?")

    sub.add_parser("panel", parents=[comun], help="genera progreso/panel.html")

    s = sub.add_parser("validar", parents=[comun], help="recorre y confirma todo el programa")
    s.add_argument("--estricto", action="store_true", help="los avisos también fallan")

    s = sub.add_parser("iniciar", parents=[comun], help="crea progreso/ limpio en semana 1")
    s.add_argument("--forzar", action="store_true", help="borra el progreso existente")

    sub.add_parser("bloque", parents=[comun], help="imprime el bloque de estado para claude.ai")
    s = sub.add_parser("importar", parents=[comun], help="aplica un bloque de estado pegado desde claude.ai")
    s.add_argument("archivo", nargs="?", default="-", help="archivo con el bloque ('-' = entrada estándar)")

    s = sub.add_parser("integrar-lecturas", parents=[comun],
                       help="propone (y con --aplicar escribe) las lecturas por semana desde base/fuentes.json")
    s.add_argument("--aplicar", action="store_true")
    s.add_argument("--maximo", type=int, default=4)

    sub.add_parser("empaquetar-skill", parents=[comun], help="crea dist/tutor-ia-agentica.zip para claude.ai")

    s = sub.add_parser("simular", parents=[comun], help="simula a un estudiante recorriendo las 24 semanas")
    s.add_argument("--semilla", type=int, default=7)
    s.add_argument("--detalle", action="store_true")
    return p


def _imprimir(texto: str = "") -> None:
    print(texto)


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass
    parser = construir_parser()
    args = parser.parse_args(argv)
    if not args.comando:
        parser.print_help()
        return 0
    try:
        rutas = resolver_rutas(args.raiz, args.progreso)
        hoy = fecha_hoy(args.hoy)
        return _ejecutar(args, rutas, hoy)
    except ErrorTutor as e:
        print(f"✗ {e}", file=sys.stderr)
        return 2


def _ejecutar(args, rutas: Rutas, hoy: date) -> int:
    cmd = args.comando

    if cmd == "validar":
        inf = validar(rutas, hoy)
        _imprimir(f"VALIDAR · {hoy.isoformat()} · raíz: {rutas.raiz}")
        seccion = None
        for nivel, sec, msg in inf.items:
            if sec != seccion:
                _imprimir(f"\n{sec}")
                seccion = sec
            _imprimir(f"  [{nivel}] {msg}")
        fallo = bool(inf.errores) or (args.estricto and bool(inf.avisos))
        _imprimir(f"\nResultado: {len(inf.errores)} error(es), {len(inf.avisos)} aviso(s) → "
                  f"{'FALLA' if fallo else 'OK'}")
        return 1 if fallo else 0

    if cmd == "iniciar":
        if rutas.estado.exists() and not args.forzar:
            e = leer_json(rutas.estado)
            if e.get("sesiones") or e.get("aprobaciones"):
                raise ErrorTutor("Ya hay progreso registrado. Usa --forzar si de verdad quieres empezar de cero.")
        rutas.progreso.mkdir(parents=True, exist_ok=True)
        escribir_json(rutas.estado, estado_inicial(hoy))
        escribir_json(rutas.tarjetas, tarjetas_iniciales())
        rutas.bitacora.write_text(ENCABEZADO_BITACORA, encoding="utf-8")
        Contexto(rutas, hoy).guardar()
        _imprimir(f"Progreso iniciado en semana 1 ({hoy.isoformat()}). Siguiente: python3 herramientas/tutor.py hoy")
        return 0

    if cmd == "simular":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import simular  # noqa: E402
        return simular.main(["--semilla", str(args.semilla), "--origen", str(rutas.raiz)]
                            + (["--detalle"] if args.detalle else []))

    if cmd == "integrar-lecturas":
        malla = cargar_malla(rutas)
        lista = leer_lista_fuentes(rutas)
        if lista is None:
            raise ErrorTutor("base/fuentes.json aún no existe: no hay nada que integrar.")
        prop = proponer_lecturas(malla, lista, args.maximo)
        fuentes = indice_fuentes(lista)
        cambios = 0
        for s in malla["semanas"]:
            n = s["semana"]
            actuales = [i for i in s.get("lectura", []) if i in fuentes]
            nuevas = list(dict.fromkeys(actuales + prop.get(n, [])))[:max(args.maximo, len(actuales))]
            marca = "" if nuevas == s.get("lectura", []) else "  ← cambia"
            _imprimir(f"Semana {n:>2}: {', '.join(nuevas) or '(sin fuentes sugeridas)'}{marca}")
            if nuevas != s.get("lectura", []):
                cambios += 1
                if args.aplicar:
                    s["lectura"] = nuevas
        asignadas = {i for ids in prop.values() for i in ids}
        sin_semana = [f["id"] for f in lista if isinstance(f, dict) and f.get("id") not in asignadas]
        if sin_semana:
            _imprimir(f"\nFuentes que no quedan como lectura principal de ninguna semana ({len(sin_semana)}): "
                      f"{', '.join(sin_semana[:15])}{' …' if len(sin_semana) > 15 else ''}")
        if args.aplicar and cambios:
            escribir_json(rutas.malla, malla)
            _imprimir(f"\n{cambios} semana(s) actualizadas en curriculo/malla.json. Corre: python3 herramientas/tutor.py validar")
        elif cambios:
            _imprimir(f"\n{cambios} semana(s) cambiarían. Para escribirlas: python3 herramientas/tutor.py integrar-lecturas --aplicar")
        return 0

    if cmd == "empaquetar-skill":
        if not rutas.skill.exists():
            raise ErrorTutor(f"No existe {rutas.rel(rutas.skill)}")
        rutas.dist.mkdir(parents=True, exist_ok=True)
        destino = rutas.dist / f"{NOMBRE_SKILL}.zip"
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(rutas.skill, f"{NOMBRE_SKILL}/SKILL.md")
            z.write(rutas.malla, f"{NOMBRE_SKILL}/referencias/malla.json")
            if rutas.fuentes.exists():
                z.write(rutas.fuentes, f"{NOMBRE_SKILL}/referencias/fuentes.json")
            if rutas.fichas.is_dir():
                for f in sorted(rutas.fichas.glob("*.md")):
                    z.write(f, f"{NOMBRE_SKILL}/referencias/fichas/{f.name}")
            nombres = z.namelist()
        _imprimir(f"Listo: {rutas.rel(destino)} ({len(nombres)} archivos). Súbelo en claude.ai → Configuración → "
                  "Capacidades → Skills → Subir skill.")
        return 0

    ctx = Contexto(rutas, hoy)

    if cmd == "estado":
        _imprimir(json.dumps(resumen(ctx), ensure_ascii=False, indent=2) if args.json else texto_estado(ctx))
        return 0

    if cmd == "hoy":
        plan = plan_de_hoy(ctx, args.modo)
        _imprimir(json.dumps(plan, ensure_ascii=False, indent=2) if args.json else texto_plan(ctx, plan))
        return 0

    if cmd == "repaso":
        vencidas = tarjetas_vencidas(ctx.tarjetas, ctx.hoy)
        mostrar = vencidas if args.todas else vencidas[:max(1, args.limite)]
        if args.json:
            _imprimir(json.dumps([{"id": t, "pregunta": ctx.catalogo.get(t, {}).get("pregunta", "")} for t in mostrar],
                                 ensure_ascii=False, indent=2))
            return 0
        if not ctx.tarjetas["tarjetas"]:
            _imprimir("REPASO · aún no hay tarjetas activas. Se activan al aprobar cada semana "
                      "(y al registrar lecturas con --leido).")
            return 0
        if not vencidas:
            prox = min((t["proxima"] for t in ctx.tarjetas["tarjetas"].values()), default="-")
            _imprimir(f"REPASO · nada vencido hoy. Próxima tarjeta: {prox}.")
            return 0
        _imprimir(f"REPASO · {fecha_corta(ctx.hoy)} · {len(vencidas)} vencida(s) (mostrando {len(mostrar)})")
        for t in mostrar:
            c = ctx.catalogo.get(t, {})
            origen = f"Semana {c.get('semana')}" if c.get("origen") == "malla" else f"Ficha {c.get('ficha')}"
            _imprimir(f"  [{t}] ({origen}) {c.get('pregunta', '(tarjeta huérfana)')}")
        _imprimir("Responde cada una ANTES de ver la respuesta: python3 herramientas/tutor.py respuesta <id>")
        _imprimir("Luego califica: python3 herramientas/tutor.py calificar <id> <0-5>")
        _imprimir(f"Escala: {ESCALA_CALIDAD}")
        return 0

    if cmd == "respuesta":
        c = ctx.catalogo.get(args.id_tarjeta)
        if not c:
            raise ErrorTutor(f"No existe la tarjeta «{args.id_tarjeta}».")
        origen = (f"curriculo/malla.json, semana {c['semana']}" if c["origen"] == "malla"
                  else f"base/fichas/{c['ficha']}.md")
        _imprimir(f"[{args.id_tarjeta}] {c['pregunta']}\nRespuesta: {c['respuesta']}\nFuente: {origen}")
        return 0

    if cmd == "calificar":
        t = calificar_tarjeta(ctx, args.id_tarjeta, args.calidad)
        _imprimir(f"[{args.id_tarjeta}] calidad {args.calidad} → próxima revisión {t['proxima']} "
                  f"(en {t['intervalo']} día(s); caja «{caja(t)}»).")
        return 0

    if cmd == "registrar":
        res = registrar_sesion(ctx, args.minutos, args.nota, args.tipo, args.evidencia, args.leido, args.semana,
                               args.objetivo, args.logrado, args.duda, args.si_entonces)
        s = res["sesion"]
        w = racha_de(ctx)["semana_en_curso"]
        _imprimir(f"Registrado: {formato_minutos(s['minutos'])} ({s['tipo']}) · semana {s['semana']} · {s['fecha']}"
                  + (f" · recuperación {s['recuperacion']}" if s.get("recuperacion") else "") + ".")
        _imprimir(f"Esta semana: {w['sesiones']} sesión(es), {w['minutos']} min · {texto_falta_piso(w)}.")
        if not s.get("si_entonces"):
            _imprimir("Falta el si-entonces: «Si es [día/hora] y [ancla], entonces abro el tutor y [primera acción]» "
                      "(agrégalo con --si-entonces la próxima vez).")
        for a in res["avisos"]:
            _imprimir(f"Aviso: {a}")
        if res["tarjetas_nuevas"]:
            _imprimir(f"Tarjetas nuevas para repaso: {len(res['tarjetas_nuevas'])}.")
        _imprimir("Panel actualizado: progreso/panel.html")
        _imprimir(f"Commit sugerido: git add progreso && git commit -m "
                  f"\"tutor: semana {s['semana']}, sesión {s['fecha']} ({formato_minutos(s['minutos'])})\"")
        return 0

    if cmd == "rubrica":
        n = args.semana or min(ctx.semana_actual, TOTAL_SEMANAS)
        if not 1 <= n <= TOTAL_SEMANAS:
            raise ErrorTutor(f"La semana debe estar entre 1 y {TOTAL_SEMANAS}.")
        _imprimir(texto_rubrica(ctx, n))
        return 0

    if cmd == "aprobar-semana":
        res = aprobar_semana(ctx, args.semana, args.evidencia, args.rubrica, args.test_out)
        reg = res["registro"]
        rub = ", ".join(f"{c}={v}" for c, v in reg["rubrica"].items())
        _imprimir(f"Semana {reg['semana']} aprobada con evidencia ({reg['tipo_evidencia']}) y rúbrica ({rub})"
                  + (" como test-out" if args.test_out else "") + ".")
        if reg.get("proyecto"):
            _imprimir(f"Proyecto registrado: {reg['proyecto']}.")
        nivel = nivel_actual(ctx.malla, [a["semana"] for a in ctx.estado["aprobaciones"]])
        if reg["semana"] in FIN_DE_ETAPA and nivel:
            _imprimir(f"Etapa completa. Nivel: {nivel}.")
        _imprimir(f"Tarjetas nuevas para repaso: {len(res['tarjetas_nuevas'])} (primera revisión mañana).")
        if ctx.terminado:
            _imprimir("Programa completado: 24/24. Lo que sigue: pilotear el capstone y mantener los repasos.")
        else:
            _imprimir(f"Siguiente: semana {ctx.semana_actual} — {ctx.semana().get('titulo', '')}.")
        return 0

    if cmd == "retomar":
        dias = dias_fuera(ctx)
        declarada = pausa_reciente(ctx.estado, ctx.hoy) or en_pausa_declarada(ctx.estado, ctx.hoy)
        proto = protocolo_retomar(dias, ctx.hoy, declarada)
        registrar_retorno(ctx, dias, proto["codigo"])
        _imprimir(texto_retomar(ctx, proto))
        return 0

    if cmd == "pausa":
        p = declarar_pausa(ctx, parse_fecha(args.hasta, "--hasta"), args.motivo)
        _imprimir(f"Pausa declarada del {p['desde']} al {p['hasta']} ({p['motivo']}). La racha queda congelada. "
                  "Al volver: python3 herramientas/tutor.py retomar")
        return 0

    if cmd == "parking":
        if args.idea:
            agregar_parking(ctx, args.idea)
            _imprimir(f"Anotada en el parking ({len(ctx.estado['parking'])} idea(s)). Se retoma al cerrar el módulo.")
        else:
            ideas = ctx.estado.get("parking", [])
            _imprimir("PARKING DE IDEAS" if ideas else "PARKING vacío.")
            for i, p in enumerate(ideas, 1):
                _imprimir(f"  {i}. {p['idea']} ({p['fecha']}, semana {p.get('semana')})")
        return 0

    if cmd == "panel":
        ctx.rutas.progreso.mkdir(parents=True, exist_ok=True)
        ctx.rutas.panel.write_text(generar_panel(ctx), encoding="utf-8")
        _imprimir(f"Panel generado: {rutas.rel(rutas.panel)}")
        return 0

    if cmd == "bloque":
        _imprimir(bloque_estado(ctx))
        return 0

    if cmd == "importar":
        texto = sys.stdin.read() if args.archivo == "-" else Path(args.archivo).read_text(encoding="utf-8")
        res = importar_bloque(lambda f: Contexto(rutas, f), texto)
        if res["aplicados"]:
            Contexto(rutas, hoy).guardar()  # panel con la fecha real, no la del último evento
        for a in res["aplicados"]:
            _imprimir(f"  + {a}")
        for o in res["omitidos"]:
            _imprimir(f"  = {o}")
        for e in res["errores"]:
            _imprimir(f"  ✗ {e}")
        _imprimir(f"Importación: {len(res['aplicados'])} aplicados, {len(res['omitidos'])} omitidos, "
                  f"{len(res['errores'])} con error.")
        return 1 if res["errores"] else 0

    raise ErrorTutor(f"Comando desconocido: {cmd}")  # pragma: no cover


if __name__ == "__main__":
    sys.exit(main())
