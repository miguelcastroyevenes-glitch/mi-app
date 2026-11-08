import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import stock_quilin_vigilante as v


def correo(subject="Re: Stock Quilín para conteo · lunes 27-10-2026", sender=v.MIGUEL, attachments=None):
    return {"subject": subject, "sender": sender, "attachments": attachments if attachments is not None else [{"extension": ".jpeg", "hidden": False, "inline": False}]}


def test_respuesta_image_jpeg_dispara():
    assert len(v.seleccionar_respuestas([correo()], set())) == 1


def test_duplicado_estado_real_y_reenvio_no_disparan(tmp_path, monkeypatch):
    estado = tmp_path / "vigilante_trabajados.json"
    monkeypatch.setattr(v, "ESTADO", estado)
    v.guardar_estado({"trabajados": ["27-10-2026"], "avisos": []}, simular=False)
    trabajados = set(v.cargar_estado()["trabajados"])
    correos = [correo(), correo(), correo("RV: Stock Quilín para conteo · lunes 27-10-2026")]
    assert v.seleccionar_respuestas(correos, trabajados) == []
    assert len(v.seleccionar_respuestas(correos, set())) == 1


def test_correos_que_no_disparan():
    casos = [
        correo(attachments=[]),
        correo(attachments=[{"extension": ".png", "hidden": True, "inline": True}]),
        correo(sender="otro@pompeyo.cl"),
        correo("Re: otra cosa"),
        correo("Stock Quilín para conteo · lunes 27-10-2026", attachments=[{"extension": ".xlsx", "hidden": False, "inline": False}]),
    ]
    assert all(not v.seleccionar_respuestas([caso], set()) for caso in casos)


def test_aviso_mediodia_se_reserva_una_sola_vez():
    estado = {"trabajados": [], "avisos": []}
    hoy = v.dt.date(2026, 10, 28)
    assert not v.reservar_aviso(estado, hoy, "11:59", True, False)
    assert v.reservar_aviso(estado, hoy, "12:00", True, False)
    assert not v.reservar_aviso(estado, hoy, "12:00", True, False)
    assert not v.reservar_aviso({"trabajados": [], "avisos": []}, hoy, "12:00", True, True)


def test_codigo_ia_fuera_excel_se_ignora_por_funcion_del_programa():
    marcas, dudosas, ignorados = v.filtrar_lectura(
        {"filas": [{"codigo": "FUERA", "marca": "X"}]}, {"VJ1": {}}
    )
    assert marcas == set()
    assert dudosas == set()
    assert ignorados == ["FUERA"]


def test_validar_destinatarios_rechaza_cualquier_otro():
    v.validar_destinatarios([v.MIGUEL])
    with pytest.raises(RuntimeError):
        v.validar_destinatarios(["otro@pompeyo.cl"])
    with pytest.raises(RuntimeError):
        v.validar_destinatarios([v.MIGUEL, "otro@pompeyo.cl"])


# Formas tomadas de Roma en solo lectura el 28-10-2026 (ventas 214303, 220488, 220843, 223559).
def test_elegir_venta_salta_anulada_y_calza_por_chasis():
    ventas = [
        {"ID": "214303", "Vin": "VR7XXXXXXXVB502279", "EstadoVenta": "ANULADA", "nombre_Vendedor": "DANIEL"},
        {"ID": "220488", "Vin": "VR7XXXXXXXVB502279", "EstadoVenta": "VIGENTE", "nombre_Vendedor": "TERRY"},
        {"ID": "999", "Vin": "VR7XXXXXXXVB502279X", "EstadoVenta": "FACTURADA", "nombre_Vendedor": "OTRO"},
    ]
    assert v.elegir_venta(ventas, "VB502279")["ID"] == "220488"
    assert v.elegir_venta(ventas[:1], "VB502279") is None


def test_elegir_venta_prefiere_facturada():
    ventas = [{"ID": "1", "Vin": "AAVJ011267", "EstadoVenta": "VIGENTE"}, {"ID": "2", "Vin": "AAVJ011267", "EstadoVenta": "FACTURADA"}]
    assert v.elegir_venta(ventas, "VJ011267")["ID"] == "2"


