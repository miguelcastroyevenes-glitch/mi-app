import datetime as dt

import actualizar_zonal as a
import openpyxl


def test_limpio_normaliza_espacios_y_nulos():
    assert a.limpio("  Nuevo\n  2008  ") == "Nuevo 2008"
    assert a.limpio(None) == ""


def test_fecha_de_acepta_formatos_y_descarta_fechas_invalidas():
    assert a.fecha_de("Stock al 7.10.26") == dt.date(2026, 10, 7)
    assert a.fecha_de("corte 07-10-2026") == dt.date(2026, 10, 7)
    assert a.fecha_de("sin fecha") is None
    assert a.fecha_de("al 31/02/2026") is None


def test_cant_txt_convierte_x_numeros_y_vacios():
    assert a.cant_txt("X") == "+10"
    assert a.cant_txt(" 2.0 ") == "2"
    assert a.cant_txt(0) is None
    assert a.cant_txt(-1) is None
    assert a.cant_txt("") is None
    assert a.cant_txt("texto") is None


def test_cant_txt_no_acepta_booleanos_como_cantidad():
    assert a.cant_txt(True) is None


def test_zonal_actual_y_escribir_reemplazan_el_bloque():
    html = '<script>\nconst zonal = {"peugeot":null,"citroen":null};\nconst otro = 1;\n</script>\n'
    zonal = a.zonal_actual(html)
    assert zonal == {"peugeot": None, "citroen": None}
    nuevo = {"peugeot": {"fecha": "07-10-2026"}, "citroen": None}
    escrito = a.escribir(html, nuevo)
    assert a.zonal_actual(escrito) == nuevo
    assert "const otro = 1;" in escrito


def test_zonal_actual_convierte_el_formato_js_antiguo():
    html = """<script>
const zonal = {citroen:{fecha:"07-10-2026",items:[{modelo:"C3",colores:[{color:"ROJO",cant:"X"}]}]},peugeot:null};
</script>
"""
    zonal = a.zonal_actual(html)
    assert zonal["citroen"]["fecha"] == "07-10-2026"
    assert zonal["citroen"]["fuente"] == "planilla cargada a mano"
    assert zonal["citroen"]["chile"][0]["colores"][0]["cant"] == "+10"
    assert zonal["citroen"]["transito"] == []
    assert zonal["peugeot"] is None


def test_leer_citroen_acepta_uno_dos_y_tres_bloques():
    for bloques in (1, 2, 3):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Citroen"
        for i in range(bloques):
            inicio = 1 + i * 4
            ws.cell(3, inicio, "Modelo/Versión")
            ws.cell(3, inicio + 1, f"COLOR {i}")
            if i:
                ws.cell(3, inicio + 2, "ENTERGAS DESDE")  # error real del envío 24-11
                ws.merge_cells(start_row=4, start_column=inicio + 2, end_row=5, end_column=inicio + 2)
                ws.cell(4, inicio + 2, f"2{i}-12-2026")
            ws.cell(4, inicio, f"Modelo {i}")
            ws.cell(4, inicio + 1, i + 1)

        leido = a.leer_citroen(wb)

        assert [x["modelo"] for x in leido["chile"]] == ["Modelo 0"]
        assert [x["modelo"] for x in leido["transito"]] == [f"Modelo {i}" for i in range(1, bloques)]
        assert [x["entrega"] for x in leido["transito"]] == [f"2{i}-12-2026" for i in range(1, bloques)]
