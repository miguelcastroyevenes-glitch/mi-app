#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simular.py — Simula a un estudiante que sigue al tutor durante las 24 semanas.

Copia el programa a un directorio temporal (nunca toca tu progreso real), inicia un
progreso limpio y avanza día a día con fechas inyectadas usando la CLI real de tutor.py.
El estudiante simulado hace lo que el tutor le propone (`hoy`), con la disponibilidad de
un jefe de local: lunes a miércoles y domingo sesiones normales; jueves a sábado, si
estudia, solo micro. Incluye a propósito lo que pasa en la vida real:

  * días perdidos al azar (semilla fija, reproducible) y semanas de cierre de mes;
  * una pausa de 10 días sin estudiar (reinicio), una de 4 (reentrada) y una de 2 (al día);
  * unas vacaciones declaradas con `pausa` (la racha queda congelada);
  * intentos de aprobar sin evidencia, con «vi el contenido», proyectos sin artefacto,
    semanas fuera de orden, evidencia vaga, rúbrica bajo el umbral y sin checkpoint sin IA;
  * repasos con calificaciones variadas (repetición espaciada);
  * sesiones hechas en claude.ai que se sincronizan con el bloque de estado (incluida una aprobación).

Después de cada día verifica la consistencia de la memoria y, al final, que el estudiante
llegó a la semana 25 (programa completo) de forma coherente y que `tutor.py validar` pasa.

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
LIMITE_DIAS = 700

# Día de la semana (lunes = 0) → (probabilidad de estudiar, modo). None = lo que proponga el tutor.
DISPONIBILIDAD = {0: (0.92, None), 1: (0.90, None), 2: (0.88, None), 3: (0.40, "micro"),
                  4: (0.20, "micro"), 5: (0.30, "micro"), 6: (0.70, None)}

# Después de aprobar la semana k, el estudiante no estudia hasta `dias` (calendario) después de su
# última sesión. Los «días fuera» que usa el tutor solo cuentan lunes a miércoles (jueves a domingo
# son de baja disponibilidad), así que: 10 días → reentrada · 21 días → reinicio · 2 días → al día.
PAUSAS = {9: 10, 12: 21, 19: 2}
VACACIONES_DESPUES_DE = 16  # pausa declarada de 20 días (vacaciones)
DIAS_VACACIONES = 20
IMPORTAR_SESION_EN = 11     # una sesión micro hecha en claude.ai
IMPORTAR_APROBACION_EN = 22  # una aprobación hecha en claude.ai