def test_acta_solo_cuenta_si_hay_archivo_tipo_32():
    tipos = '[{"Tipo":"Acta de entrega firmada","ID":"32"},{"Tipo":"Cedula","ID":"5"}]'
    assert v.tiene_acta([tipos, '[{"Tipo":"Cedula","ArchivoTipoID":"5"}]']) is False
    assert v.tiene_acta([tipos, '[{"Tipo":"Acta de entrega firmada","ArchivoTipoID":"32"}]']) is True
    assert v.tiene_acta([tipos, "[]"]) is False
    with pytest.raises(RuntimeError):
        v.tiene_acta({"raro": 1})


def test_manda_la_ultima_entrega_y_el_motivo_sale_de_la_respuesta():
    rechazada = {"ID": "2140887", "Tipo": "Entrega Vehículo", "Estado": "RECHAZADA", "FechaCreacion": "2026-10-21 13:25:20"}
    aprobada = {"ID": "2143607", "Tipo": "Entrega Vehículo", "Estado": "CONFIRMADA", "FechaCreacion": "2026-10-26 11:50:09"}
    otra = {"ID": "1", "Tipo": "Solicitud de Confirmacion", "Estado": "RECHAZADA", "FechaCreacion": "2026-10-27 10:00:00"}
    respuestas = lambda sid: [{"Accion": "RECHAZADO", "Comentario": "Saldo negativo. Favor regularizar. Saludos"}]
    assert v.estado_sin_acta(v.ultima_entrega([rechazada, aprobada, otra]), respuestas) == "sin acta · entrega aprobada"
    assert v.estado_sin_acta(v.ultima_entrega([rechazada, otra]), respuestas) == "sin acta · entrega rechazada: Saldo negativo. Favor regularizar. Saludos"
    assert v.estado_sin_acta(v.ultima_entrega([otra]), respuestas) == "sin acta · entrega nunca pedida"


AUTOS_1B = {c: {"fila": i + 5, "modelo": "M", "rev": 10} for i, c in enumerate(
    ["VB502279", "VB514033", "VB504132", "VB501159", "VB504623", "VMC71823", "VZ000876", "VN000361",
     "VN000364", "VN000575", "VJ009742", "VJ009095", "VJ000706", "VJ008167", "VS003978", "VS003079", "VS005013"])}


def test_dos_x_y_quince_vacios_dan_dos_faltantes_sin_dudas():
    filas = [{"codigo": c, "marca": "X" if c in ("VMC71823", "VZ000876") else "vacio"} for c in AUTOS_1B]
    marcas, dudosas, ignorados = v.filtrar_lectura({"filas": filas}, AUTOS_1B)
    assert marcas == {"VMC71823", "VZ000876"} and dudosas == set() and ignorados == []


def test_texto_faltan_suma_el_auto():
    hallados, fuera = v.codigos_de_texto("faltan VB502279 y vj000706\n\nsaludos", AUTOS_1B)
    assert hallados == {"VB502279", "VJ000706"} and fuera == []


def test_chasis_completo_en_texto_se_reconoce():
    hallados, _ = v.codigos_de_texto("falta el 935CEFCE0VB502279", AUTOS_1B)
    assert hallados == {"VB502279"}


def test_codigo_fuera_de_la_hoja_se_ignora():
    hallados, fuera = v.codigos_de_texto("faltan VB999999", AUTOS_1B)
    assert hallados == set() and fuera == ["VB999999"]


def test_texto_citado_no_se_lee():
    cuerpo = "listo\r\n\r\nDe: Miguel Castro\r\nEnviado el: miércoles\r\nVB502279 VJ000706"
    assert v.codigos_de_texto(cuerpo, AUTOS_1B) == (set(), [])
    cuerpo2 = "ok\n________________________________\nFrom: robot\nVB502279"
    assert v.codigos_de_texto(cuerpo2, AUTOS_1B)[0] == set()


def test_firma_iphone_corta_el_citado():
    cuerpo = "faltan VJ000706

Enviado desde mi iPhone

VB502279"
    assert v.codigos_de_texto(cuerpo, AUTOS_1B)[0] == {"VJ000706"}
    assert v.codigos_de_texto("ok
Sent from my iPhone
VB502279", AUTOS_1B)[0] == set()
