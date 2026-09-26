#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tutor.py — Caja de herramientas determinística del Tutor de IA Agéntica.

El tutor es, a propósito, un ejemplo didáctico de agente:

  * CONTEXTO     → curriculo/malla.json (qué se estudia) y base/ (fuentes y fichas).
  * HERRAMIENTAS → este archivo: comandos que el LLM invoca en vez de «calcular de memoria».
  * MEMORIA      → progreso/estado.json, progreso/tarjetas.json y progreso/bitacora.md.
  * EVALUACIÓN   → aprobar-semana (solo con evidencia), repetición espaciada y `validar`.

Regla de diseño: lo determinístico (fechas, racha, repasos vencidos, qué toca hoy,
si una evidencia tiene la forma mínima) lo hace el código. El LLM explica, pregunta,
evalúa la calidad de lo que Miguel demuestra y da feedback.

Solo biblioteca estándar de Python 3 (>= 3.9).

Fechas inyectables para pruebas:  --hoy AAAA-MM-DD   o   TUTOR_HOY=AAAA-MM-DD
Raíz inyectable (simulación/tests): --raiz RUTA      o   TUTOR_RAIZ=RUTA

Uso rápido:
    python3 herramientas/tutor.py estado
    python3 herramientas/tutor.py hoy [--micro | --estandar | --lab]
    python3 herramientas/tutor.py repaso
    python3 herramientas/tutor.py calificar s01-p2 4
    python3 herramientas/tutor.py registrar --minutos 45 --nota "..."
    python3 herramientas/tutor.py aprobar-semana 1 --evidencia "..."
    python3 herramientas/tutor.py retomar
    python3 herramientas/tutor.py panel
    python3 herramientas/tutor.py validar
"""
from __future__ import annotations

import argparse
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

VERSION = "1.0.0"
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

MODOS = {"micro": 15, "estandar": 45, "lab": 90}
TIPOS_SESION = ("micro", "estandar", "lab", "repaso")
COMODINES_POR_SEMANA = 2

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
    def __init__(self, raiz: Path | str):
        self.raiz = Path(raiz).resolve()
        self.malla = self.raiz / "curriculo" / "malla.json"
        self.fuentes = self.raiz / "base" / "fuentes.json"
        self.fichas = self.raiz / "base" / "fichas"
        self.progreso = self.raiz / "progreso"
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


def resolver_raiz(valor: str | None) -> Rutas:
    return Rutas(valor or os.environ.get("TUTOR_RAIZ") or RAIZ_DEFECTO)


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


def formato_horas(m: float) -> str:
    h = m / 60
    return f"{h:.1f}".replace(".", ",").replace(",0", "") + " h"


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
        "version": 1,
        "estudiante": "Miguel Ángel",
        "creado": hoy.isoformat(),
        "semana_actual": 1,
        "aprobaciones": [],
        "rechazos": [],
        "sesiones": [],
        "retornos": [],
        "config": {"comodines_por_semana": COMODINES_POR_SEMANA, "minutos_por_modo": dict(MODOS)},
    }


def tarjetas_iniciales() -> dict:
    return {"version": 1, "algoritmo": "SM-2 simplificado (calidad 0-5)", "tarjetas": {}}


ENCABEZADO_BITACORA = (
    "# Bitácora de estudio — IA Agéntica\n\n"
    "Registro automático de `tutor.py` (una entrada por sesión, aprobación o retorno).\n"
    "Puedes agregar reflexiones a mano debajo de cualquier entrada.\n"
)


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
        self.tarjetas = leer_json(rutas.tarjetas) if rutas.tarjetas.exists() else tarjetas_iniciales()
        self.tarjetas.setdefault("tarjetas", {})

    # --- atajos ---
    @property
    def semana_actual(self) -> int:
        return int(self.estado.get("semana_actual", 1))

    @property
    def terminado(self) -> bool:
        return self.semana_actual >= SEMANA_FIN

    @property
    def comodines(self) -> int:
        return int(self.estado.get("config", {}).get("comodines_por_semana", COMODINES_POR_SEMANA))

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

    def anotar_bitacora(self, titulo: str, lineas: list[str]) -> None:
        self.rutas.progreso.mkdir(parents=True, exist_ok=True)
        if not self.rutas.bitacora.exists():
            self.rutas.bitacora.write_text(ENCABEZADO_BITACORA, encoding="utf-8")
        cuerpo = "\n".join(l for l in lineas if l)
        with open(self.rutas.bitacora, "a", encoding="utf-8") as f:
            f.write(f"\n## {titulo}\n{cuerpo}\n")


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
    intervalo = int(t.get("intervalo", 0))
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
    t["historial"] = list(t.get("historial", [])) + [{"fecha": hoy.isoformat(), "calidad": calidad}]
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


CAJAS = ("Nueva", "1 día", "3 días", "1 semana", "1 mes", "Dominada")


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
# Racha con comodín
# ---------------------------------------------------------------------------
def _semana_iso(d: date):
    iso = d.isocalendar()
    return (iso[0], iso[1])


def _cubrir_hueco(hueco: list, usados: dict, por_semana: int, dias_comodin: list) -> bool:
    necesidad = {}
    for d in hueco:
        k = _semana_iso(d)
        necesidad[k] = necesidad.get(k, 0) + 1
    if all(usados.get(k, 0) + n <= por_semana for k, n in necesidad.items()):
        for k, n in necesidad.items():
            usados[k] = usados.get(k, 0) + n
        dias_comodin.extend(hueco)
        return True
    return False


def calcular_racha(fechas, hoy: date, comodines_por_semana: int = COMODINES_POR_SEMANA) -> dict:
    """Racha = días de estudio seguidos, perdonando huecos con comodines.

    * Cada semana (lunes a domingo) trae `comodines_por_semana` comodines.
    * Un hueco (días sin estudio entre dos días estudiados) se cubre entero con
      comodines de la semana de cada día; si no alcanzan, la racha se corta.
    * Los días cubiertos por comodín no suman, pero tampoco cortan.
    * Hoy nunca corta la racha: el día sigue abierto.
    """
    dias = sorted({f for f in fechas if f <= hoy})
    res = {"actual": 0, "mejor": 0, "hoy_estudiado": hoy in set(dias), "dias_comodin": [],
           "comodines_usados_semana": 0, "comodines_disponibles": comodines_por_semana,
           "estado": "sin_iniciar"}
    if not dias:
        return res
    usados, dias_comodin = {}, []
    actual = mejor = 1
    for prev, cur in zip(dias, dias[1:]):
        hueco = [prev + timedelta(days=k) for k in range(1, (cur - prev).days)]
        if hueco and not _cubrir_hueco(hueco, usados, comodines_por_semana, dias_comodin):
            actual = 1
        else:
            actual += 1
        mejor = max(mejor, actual)
    ultimo = dias[-1]
    if ultimo < hoy:
        abierto = [ultimo + timedelta(days=k) for k in range(1, (hoy - ultimo).days)]
        if abierto and not _cubrir_hueco(abierto, usados, comodines_por_semana, dias_comodin):
            actual = 0
    usados_hoy = usados.get(_semana_iso(hoy), 0)
    res.update(actual=actual, mejor=mejor, dias_comodin=[d.isoformat() for d in dias_comodin],
               comodines_usados_semana=usados_hoy,
               comodines_disponibles=max(0, comodines_por_semana - usados_hoy),
               estado="activa" if actual > 0 else "cortada")
    return res


def fechas_estudio(estado: dict) -> list[date]:
    out = []
    for s in estado.get("sesiones", []):
        try:
            if int(s.get("minutos", 0)) > 0:
                out.append(date.fromisoformat(s["fecha"]))
        except (ValueError, KeyError, TypeError):
            continue
    return out


def racha_de(ctx: Contexto) -> dict:
    return calcular_racha(fechas_estudio(ctx.estado), ctx.hoy, ctx.comodines)


# ---------------------------------------------------------------------------
# Retomar sin culpa
# ---------------------------------------------------------------------------
def dias_sin_estudiar(estado: dict, hoy: date):
    fechas = [f for f in fechas_estudio(estado) if f <= hoy]
    if not fechas:
        return None
    return (hoy - max(fechas)).days


def protocolo_retomar(dias) -> dict:
    """Protocolo de retorno según días sin estudiar. Nunca castiga: re-engancha."""
    if dias is None:
        return {"codigo": "inicio", "titulo": "Primer día", "modo": "estandar",
                "mensaje": "Aún no hay sesiones registradas. Hoy empieza la semana 1: una sola cosa, bien hecha.",
                "pasos": ["Lee el objetivo de la semana 1 (tutor.py hoy).",
                          "Sesión estándar de 45 min o micro de 15 si hoy no da.",
                          "Cierra con registrar: así mañana el tutor sabe dónde quedaste."]}
    if dias <= 1:
        return {"codigo": "al_dia", "titulo": "Al día", "modo": "estandar",
                "mensaje": "No hay nada que retomar: sigue con el plan de hoy.",
                "pasos": ["tutor.py hoy y al lío."]}
    if dias <= 3:
        return {"codigo": "corto", "titulo": f"Retorno corto ({dias} días)", "modo": "estandar",
                "mensaje": f"{dias} días sin estudiar es normal en una semana de sucursal. Retomas donde quedaste.",
                "pasos": ["Lee tu última nota de bitácora (abajo) — 1 min.",
                          "Haz 3 repasos vencidos — 5 min.",
                          "Sigue con el paso que marca tutor.py hoy."]}
    if dias <= 7:
        return {"codigo": "medio", "titulo": f"Retorno medio ({dias} días)", "modo": "micro",
                "mensaje": f"Estuviste {dias} días fuera. No se recupera el tiempo: se recupera el hilo. Hoy, sesión micro.",
                "pasos": ["Lee tu última nota de bitácora — 1 min.",
                          "Di en voz alta el objetivo de tu semana sin mirarlo; después compáralo — 2 min.",
                          "Hasta 5 repasos vencidos — 5 min.",
                          "Versión micro de la semana (tutor.py hoy --micro) — 7 min.",
                          "No intentes «ponerte al día» con una maratón: mañana sigue el plan normal."]}
    if dias <= 14:
        return {"codigo": "largo", "titulo": f"Retorno largo ({dias} días)", "modo": "micro",
                "mensaje": (f"{dias} días fuera. Pasa: cierres de mes, turnos, vida. La racha se reinicia, "
                            "tu avance no: las semanas aprobadas siguen aprobadas."),
                "pasos": ["Diagnóstico de 3 preguntas de tu última semana (abajo), sin mirar — 5 min.",
                          "Si fallas 2 o más: hoy haces la versión micro de esa semana, no avanzas contenido nuevo.",
                          "Si aciertas 2 o más: versión micro de la semana en curso — 10 min.",
                          "Registra la sesión: la racha nueva empieza hoy.",
                          "Revisa la fecha estimada de término (abajo): el calendario se corre, no se comprime."]}
    return {"codigo": "reinicio", "titulo": f"Reinicio suave ({dias} días)", "modo": "micro",
            "mensaje": (f"{dias} días fuera. Volver es lo único que importa, y ya lo estás haciendo. "
                        "Nada de lo aprobado se pierde; hoy solo re-enganchas."),
            "pasos": ["Mira el panel (tutor.py panel) para ver dónde vas — 2 min.",
                      "Diagnóstico de 3 preguntas de tu última semana aprobada, sin mirar — 5 min.",
                      "Una victoria chica: la versión micro de la semana en curso — 8 min.",
                      "Acuerda con el tutor un ritmo mínimo realista (ej.: 3 micro + 1 lab por semana) por 2 semanas.",
                      "El calendario se reprograma solo: la fecha estimada de término está abajo."]}


# ---------------------------------------------------------------------------
# Evidencia de dominio (forma mínima; la calidad la juzga el tutor)
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
        tok = tok.strip("\"'«»()[]{},;:")
        tok = tok.rstrip(".")
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
    """Devuelve (ok, tipo, motivo). tipo ∈ {archivo, url, descripcion}.

    Reglas: sin evidencia no hay avance; «vi el contenido» no es evidencia;
    las semanas de proyecto exigen el artefacto (ruta existente o URL).
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