class Simulador:
    def __init__(self, raiz: Path, semilla: int, detalle: bool, hasta_semana: int = tutor.TOTAL_SEMANAS):
        self.meta = min(hasta_semana, tutor.TOTAL_SEMANAS) + 1
        self.raiz = raiz
        self.rutas = tutor.Rutas(raiz)
        self.rng = random.Random(semilla)
        self.detalle = detalle
        self.hoy = INICIO
        self.fallas: list[str] = []
        self.stats = Counter()
        self.retornos: list[str] = []
        self.no_estudiar_hasta: date | None = None
        self.retorno_esperado: str | None = None
        self.vacaciones_hasta: date | None = None
        self.mejor_previa = 0
        self.intentos: dict[int, int] = {}
        self.importada_sesion = False

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

    def semana_actual(self) -> int:
        return self.ctx().semana_actual

    def estado_json(self) -> dict:
        return json.loads(self.cli("estado", "--json")[1])

    def calidad(self) -> int:
        return self.rng.choices([5, 4, 3, 2, 1, 0], weights=[30, 35, 20, 9, 4, 2])[0]

    def rubrica(self, n: int, **cambios) -> str:
        puntajes = {c: self.rng.choice([2, 3, 3]) for c in tutor.criterios_semana(n)}
        puntajes.update(cambios)
        return ",".join(f"{c}={v}" for c, v in puntajes.items() if v is not None)

    def verificar_memoria(self) -> None:
        ctx = self.ctx()
        self.stats["chequeos_diarios"] += 1
        for e in tutor.verificar_estado(ctx):
            self.falla(f"memoria inconsistente: {e}")
        racha = tutor.racha_de(ctx)
        self.comprobar(racha["mejor"] >= racha["actual"], "la mejor racha no puede ser menor que la actual")
        self.comprobar(racha["mejor"] >= self.mejor_previa, "la mejor racha nunca debe bajar")
        self.mejor_previa = racha["mejor"]

    # ------------------------------------------------------------ acciones del estudiante
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

    def registrar(self, minutos: int, tipo: str, nota: str, semana: int | None = None) -> None:
        args = ["registrar", "--minutos", minutos, "--tipo", tipo, "--nota", nota,
                "--logrado", self.rng.choice(["si", "si", "parcial"]),
                "--si-entonces", "Si es lunes 21:30 y cierro el computador del local, entonces abro el tutor y hago la primera pregunta"]
        if semana:
            args += ["--semana", semana]
        self.cli(*args)
        self.stats["sesiones"] += 1
        self.stats["minutos"] += minutos
        self.stats[f"tipo_{tipo}"] += 1

    def intentar_aprobar(self, n: int, evidencia: str, rubrica: str, debe_pasar: bool, porque: str) -> None:
        antes = self.semana_actual()
        _, _, err = self.cli("aprobar-semana", n, "--evidencia", evidencia, "--rubrica", rubrica,
                             esperar=0 if debe_pasar else 2)
        despues = self.semana_actual()
        if debe_pasar:
            self.comprobar(despues == antes + 1, f"la semana {n} debía aprobarse ({porque})")
        else:
            self.stats["rechazos_esperados"] += 1
            self.comprobar(despues == antes, f"la semana {n} NO debía avanzar ({porque})")
            self.comprobar("Aún no" in err, f"el rechazo de la semana {n} debía explicar el motivo ({porque})")

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

    def demostrar(self, n: int) -> None:
        """Paso «Demostrar»: intentos de aprobación, algunos rechazados a propósito."""
        intento = self.intentos.get(n, 0)
        self.intentos[n] = intento + 1
        if intento == 0:
            if n == 3:
                self.intentar_aprobar(n, "entregables/mapa-que-no-existe.html", self.rubrica(n), False,
                                      "proyecto con ruta inexistente")
            if n == 4:
                self.intentar_aprobar(n, "vi el contenido", self.rubrica(n), False, "«vi el contenido»")
                self.intentar_aprobar(n, "", self.rubrica(n), False, "evidencia vacía")
            if n == 6:
                self.intentar_aprobar(n, "Construí el agente y expliqué sus razones al tutor con 5 leads nuevos.",
                                      self.rubrica(n), False, "proyecto sin artefacto")
            if n == 7:
                self.intentar_aprobar(9, "Expliqué MCP y construí el servidor con dos herramientas y un recurso.",
                                      self.rubrica(9), False, "semana fuera de orden")
            if n == 8:
                self.intentar_aprobar(n, "ok listo", self.rubrica(n), False, "evidencia vaga")
                return  # vuelve otro día: el plan debe recordar lo que faltó
            if n == 12:
                self.intentar_aprobar(n, self.evidencia_valida(n), self.rubrica(n, explicacion=1), False,
                                      "rúbrica bajo el umbral")
            if n == 14:
                self.intentar_aprobar(n, self.evidencia_valida(n), self.rubrica(n, sin_ia=None), False,
                                      "sin checkpoint sin IA al cierre de etapa")
        if n == 8 and intento == 1:
            self.comprobar("LO QUE FALTÓ" in self.cli("hoy")[1], "hoy debía recordar lo que faltó en la demostración")
        self.intentar_aprobar(n, self.evidencia_valida(n), self.rubrica(n), True, "evidencia y rúbrica válidas")
        self.despues_de_aprobar(n)

    def despues_de_aprobar(self, n: int) -> None:
        if n in PAUSAS:
            ultima = max(tutor.fechas_estudio(self.ctx().estado))
            self.no_estudiar_hasta = ultima + timedelta(days=PAUSAS[n])
            self.retorno_esperado = {10: "reentrada", 21: "reinicio", 2: "al_dia"}[PAUSAS[n]]
            self.stats[f"pausa_{PAUSAS[n]}_dias"] += 1
        if n == VACACIONES_DESPUES_DE:
            hasta = self.hoy + timedelta(days=DIAS_VACACIONES)
            self.cli("pausa", "--hasta", hasta.isoformat(), "--motivo", "vacaciones")
            self.no_estudiar_hasta = hasta + timedelta(days=1)
            self.retorno_esperado = "reinicio_declarado"
            self.vacaciones_hasta = hasta

    def importar(self, eventos: list[str]) -> None:
        _, bloque, _ = self.cli("bloque")
        self.comprobar(bloque.startswith(tutor.INICIO_BLOQUE) and tutor.FIN_BLOQUE in bloque,
                       "el bloque de estado no tiene el formato esperado")
        texto = bloque.replace(tutor.FIN_BLOQUE, "\n".join(eventos) + "\n" + tutor.FIN_BLOQUE)
        archivo = self.raiz / "bloque-importado.txt"
        archivo.write_text(texto, encoding="utf-8")
        antes = len(self.ctx().estado["sesiones"])
        self.cli("importar", archivo)
        despues = len(self.ctx().estado["sesiones"])
        self.comprobar(despues == antes + 1, "importar debía agregar exactamente 1 sesión")
        self.cli("importar", archivo)  # idempotente: la segunda vez no duplica nada
        self.comprobar(len(self.ctx().estado["sesiones"]) == despues, "importar dos veces duplicó la sesión")
        self.stats["importaciones"] += 1
        self.stats["sesiones"] += 1

    # ------------------------------------------------------------ un día de estudio
    def dia_de_estudio(self, modo: str | None) -> None:
        r = self.estado_json()
        n = r["semana_actual"]
        dias = r["dias_sin_estudiar"]
        estado_txt = self.cli("estado")[1]
        esperado = self.retorno_esperado
        if esperado:
            self.retorno_esperado = None
            modo = None  # el día del retorno se sigue el plan por defecto
            _, salida, _ = self.cli("retomar")
            n_ret = len(self.ctx().estado["retornos"])
            if esperado == "al_dia":
                self.comprobar("Toca retomar" not in estado_txt, "con 2 días fuera no se debe mencionar el retorno")
                self.comprobar("Al día" in salida, "con 2 días fuera retomar debía decir «Al día»")
            else:
                codigo = "reinicio" if esperado.startswith("reinicio") else esperado
                self.comprobar("Toca retomar" in estado_txt, f"estado debía sugerir retomar ({esperado})")
                titulo = tutor.protocolo_retomar(dias, self.hoy)["titulo"]
                self.comprobar(titulo in salida, f"retomar debía mostrar «{titulo}» (días fuera: {dias})")
                self.comprobar(self.ctx().estado["retornos"][-1]["protocolo"] == codigo,
                               f"el retorno debía registrarse como {codigo}")
                if esperado == "reinicio_declarado":
                    self.comprobar("qué lo cortó" not in salida, "tras una pausa declarada no se pregunta qué lo cortó")
                elif codigo == "reinicio":
                    self.comprobar("qué lo cortó" in salida, "el reinicio debía preguntar qué lo cortó")
                self.comprobar(n_ret == len(self.ctx().estado["retornos"]), "retomar no debe duplicar el retorno")
            self.retornos.append(esperado)
        elif r["toca_retomar"]:
            self.cli("retomar")
            self.retornos.append("reentrada-azar" if dias < 7 else "reinicio-azar")

        # Sesión hecha desde el celular en claude.ai (sin archivos) y sincronizada después.
        if n >= IMPORTAR_SESION_EN and modo == "micro" and not self.importada_sesion:
            self.importada_sesion = True
            vencidas = tutor.tarjetas_vencidas(self.ctx().tarjetas, self.hoy)
            eventos = [f"sesion: {self.hoy} | 15 | micro | repaso en el celular (claude.ai) | "
                       "Si es lunes 21:30, entonces abro el tutor",
                       f"parking: {self.hoy} | probar un agente de voz para confirmar visitas"]
            if vencidas:
                eventos.append(f"calificacion: {self.hoy} | {vencidas[0]} | 4")
            self.importar(eventos)
            self.stats["minutos"] += 15
            return

        plan = json.loads(self.cli("hoy", "--json", *([f"--{modo}"] if modo else []))[1])
        paso = plan["paso"]
        self.stats[f"paso_{paso}"] += 1
        if esperado == "reinicio" or esperado == "reinicio_declarado":
            self.comprobar(paso == "reinicio", f"tras una pausa larga el plan debía ser «reinicio» (fue {paso})")
        if esperado == "reentrada":
            self.comprobar(paso == "reentrada", f"tras 10 días el plan debía ser «reentrada» (fue {paso})")
        texto = self.cli("hoy", *([f"--{modo}"] if modo else []))[1]
        self.comprobar(f"Semana {n}/24" in texto and "Quedamos en:" in texto and "Primero:" in texto,
                       "el plan de hoy debía mostrar la semana y el arranque en frío")
        self.repasar(5 if plan["modo"] == "micro" else 3)
        minutos = plan["minutos"] + self.rng.choice([0, 0, 5, 10])
        if paso == "demostrar":
            if n == IMPORTAR_APROBACION_EN:
                evidencia = self.evidencia_valida(n)
                self.importar([f"sesion: {self.hoy} | {minutos} | estandar | demostración de la semana {n} en claude.ai",
                               f"aprobada: {self.hoy} | {n} | {self.rubrica(n)} | {evidencia}"])
                self.stats["minutos"] += minutos
                self.comprobar(self.semana_actual() == n + 1, "la aprobación importada desde claude.ai debía avanzar")
                self.despues_de_aprobar(n)
                return
            self.registrar(minutos, "estandar", f"Demostración de la semana {n}", semana=n)
            self.demostrar(n)
        else:
            tipo = plan.get("tipo_registro", plan["modo"])
            self.registrar(minutos, tipo, f"{plan['nombre_paso']} · semana {n}")

    # ------------------------------------------------------------ bucle principal
    def correr(self) -> int:
        self.cli("iniciar")
        self.comprobar("Primer día" in self.cli("retomar")[1], "retomar sin sesiones debía dar el protocolo de inicio")
        self.comprobar(self.semana_actual() == 1, "el estudiante debía partir en la semana 1")
        while self.semana_actual() < self.meta:
            if (self.hoy - INICIO).days > LIMITE_DIAS:
                self.falla(f"no terminó en {LIMITE_DIAS} días: quedó en la semana {self.semana_actual()}")
                break
            prob, modo = DISPONIBILIDAD[self.hoy.weekday()]
            if self.no_estudiar_hasta:
                estudia = self.hoy >= self.no_estudiar_hasta
                if estudia:
                    self.no_estudiar_hasta = None
                    modo = None
            else:
                estudia = self.rng.random() < prob
            if estudia:
                self.dia_de_estudio(modo)
                self.stats["dias_estudio"] += 1
            else:
                self.stats["dias_sin_estudio"] += 1
            self.verificar_memoria()
            self.hoy += timedelta(days=1)
        self.hoy -= timedelta(days=1)
        if self.meta < tutor.SEMANA_FIN:
            r = tutor.resumen(self.ctx())
            print(f"SIMULACIÓN PARCIAL · {INICIO} → {self.hoy} · semana en curso {r['semana_actual']} · "
                  f"{len(r['aprobadas'])} aprobadas · {len(self.fallas)} problema(s)")
            for f in self.fallas[:20]:
                print(f"  ✗ {f}")
            return 1 if self.fallas else 0
        return self.cierre()

    def cierre(self) -> int:
        ctx = self.ctx()
        e = ctx.estado
        r = tutor.resumen(ctx)
        racha = r["racha"]
        self.comprobar(ctx.semana_actual == tutor.SEMANA_FIN, f"debía terminar en la semana 25 (quedó en {ctx.semana_actual})")
        self.comprobar([a["semana"] for a in e["aprobaciones"]] == list(range(1, 25)), "debían quedar 24 aprobaciones en orden")
        for a in e["aprobaciones"]:
            if a["semana"] in tutor.PROYECTOS_MALLA:
                self.comprobar(a["tipo_evidencia"] in ("archivo", "url"), f"proyecto de la semana {a['semana']} sin artefacto")
                self.comprobar(a["rubrica"].get("sin_ia", 0) >= 2, f"cierre de etapa {a['semana']} sin checkpoint sin IA")
        activas_malla = [t for t in ctx.tarjetas["tarjetas"] if t.startswith("s")]
        total_malla = sum(len(s["preguntas_de_repaso"]) for s in ctx.malla["semanas"])
        self.comprobar(len(activas_malla) == total_malla, f"debían quedar {total_malla} tarjetas de la malla activas")
        max_int = max((t["intervalo"] for t in ctx.tarjetas["tarjetas"].values()), default=0)
        self.comprobar(max_int >= 20, f"la repetición espaciada debía espaciar alguna tarjeta ≥ 20 días (máx {max_int})")
        for esperado in ("reinicio", "reentrada", "al_dia", "reinicio_declarado"):
            self.comprobar(esperado in self.retornos, f"faltó el escenario de retorno «{esperado}» ({self.retornos})")
        self.comprobar(len(e["rechazos"]) >= 8, f"debían registrarse ≥ 8 rechazos (hay {len(e['rechazos'])})")
        estados = Counter(w["estado"] for w in racha["semanas"])
        self.comprobar(estados["pausa"] >= 1, "las vacaciones declaradas debían dejar al menos una semana en «pausa»")
        self.comprobar(self.stats["paso_mantenimiento"] >= 1, "debía haber sesiones de mantenimiento en cierre de mes")
        self.comprobar(e["parking"], "la idea anotada desde claude.ai debía quedar en el parking")
        self.cli("aprobar-semana", 25, "--evidencia", "https://ejemplo.cl", "--rubrica", "entregable=3", esperar=2)
        self.comprobar("Programa completado" in self.cli("estado")[1], "estado debía decir «Programa completado»")
        self.comprobar("Programa completado" in self.cli("hoy")[1], "hoy debía pasar a modo mantener")
        self.cli("panel")
        panel = self.rutas.panel.read_text(encoding="utf-8")
        self.comprobar("24/24" in panel and "Hoja de Combate" in panel, "el panel debía mostrar 24/24")
        bitacora = self.rutas.bitacora.read_text(encoding="utf-8")
        self.comprobar(bitacora.count("APROBADA") == 24, "la bitácora debía tener 24 filas APROBADA")
        codigo, salida_validar, _ = self.cli("validar", esperar=None)
        self.comprobar(codigo == 0, "validar sobre la copia simulada debía pasar:\n" + salida_validar)
        self.verificar_memoria()
        resultado_validar = salida_validar.strip().splitlines()[-1] if salida_validar.strip() else "?"

        dias_totales = (self.hoy - INICIO).days + 1
        rec = r["recuperacion"]
        motivos = Counter()
        for x in e["rechazos"]:
            m = x["motivo"]
            clave = ("fuera de orden" if "en orden" in m else "consumo («vi el contenido»)" if "consumo" in m
                     else "sin evidencia" if "Falta la evidencia" in m else "proyecto sin artefacto" if "Semana de proyecto" in m
                     else "evidencia vaga" if "vaga" in m else "rúbrica bajo umbral" if "umbral" in m
                     else "falta criterio (sin IA)" if "Falta puntuar" in m else "otro")
            motivos[clave] += 1
        print(f"SIMULACIÓN · {INICIO} → {self.hoy} ({dias_totales} días ≈ {dias_totales / 30.4:.1f} meses)")
        print(f"  Semanas aprobadas: {len(e['aprobaciones'])}/24 (semana_actual = {ctx.semana_actual}) · "
              f"nivel final: {r['nivel']}")
        print(f"  Días con estudio: {self.stats['dias_estudio']} · días sin estudio: {self.stats['dias_sin_estudio']} · "
              f"sesiones: {self.stats['sesiones']} (micro {self.stats['tipo_micro']}, estándar {self.stats['tipo_estandar']}, "
              f"lab {self.stats['tipo_lab']}, reinicio {self.stats['tipo_repaso']}) · {self.stats['minutos'] / 60:.0f} h")
        print(f"  Pasos seguidos: " + ", ".join(f"{k[5:]} {v}" for k, v in sorted(self.stats.items()) if k.startswith("paso_")))
        azar = Counter(x for x in self.retornos if x.endswith("-azar"))
        print(f"  Retornos guionizados: {', '.join(x for x in self.retornos if not x.endswith('-azar'))}"
              f" · por días perdidos al azar: {dict(azar) or 'ninguno'} · pausa de 10 días: "
              f"{'sí' if self.stats['pausa_10_dias'] else 'no'}")
        print(f"  Rechazos: {len(e['rechazos'])} → " + ", ".join(f"{k} {v}" for k, v in motivos.items()))
        print(f"  Repasos: {self.stats['repasos']} · tarjetas activas: {r['tarjetas_activas']} · intervalo máx.: {max_int} días · "
              f"acierto a 1 semana: {rec['a_1_semana']}% · a 1 mes: {rec['a_1_mes']}%")
        print(f"  Racha semanal final: {racha['actual']} · mejor: {racha['mejor']} · semanas: "
              + ", ".join(f"{k} {v}" for k, v in sorted(estados.items())))
        print(f"  Sincronización con claude.ai: {self.stats['importaciones']} importaciones (sin duplicar al reimportar)")
        print(f"  Comandos: {self.stats['comandos']} · comprobaciones: {self.stats['comprobaciones']} · "
              f"chequeos diarios de memoria: {self.stats['chequeos_diarios']}")
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
    p = argparse.ArgumentParser(description="Simula a un estudiante que sigue al tutor durante las 24 semanas.")
    p.add_argument("--semilla", type=int, default=7)
    p.add_argument("--detalle", action="store_true", help="muestra cada comando")
    p.add_argument("--conservar", action="store_true", help="no borra el directorio temporal")
    p.add_argument("--origen", default=str(tutor.RAIZ_DEFECTO), help="carpeta del programa a copiar")
    p.add_argument("--hasta-semana", type=int, default=tutor.TOTAL_SEMANAS,
                   help="detiene la simulación al aprobar esa semana (para inspeccionar un estado intermedio)")
    args = p.parse_args(argv)
    tmp = Path(tempfile.mkdtemp(prefix="sim-tutor-"))
    try:
        raiz = preparar_copia(Path(args.origen), tmp)
        codigo = Simulador(raiz, args.semilla, args.detalle, args.hasta_semana).correr()
        if args.conservar:
            print(f"(copia simulada conservada en {raiz})")
        return codigo
    finally:
        if not args.conservar:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
