import numpy as np
import pytest

from gasolinera.generadores import generar_exponenciales
from gasolinera.validacion import (
    estadisticos_exponenciales,
    medir_rendimiento,
    prueba_bondad_ajuste,
    tasa_aceptacion_observada,
)


def test_estadisticos_exponenciales_se_ajustan_a_la_media_y_varianza_esperadas():
    rng = np.random.default_rng(123)
    muestras = generar_exponenciales("inversa", 0.7, 2000, rng)

    resumen = estadisticos_exponenciales(muestras, 0.7)

    assert resumen["media_observada"] > 0.0
    assert resumen["varianza_observada"] > 0.0
    assert abs(resumen["media_observada"] - (1.0 / 0.7)) < 0.25
    assert abs(resumen["varianza_observada"] - (1.0 / (0.7 ** 2))) < 0.6


def test_prueba_bondad_ajuste_informa_estadistico_y_p_valor():
    rng = np.random.default_rng(321)
    muestras = generar_exponenciales("inversa", 1.5, 5000, rng)

    resultado = prueba_bondad_ajuste(muestras, 1.5)

    assert "statistic" in resultado
    assert "p_value" in resultado
    assert 0.0 <= resultado["p_value"] <= 1.0
    assert resultado["statistic"] >= 0.0


def test_tasa_aceptacion_observada_retorna_ratio_entre_aceptadas_y_candidatos():
    aceptadas = 8
    candidatos = 16

    assert tasa_aceptacion_observada(candidatos, aceptadas) == pytest.approx(0.5)


def test_medir_rendimiento_devuelve_mediana_y_dispersion():
    def f(x):
        return np.sum(np.arange(x, dtype=np.float64))

    resumen = medir_rendimiento(f, 2000, repeticiones=3)

    assert "mediana" in resumen
    assert "desviacion_estandar" in resumen
    assert resumen["mediana"] > 0.0
    assert resumen["desviacion_estandar"] >= 0.0