# ---------------------------------------------------------------------------
# Acciones que modifican la memoria
# ---------------------------------------------------------------------------
def inferir_tipo(minutos: int) -> str:
    if minutos <= 20:
        return "micro"
    if minutos <= 60:
        return "estandar"
    return "lab"


def registrar_sesion(ctx: Contexto, minutos: int, nota: str, tipo: str | None = None,
                     evidencia: str | None = None, leido=(), semana: int | None = None) -> dict:
    if not isinstance(minutos, int) or not 1 <= minutos <= 600:
        raise ErrorTutor("--minutos debe ser un entero entre 1 y 600.")
    nota = (nota or "").strip()
    if not nota:
        raise ErrorTutor("La nota es obligatoria: 1 línea de qué hiciste o aprendiste (es lo que te "
                         "permite retomar rápido la próxima vez).")
    tipo = tipo or inferir_tipo(minutos)
    if tipo not in TIPOS_SESION:
        raise ErrorTutor(f"--tipo debe ser uno de: {', '.join(TIPOS_SESION)}.")
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
    sesion = {"fecha": ctx.hoy.isoformat(), "minutos": minutos, "tipo": tipo, "semana": semana,
              "nota": nota}
    if evidencia:
        sesion["evidencia"] = evidencia.strip()
    if leido:
        sesion["leido"] = leido
    ctx.estado["sesiones"].append(sesion)
    nuevas = []
    for fid in leido:
        nuevas += activar_tarjetas(ctx, ids_tarjetas_ficha(ctx, fid), ctx.hoy)
    ctx.anotar_bitacora(
        f"{ctx.hoy.isoformat()} · Semana {semana} · {tipo} · {formato_minutos(minutos)}",
        [f"- Nota: {nota}",
         f"- Evidencia: {evidencia}" if evidencia else "",
         f"- Leído: {', '.join(leido)}" if leido else ""])
    ctx.guardar()
    return {"sesion": sesion, "avisos": avisos, "tarjetas_nuevas": nuevas}


def aprobar_semana(ctx: Contexto, n: int, evidencia: str) -> dict:
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

    def rechazar(motivo: str):
        ctx.estado["rechazos"].append({"semana": n, "fecha": ctx.hoy.isoformat(),
                                       "evidencia": (evidencia or "").strip(), "motivo": motivo})
        ctx.anotar_bitacora(f"{ctx.hoy.isoformat()} · Semana {n}: todavía no se aprueba",
                            [f"- Evidencia presentada: {(evidencia or '(vacía)').strip()}",
                             f"- Qué falta: {motivo}"])
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
    registro = {"semana": n, "fecha": ctx.hoy.isoformat(), "evidencia": evidencia.strip(),
                "tipo_evidencia": tipo}
    if es_proyecto:
        registro["proyecto"] = (datos.get("proyecto") or {}).get("nombre", PROYECTOS_MALLA.get(n))
    aprobs.append(registro)
    ctx.estado["semana_actual"] = n + 1
    nuevas = activar_tarjetas(ctx, ids_tarjetas_semana(ctx, n), ctx.hoy)
    for fid in datos.get("lectura") or []:
        nuevas += activar_tarjetas(ctx, ids_tarjetas_ficha(ctx, fid), ctx.hoy)
    ctx.anotar_bitacora(f"{ctx.hoy.isoformat()} · Semana {n} APROBADA",
                        [f"- Evidencia ({tipo}): {evidencia.strip()}",
                         f"- Proyecto: {registro['proyecto']}" if es_proyecto else "",
                         f"- Tarjetas nuevas para repaso: {len(nuevas)}"])
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


def registrar_retorno(ctx: Contexto, dias: int, codigo: str) -> bool:
    if dias is None or dias < 2:
        return False
    hoy = ctx.hoy.isoformat()
    if any(r.get("fecha") == hoy for r in ctx.estado["retornos"]):
        return False
    ctx.estado["retornos"].append({"fecha": hoy, "dias_fuera": dias, "protocolo": codigo})
    ctx.anotar_bitacora(f"{hoy} · Retorno después de {dias} días ({codigo})",
                        ["- Volviste. Eso es lo que cuenta."])
    ctx.guardar()
    return True


# ---------------------------------------------------------------------------
# Plan del día
# ---------------------------------------------------------------------------
PASOS = {
    "entender-1": {"modo": "estandar", "nombre": "Entender (1/2)"},
    "entender-2": {"modo": "estandar", "nombre": "Entender (2/2)"},
    "construir-1": {"modo": "lab", "nombre": "Construir (1/2)"},
    "construir-2": {"modo": "lab", "nombre": "Construir (2/2)"},
    "demostrar": {"modo": "estandar", "nombre": "Demostrar"},
    "micro": {"modo": "micro", "nombre": "Micro"},
    "mantener": {"modo": "micro", "nombre": "Mantener (programa completo)"},
}


def sesiones_de_semana(estado: dict, n: int) -> list:
    return [s for s in estado.get("sesiones", []) if s.get("semana") == n]


