#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simular.py — Simula a un estudiante recorriendo las 24 semanas del programa.

Copia el programa a un directorio temporal (nunca toca tu progreso real), inicia un
progreso limpio y recorre el calendario día a día con fechas inyectadas, usando la
CLI real de tutor.py. Incluye a propósito lo que pasa en la vida real:

  * días perdidos al azar (semilla fija, reproducible),
  * una pausa de 10 días sin estudiar (retorno largo), una de 4 (medio) y una de 2 (corto),
  * intentos de aprobar sin evidencia, con «vi el contenido», proyectos sin artefacto,
    semanas fuera de orden y evidencia vaga (todos deben ser rechazados),
  * una semana que se alarga porque la demostración no alcanzó,
  * repasos con calificaciones variadas (repetición espaciada),
  * una sesión hecha en claude.ai que se importa con el bloque de estado.

Después de cada día verifica la consistencia de la memoria y, al final, que el
estudiante llegó a la semana 25 (programa completo) de forma coherente y que
`tutor.py validar` pasa sobre la copia simulada.

Uso:  python3 herramientas/simular.py [--semilla 7] [--detalle] [--conservar]
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import random
import shutil
import sys
import tempfile
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import tutor  # noqa: E402

INICIO = date(2026, 10, 5)  # un lunes

# Reparto de las horas de cada semana del curso en una semana calendario.
# (día desde el lunes, tipo, fracción de las horas de la semana)
PATRON = [
    (0, "estandar", 0.12),
    (1, "estandar", 0.12),
    (2, "micro", 0.03),
    (3, "lab", 0.30),
    (5, "lab", 0.30),
    (6, "estandar", 0.13),  # domingo: demostrar y aprobar
]
PROB_DIA_PERDIDO = 0.12


def siguiente_lunes(d: date) -> date:
    return d + timedelta(days=(7 - d.weekday()) % 7 or 7)


