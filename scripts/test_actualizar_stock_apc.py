import pytest

import actualizar_stock_apc as a


def test_validar_entrada_apc_detiene_pagina_de_error_antes_de_los_filtros():
    with pytest.raises(RuntimeError, match="página de error"):
        a.validar_entrada_apc("https://provider.autoprocloud.com/mc/Shared/Show_Error.aspx")


def test_validar_entrada_apc_acepta_ruta_normal():
    a.validar_entrada_apc("https://provider.autoprocloud.com/mc/mobile/inicio.aspx")