def elegir_paso(estado: dict, n: int, modo: str | None = None, dias_fuera=None):
    """Decide el paso de hoy. Devuelve (clave_paso, motivo)."""
    if n >= SEMANA_FIN:
        return "mantener", "programa completo"
    ses = sesiones_de_semana(estado, n)
    teoria = sum(1 for s in ses if s.get("tipo") == "estandar")
    lab = sum(1 for s in ses if s.get("tipo") == "lab")
    if modo == "micro":
        return "micro", "elegiste modo micro"
    if modo is None and dias_fuera is not None and dias_fuera >= 4:
        return "micro", f"vienes de {dias_fuera} días sin estudiar: hoy re-enganchas en modo micro"
    if modo == "lab":
        return ("construir-1" if lab == 0 else "construir-2"), f"{lab} lab(s) hechos esta semana"
    if modo == "estandar":
        clave = "entender-1" if teoria == 0 else "entender-2" if teoria == 1 else "demostrar"
        return clave, f"{teoria} sesión(es) estándar esta semana"
    if teoria == 0:
        return "entender-1", "semana nueva: primero entender"
    if teoria == 1:
        return "entender-2", "ya hiciste la primera sesión de teoría"
    if lab == 0:
        return "construir-1", "teoría lista: toca construir"
    if lab == 1:
        return "construir-2", "laboratorio a medias: cerrar el entregable"
    return "demostrar", "teoría y laboratorio hechos: toca demostrar para avanzar"


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
                    "acceso": f.get("acceso"), "leida": fid in leidas,
                    "ficha": ctx.rutas.rel(ctx.fichas[fid]["ruta"]) if fid in ctx.fichas else None})
    return out


def plan_de_hoy(ctx: Contexto, modo: str | None = None) -> dict:
    n = ctx.semana_actual
    dias = dias_sin_estudiar(ctx.estado, ctx.hoy)
    paso, motivo = elegir_paso(ctx.estado, n, modo, dias)
    vencidas = tarjetas_vencidas(ctx.tarjetas, ctx.hoy)
    plan = {"fecha": ctx.hoy.isoformat(), "semana": n, "paso": paso,
            "nombre_paso": PASOS[paso]["nombre"], "modo": PASOS[paso]["modo"],
            "minutos": MODOS[PASOS[paso]["modo"]], "motivo": motivo, "dias_sin_estudiar": dias,
            "repasos_vencidos": vencidas, "bloques": [], "lecturas": [], "terminado": ctx.terminado}
    if paso == "mantener":
        plan["bloques"] = [
            (5, f"Repaso: {len(vencidas)} tarjetas vencidas → tutor.py repaso"),
            (10, "Avanza el piloto de tu capstone: 1 tarea concreta del roadmap 30/60/90."),
        ]
        return plan
    datos = ctx.semana(n)
    plan.update(titulo=datos.get("titulo", ""), objetivo=datos.get("objetivo", ""),
                etapa=datos.get("etapa"), version_micro=datos.get("version_micro", ""),
                lecturas=lecturas_de(ctx, datos))
    k = min(len(vencidas), 3 if paso == "micro" else 5)
    recuperar = (f"Recuperar: {k} repaso(s) vencido(s) → tutor.py repaso (responde antes de ver la respuesta)"
                 if k else "Recuperar: di en voz alta qué recuerdas de tu última sesión (lee tu nota en la bitácora)")
    c1, c2 = _mitades(datos.get("conceptos") or [])
    ids_semana = ids_tarjetas_semana(ctx, n)
    cierre = (f"Cierre: tutor.py registrar --minutos {MODOS[PASOS[paso]['modo']]} "
              f"--tipo {PASOS[paso]['modo']} --nota \"...\"")
    lectura_txt = ("Lectura: " + "; ".join(f"{l['id']} — {l['titulo']}" for l in plan["lecturas"] if not l["leida"])
                   if any(not l["leida"] for l in plan["lecturas"]) else
                   "Idea clave: repasa los conceptos de abajo (la lectura de la semana ya está hecha o aún no se integra la base)")
    if paso == "entender-1":
        plan["bloques"] = [
            (5, recuperar),
            (10, lectura_txt),
            (20, "Tu intento primero: explica con tus palabras y un ejemplo de tu sucursal → " + " | ".join(c1)),
            (7, "Feedback del tutor: qué está bien, qué falta, 1 corrección concreta"),
            (3, cierre),
        ]
    elif paso == "entender-2":
        plan["bloques"] = [
            (5, recuperar),
            (15, "Tu intento primero: explica con un ejemplo de tu sucursal → " + " | ".join(c2 or c1)),
            (15, "Responde sin mirar las preguntas de la semana: " + ", ".join(ids_semana)
             + " (el tutor muestra cada respuesta con: tutor.py respuesta <id>)"),
            (7, "Feedback del tutor sobre tus respuestas"),
            (3, cierre),
        ]
    elif paso == "construir-1":
        plan["bloques"] = [
            (5, recuperar),
            (10, "Planifica: ¿cuál es la versión mínima del laboratorio que puedes dejar funcionando hoy?"),
            (60, "Construye: " + datos.get("laboratorio", "")),
            (10, "Revisión con el tutor: qué funciona, qué no y qué sigue"),
            (5, cierre),
        ]
    elif paso == "construir-2":
        plan["bloques"] = [
            (5, recuperar),
            (60, "Cierra el entregable: " + datos.get("entregable", "")),
            (15, "Autoevalúate contra la evidencia de dominio: " + datos.get("evidencia_de_dominio", "")),
            (10, cierre),
        ]
    elif paso == "demostrar":
        plan["bloques"] = [
            (5, recuperar),
            (25, "Demuestra: " + datos.get("evidencia_de_dominio", "")),
            (10, "El tutor evalúa con exigencia; si hay brechas, las cierras hoy o agendas un lab"),
            (5, f"Si pasa: tutor.py aprobar-semana {n} --evidencia \"<ruta, URL o qué demostraste>\""),
        ]
        rech = [r for r in ctx.estado.get("rechazos", []) if r.get("semana") == n]
        if rech:
            plan["ultimo_rechazo"] = rech[-1]["motivo"]
    elif paso == "micro":
        plan["bloques"] = [
            (5, recuperar),
            (9, "Versión micro: " + datos.get("version_micro", "")),
            (1, "Cierre: tutor.py registrar --minutos 15 --tipo micro --nota \"...\""),
        ]
    return plan


# ---------------------------------------------------------------------------
# Resumen de estado
# ---------------------------------------------------------------------------
def minutos_en_semana_calendario(estado: dict, hoy: date) -> int:
    lunes = hoy - timedelta(days=hoy.weekday())
    total = 0
    for s in estado.get("sesiones", []):
        try:
            f = date.fromisoformat(s["fecha"])
        except (ValueError, KeyError):
            continue
        if lunes <= f <= hoy:
            total += int(s.get("minutos", 0))
    return total


def inicio_semana_en_curso(ctx: Contexto):
    aprobs = ctx.estado.get("aprobaciones", [])
    if aprobs:
        return parse_fecha(aprobs[-1]["fecha"])
    fechas = fechas_estudio(ctx.estado)
    return min(fechas) if fechas else None