class Simulador:
    def __init__(self, raiz: Path, semilla: int, detalle: bool):
        self.raiz = raiz
        self.rutas = tutor.Rutas(raiz)
        self.rng = random.Random(semilla)
        self.detalle = detalle
        self.hoy = INICIO
        self.fallas: list[str] = []
        self.stats = Counter()
        self.retornos_vistos: list[str] = []

    # ------------------------------------------------------------ utilidades
    def cli(self, *args, esperar=0):
        argv = [str(a) for a in args] + ["--raiz", str(self.raiz), "--hoy", self.hoy.isoformat()]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                codigo = tutor.main(argv)
            except SystemExit as e:  # argparse
                codigo = e.code if isinstance(e.code, int) else 2
        self.stats["comandos"] += 1
        if esperar is not None and codigo != esperar:
            self.falla(f"`tutor.py {' '.join(map(str, args))}` devolvió {codigo} (esperaba {esperar}): "
                       f"{(err.getvalue() or out.getvalue()).strip()[:300]}")
        if self.detalle:
            print(f"  $ {self.hoy} tutor.py {' '.join(map(str, args))} → {codigo}")
        return codigo, out.getvalue(), err.getvalue()

    def falla(self, msg: str) -> None:
        self.fallas.append(f"{self.hoy}: {msg}")

    def comprobar(self, condicion: bool, msg: str) -> None:
        self.stats["comprobaciones"] += 1
        if not condicion:
            self.falla(msg)

    def ctx(self) -> tutor.Contexto:
        return tutor.Contexto(self.rutas, self.hoy)

    def verificar_memoria(self) -> None:
        errores = tutor.verificar_estado(self.ctx())
        self.stats["chequeos_diarios"] += 1
        for e in errores:
            self.falla(f"memoria inconsistente: {e}")

    def calidad(self) -> int:
        return self.rng.choices([5, 4, 3, 2, 1, 0], weights=[30, 35, 20, 9, 4, 2])[0]

    def semana_actual(self) -> int:
        return self.ctx().semana_actual

    # ------------------------------------------------------------ acciones
    def repasar(self, maximo: int) -> None:
        _, out, _ = self.cli("repaso", "--json", "--limite", maximo)
        for item in json.loads(out or "[]"):
            self.cli("respuesta", item["id"])
            antes = self.ctx().tarjetas["tarjetas"][item["id"]]
            q = self.calidad()
            self.cli("calificar", item["id"], q)
            despues = self.ctx().tarjetas["tarjetas"][item["id"]]
            self.comprobar(date.fromisoformat(despues["proxima"]) > self.hoy,
                           f"la tarjeta {item['id']} quedó vencida después de calificarla")
            if q < 3:
                self.comprobar(despues["intervalo"] == 1 and despues["repeticiones"] == 0,
                               f"calidad {q} debería reiniciar la tarjeta {item['id']}")
            else:
                self.comprobar(despues["intervalo"] >= antes.get("intervalo", 0),
                               f"calidad {q} no debería acortar el intervalo de {item['id']}")
            self.stats["repasos"] += 1

    def dia_de_estudio(self, tipo: str, minutos: int, nota: str, verificar_paso: str | None = None) -> None:
        dias = tutor.dias_sin_estudiar(self.ctx().estado, self.hoy)
        self.cli("estado")
        if dias is not None and dias >= 2:
            _, out, _ = self.cli("retomar")
            proto = tutor.protocolo_retomar(dias)
            self.comprobar(proto["titulo"] in out, f"retomar no mostró «{proto['titulo']}»")
            self.retornos_vistos.append(proto["codigo"])
        if verificar_paso:
            _, out, _ = self.cli("hoy")
            self.comprobar(f"Paso: {verificar_paso}" in out,
                           f"hoy (sin modo) debía proponer «{verificar_paso}»; dijo: "
                           f"{next((l for l in out.splitlines() if l.startswith('Paso:')), '?')}")
        self.repasar(3 if tipo == "micro" else 5)
        n = self.semana_actual()
        _, out, _ = self.cli("hoy", f"--{tipo}")
        datos = self.ctx().semana(n)
        self.comprobar(f"Semana {n}/24" in out and datos.get("objetivo", "")[:40] in out,
                       f"el plan de hoy no muestra la semana {n} y su objetivo")
        self.cli("registrar", "--minutos", minutos, "--tipo", tipo, "--nota", nota)
        self.stats["sesiones"] += 1
        self.stats["minutos"] += minutos

    def intentar_aprobar(self, n: int, evidencia: str, debe_pasar: bool, porque: str) -> None:
        antes = self.semana_actual()
        codigo, _, err = self.cli("aprobar-semana", n, "--evidencia", evidencia, esperar=0 if debe_pasar else 2)
        despues = self.semana_actual()
        if debe_pasar:
            self.comprobar(despues == antes + 1, f"la semana {n} debía aprobarse ({porque})")
        else:
            self.stats["rechazos"] += 1
            self.comprobar(despues == antes, f"la semana {n} NO debía avanzar ({porque})")
            self.comprobar(bool(err.strip()), f"el rechazo de la semana {n} debía explicar el motivo")

    def crear_artefacto(self, n: int, nombre: str) -> str:
        rel = f"entregables/semana-{n:02d}-{tutor.normalizar(nombre).replace(' ', '-')}.md"
        ruta = self.raiz / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(f"# {nombre}\n\nEntregable simulado de la semana {n}.\n", encoding="utf-8")
        return rel

    def evidencia_valida(self, n: int) -> str:
        if n in tutor.PROYECTOS_MALLA:
            return self.crear_artefacto(n, tutor.PROYECTOS_MALLA[n])
        if n % 5 == 0:
            return f"https://github.com/ejemplo/ia-agentica/tree/main/semana-{n:02d}"
        return (f"Expliqué sin apuntes el objetivo de la semana {n} con un caso de leads de la sucursal "
                f"y respondí 3 de 3 preguntas de repaso; el tutor revisó mi entregable.")

    def avanzar(self, dias: int = 1) -> None:
        for _ in range(dias):
            self.verificar_memoria()
            self.hoy += timedelta(days=1)

    # ------------------------------------------------------------ escenario
    def semana_calendario(self, n: int, horas: float) -> None:
        """Una semana calendario (lunes a domingo) dedicada a la semana n del curso."""
        lunes = self.hoy
        forzados = set()
        if n == 2:
            forzados = {1, 2}  # martes y miércoles perdidos: los cubren los comodines
        for dia, tipo, frac in PATRON:
            self.hoy = lunes + timedelta(days=dia)
            minutos = max(15, int(round(horas * 60 * frac)))
            es_cierre = dia == 6
            if not es_cierre and (dia in forzados or (dia > 0 and self.rng.random() < PROB_DIA_PERDIDO)):
                self.stats["dias_perdidos"] += 1
                continue
            paso = "Entender (1/2)" if dia == 0 and (tutor.dias_sin_estudiar(self.ctx().estado, self.hoy) or 0) < 4 else None
            self.dia_de_estudio(tipo, minutos, f"Semana {n}: sesión {tipo} del día {dia + 1}", paso)
            if es_cierre:
                self.cierre_de_semana(n)
            self.verificar_memoria()
        self.hoy = siguiente_lunes(self.hoy)

    def cierre_de_semana(self, n: int) -> None:
        if n == 3:
            self.intentar_aprobar(n, "entregables/mapa-que-no-existe.html", False, "proyecto con ruta inexistente")
        if n == 4:
            self.intentar_aprobar(n, "vi el contenido", False, "«vi el contenido» no es evidencia")
            self.intentar_aprobar(n, "", False, "evidencia vacía")
        if n == 6:
            self.intentar_aprobar(n, "Construí el agente y expliqué sus razones al tutor con 5 leads nuevos, "
                                     "todo funcionó bien.", False, "semana de proyecto sin artefacto")
        if n == 7:
            self.intentar_aprobar(9, "Expliqué MCP y construí el servidor completo con dos herramientas.", False,
                                  "semana fuera de orden")
        if n == 8:
            self.intentar_aprobar(n, "ok listo", False, "evidencia vaga")
            # La demostración no alcanzó: una semana calendario extra de laboratorio y se vuelve a intentar.
            base = self.hoy
            for d, tipo, minutos in ((1, "lab", 90), (3, "lab", 90), (5, "estandar", 45)):
                self.hoy = base + timedelta(days=d)
                self.dia_de_estudio(tipo, minutos, f"Semana {n}: cerrar brechas de la demostración",
                                    verificar_paso="Demostrar" if d == 5 else None)
            self.comprobar("LO QUE FALTÓ" in self.cli("hoy")[1], "hoy debía recordar lo que faltó en la demostración")
            self.stats["semanas_extendidas"] += 1
        self.intentar_aprobar(n, self.evidencia_valida(n), True, "evidencia válida")

    def sesion_claude_ai(self) -> None:
        """Una sesión hecha en claude.ai (sin archivos) que se sincroniza con importar."""
        _, bloque, _ = self.cli("bloque")
        self.comprobar(bloque.startswith(tutor.INICIO_BLOQUE) and tutor.FIN_BLOQUE in bloque,
                       "el bloque de estado no tiene el formato esperado")
        vencidas = tutor.tarjetas_vencidas(self.ctx().tarjetas, self.hoy)
        eventos = [f"sesion: {self.hoy} | 20 | micro | repaso en el celular (claude.ai)"]
        if vencidas:
            eventos.append(f"calificacion: {self.hoy} | {vencidas[0]} | 4")
        texto = bloque.replace(tutor.FIN_BLOQUE, "\n".join(eventos) + "\n" + tutor.FIN_BLOQUE)
        archivo = self.raiz / "bloque-importado.txt"
        archivo.write_text(texto, encoding="utf-8")
        antes = len(self.ctx().estado["sesiones"])
        self.cli("importar", archivo)
        self.comprobar(len(self.ctx().estado["sesiones"]) == antes + 1, "importar no agregó la sesión de claude.ai")
        self.cli("importar", archivo)  # idempotente: la segunda vez no duplica
        self.comprobar(len(self.ctx().estado["sesiones"]) == antes + 1, "importar dos veces duplicó la sesión")
        self.stats["sesiones"] += 1
        self.stats["minutos"] += 20
        self.stats["importaciones"] += 1

    def pausa(self, dias_sin_estudio: int) -> None:
        """Deja pasar días sin estudiar: el próximo estudio ocurre con `dias_sin_estudio` días fuera."""
        ultima = max(tutor.fechas_estudio(self.ctx().estado))
        self.hoy = ultima + timedelta(days=dias_sin_estudio)
        racha = tutor.calcular_racha(tutor.fechas_estudio(self.ctx().estado), self.hoy)
        self.stats[f"pausa_{dias_sin_estudio}"] += 1
        return racha

    def correr(self) -> int:
        self.cli("iniciar")
        self.comprobar("Aún no hay sesiones" in self.cli("retomar")[1], "retomar sin sesiones debía dar el protocolo de inicio")
        malla = self.ctx().malla
        for s in malla["semanas"]:
            n = s["semana"]
            if n == 13:
                # Pausa de 10 días después de aprobar la semana 12.
                mejor_antes = tutor.racha_de(self.ctx())["mejor"]
                racha = self.pausa(10)
                self.comprobar(racha["actual"] == 0, "después de 10 días sin estudiar la racha debía cortarse")
                self.comprobar(racha["mejor"] == mejor_antes, "la mejor racha no debe perderse con una pausa")
                self.comprobar("retomar" in self.cli("estado")[1], "estado debía sugerir retomar tras 10 días")
                self.dia_de_estudio("micro", 15, "Retomo después de 10 días: diagnóstico y versión micro")
                self.comprobar(self.retornos_vistos[-1] == "largo", "10 días fuera debía activar el retorno largo")
                self.comprobar(tutor.racha_de(self.ctx())["actual"] == 1, "la racha nueva debía partir en 1")
                self.hoy = siguiente_lunes(self.hoy)
            if n == 16:
                self.pausa(4)
                self.dia_de_estudio("micro", 15, "Retomo después de 4 días", verificar_paso="Micro")
                self.comprobar(self.retornos_vistos[-1] == "medio", "4 días fuera debía activar el retorno medio")
                self.hoy = siguiente_lunes(self.hoy)
            if n == 20:
                self.pausa(2)
                self.dia_de_estudio("micro", 20, "Retomo después de 2 días")
                self.comprobar(self.retornos_vistos[-1] == "corto", "2 días fuera debía activar el retorno corto")
                self.hoy = siguiente_lunes(self.hoy)
            if n == 11:
                self.sesion_claude_ai()  # el mismo lunes, desde el celular
            self.semana_calendario(n, s["horas"])
            self.comprobar(self.semana_actual() == n + 1, f"después de la semana {n} debía quedar en la {n + 1}")
            self.verificar_memoria()
        return self.cierre()

    def cierre(self) -> int:
        ctx = self.ctx()
        e = ctx.estado
        r = tutor.resumen(ctx)
        self.comprobar(ctx.semana_actual == tutor.SEMANA_FIN, f"debía terminar en la semana 25 (quedó en {ctx.semana_actual})")
        self.comprobar([a["semana"] for a in e["aprobaciones"]] == list(range(1, 25)), "debían quedar 24 aprobaciones en orden")
        for a in e["aprobaciones"]:
            if a["semana"] in tutor.PROYECTOS_MALLA:
                self.comprobar(a["tipo_evidencia"] in ("archivo", "url"), f"proyecto de la semana {a['semana']} sin artefacto")
        activas_malla = [t for t in ctx.tarjetas["tarjetas"] if t.startswith("s")]
        total_malla = sum(len(s["preguntas_de_repaso"]) for s in ctx.malla["semanas"])
        self.comprobar(len(activas_malla) == total_malla, f"debían quedar {total_malla} tarjetas de la malla activas")
        max_int = max((t["intervalo"] for t in ctx.tarjetas["tarjetas"].values()), default=0)
        self.comprobar(max_int >= 20, f"la repetición espaciada debía espaciar alguna tarjeta ≥ 20 días (máx {max_int})")
        self.comprobar(set(self.retornos_vistos) >= {"corto", "medio", "largo"}, f"faltan retornos: {self.retornos_vistos}")
        self.comprobar(len(e["rechazos"]) >= 6, f"debían registrarse ≥ 6 rechazos (hay {len(e['rechazos'])})")
        self.cli("aprobar-semana", 25, "--evidencia", "https://ejemplo.cl", esperar=2)
        self.comprobar("Programa completado" in self.cli("estado")[1], "estado debía decir «Programa completado»")
        self.comprobar("Programa completado" in self.cli("hoy")[1], "hoy debía pasar a modo mantener")
        self.cli("panel")
        panel = self.rutas.panel.read_text(encoding="utf-8")
        self.comprobar("24/24" in panel, "el panel debía mostrar 24/24")
        codigo, salida_validar, _ = self.cli("validar", esperar=None)
        self.comprobar(codigo == 0, "validar sobre la copia simulada debía pasar:\n" + salida_validar)
        self.verificar_memoria()
        resultado_validar = salida_validar.strip().splitlines()[-1] if salida_validar.strip() else "?"

        dias_totales = (self.hoy - INICIO).days
        print(f"SIMULACIÓN · semilla fija · {INICIO} → {self.hoy} ({dias_totales} días calendario)")
        print(f"  Semanas aprobadas: {len(e['aprobaciones'])}/24 (semana_actual = {ctx.semana_actual})")
        print(f"  Sesiones: {self.stats['sesiones']} · horas registradas: {self.stats['minutos'] / 60:.1f} h (malla: ~210 h)")
        print(f"  Días perdidos al azar u obligados: {self.stats['dias_perdidos']} · pausa de 10 días: "
              f"{'sí' if self.stats['pausa_10'] else 'no'} · semanas alargadas: {self.stats['semanas_extendidas']}")
        print(f"  Retornos detectados: {', '.join(self.retornos_vistos)}")
        print(f"  Intentos de aprobación rechazados: {len(e['rechazos'])} "
              f"(vacía, «vi el contenido», proyecto sin artefacto, fuera de orden, vaga)")
        print(f"  Repasos hechos: {self.stats['repasos']} · tarjetas activas: {r['tarjetas_activas']} · "
              f"intervalo máximo: {max_int} días")
        print(f"  Racha final: {r['racha']['actual']} días · mejor racha: {r['racha']['mejor']}")
        print(f"  Sesión importada desde claude.ai: {self.stats['importaciones']} (sin duplicar al reimportar)")
        print(f"  Comandos ejecutados: {self.stats['comandos']} · comprobaciones: {self.stats['comprobaciones']} · "
              f"chequeos de memoria: {self.stats['chequeos_diarios']}")
        print(f"  validar (copia simulada): {resultado_validar}")
        if self.fallas:
            print(f"\nResultado: FALLA ({len(self.fallas)} problema(s))")
            for f in self.fallas[:40]:
                print(f"  ✗ {f}")
            return 1
        print("\nResultado: OK — el estudiante simulado llegó al final de forma coherente.")
        return 0


def preparar_copia(origen: Path, destino: Path) -> Path:
    raiz = destino / "programa"
    shutil.copytree(origen, raiz, ignore=shutil.ignore_patterns(
        "progreso", "privado", "dist", "entregables", "__pycache__", ".git", "*.tmp"))
    return raiz


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass
    p = argparse.ArgumentParser(description="Simula a un estudiante recorriendo las 24 semanas.")
    p.add_argument("--semilla", type=int, default=7)
    p.add_argument("--detalle", action="store_true", help="muestra cada comando")
    p.add_argument("--conservar", action="store_true", help="no borra el directorio temporal")
    p.add_argument("--origen", default=str(tutor.RAIZ_DEFECTO), help="carpeta del programa a copiar")
    args = p.parse_args(argv)
    tmp = Path(tempfile.mkdtemp(prefix="sim-tutor-"))
    try:
        raiz = preparar_copia(Path(args.origen), tmp)
        codigo = Simulador(raiz, args.semilla, args.detalle).correr()
        if args.conservar:
            print(f"(copia simulada conservada en {raiz})")
        return codigo
    finally:
        if not args.conservar:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
