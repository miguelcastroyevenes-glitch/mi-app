import vitrina_quilin as v


def auto(marca, modelo, estado="Disponible", bodega="KAR-LOGISTICS", vin="VR3XXXXXXXX000001", dias=10,
         dealer="DISPONIBLE", version="", color="GRIS"):
    return {"Marca": marca, "Modelo": modelo, "Estado AutoPro": estado, "Bodega": bodega, "Numero Chasis": vin,
            "Días Stock": str(dias), "Estado Dealer": dealer, "Versión": version, "Color Exterior": color}


def cupo(cupos, nombre):
    return next(c for c in cupos if c.nombre == nombre)


def test_hay_16_cupos():
    assert len(v.CUPOS) == 16


def test_cupo_libre_y_vendido():
    quilin = [auto("PEUGEOT", "Nuevo 2008", bodega="STOCK PEUGEOT QUILIN"),
              auto("PEUGEOT", "NUEVO 3008", estado="Vendido", bodega="STOCK PEUGEOT QUILIN")]
    kar = [auto("PEUGEOT", "NUEVO 3008", vin="A1", dias=5), auto("PEUGEOT", "NUEVO 3008", vin="A2", dias=90)]
    cupos, _ = v.cruzar(quilin, kar, [])
    assert cupo(cupos, "2008").estado == "libre"
    c = cupo(cupos, "3008")
    assert c.estado == "pedir" and [v.vin_de(f) for f in c.candidatos] == ["A2", "A1"]  # más días primero


def test_pareja_de_furgones():
    quilin = [auto("CITROEN", "JUMPER", bodega="STOCK CITROEN QUILIN")]
    kar = [auto("PEUGEOT", "Boxer", vin="B1")]
    cupos, _ = v.cruzar(quilin, kar, [])
    assert cupo(cupos, "Jumper o Boxer").estado == "libre"
    cupos, _ = v.cruzar([], kar, [])
    assert cupo(cupos, "Jumper o Boxer").estado == "pedir"


def test_excepciones_no_se_piden_solas():
    kar = [auto("PEUGEOT", "Landtrek"), auto("PEUGEOT", "Rifter"), auto("CITROEN", "C5 Aircross")]
    cupos, desconocidos = v.cruzar([], kar, [])
    assert all(not any(v.modelo_de(f) and v.modelo_de(f).cupo == c.nombre for f in kar) for c in cupos)
    assert desconocidos == []


def test_ya_pedido_solo_si_el_chasis_sigue_en_kar():
    kar = [auto("PEUGEOT", "Nuevo 208", vin="C1")]
    sol = [{"ID": "99", "FechaCreacion": "2026-11-01", "vin": "C1", "EstadoTxt": "PENDIENTE", "BodegaDestino": "STOCK CITROEN QUILIN"}]
    cupos, _ = v.cruzar([], kar, sol)
    assert cupo(cupos, "208").estado == "ya pedido"
    sol[0]["vin"] = "OTRO"  # el auto ya salió de KAR: se vuelve a pedir
    cupos, _ = v.cruzar([], kar, sol)
    assert cupo(cupos, "208").estado == "pedir"


def test_fuera_de_kar_no_se_pide():
    kar = [auto("PEUGEOT", "Nuevo 308", bodega="EN BARCO")]
    cupos, _ = v.cruzar([], kar, [])
    assert cupo(cupos, "308").estado == "no hay en KAR"


def test_rechazo_y_reintento():
    cands = [auto("PEUGEOT", "Nuevo 2008", vin="D1"), auto("PEUGEOT", "Nuevo 2008", vin="D2")]
    respuestas = iter([{"type": "0", "message": "vin ya se encuentra tomado en otra solicitud."}, {"type": "1"}])
    r = v.pedir("2008", cands, lambda f: next(respuestas), escribir=True)
    assert r["resultado"] == "pedido" and v.vin_de(r["fila"]) == "D2" and r["tomados"][0][0] == "D1"


def test_ensayo_no_escribe():
    llamadas = []
    r = v.pedir("2008", [auto("PEUGEOT", "Nuevo 2008")], lambda f: llamadas.append(f), escribir=False)
    assert r["resultado"] == "se pediría" and llamadas == []


class RomaFalsa:
    def __init__(self, caida=False):
        self.caida, self.creados = caida, []

    def solicitudes(self):
        return []

    def crear(self, fila):
        if self.caida:
            raise v.RomaRaro("CrearSolTrasladoNoVenta: Roma respondió algo inesperado")
        self.creados.append(fila); return {"type": "1"}


def test_sesion_caida_se_detiene_y_avisa():
    kar = [auto("PEUGEOT", "Nuevo 208", vin="E1"), auto("PEUGEOT", "Nuevo 308", vin="E2")]
    texto = v.correr(True, roma=RomaFalsa(caida=True), descargas=([], kar))
    assert "no pedir a ciegas" in texto


def test_bloque_nunca_muestra_costos():
    kar = [{**auto("PEUGEOT", "Nuevo 208", vin="F1"), "Precio Compra Total": "12345678", "Bono": "999", "Unidad Margen": "555"}]
    texto = v.correr(False, roma=RomaFalsa(), descargas=([], kar))
    assert "12345678" not in texto and "999" not in texto and "555" not in texto
    assert "ENSAYO" in texto and "F1" in texto


def test_dictado_respeta_version_y_aircross():
    kar = [auto("PEUGEOT", "Nuevo 2008", vin="G1", version="2008 Allure", dias=90),
           auto("PEUGEOT", "Nuevo 2008", vin="G2", version="2008 GT", dias=5),
           auto("CITROEN", "C5 Aircross", vin="G3")]
    nombre, cands = v.candidatos_dictado("2008 GT", kar)
    assert [v.vin_de(f) for f in cands] == ["G2"]
    nombre, cands = v.candidatos_dictado("Aircross", kar)
    assert nombre.startswith("C5 Aircross") and [v.vin_de(f) for f in cands] == ["G3"]
    texto = v.correr(False, dictado=["2008 GT", "Traveller"], roma=RomaFalsa(), descargas=([], kar))
    assert "G2" in texto and "Traveller: no hay en KAR" in texto