def resumen(ctx: Contexto) -> dict:
    n = ctx.semana_actual
    datos = ctx.semana(n)
    aprobadas = [a["semana"] for a in ctx.estado.get("aprobaciones", [])]
    racha = racha_de(ctx)
    dias = dias_sin_estudiar(ctx.estado, ctx.hoy)
    vencidas = tarjetas_vencidas(ctx.tarjetas, ctx.hoy)
    paso, motivo = elegir_paso(ctx.estado, n, None, dias)
    total_min = sum(int(s.get("minutos", 0)) for s in ctx.estado.get("sesiones", []))
    inicio = inicio_semana_en_curso(ctx)
    etapas = []
    for e in ctx.malla.get("etapas", []):
        ini, fin = e.get("semanas", [0, 0])
        rango = list(range(ini, fin + 1))
        etapas.append({"numero": e.get("numero"), "nombre": e.get("nombre"),
                       "aprobadas": sum(1 for s in rango if s in aprobadas), "total": len(rango)})
    restantes = TOTAL_SEMANAS - len(aprobadas)
    return {
        "fecha": ctx.hoy.isoformat(),
        "semana_actual": n,
        "terminado": ctx.terminado,
        "titulo": datos.get("titulo", "") if not ctx.terminado else "Programa completado",
        "etapa": datos.get("etapa") if not ctx.terminado else 6,
        "nombre_etapa": etapa_de(ctx.malla, datos.get("etapa")).get("nombre") if not ctx.terminado else "",
        "objetivo": datos.get("objetivo", "") if not ctx.terminado else "",
        "aprobadas": aprobadas,
        "porcentaje": round(100 * len(aprobadas) / TOTAL_SEMANAS),
        "etapas": etapas,
        "racha": racha,
        "dias_sin_estudiar": dias,
        "ultima_sesion": max(fechas_estudio(ctx.estado)).isoformat() if fechas_estudio(ctx.estado) else None,
        "repasos_vencidos": vencidas,
        "tarjetas_activas": len(ctx.tarjetas.get("tarjetas", {})),
        "paso_siguiente": PASOS[paso]["nombre"],
        "modo_siguiente": PASOS[paso]["modo"],
        "motivo_paso": motivo,
        "minutos_semana": minutos_en_semana_calendario(ctx.estado, ctx.hoy),
        "meta_minutos_semana": int(datos.get("horas", 8) * 60) if not ctx.terminado else 0,
        "minutos_totales": total_min,
        "dias_en_semana_actual": (ctx.hoy - inicio).days if inicio and not ctx.terminado else None,
        "fecha_estimada_termino": (ctx.hoy + timedelta(weeks=restantes)).isoformat() if restantes else None,
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
    ult = ctx.estado.get("sesiones", [])[-1:] or [{}]
    lineas = [
        INICIO_BLOQUE,
        f"fecha: {r['fecha']}",
        f"semana_actual: {r['semana_actual']}",
        f"titulo: {r['titulo']}",
        f"aprobadas: {', '.join(map(str, r['aprobadas'])) or '-'}",
        f"paso_siguiente: {r['paso_siguiente']}",
        f"racha: {r['racha']['actual']} (mejor {r['racha']['mejor']})",
        f"ultima_sesion: {r['ultima_sesion'] or '-'}",
        f"ultima_nota: {ult[0].get('nota', '-')}",
        f"repasos_vencidos: {', '.join(r['repasos_vencidos'][:10]) or '-'}",
        "# Eventos de esta conversación (una línea por evento; formato exacto):",
        "# sesion: AAAA-MM-DD | minutos | micro/estandar/lab | nota",
        "# calificacion: AAAA-MM-DD | id_tarjeta | 0-5",
        "# leido: AAAA-MM-DD | id_fuente",
        "# aprobada: AAAA-MM-DD | semana | evidencia",
        FIN_BLOQUE,
    ]
    return "\n".join(lineas)


def importar_bloque(ctx_factory, texto: str) -> dict:
    """Aplica los eventos de un bloque pegado desde claude.ai. `ctx_factory(fecha)` crea un Contexto."""
    eventos = []
    for num, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        m = re.match(r"^(sesion|calificacion|leido|aprobada)\s*:\s*(.+)$", s, re.I)
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
                    raise ErrorTutor(f"línea {num}: sesion necesita minutos | tipo | nota")
                minutos, tipo_s, nota = int(datos[0]), normalizar(datos[1]).strip(), " | ".join(datos[2:])
                if any(s.get("fecha") == fecha.isoformat() and s.get("minutos") == minutos and s.get("nota") == nota
                       for s in ctx.estado["sesiones"]):
                    resultado["omitidos"].append(f"línea {num}: sesión ya registrada")
                    continue
                registrar_sesion(ctx, minutos, nota, tipo_s)
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
            elif tipo == "aprobada":
                n, evidencia = int(datos[0]), " | ".join(datos[1:])
                if n < ctx.semana_actual:
                    resultado["omitidos"].append(f"línea {num}: semana {n} ya aprobada")
                    continue
                aprobar_semana(ctx, n, evidencia)
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
# Panel HTML (autocontenido)
# ---------------------------------------------------------------------------
CSS_PANEL = """
:root{color-scheme:light;
 --plano:#f9f9f7;--sup:#fcfcfb;--tarjeta:#ffffff;--tinta:#0b0b0b;--tinta2:#52514e;--tinta3:#6f6d67;
 --linea:#e1e0d9;--borde:rgba(11,11,11,.10);--acento:#2a78d6;--acento-suave:#e3eefc;
 --ok:#0ca30c;--ok-texto:#006300;--aviso:#fab219;--critico:#d03b3b;
 --h0:#eeede8;--h1:#b7d3f6;--h2:#6da7ec;--h3:#2a78d6;--h4:#184f95;--comodin:#a9a79e;}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
 --plano:#0d0d0d;--sup:#1a1a19;--tarjeta:#1f1f1e;--tinta:#ffffff;--tinta2:#c3c2b7;--tinta3:#a3a199;
 --linea:#2c2c2a;--borde:rgba(255,255,255,.10);--acento:#3987e5;--acento-suave:#17263a;
 --ok:#0ca30c;--ok-texto:#0ca30c;--aviso:#fab219;--critico:#e66767;
 --h0:#2c2c2a;--h1:#104281;--h2:#1c5cab;--h3:#3987e5;--h4:#86b6ef;--comodin:#6b6a64;}}
:root[data-theme="dark"]{color-scheme:dark;
 --plano:#0d0d0d;--sup:#1a1a19;--tarjeta:#1f1f1e;--tinta:#ffffff;--tinta2:#c3c2b7;--tinta3:#a3a199;
 --linea:#2c2c2a;--borde:rgba(255,255,255,.10);--acento:#3987e5;--acento-suave:#17263a;
 --ok:#0ca30c;--ok-texto:#0ca30c;--aviso:#fab219;--critico:#e66767;
 --h0:#2c2c2a;--h1:#104281;--h2:#1c5cab;--h3:#3987e5;--h4:#86b6ef;--comodin:#6b6a64;}
*{box-sizing:border-box}
body{margin:0;background:var(--plano);color:var(--tinta);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1080px;margin:0 auto;padding:20px 16px 48px}
header{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline;justify-content:space-between;margin-bottom:12px}
h1{font-size:20px;margin:0}
h2{font-size:15px;margin:0 0 12px;color:var(--tinta)}
.sub{color:var(--tinta2);font-size:13px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}
.kpis{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,160px),1fr));margin:12px 0}
.card{background:var(--tarjeta);border:1px solid var(--borde);border-radius:12px;padding:16px;min-width:0}
.kpi .lab{color:var(--tinta2);font-size:13px}
.kpi .val{font-size:28px;font-weight:650;line-height:1.2}
.kpi .det{color:var(--tinta3);font-size:12px}
.hero{display:grid;gap:4px}
.hero .num{font-size:48px;font-weight:650;line-height:1}
.hero .obj{margin-top:8px}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;background:var(--acento-suave);color:var(--tinta);font-size:12px;border:1px solid var(--borde)}
.plan li{margin:4px 0}
.etapa{margin:10px 0}
.etapa .cab{display:flex;justify-content:space-between;gap:8px;font-size:13px;color:var(--tinta2)}
.semanas{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.sem{position:relative;width:30px;height:30px;border-radius:6px;display:grid;place-items:center;font-size:12px;
 border:1px solid var(--linea);background:var(--sup);color:var(--tinta2);font-variant-numeric:tabular-nums}
.sem.ok{background:var(--acento);border-color:var(--acento);color:#fff}
.sem.curso{border:2px solid var(--acento);color:var(--tinta);font-weight:650}
.sem.proy::after{content:"";position:absolute;right:-3px;top:-3px;width:9px;height:9px;border-radius:50%;
 background:var(--aviso);box-shadow:0 0 0 2px var(--tarjeta)}
.leyenda{display:flex;flex-wrap:wrap;gap:12px;font-size:12px;color:var(--tinta2);margin-top:8px}
.leyenda span{display:inline-flex;align-items:center;gap:4px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block;border:1px solid var(--borde)}
.heat{display:grid;grid-template-columns:28px repeat(12,minmax(0,16px));gap:3px;align-items:center}
.heat .d{font-size:10px;color:var(--tinta3)}
.cel{width:100%;aspect-ratio:1;border-radius:3px;background:var(--h0)}
.cel.m1{background:var(--h1)}.cel.m2{background:var(--h2)}.cel.m3{background:var(--h3)}.cel.m4{background:var(--h4)}
.cel.com{background:repeating-linear-gradient(45deg,var(--comodin) 0 2px,transparent 2px 5px),var(--h0)}
.cel.hoy{outline:2px solid var(--tinta);outline-offset:1px}
.cel.fut{background:transparent}
.barras{display:flex;align-items:flex-end;gap:10px;height:140px;border-bottom:1px solid var(--linea);position:relative;margin-top:24px}
.barra{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;min-width:0}
.barra .b{width:min(24px,100%);background:var(--acento);border-radius:4px 4px 0 0;min-height:2px}
.barra .v{font-size:11px;color:var(--tinta2);margin-bottom:2px}
.ejes{display:flex;gap:10px;margin-top:4px}
.ejes span{flex:1;text-align:center;font-size:11px;color:var(--tinta3);min-width:0}
.meta{position:absolute;left:0;right:0;border-top:1px solid var(--tinta3)}
.meta span{position:absolute;right:0;top:-16px;font-size:11px;color:var(--tinta2);background:var(--tarjeta);padding:0 2px}
.hbar{display:grid;grid-template-columns:80px 1fr 32px;gap:8px;align-items:center;margin:6px 0;font-size:13px}
.hbar .t{height:12px;background:transparent;border-radius:0 4px 4px 0}
.hbar .f{height:12px;background:var(--acento);border-radius:0 4px 4px 0;min-width:2px}
.hbar .n{text-align:right;color:var(--tinta2);font-variant-numeric:tabular-nums}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--linea);vertical-align:top}
th{color:var(--tinta2);font-weight:600}
td.num{font-variant-numeric:tabular-nums}
.est{white-space:nowrap}
.est.ok{color:var(--ok-texto)}
.ev{color:var(--tinta2);word-break:break-word}
.bit{margin:0;padding-left:18px}.bit li{margin:6px 0}
details summary{cursor:pointer;color:var(--tinta2);font-size:13px}
.tabla-scroll{overflow-x:auto}
footer{margin-top:24px;color:var(--tinta3);font-size:12px}
@media (forced-colors:active){.sem.ok,.barra .b,.hbar .f{forced-color-adjust:none}}
"""


def _esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def _clase_minutos(m: int) -> str:
    if m <= 0:
        return ""
    if m <= 20:
        return "m1"
    if m <= 50:
        return "m2"
    if m <= 100:
        return "m3"
    return "m4"


def generar_panel(ctx: Contexto) -> str:
    r = resumen(ctx)
    hoy = ctx.hoy
    racha = r["racha"]
    aprob = {a["semana"]: a for a in ctx.estado.get("aprobaciones", [])}
    n = r["semana_actual"]
    datos = ctx.semana(n)
    plan = plan_de_hoy(ctx)

    # --- encabezado + KPIs ---
    horas_tot = r["minutos_totales"]
    partes = [f"""<header><h1>Tutor IA Agéntica · Panel de progreso</h1>
<div class="sub">Actualizado {_esc(fecha_corta(hoy))} · {_esc(ctx.estado.get('estudiante', ''))}</div></header>"""]
    if r["terminado"]:
        hero = """<div class="card hero"><div class="sub">Programa</div><div class="num">24/24</div>
<div>Programa completado. Mantén los repasos y pilotea tu capstone.</div></div>"""
    else:
        hero = f"""<div class="card hero"><div class="sub">Semana en curso · Etapa {_esc(r['etapa'])} — {_esc(r['nombre_etapa'])}</div>
<div class="num">Semana {n} <span class="sub">de {TOTAL_SEMANAS}</span></div>
<div><strong>{_esc(r['titulo'])}</strong></div>
<div class="obj"><span class="chip">Objetivo</span> {_esc(r['objetivo'])}</div>
<div class="obj"><span class="chip">Próximo paso</span> {_esc(r['paso_siguiente'])} · {_esc(formato_minutos(MODOS[r['modo_siguiente']]))} — {_esc(r['motivo_paso'])}</div>
<div class="obj sub">¿Solo 15 min? {_esc(datos.get('version_micro', ''))}</div></div>"""
    partes.append(hero)
    com_txt = " ".join("●" if i < racha["comodines_disponibles"] else "○" for i in range(ctx.comodines))
    kpis = [
        ("Semanas aprobadas", f"{len(r['aprobadas'])}/{TOTAL_SEMANAS}", f"{r['porcentaje']}% del programa"),
        ("Horas registradas", formato_horas(horas_tot), f"de ~{HORAS_TOTALES_MALLA} h de la malla"),
        ("Racha", f"{racha['actual']} días", f"mejor {racha['mejor']} · comodines esta semana {com_txt}"),
        ("Repasos vencidos", str(len(r["repasos_vencidos"])), f"{r['tarjetas_activas']} tarjetas activas"),
        ("Esta semana", formato_horas(r["minutos_semana"]),
         f"meta {formato_horas(r['meta_minutos_semana'])}" if r["meta_minutos_semana"] else "sin meta"),
    ]
    partes.append('<section class="kpis">' + "".join(
        f'<div class="card kpi"><div class="lab">{_esc(a)}</div><div class="val">{_esc(b)}</div>'
        f'<div class="det">{_esc(c)}</div></div>' for a, b, c in kpis) + "</section>")

    # --- avance por etapa ---
    filas = []
    for e in ctx.malla.get("etapas", []):
        ini, fin = e.get("semanas", [0, 0])
        chips = []
        for s in range(ini, fin + 1):
            clases = ["sem"]
            estado_s = "pendiente"
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
        filas.append(f'<div class="etapa"><div class="cab"><span>Etapa {e.get("numero")} · {_esc(e.get("nombre"))}</span>'
                     f'<span>{hechas}/{fin - ini + 1} · {e.get("horas")} h</span></div><div class="semanas">{"".join(chips)}</div></div>')
    leyenda_etapas = ('<div class="leyenda"><span><i class="sw" style="background:var(--acento)"></i>Aprobada</span>'
                      '<span><i class="sw" style="border:2px solid var(--acento)"></i>En curso</span>'
                      '<span><i class="sw"></i>Pendiente</span>'
                      '<span><i class="sw" style="background:var(--aviso);border-radius:50%"></i>Semana de proyecto</span></div>')
    bloque_etapas = f'<div class="card"><h2>Avance por etapa</h2>{"".join(filas)}{leyenda_etapas}</div>'

    # --- racha: mapa de calor de 12 semanas ---
    min_por_dia = {}
    for s in ctx.estado.get("sesiones", []):
        min_por_dia[s["fecha"]] = min_por_dia.get(s["fecha"], 0) + int(s.get("minutos", 0))
    comodines = set(racha["dias_comodin"])
    lunes_actual = hoy - timedelta(days=hoy.weekday())
    cols = 12
    inicio = lunes_actual - timedelta(weeks=cols - 1)
    celdas = []
    for fila in range(7):
        celdas.append(f'<span class="d">{DIAS[fila]}</span>')
        for c in range(cols):
            d = inicio + timedelta(weeks=c, days=fila)
            iso = d.isoformat()
            m = min_por_dia.get(iso, 0)
            clases = ["cel"]
            if d > hoy:
                clases.append("fut")
                txt = f"{fecha_corta(d)}: por venir"
            elif m:
                clases.append(_clase_minutos(m))
                txt = f"{fecha_corta(d)}: {formato_minutos(m)}"
            elif iso in comodines:
                clases.append("com")
                txt = f"{fecha_corta(d)}: comodín (la racha no se cortó)"
            else:
                txt = f"{fecha_corta(d)}: sin estudio"
            if d == hoy:
                clases.append("hoy")
                txt += " · hoy"
            celdas.append(f'<span class="{" ".join(clases)}" title="{_esc(txt)}"></span>')
    leyenda_heat = ('<div class="leyenda"><span>Menos</span><i class="sw" style="background:var(--h0)"></i>'
                    '<i class="sw" style="background:var(--h1)"></i><i class="sw" style="background:var(--h2)"></i>'
                    '<i class="sw" style="background:var(--h3)"></i><i class="sw" style="background:var(--h4)"></i><span>Más minutos</span>'
                    '<span><i class="sw" style="background:repeating-linear-gradient(45deg,var(--comodin) 0 2px,transparent 2px 5px),var(--h0)"></i>Comodín</span>'
                    '<span><i class="sw" style="outline:2px solid var(--tinta)"></i>Hoy</span></div>')
    estado_racha = ("Aún no empiezas: la racha parte con tu primera sesión." if racha["estado"] == "sin_iniciar" else
                    f"Racha de {racha['actual']} días de estudio (mejor: {racha['mejor']}). "
                    f"Cada semana trae {ctx.comodines} comodines para días sin estudio; hoy {'ya cuenta' if racha['hoy_estudiado'] else 'sigue abierto'}.")
    bloque_racha = (f'<div class="card"><h2>Racha y constancia (últimas 12 semanas)</h2><p class="sub">{_esc(estado_racha)}</p>'
                    f'<div class="heat">{"".join(celdas)}</div>{leyenda_heat}</div>')

    # --- horas por semana calendario (8 semanas) ---
    barras, ejes = [], []
    semanas_cal = [lunes_actual - timedelta(weeks=k) for k in range(7, -1, -1)]
    valores = []
    for lun in semanas_cal:
        tot = sum(m for iso, m in min_por_dia.items() if lun <= date.fromisoformat(iso) <= lun + timedelta(days=6))
        valores.append(tot)
    meta = r["meta_minutos_semana"] or 480
    tope = max(max(valores or [0]), meta, 60) * 1.1
    for i, (lun, v) in enumerate(zip(semanas_cal, valores)):
        alto = 100 * v / tope
        etiqueta = formato_horas(v) if (i == len(valores) - 1 or (v and v == max(valores))) else ""
        barras.append(f'<div class="barra" title="Semana del {fecha_corta(lun)}: {formato_horas(v)}">'
                      f'<span class="v">{_esc(etiqueta)}</span><span class="b" style="height:{alto:.1f}%"></span></div>')
        ejes.append(f"<span>{lun.day:02d}-{MESES[lun.month - 1]}</span>")
    linea_meta = (f'<div class="meta" style="bottom:{100 * meta / tope:.1f}%"><span>meta {formato_horas(meta)}</span></div>')
    bloque_horas = (f'<div class="card"><h2>Horas por semana (lunes a domingo)</h2>'
                    f'<div class="barras">{linea_meta}{"".join(barras)}</div><div class="ejes">{"".join(ejes)}</div></div>')

    # --- proyectos / entregables ---
    filas_p = []
    for sem, nombre in PROYECTOS_MALLA.items():
        if sem in aprob:
            est = '<span class="est ok">✓ Aprobado</span>'
            ev = aprob[sem]["evidencia"]
            ev_html = (f'<a href="{_esc(ev)}">{_esc(ev)}</a>' if RE_URL.fullmatch(ev.strip()) else _esc(ev))
        elif sem == n:
            est, ev_html = '<span class="est">● En curso</span>', ""
        else:
            est, ev_html = '<span class="est">○ Pendiente</span>', ""
        entreg = ctx.semanas.get(sem, {}).get("entregable", "")
        filas_p.append(f'<tr><td class="num">{sem}</td><td><strong>{_esc(nombre)}</strong><div class="sub">{_esc(entreg)}</div></td>'
                       f'<td>{est}</td><td class="ev">{ev_html}</td></tr>')
    bloque_proy = ('<div class="card"><h2>Proyectos y entregables</h2><div class="tabla-scroll"><table>'
                   '<thead><tr><th>Sem.</th><th>Proyecto</th><th>Estado</th><th>Evidencia</th></tr></thead>'
                   f'<tbody>{"".join(filas_p)}</tbody></table></div></div>')

    # --- repasos ---
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
    hbars = "".join(f'<div class="hbar" title="{_esc(c)}: {v} tarjetas"><span>{_esc(c)}</span><span class="t">'
                     f'<span class="f" style="display:block;width:{100 * v / maxc:.1f}%"></span></span><span class="n">{v}</span></div>'
                     for c, v in por_caja.items())
    bloque_rep = (f'<div class="card"><h2>Repasos (repetición espaciada)</h2>'
                  f'<p class="sub">Vencidos hoy: <strong>{len(r["repasos_vencidos"])}</strong> · próximos 7 días: {prox7} · '
                  f'activas: {r["tarjetas_activas"]}. Las tarjetas se activan al aprobar cada semana.</p>'
                  f'<div>{hbars}</div><p class="sub">Tarjetas por intervalo de repaso (de «Nueva» a «Dominada»).</p></div>')

    # --- bitácora ---
    ult = list(reversed(ctx.estado.get("sesiones", [])[-6:]))
    items = "".join(f'<li><strong>{_esc(s["fecha"])}</strong> · Sem. {_esc(s.get("semana"))} · {_esc(s.get("tipo"))} · '
                    f'{_esc(formato_minutos(s.get("minutos", 0)))}<div class="sub">{_esc(s.get("nota", ""))}</div></li>'
                    for s in ult) or '<li class="sub">Sin sesiones todavía. La primera es la más importante.</li>'
    bloque_bit = f'<div class="card"><h2>Últimas sesiones</h2><ul class="bit">{items}</ul></div>'

    # --- plan de hoy ---
    lis = "".join(f"<li><strong>{m} min</strong> · {_esc(t)}</li>" for m, t in plan["bloques"])
    bloque_plan = (f'<div class="card plan"><h2>Plan de la próxima sesión · {_esc(plan["nombre_paso"])} '
                   f'({_esc(formato_minutos(plan["minutos"]))})</h2><ol>{lis}</ol></div>')

    # --- vista de tabla (accesibilidad) ---
    filas_t = []
    for s in range(1, TOTAL_SEMANAS + 1):
        d = ctx.semanas.get(s, {})
        est = (f"Aprobada {aprob[s]['fecha']}" if s in aprob else "En curso" if s == n else "Pendiente")
        filas_t.append(f'<tr><td class="num">{s}</td><td class="num">{_esc(d.get("etapa"))}</td><td>{_esc(d.get("titulo"))}</td>'
                       f'<td class="num">{_esc(d.get("horas"))}</td><td>{_esc(est)}</td></tr>')
    bloque_tabla = ('<div class="card"><details><summary>Ver las 24 semanas en tabla</summary><div class="tabla-scroll"><table>'
                    '<thead><tr><th>Sem.</th><th>Etapa</th><th>Título</th><th>Horas</th><th>Estado</th></tr></thead>'
                    f'<tbody>{"".join(filas_t)}</tbody></table></div></details></div>')

    cuerpo = (
        "".join(partes)
        + f'<section class="grid">{bloque_plan}{bloque_etapas}</section>'
        + f'<section class="grid" style="margin-top:12px">{bloque_racha}{bloque_horas}</section>'
        + f'<section style="margin-top:12px">{bloque_proy}</section>'
        + f'<section class="grid" style="margin-top:12px">{bloque_rep}{bloque_bit}</section>'
        + f'<section style="margin-top:12px">{bloque_tabla}</section>'
        + f'<footer>Generado por <code>tutor.py panel</code> el {hoy.isoformat()} desde progreso/estado.json y '
          f'progreso/tarjetas.json. No edites este archivo a mano: se regenera en cada registro.</footer>'
    )
    return ("<!doctype html>\n<html lang=\"es\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
            "<title>Panel del tutor</title>\n"
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
    # etapas
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
    # semanas consecutivas
    lista = [s for s in malla.get("semanas", []) if isinstance(s, dict)]
    numeros = [s.get("semana") for s in lista]
    if numeros != list(range(1, TOTAL_SEMANAS + 1)):
        faltan = sorted(set(range(1, TOTAL_SEMANAS + 1)) - set(n for n in numeros if isinstance(n, int)))
        extra = [n for n in numeros if n not in range(1, TOTAL_SEMANAS + 1)]
        dup = sorted({n for n in numeros if numeros.count(n) > 1})
        inf.error(sec, f"las semanas deben ser 1..24 consecutivas y en orden (faltan {faltan}, "
                       f"sobran {extra}, duplicadas {dup})")
    else:
        inf.ok(sec, "24 semanas consecutivas (1..24) y 6 etapas con los rangos de la malla")
    # campos por semana
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
            inf.aviso(sec, f"semana {n}: {horas} h está fuera del rango típico de 8–10 h/semana")
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
    # horas
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
    # proyectos
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
    if prob:
        for p in prob:
            inf.error(sec, p)
    elif proy_top == PROYECTOS_MALLA:
        inf.ok(sec, "proyectos en las semanas 3, 6, 10, 14, 19 y 24")
    return malla


def _validar_fuentes_y_fichas(rutas: Rutas, malla, inf: Informe):
    sec = "Base de conocimiento"
    lecturas = {}
    if malla:
        for s in malla.get("semanas", []):
            if isinstance(s, dict) and isinstance(s.get("lectura"), list):
                for fid in s["lectura"]:
                    lecturas.setdefault(fid, []).append(s.get("semana"))
    vacias = [s.get("semana") for s in (malla or {}).get("semanas", []) if isinstance(s, dict) and not s.get("lectura")]
    try:
        lista = leer_lista_fuentes(rutas)
    except (json.JSONDecodeError, ErrorTutor) as e:
        inf.error(sec, f"base/fuentes.json no se puede leer: {e}")
        lista = None
        fuentes = None
    else:
        fuentes = indice_fuentes(lista) if lista is not None else None
    if lista is None and rutas.fuentes.exists() is False:
        inf.aviso(sec, "base/fuentes.json aún no existe (lo entrega el agente 2): no puedo verificar lecturas")
        if lecturas:
            inf.aviso(sec, f"{len(lecturas)} ids en «lectura» quedan sin verificar")
    elif fuentes is not None:
        ids = [f.get("id") for f in lista if isinstance(f, dict)]
        sin_id = sum(1 for f in lista if not isinstance(f, dict) or not isinstance(f.get("id"), str) or not f.get("id"))
        if sin_id:
            inf.error(sec, f"{sin_id} fuente(s) sin «id» de texto")
        dup = sorted({i for i in ids if ids.count(i) > 1 and i})
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
        no_asignadas = sum(1 for n, ids_p in prop.items() for i in ids_p if i not in lecturas)
        if no_asignadas:
            inf.aviso(sec, f"{no_asignadas} fuente(s) sugeridas para alguna semana aún no están en «lectura» "
                           "→ python3 herramientas/tutor.py integrar-lecturas --aplicar")
    if vacias:
        inf.aviso(sec, f"{len(vacias)} semana(s) con «lectura» vacía (pendiente integrar la base de conocimiento)")
    # fichas
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
        if not err and nombre == NOMBRE_SKILL and desc:
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
        errores.append(f"semana_actual inválida: {sa}")
        return errores
    aprobs = e.get("aprobaciones", [])
    semanas_aprob = [a.get("semana") for a in aprobs]
    if semanas_aprob != list(range(1, sa)):
        errores.append(f"aprobaciones {semanas_aprob} no calzan con semana_actual={sa} (deberían ser 1..{sa - 1})")
    fecha_prev = None
    for a in aprobs:
        if not str(a.get("evidencia", "")).strip():
            errores.append(f"semana {a.get('semana')} aprobada sin evidencia")
        try:
            f = date.fromisoformat(a.get("fecha", ""))
            if f > hoy:
                errores.append(f"semana {a.get('semana')} aprobada en fecha futura ({f})")
            if fecha_prev and f < fecha_prev:
                errores.append(f"aprobación de la semana {a.get('semana')} con fecha anterior a la previa")
            fecha_prev = f
        except (ValueError, TypeError):
            errores.append(f"semana {a.get('semana')}: fecha de aprobación inválida")
        if a.get("semana") in PROYECTOS_MALLA and a.get("tipo_evidencia") not in ("archivo", "url"):
            errores.append(f"semana de proyecto {a.get('semana')} aprobada sin artefacto (archivo o URL)")
    for i, s in enumerate(e.get("sesiones", []), 1):
        try:
            f = date.fromisoformat(s.get("fecha", ""))
            if f > hoy:
                errores.append(f"sesión {i}: fecha futura ({f})")
        except (ValueError, TypeError):
            errores.append(f"sesión {i}: fecha inválida")
        m = s.get("minutos")
        if not isinstance(m, int) or not 1 <= m <= 600:
            errores.append(f"sesión {i}: minutos inválidos ({m})")
        if s.get("tipo") not in TIPOS_SESION:
            errores.append(f"sesión {i}: tipo inválido ({s.get('tipo')})")
        sem = s.get("semana")
        if not isinstance(sem, int) or not 1 <= sem <= min(sa, TOTAL_SEMANAS):
            errores.append(f"sesión {i}: semana {sem} fuera de rango (semana en curso: {sa})")
        if not str(s.get("nota", "")).strip():
            errores.append(f"sesión {i}: sin nota")
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
        calcular_racha(fechas_estudio(e), hoy, ctx.comodines)
    except Exception as ex:  # pragma: no cover - defensivo
        errores.append(f"no se pudo calcular la racha: {ex}")
    return errores


def _validar_estado(rutas: Rutas, hoy: date, inf: Informe):
    sec = "Estado del estudiante"
    if not rutas.estado.exists():
        inf.aviso(sec, "progreso/estado.json no existe todavía (python3 herramientas/tutor.py iniciar)")
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
    out = [f"ESTADO · {fecha_corta(ctx.hoy)}"]
    if r["terminado"]:
        out.append("Programa completado: 24/24 semanas aprobadas.")
    else:
        out.append(f"Semana {r['semana_actual']}/{TOTAL_SEMANAS} · Etapa {r['etapa']} — {r['nombre_etapa']}")
        out.append(f"«{r['titulo']}»")
        out.append(f"Objetivo: {r['objetivo']}")
    barra = "█" * (len(r["aprobadas"])) + "░" * (TOTAL_SEMANAS - len(r["aprobadas"]))
    out.append(f"Avance: {len(r['aprobadas'])}/{TOTAL_SEMANAS} semanas ({r['porcentaje']}%) {barra}")
    out.append("Etapas: " + " · ".join(f"E{e['numero']} {e['aprobadas']}/{e['total']}" for e in r["etapas"]))
    if rc["estado"] == "sin_iniciar":
        out.append("Racha: aún sin sesiones (parte con la primera).")
    else:
        out.append(f"Racha: {rc['actual']} días (mejor {rc['mejor']}) · comodines disponibles esta semana: "
                   f"{rc['comodines_disponibles']}/{ctx.comodines} · hoy: {'cuenta' if rc['hoy_estudiado'] else 'pendiente'}")
    if r["meta_minutos_semana"]:
        out.append(f"Esta semana: {formato_minutos(r['minutos_semana'])} de {formato_horas(r['meta_minutos_semana'])} (meta de la malla)")
    if r["ultima_sesion"]:
        d = r["dias_sin_estudiar"]
        out.append(f"Última sesión: {r['ultima_sesion']} ({'hoy' if d == 0 else f'hace {d} día' + ('s' if d != 1 else '')})")
    out.append(f"Repasos vencidos: {len(r['repasos_vencidos'])} (de {r['tarjetas_activas']} tarjetas activas)")
    if not r["terminado"]:
        out.append(f"Próximo paso: {r['paso_siguiente']} ({formato_minutos(MODOS[r['modo_siguiente']])}) — {r['motivo_paso']}")
        out.append("  → python3 herramientas/tutor.py hoy")
        if r["dias_en_semana_actual"] and r["dias_en_semana_actual"] > 14:
            out.append(f"Llevas {r['dias_en_semana_actual']} días en esta semana: apunta a la evidencia mínima "
                       "con la versión micro; no hace falta perfección para demostrar.")
        out.append(f"Término estimado a ritmo de 1 semana por semana: {r['fecha_estimada_termino']}")
    if r["dias_sin_estudiar"] is not None and r["dias_sin_estudiar"] >= 2:
        out.append(f"Vienes de {r['dias_sin_estudiar']} días sin estudiar → python3 herramientas/tutor.py retomar")
    return "\n".join(out)


def texto_plan(ctx: Contexto, plan: dict) -> str:
    if plan["terminado"]:
        lineas = [f"HOY · {fecha_corta(ctx.hoy)} · Programa completado",
                  "Modo mantener (15 min):"]
        lineas += [f"  [{m:>2} min] {t}" for m, t in plan["bloques"]]
        return "\n".join(lineas)
    etapa = etapa_de(ctx.malla, plan.get("etapa"))
    lineas = [
        f"HOY · {fecha_corta(ctx.hoy)} · Semana {plan['semana']}/{TOTAL_SEMANAS} · Etapa {plan.get('etapa')} — {etapa.get('nombre', '')}",
        f"{plan.get('titulo', '')}",
        f"Paso: {plan['nombre_paso']} · modo {plan['modo']} · {formato_minutos(plan['minutos'])} ({plan['motivo']})",
    ]
    if plan["dias_sin_estudiar"] is not None and plan["dias_sin_estudiar"] >= 2:
        lineas.append(f"Ojo: {plan['dias_sin_estudiar']} días sin estudiar → primero: python3 herramientas/tutor.py retomar")
    lineas += ["", "OBJETIVO ÚNICO", f"  {plan.get('objetivo', '')}", "", "PLAN"]
    lineas += [f"  [{m:>2} min] {t}" for m, t in plan["bloques"]]
    if plan.get("ultimo_rechazo"):
        lineas += ["", "LO QUE FALTÓ LA ÚLTIMA VEZ", f"  {plan['ultimo_rechazo']}"]
    lineas += ["", "LECTURA"]
    if plan["lecturas"]:
        for l in plan["lecturas"]:
            detalle = ", ".join(x for x in (l.get("autor"), f"{l['minutos']} min" if l.get("minutos") else None,
                                            l.get("acceso")) if x)
            marca = "[leída] " if l["leida"] else ""
            lineas.append(f"  {marca}{l['id']} — {l['titulo']}" + (f" ({detalle})" if detalle else ""))
            if l.get("url"):
                lineas.append(f"      {l['url']}")
            if l.get("ficha"):
                lineas.append(f"      ficha: {l['ficha']}")
        lineas.append("  Al registrar, agrega --leido <ID> para activar sus preguntas de repaso.")
    else:
        lineas.append("  Pendiente de integrar base/fuentes.json. Hoy trabaja con los conceptos; "
                      "el tutor no inventa fuentes.")
    if plan["paso"] != "micro":
        lineas += ["", "SI SOLO TIENES 15 MIN", f"  {plan.get('version_micro', '')}"]
    return "\n".join(lineas)


def texto_retomar(ctx: Contexto, dias, proto: dict) -> str:
    r = resumen(ctx)
    lineas = [f"RETOMAR · {fecha_corta(ctx.hoy)} · {proto['titulo']}", proto["mensaje"], "", "PASOS"]
    lineas += [f"  {i}. {p}" for i, p in enumerate(proto["pasos"], 1)]
    ses = ctx.estado.get("sesiones", [])
    if ses:
        u = ses[-1]
        lineas += ["", "TU ÚLTIMA NOTA", f"  {u['fecha']} · semana {u.get('semana')}: {u.get('nota', '')}"]
    if proto["codigo"] in ("largo", "reinicio", "medio"):
        vencidas = tarjetas_vencidas(ctx.tarjetas, ctx.hoy)
        diag = vencidas[:3]
        if len(diag) < 3 and r["aprobadas"]:
            diag += [t for t in ids_tarjetas_semana(ctx, r["aprobadas"][-1]) if t not in diag][:3 - len(diag)]
        if diag:
            lineas += ["", "DIAGNÓSTICO (responde sin mirar; el tutor muestra la respuesta después)"]
            lineas += [f"  [{t}] {ctx.catalogo[t]['pregunta']}" for t in diag if t in ctx.catalogo]
    if not r["terminado"]:
        lineas += ["", f"Semana en curso: {r['semana_actual']} — {r['titulo']}",
                   f"Término estimado (reprogramado desde hoy): {r['fecha_estimada_termino']}",
                   f"Modo sugerido hoy: {proto['modo']} → python3 herramientas/tutor.py hoy --{proto['modo']}"]
    return "\n".join(lineas)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def construir_parser() -> argparse.ArgumentParser:
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--hoy", default=argparse.SUPPRESS, help="fecha a usar como hoy (AAAA-MM-DD)")
    comun.add_argument("--raiz", default=argparse.SUPPRESS, help="carpeta del programa (por defecto, la del script)")
    p = argparse.ArgumentParser(prog="tutor.py", description="Tutor de IA Agéntica: herramientas determinísticas.")
    p.add_argument("--hoy", default=None, help="fecha a usar como hoy (AAAA-MM-DD); también TUTOR_HOY")
    p.add_argument("--raiz", default=None, help="carpeta del programa; también TUTOR_RAIZ")
    p.add_argument("--version", action="version", version=f"tutor.py {VERSION}")
    sub = p.add_subparsers(dest="comando", metavar="comando")

    s = sub.add_parser("estado", parents=[comun], help="dónde vas, racha, próxima tarea y repasos vencidos")
    s.add_argument("--json", action="store_true", help="salida en JSON (para el LLM)")

    s = sub.add_parser("hoy", parents=[comun], help="arma el plan de la sesión de hoy")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--micro", dest="modo", action="store_const", const="micro", help="15 min")
    g.add_argument("--estandar", dest="modo", action="store_const", const="estandar", help="45 min de teoría activa")
    g.add_argument("--lab", dest="modo", action="store_const", const="lab", help="90 min de laboratorio")
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

    s = sub.add_parser("registrar", parents=[comun], help="registra una sesión de estudio")
    s.add_argument("--minutos", type=int, required=True)
    s.add_argument("--nota", required=True)
    s.add_argument("--tipo", choices=TIPOS_SESION)
    s.add_argument("--evidencia")
    s.add_argument("--leido", action="append", default=[], help="id de fuente leída (repetible)")
    s.add_argument("--semana", type=int)

    s = sub.add_parser("aprobar-semana", parents=[comun], help="aprueba la semana en curso SOLO con evidencia")
    s.add_argument("semana", type=int)
    s.add_argument("--evidencia", required=True)

    sub.add_parser("retomar", parents=[comun], help="protocolo de retorno sin culpa")
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
        rutas = resolver_raiz(args.raiz)
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
        ctx = Contexto(rutas, hoy)
        ctx.guardar()
        _imprimir(f"Progreso iniciado en semana 1 ({hoy.isoformat()}). Siguiente: python3 herramientas/tutor.py hoy")
        return 0

    if cmd == "simular":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import simular  # noqa: E402
        return simular.main(["--semilla", str(args.semilla)] + (["--detalle"] if args.detalle else []))

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
            _imprimir(f"\nFuentes sin semana asignada ({len(sin_semana)}): {', '.join(sin_semana[:15])}")
        if args.aplicar and cambios:
            escribir_json(rutas.malla, malla)
            _imprimir(f"\n{cambios} semana(s) actualizadas en curriculo/malla.json. Corre: tutor.py validar")
        elif cambios:
            _imprimir(f"\n{cambios} semana(s) cambiarían. Para escribirlas: tutor.py integrar-lecturas --aplicar")
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
        if args.json:
            _imprimir(json.dumps(resumen(ctx), ensure_ascii=False, indent=2))
        else:
            _imprimir(texto_estado(ctx))
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
        _imprimir(f"[{args.id_tarjeta}] {c['pregunta']}\nRespuesta: {c['respuesta']}")
        origen = (f"curriculo/malla.json, semana {c['semana']}" if c["origen"] == "malla"
                  else f"base/fichas/{c['ficha']}.md")
        _imprimir(f"Fuente: {origen}")
        return 0

    if cmd == "calificar":
        t = calificar_tarjeta(ctx, args.id_tarjeta, args.calidad)
        _imprimir(f"[{args.id_tarjeta}] calidad {args.calidad} → próxima revisión {t['proxima']} "
                  f"(en {t['intervalo']} día(s); caja «{caja(t)}»).")
        return 0

    if cmd == "registrar":
        res = registrar_sesion(ctx, args.minutos, args.nota, args.tipo, args.evidencia, args.leido, args.semana)
        s = res["sesion"]
        r = resumen(ctx)
        _imprimir(f"Registrado: {formato_minutos(s['minutos'])} ({s['tipo']}) · semana {s['semana']} · {s['fecha']}.")
        if r["meta_minutos_semana"]:
            _imprimir(f"Esta semana: {formato_minutos(r['minutos_semana'])} de {formato_horas(r['meta_minutos_semana'])}. "
                      f"Racha: {r['racha']['actual']} días (mejor {r['racha']['mejor']}).")
        for a in res["avisos"]:
            _imprimir(f"Aviso: {a}")
        if res["tarjetas_nuevas"]:
            _imprimir(f"Tarjetas nuevas para repaso: {len(res['tarjetas_nuevas'])}.")
        _imprimir("Siguiente: python3 herramientas/tutor.py hoy (la próxima vez) · Panel actualizado: progreso/panel.html")
        _imprimir(f"Commit sugerido: git add aprendizaje-ia-agentica/progreso && git commit -m "
                  f"\"tutor: semana {s['semana']}, sesión {s['fecha']} ({formato_minutos(s['minutos'])})\"")
        return 0

    if cmd == "aprobar-semana":
        res = aprobar_semana(ctx, args.semana, args.evidencia)
        reg = res["registro"]
        _imprimir(f"Semana {reg['semana']} aprobada con evidencia ({reg['tipo_evidencia']}).")
        if reg.get("proyecto"):
            _imprimir(f"Proyecto registrado: {reg['proyecto']}.")
        _imprimir(f"Tarjetas nuevas para repaso: {len(res['tarjetas_nuevas'])} (primera revisión mañana).")
        if ctx.terminado:
            _imprimir("Programa completado: 24/24. Lo que sigue: pilotear el capstone y mantener los repasos.")
        else:
            sig = ctx.semana()
            _imprimir(f"Siguiente: semana {ctx.semana_actual} — {sig.get('titulo', '')}.")
        return 0

    if cmd == "retomar":
        dias = dias_sin_estudiar(ctx.estado, ctx.hoy)
        proto = protocolo_retomar(dias)
        registrar_retorno(ctx, dias, proto["codigo"])
        _imprimir(texto_retomar(ctx, dias, proto))
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
