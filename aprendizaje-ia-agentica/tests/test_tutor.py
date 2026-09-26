# -*- coding: utf-8 -*-
"""Pruebas del tutor (unittest, solo biblioteca estándar).

Correr desde aprendizaje-ia-agentica/:
    python3 -m unittest discover -s tests -v

Cada prueba trabaja sobre una copia temporal del programa: nunca toca progreso/ real.
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "herramientas"))
import tutor  # noqa: E402

RUBRICA_OK = "entregable=3,explicacion=2,recuperacion=3"
RUBRICA_OK_CIERRE = RUBRICA_OK + ",sin_ia=2"
EVIDENCIA_OK = ("Expliqué sin apuntes a un ejecutivo la diferencia entre chatbot y agente con el "
                "seguimiento de leads y respondí 4 de 4 preguntas de repaso.")


def d(texto: str) -> date:
    return date.fromisoformat(texto)


class BaseCopia(unittest.TestCase):
    """Copia el programa a un directorio temporal e inicia un progreso limpio."""

    con_base = False
    inicio = "2026-10-05"  # lunes

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        ignorar = ["progreso", "privado", "dist", "entregables", "__pycache__", ".git"]
        if not self.con_base:
            ignorar.append("base")
        self.raiz = Path(self._tmp.name) / "programa"
        shutil.copytree(RAIZ, self.raiz, ignore=shutil.ignore_patterns(*ignorar))
        self.rutas = tutor.Rutas(self.raiz)
        codigo, _, err = self.cli("iniciar", hoy=self.inicio)
        self.assertEqual(codigo, 0, err)

    def tearDown(self):
        self._tmp.cleanup()

    def cli(self, *args, hoy=None):
        argv = [str(a) for a in args] + ["--raiz", str(self.raiz), "--hoy", hoy or self.inicio]
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                codigo = tutor.main(argv)
            except SystemExit as e:
                codigo = e.code if isinstance(e.code, int) else 2
        return codigo, out.getvalue(), err.getvalue()

    def ctx(self, hoy=None):
        return tutor.Contexto(self.rutas, d(hoy or self.inicio))

    def aprobar(self, n, hoy, evidencia=EVIDENCIA_OK, rubrica=None):
        rubrica = rubrica or (RUBRICA_OK_CIERRE if n in tutor.FIN_DE_ETAPA else RUBRICA_OK)
        return self.cli("aprobar-semana", n, "--evidencia", evidencia, "--rubrica", rubrica, hoy=hoy)

    def artefacto(self, rel="entregables/mapa.html"):
        ruta = self.raiz / rel
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("<h1>AI Opportunity Map</h1>", encoding="utf-8")
        return rel

    def malla(self):
        return json.loads(self.rutas.malla.read_text(encoding="utf-8"))

    def guardar_malla(self, m):
        self.rutas.malla.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

    def validar(self, hoy=None):
        inf = tutor.validar(self.rutas, d(hoy or self.inicio))
        return inf, [m for n, _, m in inf.items if n == "ERROR"], [m for n, _, m in inf.items if n == "AVISO"]


# ---------------------------------------------------------------------------
class TestRepeticionEspaciada(unittest.TestCase):
    def test_respuestas_buenas_espacian_1_3_8(self):
        hoy = d("2026-10-10")
        t = tutor.nueva_tarjeta(hoy)
        intervalos = []
        for _ in range(3):
            t = tutor.aplicar_sm2(t, 5, hoy)
            intervalos.append(t["intervalo"])
            self.assertEqual(t["proxima"], (hoy + timedelta(days=t["intervalo"])).isoformat())
        self.assertEqual(intervalos, [1, 3, 8])
        self.assertAlmostEqual(t["ef"], 2.8)

    def test_respuesta_mala_reinicia(self):
        hoy = d("2026-10-10")
        t = tutor.nueva_tarjeta(hoy)
        for q in (5, 4, 4):
            t = tutor.aplicar_sm2(t, q, hoy)
        ef_antes = t["ef"]
        t = tutor.aplicar_sm2(t, 2, hoy)
        self.assertEqual((t["intervalo"], t["repeticiones"]), (1, 0))
        self.assertLess(t["ef"], ef_antes)
        self.assertEqual(t["historial"][-1]["intervalo_previo"], 8)

    def test_facilidad_nunca_baja_de_1_3(self):
        t = tutor.nueva_tarjeta(d("2026-10-10"))
        for _ in range(15):
            t = tutor.aplicar_sm2(t, 0, d("2026-10-10"))
        self.assertEqual(t["ef"], tutor.EF_MINIMO)

    def test_intervalo_tiene_tope(self):
        t = tutor.nueva_tarjeta(d("2026-10-10"))
        for _ in range(12):
            t = tutor.aplicar_sm2(t, 5, d("2026-10-10"))
        self.assertLessEqual(t["intervalo"], tutor.INTERVALO_MAXIMO)

    def test_calidad_invalida(self):
        t = tutor.nueva_tarjeta(d("2026-10-10"))
        for q in (6, -1, True, "4"):
            with self.assertRaises(tutor.ErrorTutor):
                tutor.aplicar_sm2(t, q, d("2026-10-10"))

    def test_vencidas_en_orden_y_sin_futuras(self):
        tarjetas = {"tarjetas": {
            "a": {"proxima": "2026-10-09"}, "b": {"proxima": "2026-10-05"},
            "c": {"proxima": "2026-10-11"}, "d": {"proxima": "2026-10-10"}}}
        self.assertEqual(tutor.tarjetas_vencidas(tarjetas, d("2026-10-10")), ["b", "a", "d"])


class TestRepasoCLI(BaseCopia):
    def test_tarjetas_se_activan_al_aprobar_y_se_califican(self):
        codigo, _, err = self.aprobar(1, "2026-10-07")
        self.assertEqual(codigo, 0, err)
        _, out, _ = self.cli("repaso", "--json", hoy="2026-10-07")
        self.assertEqual(json.loads(out), [], "las tarjetas nuevas vencen mañana, no hoy")
        _, out, _ = self.cli("repaso", "--json", hoy="2026-10-08")
        self.assertEqual([x["id"] for x in json.loads(out)], ["s01-p1", "s01-p2", "s01-p3", "s01-p4"])
        _, out, _ = self.cli("repaso", hoy="2026-10-08")
        self.assertNotIn("Respuesta:", out, "repaso nunca muestra respuestas")
        codigo, out, _ = self.cli("calificar", "s01-p1", 4, hoy="2026-10-08")
        self.assertEqual(codigo, 0)
        self.assertIn("2026-10-09", out)
        _, out, _ = self.cli("respuesta", "s01-p1", hoy="2026-10-08")
        self.assertIn("Respuesta:", out)

    def test_calificar_tarjeta_no_activa_o_inexistente(self):
        self.assertEqual(self.cli("calificar", "s05-p1", 4)[0], 2)
        self.assertEqual(self.cli("calificar", "s99-p9", 4)[0], 2)

    def test_registrar_calcula_recuperacion_del_dia(self):
        self.aprobar(1, "2026-10-07")
        self.cli("calificar", "s01-p1", 5, hoy="2026-10-08")
        self.cli("calificar", "s01-p2", 1, hoy="2026-10-08")
        self.cli("registrar", "--minutos", 15, "--tipo", "micro", "--nota", "repaso", hoy="2026-10-08")
        self.assertEqual(self.ctx("2026-10-08").estado["sesiones"][-1]["recuperacion"], "1/2")


# ---------------------------------------------------------------------------
class TestRachaSemanal(unittest.TestCase):
    # Enero 2027: semanas del 4, 11 y 18 son normales; la del 25 es de cierre de mes.
    def racha(self, fechas, hoy, pausas=(), minutos=15):
        return tutor.calcular_racha([(d(f), minutos) for f in fechas], d(hoy), pausas=pausas)

    def test_piso_por_sesiones(self):
        r = self.racha(["2027-01-04", "2027-01-05", "2027-01-06"], "2027-01-10")
        self.assertEqual((r["actual"], r["semanas"][0]["estado"]), (1, "cumplida"))

    def test_piso_por_minutos(self):
        r = tutor.calcular_racha([(d("2027-01-04"), 60)], d("2027-01-10"))
        self.assertEqual(r["actual"], 1)

    def test_semana_en_curso_no_corta(self):
        r = self.racha(["2027-01-04", "2027-01-05", "2027-01-06", "2027-01-11"], "2027-01-13")
        self.assertEqual(r["actual"], 1)
        self.assertEqual(r["semana_en_curso"]["estado"], "en_curso")

    def test_semana_fallida_se_repara_con_2_sesiones(self):
        r = self.racha(["2027-01-04", "2027-01-05", "2027-01-06", "2027-01-12",
                        "2027-01-18", "2027-01-19"], "2027-01-20")
        self.assertEqual([w["estado"] for w in r["semanas"]], ["cumplida", "reparada", "en_curso"])
        self.assertEqual(r["actual"], 1)

    def test_una_sesion_larga_que_cumple_el_piso_tambien_repara(self):
        # Semilla 11 de la simulación: la mejor racha no puede bajar al cerrar la semana.
        base = [(d(f), 15) for f in ("2027-01-04", "2027-01-05", "2027-01-06")] + [(d("2027-01-19"), 75)]
        antes = tutor.calcular_racha(base, d("2027-01-20"))
        despues = tutor.calcular_racha(base, d("2027-01-26"))
        self.assertEqual([w["estado"] for w in despues["semanas"]][:3], ["cumplida", "reparada", "cumplida"])
        self.assertGreaterEqual(despues["mejor"], antes["mejor"])
        self.assertEqual(despues["actual"], 2)

    def test_comodin_del_mes_y_luego_se_corta(self):
        fechas = ["2027-01-04", "2027-01-05", "2027-01-06"]
        r = self.racha(fechas, "2027-01-20")
        self.assertEqual([w["estado"] for w in r["semanas"]], ["cumplida", "por_reparar", "en_curso"])
        r = self.racha(fechas, "2027-01-26")
        self.assertEqual([w["estado"] for w in r["semanas"]], ["cumplida", "comodin", "por_reparar", "en_curso"])
        self.assertEqual(r["actual"], 1)
        self.assertFalse(r["comodin_disponible"])
        r = self.racha(fechas, "2027-02-02")
        self.assertEqual([w["estado"] for w in r["semanas"]][:3], ["cumplida", "comodin", "rota"])
        self.assertEqual((r["actual"], r["mejor"]), (0, 1))
        self.assertTrue(r["comodin_disponible"], "febrero trae un comodín nuevo")

    def test_cierre_de_mes_tiene_piso_reducido(self):
        r = self.racha(["2027-01-25", "2027-01-26"], "2027-01-31")
        self.assertTrue(r["semanas"][0]["cierre"])
        self.assertEqual(r["semanas"][0]["estado"], "cumplida")
        r = self.racha(["2027-01-11", "2027-01-12"], "2027-01-17")
        self.assertEqual(r["semanas"][0]["estado"], "en_curso")

    def test_pausa_declarada_es_neutra(self):
        pausas = [(d("2027-01-09"), d("2027-01-17"))]
        fechas = ["2027-01-04", "2027-01-05", "2027-01-06", "2027-01-18", "2027-01-19", "2027-01-20"]
        r = self.racha(fechas, "2027-01-24", pausas=pausas)
        self.assertEqual([w["estado"] for w in r["semanas"]], ["cumplida", "pausa", "cumplida"])
        self.assertEqual(r["actual"], 2)

    def test_mejor_racha_se_conserva(self):
        fechas = [f"2027-01-{x:02d}" for x in (4, 5, 6, 11, 12, 13)]
        r = self.racha(fechas, "2027-02-10")
        self.assertEqual(r["mejor"], 2)
        self.assertLessEqual(r["actual"], r["mejor"])

    def test_sin_sesiones(self):
        r = tutor.calcular_racha([], d("2027-01-10"))
        self.assertEqual((r["estado"], r["actual"], r["mejor"]), ("sin_iniciar", 0, 0))

    def test_una_semana_de_cierre_por_mes(self):
        lunes = tutor.lunes_de(d("2026-10-01"))
        por_mes = {}
        while lunes < d("2027-10-01"):
            if tutor.es_semana_de_cierre(lunes):
                clave = tutor.mes_de_semana(lunes)
                por_mes[clave] = por_mes.get(clave, 0) + 1
            lunes += timedelta(weeks=1)
        self.assertEqual(len(por_mes), 12)
        self.assertTrue(all(v == 1 for v in por_mes.values()), por_mes)


# ---------------------------------------------------------------------------
class TestAprobarSemana(BaseCopia):
    def assert_rechazo(self, codigo, err, n_rechazos):
        self.assertEqual(codigo, 2, err)
        self.assertIn("Aún no", err)
        ctx = self.ctx("2026-10-09")
        self.assertEqual(ctx.semana_actual, 1)
        self.assertEqual(len(ctx.estado["rechazos"]), n_rechazos)

    def test_sin_evidencia_no_avanza(self):
        codigo, _, err = self.cli("aprobar-semana", 1, "--evidencia", "", "--rubrica", RUBRICA_OK, hoy="2026-10-09")
        self.assert_rechazo(codigo, err, 1)

    def test_vi_el_contenido_no_es_evidencia(self):
        for i, texto in enumerate(("vi el contenido", "Ya lo vi todo y lo entendí perfecto, leí la lectura completa"), 1):
            codigo, _, err = self.aprobar(1, "2026-10-09", evidencia=texto)
            self.assert_rechazo(codigo, err, i)
            self.assertIn("consumo", err)

    def test_evidencia_vaga(self):
        codigo, _, err = self.aprobar(1, "2026-10-09", evidencia="ok listo")
        self.assert_rechazo(codigo, err, 1)
        self.assertIn("vaga", err)

    def test_fuera_de_orden(self):
        codigo, _, err = self.aprobar(3, "2026-10-09")
        self.assert_rechazo(codigo, err, 1)
        self.assertIn("en orden", err)

    def test_rubrica_bajo_umbral_o_incompleta(self):
        codigo, _, err = self.aprobar(1, "2026-10-09", rubrica="entregable=3,explicacion=1,recuperacion=3")
        self.assert_rechazo(codigo, err, 1)
        self.assertIn("umbral", err)
        codigo, _, err = self.aprobar(1, "2026-10-09", rubrica="entregable=3,explicacion=3")
        self.assert_rechazo(codigo, err, 2)
        self.assertIn("recuperacion", err)
        codigo, _, err = self.aprobar(1, "2026-10-09", rubrica="entregable=9")
        self.assertEqual(codigo, 2)

    def test_aprobacion_valida_activa_tarjetas_y_bitacora(self):
        codigo, out, err = self.aprobar(1, "2026-10-09")
        self.assertEqual(codigo, 0, err)
        ctx = self.ctx("2026-10-09")
        self.assertEqual(ctx.semana_actual, 2)
        reg = ctx.estado["aprobaciones"][0]
        self.assertEqual((reg["tipo_evidencia"], reg["modalidad"]), ("descripcion", "normal"))
        for i in range(1, 5):
            self.assertEqual(ctx.tarjetas["tarjetas"][f"s01-p{i}"]["proxima"], "2026-10-10")
        self.assertIn("APROBADA", self.rutas.bitacora.read_text(encoding="utf-8"))
        self.assertEqual(self.aprobar(1, "2026-10-09")[0], 2, "no se aprueba dos veces")

    def test_url_y_test_out(self):
        codigo, _, err = self.cli("aprobar-semana", 1, "--evidencia", "https://github.com/miguel/ia/tree/main/s01",
                                  "--rubrica", RUBRICA_OK, "--test-out", hoy="2026-10-09")
        self.assertEqual(codigo, 0, err)
        reg = self.ctx("2026-10-09").estado["aprobaciones"][0]
        self.assertEqual((reg["tipo_evidencia"], reg["modalidad"]), ("url", "test-out"))

    def test_proyecto_exige_artefacto_y_checkpoint_sin_ia(self):
        self.aprobar(1, "2026-10-08")
        self.aprobar(2, "2026-10-09")
        codigo, _, err = self.aprobar(3, "2026-10-10", evidencia=EVIDENCIA_OK)
        self.assertEqual(codigo, 2)
        self.assertIn("Semana de proyecto", err)
        codigo, _, err = self.aprobar(3, "2026-10-10", evidencia="entregables/no-existe.html")
        self.assertEqual(codigo, 2)
        self.assertIn("no encontré", err)
        rel = self.artefacto()
        codigo, _, err = self.aprobar(3, "2026-10-10", evidencia=rel, rubrica=RUBRICA_OK)
        self.assertEqual(codigo, 2)
        self.assertIn("sin_ia", err)
        codigo, out, err = self.aprobar(3, "2026-10-10", evidencia=rel, rubrica=RUBRICA_OK_CIERRE)
        self.assertEqual(codigo, 0, err)
        self.assertIn("Nivel: Estratega", out)
        reg = self.ctx("2026-10-10").estado["aprobaciones"][-1]
        self.assertEqual((reg["tipo_evidencia"], reg["proyecto"]), ("archivo", "AI Opportunity Map"))

    def test_evaluar_evidencia_directo(self):
        r = self.rutas
        self.assertFalse(tutor.evaluar_evidencia("", False, r)[0])
        self.assertFalse(tutor.evaluar_evidencia("terminé de ver el video y leí el capítulo", False, r)[0])
        self.assertTrue(tutor.evaluar_evidencia(EVIDENCIA_OK, False, r)[0])
        self.assertEqual(tutor.evaluar_evidencia("https://ejemplo.cl/demo", True, r)[1], "url")


# ---------------------------------------------------------------------------
class TestRetomar(BaseCopia):
    def test_protocolo_segun_dias(self):
        esperado = {None: "inicio", 0: "al_dia", 1: "al_dia", 2: "al_dia", 3: "reentrada",
                    6: "reentrada", 7: "reinicio", 30: "reinicio"}
        for dias, codigo in esperado.items():
            self.assertEqual(tutor.protocolo_retomar(dias, d("2026-10-13"))["codigo"], codigo, dias)

    def test_dias_fuera_no_cuentan_jueves_a_domingo(self):
        estado = {"sesiones": [{"fecha": "2026-10-07", "minutos": 30}]}  # miércoles
        libres = tutor.CONFIG_DEFECTO["dias_de_baja_disponibilidad"]
        self.assertEqual(tutor.dias_sin_estudiar(estado, d("2026-10-12"), libres), 1)  # lunes
        self.assertEqual(tutor.dias_sin_estudiar(estado, d("2026-10-14"), libres), 3)  # miércoles siguiente
        self.assertEqual(tutor.dias_sin_estudiar(estado, d("2026-10-14")), 7)  # calendario
        self.assertIsNone(tutor.dias_sin_estudiar({"sesiones": []}, d("2026-10-14")))

    def test_mensajes_sin_conteo_de_dias(self):
        for dias in (3, 10):
            p = tutor.protocolo_retomar(dias, d("2026-10-13"))
            self.assertNotIn(str(dias), p["mensaje"])

    def test_al_dia_no_se_menciona(self):
        self.cli("registrar", "--minutos", 30, "--nota", "x", hoy="2026-10-07")
        _, estado, _ = self.cli("estado", hoy="2026-10-12")
        self.assertNotIn("Toca retomar", estado)
        _, out, _ = self.cli("retomar", hoy="2026-10-12")
        self.assertIn("Al día", out)
        self.assertEqual(self.ctx("2026-10-12").estado["retornos"], [])

    def test_reentrada_y_reinicio(self):
        self.cli("registrar", "--minutos", 30, "--nota", "x", hoy="2026-10-07")
        _, out, _ = self.cli("retomar", hoy="2026-10-14")
        self.assertIn("Reentrada", out)
        self.cli("retomar", hoy="2026-10-14")
        self.assertEqual(len(self.ctx("2026-10-14").estado["retornos"]), 1, "un retorno por día")
        _, out, _ = self.cli("retomar", hoy="2026-10-28")
        self.assertIn("Reinicio limpio", out)
        self.assertIn("qué lo cortó", out)
        self.assertIn("PRUEBA DE NIVEL", out)
        self.assertEqual(self.cli("hoy", "--json", hoy="2026-10-28")[1].count('"paso": "reinicio"'), 1)

    def test_pausa_declarada_congela_y_no_pregunta(self):
        self.cli("registrar", "--minutos", 30, "--nota", "x", hoy="2026-10-07")
        codigo, _, err = self.cli("pausa", "--hasta", "2026-10-30", "--motivo", "vacaciones", hoy="2026-10-08")
        self.assertEqual(codigo, 0, err)
        _, out, _ = self.cli("retomar", hoy="2026-10-31")
        self.assertIn("Reinicio limpio", out)
        self.assertNotIn("qué lo cortó", out)
        self.assertEqual(self.cli("pausa", "--hasta", "2026-10-01", hoy="2026-10-08")[0], 2)

    def test_ancla_del_reinicio(self):
        self.assertEqual(tutor.ancla_reinicio(d("2026-10-30")), (d("2026-11-01"), "el inicio de mes"))
        self.assertEqual(tutor.ancla_reinicio(d("2026-10-16")), (d("2026-10-19"), "el lunes"))
        self.assertEqual(tutor.ancla_reinicio(d("2026-10-13")), (d("2026-10-13"), "hoy"))


# ---------------------------------------------------------------------------
class TestPlanDeHoy(BaseCopia):
    def paso(self, hoy, *flags):
        return json.loads(self.cli("hoy", "--json", *flags, hoy=hoy)[1])["paso"]

    def test_secuencia_entender_construir_cerrar_demostrar(self):
        self.assertEqual(self.paso("2026-10-05"), "entender")
        self.cli("registrar", "--minutos", 30, "--tipo", "estandar", "--nota", "a", hoy="2026-10-05")
        self.assertEqual(self.paso("2026-10-06"), "construir")
        self.cli("registrar", "--minutos", 75, "--tipo", "lab", "--nota", "b", hoy="2026-10-06")
        self.assertEqual(self.paso("2026-10-07"), "cerrar")
        self.cli("registrar", "--minutos", 30, "--tipo", "estandar", "--nota", "c", hoy="2026-10-07")
        self.assertEqual(self.paso("2026-10-08"), "demostrar")
        self.aprobar(1, "2026-10-08")
        self.assertEqual(self.paso("2026-10-12"), "entender", "semana nueva, pasos nuevos")

    def test_modos_explicitos(self):
        self.assertEqual(self.paso("2026-10-05", "--micro"), "micro")
        self.assertEqual(self.paso("2026-10-05", "--lab"), "construir")
        self.cli("registrar", "--minutos", 75, "--tipo", "lab", "--nota", "b", hoy="2026-10-05")
        self.assertEqual(self.paso("2026-10-05", "--lab"), "construir-mas")
        self.assertEqual(self.paso("2026-10-05", "--estandar"), "entender")

    def test_cierre_de_mes_es_mantenimiento(self):
        self.cli("registrar", "--minutos", 15, "--tipo", "micro", "--nota", "x", hoy="2026-10-26")
        self.assertEqual(self.paso("2026-10-27"), "mantenimiento")
        self.assertEqual(self.paso("2026-10-27", "--estandar"), "entender")

    def test_primer_dia_en_cierre_de_mes_es_micro(self):
        self.assertEqual(self.paso("2026-10-27"), "micro")

    def test_reentrada_por_dias_fuera(self):
        self.cli("registrar", "--minutos", 30, "--nota", "x", hoy="2026-10-07")
        self.assertEqual(self.paso("2026-10-14"), "reentrada")
        self.assertEqual(self.paso("2026-10-12"), "construir", "un fin de semana no es un retorno")

    def test_arranque_en_frio_y_objetivo(self):
        _, out, _ = self.cli("hoy")
        for texto in ("Quedamos en:", "Hoy:", "Primero:", "OBJETIVO ÚNICO", "SI SOLO TIENES 15 MIN"):
            self.assertIn(texto, out)
        self.assertIn(self.ctx().semana(1)["objetivo"], out)

    def test_registrar_valida_entradas(self):
        self.assertEqual(self.cli("registrar", "--minutos", 0, "--nota", "x")[0], 2)
        self.assertEqual(self.cli("registrar", "--minutos", 30, "--nota", " ")[0], 2)
        self.assertEqual(self.cli("registrar", "--minutos", 30, "--nota", "x", "--semana", 5)[0], 2)
        self.assertEqual(self.cli("registrar", "--minutos", 30, "--nota", "x", "--logrado", "quizas")[0], 2)
        codigo, out, _ = self.cli("registrar", "--minutos", 30, "--nota", "x", "--logrado", "sí",
                                  "--si-entonces", "Si es lunes 21:00, abro el tutor")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.ctx().estado["sesiones"][-1]["logrado"], "si")

    def test_iniciar_no_borra_progreso_sin_forzar(self):
        self.cli("registrar", "--minutos", 30, "--nota", "x")
        self.assertEqual(self.cli("iniciar")[0], 2)
        self.assertEqual(self.cli("iniciar", "--forzar")[0], 0)
        self.assertEqual(self.ctx().estado["sesiones"], [])


# ---------------------------------------------------------------------------
class TestValidar(BaseCopia):
    def test_programa_real_pasa(self):
        inf = tutor.validar(tutor.Rutas(RAIZ), tutor.fecha_hoy())
        self.assertEqual([m for n, _, m in inf.items if n == "ERROR"], [])

    def test_copia_limpia_pasa(self):
        _, errores, avisos = self.validar()
        self.assertEqual(errores, [])
        self.assertTrue(any("fuentes.json aún no existe" in a for a in avisos), "sin base: aviso, no error")

    def test_semana_faltante(self):
        m = self.malla()
        m["semanas"] = [s for s in m["semanas"] if s["semana"] != 5]
        self.guardar_malla(m)
        _, errores, _ = self.validar()
        self.assertTrue(any("consecutivas" in e for e in errores), errores)

    def test_horas_que_no_calzan(self):
        m = self.malla()
        m["semanas"][0]["horas"] = 20
        self.guardar_malla(m)
        _, errores, _ = self.validar()
        self.assertTrue(any("horas por etapa" in e for e in errores))
        self.assertTrue(any("las horas suman" in e for e in errores))

    def test_proyecto_en_semana_equivocada(self):
        m = self.malla()
        m["semanas"][1]["proyecto"], m["semanas"][2]["proyecto"] = m["semanas"][2]["proyecto"], None
        self.guardar_malla(m)
        _, errores, _ = self.validar()
        self.assertTrue(any("semana 3 debe tener proyecto" in e for e in errores))
        self.assertTrue(any("semana 2 tiene un proyecto" in e for e in errores))

    def test_campo_vacio_y_objetivo_multiple(self):
        m = self.malla()
        m["semanas"][3]["laboratorio"] = ""
        m["semanas"][4]["objetivo"] = "Explicar el loop. Construir tres herramientas."
        m["semanas"][5]["preguntas_de_repaso"] = m["semanas"][5]["preguntas_de_repaso"][:2]
        self.guardar_malla(m)
        _, errores, _ = self.validar()
        self.assertTrue(any("semana 4: el campo «laboratorio» está vacío" in e for e in errores))
        self.assertTrue(any("semana 5: el objetivo debe ser una sola oración" in e for e in errores))
        self.assertTrue(any("semana 6: debe tener 3–5 preguntas" in e for e in errores))

    def test_lectura_sin_base_es_aviso_y_con_base_es_error(self):
        m = self.malla()
        m["semanas"][0]["lectura"] = ["NO-EXISTE"]
        self.guardar_malla(m)
        _, errores, avisos = self.validar()
        self.assertEqual(errores, [])
        self.assertTrue(any("sin verificar" in a for a in avisos))
        (self.raiz / "base").mkdir()
        self.rutas.fuentes.write_text(json.dumps([{"id": "OTRA", "semanas": [1]}]), encoding="utf-8")
        _, errores, _ = self.validar()
        self.assertTrue(any("«NO-EXISTE»" in e for e in errores), errores)

    def test_fichas_parseables(self):
        self.rutas.fichas.mkdir(parents=True)
        (self.rutas.fichas / "BUENA.md").write_text(
            "# Ficha\n\n## Preguntas de práctica\n- P: ¿Qué es un agente?\n  R: Un LLM con herramientas\n  y un loop.\n"
            "- P: ¿Y un workflow?\n  R: Un camino fijo en código.\n\n## Otra sección\n- P: no cuenta\n", encoding="utf-8")
        info = tutor.parsear_ficha((self.rutas.fichas / "BUENA.md").read_text(encoding="utf-8"))
        self.assertEqual(info["preguntas"][0], ("¿Qué es un agente?", "Un LLM con herramientas y un loop."))
        self.assertEqual(len(info["preguntas"]), 2)
        self.assertIn("f-BUENA-p2", self.ctx().catalogo)
        _, errores, _ = self.validar()
        self.assertEqual(errores, [])
        (self.rutas.fichas / "MALA.md").write_text("# Sin sección\n", encoding="utf-8")
        (self.rutas.fichas / "COJA.md").write_text("## Preguntas de práctica\n- P: sin respuesta\n", encoding="utf-8")
        _, errores, _ = self.validar()
        self.assertTrue(any("MALA.md: no tiene la sección" in e for e in errores))
        self.assertTrue(any("COJA.md" in e and "no tiene «R:»" in e for e in errores))

    def test_skill_invalida(self):
        texto = self.rutas.skill.read_text(encoding="utf-8")
        self.rutas.skill.write_text(texto.replace("name: tutor-ia-agentica\n", ""), encoding="utf-8")
        self.assertTrue(any("name debe ser" in e for e in self.validar()[1]))
        self.rutas.skill.write_text(texto.replace("cómo voy", "como andamos"), encoding="utf-8")
        self.assertTrue(any("frases de disparo" in e for e in self.validar()[1]))
        self.rutas.skill.write_text(texto.replace("description: Tutor", "description: Tutor: personal"), encoding="utf-8")
        self.assertTrue(any("YAML inválido" in e for e in self.validar()[1]))
        self.rutas.skill.write_text("sin frontmatter\n", encoding="utf-8")
        self.assertTrue(any("frontmatter" in e for e in self.validar()[1]))

    def test_estado_inconsistente_y_tarjeta_huerfana(self):
        estado = json.loads(self.rutas.estado.read_text(encoding="utf-8"))
        estado["semana_actual"] = 3
        self.rutas.estado.write_text(json.dumps(estado), encoding="utf-8")
        tarjetas = json.loads(self.rutas.tarjetas.read_text(encoding="utf-8"))
        tarjetas["tarjetas"]["s99-p1"] = tutor.nueva_tarjeta(d("2026-10-05"))
        self.rutas.tarjetas.write_text(json.dumps(tarjetas), encoding="utf-8")
        _, errores, _ = self.validar()
        self.assertTrue(any("no calzan con semana_actual=3" in e for e in errores))
        self.assertTrue(any("huérfana" in e for e in errores))

    def test_documento_con_comando_inexistente(self):
        readme = self.raiz / "README.md"
        readme.write_text(readme.read_text(encoding="utf-8") + "\npython3 herramientas/tutor.py volar\n", encoding="utf-8")
        self.assertTrue(any("volar" in e for e in self.validar()[1]))

    def test_cli_validar_devuelve_1_con_errores(self):
        self.assertEqual(self.cli("validar")[0], 0)
        m = self.malla()
        m["etapas"][0]["horas"] = 30
        self.guardar_malla(m)
        self.assertEqual(self.cli("validar")[0], 1)


# ---------------------------------------------------------------------------
class TestFechasInyectadas(BaseCopia):
    def test_argumento_y_variable_de_entorno(self):
        self.assertEqual(tutor.fecha_hoy("2026-01-02"), d("2026-01-02"))
        with self.assertRaises(tutor.ErrorTutor):
            tutor.fecha_hoy("02/01/2026")
        anterior = os.environ.get("TUTOR_HOY")
        os.environ["TUTOR_HOY"] = "2026-11-03"
        try:
            self.assertEqual(tutor.fecha_hoy(), d("2026-11-03"))
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                codigo = tutor.main(["registrar", "--minutos", "20", "--nota", "desde el entorno", "--raiz", str(self.raiz)])
            self.assertEqual(codigo, 0, err.getvalue())
            self.assertEqual(self.ctx("2026-11-03").estado["sesiones"][-1]["fecha"], "2026-11-03")
        finally:
            if anterior is None:
                os.environ.pop("TUTOR_HOY", None)
            else:
                os.environ["TUTOR_HOY"] = anterior

    def test_progreso_en_otra_carpeta(self):
        otra = Path(self._tmp.name) / "repo-privado" / "progreso"
        rutas = tutor.resolver_rutas(str(self.raiz), str(otra))
        self.assertEqual(rutas.estado, otra.resolve() / "estado.json")


# ---------------------------------------------------------------------------
class TestBloqueImportar(BaseCopia):
    def test_ida_y_vuelta_idempotente(self):
        self.aprobar(1, "2026-10-07")
        _, bloque, _ = self.cli("bloque", hoy="2026-10-08")
        self.assertTrue(bloque.startswith(tutor.INICIO_BLOQUE))
        eventos = ["sesion: 2026-10-08 | 15 | micro | repasé en el celular | Si es lunes, abro el tutor",
                   "calificacion: 2026-10-08 | s01-p2 | 4",
                   "parking: 2026-10-08 | agente de voz para confirmar visitas",
                   f"aprobada: 2026-10-08 | 2 | {RUBRICA_OK} | {EVIDENCIA_OK}"]
        archivo = self.raiz / "bloque.txt"
        archivo.write_text(bloque.replace(tutor.FIN_BLOQUE, "\n".join(eventos) + "\n" + tutor.FIN_BLOQUE), encoding="utf-8")
        codigo, out, _ = self.cli("importar", archivo, hoy="2026-10-09")
        self.assertEqual(codigo, 0, out)
        ctx = self.ctx("2026-10-09")
        self.assertEqual(ctx.semana_actual, 3)
        self.assertEqual(len(ctx.estado["sesiones"]), 1)
        self.assertEqual(ctx.estado["sesiones"][0]["si_entonces"], "Si es lunes, abro el tutor")
        self.assertEqual(len(ctx.estado["parking"]), 1)
        self.assertEqual(ctx.tarjetas["tarjetas"]["s01-p2"]["historial"][-1]["calidad"], 4)
        codigo, out, _ = self.cli("importar", archivo, hoy="2026-10-09")
        self.assertEqual(codigo, 0)
        self.assertIn("0 aplicados", out)

    def test_errores_de_formato_se_reportan(self):
        archivo = self.raiz / "malo.txt"
        archivo.write_text("sesion: ayer | 15 | micro | x\naprobada: 2026-10-08 | 1 | entregable=3 | https://x.cl\n",
                           encoding="utf-8")
        codigo, out, _ = self.cli("importar", archivo, hoy="2026-10-09")
        self.assertEqual(codigo, 1)
        self.assertIn("Fecha inválida", out)
        self.assertIn("Falta puntuar", out)


# ---------------------------------------------------------------------------
class TestIntegracionBase(BaseCopia):
    def test_integrar_lecturas_prioriza_nucleo(self):
        (self.raiz / "base").mkdir()
        fuentes = [{"id": "LARGA", "semanas": [1], "nucleo": False, "minutos": 10},
                   {"id": "NUCLEO", "semanas": [1, 2], "nucleo": True, "minutos": 60},
                   {"id": "OTRA", "semanas": [2], "minutos": 5}]
        self.rutas.fuentes.write_text(json.dumps(fuentes), encoding="utf-8")
        codigo, out, _ = self.cli("integrar-lecturas")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.malla()["semanas"][0]["lectura"], [], "sin --aplicar no escribe")
        self.cli("integrar-lecturas", "--aplicar")
        m = self.malla()
        self.assertEqual(m["semanas"][0]["lectura"], ["NUCLEO", "LARGA"])
        self.assertEqual(m["semanas"][1]["lectura"], ["NUCLEO", "OTRA"])
        _, errores, _ = self.validar()
        self.assertEqual(errores, [])
        _, out, _ = self.cli("hoy")
        self.assertIn("NUCLEO", out)
        self.cli("registrar", "--minutos", 30, "--nota", "leí", "--leido", "NUCLEO")
        self.assertIn("[leída] NUCLEO", self.cli("hoy")[1])

    def test_empaquetar_skill(self):
        codigo, out, err = self.cli("empaquetar-skill")
        self.assertEqual(codigo, 0, err)
        with zipfile.ZipFile(self.raiz / "dist" / "tutor-ia-agentica.zip") as z:
            nombres = z.namelist()
        self.assertIn("tutor-ia-agentica/SKILL.md", nombres)
        self.assertIn("tutor-ia-agentica/referencias/malla.json", nombres)

    def test_panel_y_parking(self):
        self.cli("parking", "probar n8n para el correo de leads")
        self.cli("registrar", "--minutos", 30, "--nota", "primera sesión")
        codigo, _, _ = self.cli("panel")
        self.assertEqual(codigo, 0)
        html = self.rutas.panel.read_text(encoding="utf-8")
        for texto in ("<!doctype html>", "Hoja de Combate", "Semana 1", "Racha semanal", "probar n8n",
                      "prefers-color-scheme:dark"):
            self.assertIn(texto, html)
        self.assertIn("probar n8n", self.cli("parking")[1])


if __name__ == "__main__":
    unittest.main()
