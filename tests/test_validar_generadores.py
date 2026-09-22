"""Pruebas de la comparacion de los dos metodos de generacion."""

import json

import numpy as np
import pytest

from scripts.validar_generadores import (
    CONFIG_POR_OMISION,
    cargar_config,
    medir_aceptacion,
    medir_ajuste,
    medir_tiempos,
)

#: Configuracion minima: la suite no debe tardar por culpa del bucle de rechazo.
CONFIG_CORTA = {
    "tasas": [1.0, 2.0],
    "cantidad_ajuste": 500,
    "cantidad_aceptacion": 2000,
    "tamanos_rendimiento": [100, 200],
    "repeticiones_rendimiento": 2,
    "semilla_raiz": 7,
    "alpha": 0.05,
}


def test_cargar_config_usa_los_valores_por_omision(tmp_path):
    ruta = tmp_path / "escenarios.json"
    ruta.write_text(json.dumps({"replicas": 30}), encoding="utf-8")

    config = cargar_config(ruta)

    assert config == CONFIG_POR_OMISION


def test_cargar_config_respeta_lo_que_trae_el_json(tmp_path):
    ruta = tmp_path / "escenarios.json"
    ruta.write_text(
        json.dumps({"generadores": {"tasas": [5.0], "semilla_raiz": 99}}),
        encoding="utf-8",
    )

    config = cargar_config(ruta)

    assert config["tasas"] == [5.0]
    assert config["semilla_raiz"] == 99
    # Lo que no se especifica se completa, no se pierde.
    assert config["cantidad_ajuste"] == CONFIG_POR_OMISION["cantidad_ajuste"]


def test_cargar_config_sin_archivo_no_falla(tmp_path):
    config = cargar_config(tmp_path / "no_existe.json")

    assert config == CONFIG_POR_OMISION


def test_ajuste_cubre_los_dos_metodos_y_todas_las_tasas():
    filas, series = medir_ajuste(CONFIG_CORTA)

    assert len(filas) == 4  # 2 metodos x 2 tasas
    assert {f["metodo"] for f in filas} == {"inversa", "rechazo"}
    assert {f["tasa"] for f in filas} == {1.0, 2.0}
    assert len(series) == 4

    for fila in filas:
        assert fila["n"] == CONFIG_CORTA["cantidad_ajuste"]
        assert 0.0 <= fila["p_valor"] <= 1.0
        assert fila["ks_estadistico"] >= 0.0
        # La media teorica es 1/tasa, no la tasa.
        assert fila["media_teorica"] == pytest.approx(1.0 / fila["tasa"])


def test_ajuste_devuelve_cdf_utilizable_para_graficar():
    _, series = medir_ajuste(CONFIG_CORTA)

    for serie in series:
        x = np.asarray(serie["x"])
        assert x.size == CONFIG_CORTA["cantidad_ajuste"]
        # La CDF empirica debe ser no decreciente y terminar en 1.
        empirica = np.asarray(serie["cdf_empirica"])
        assert np.all(np.diff(empirica) >= 0)
        assert empirica[-1] == pytest.approx(1.0)
        assert np.all(np.diff(x) >= 0)


def test_aceptacion_ronda_el_valor_teorico():
    """La aceptacion teorica es 1/M = 0.5 con la propuesta Exp(tasa/2)."""
    filas = medir_aceptacion(CONFIG_CORTA)

    assert len(filas) == 2
    for fila in filas:
        assert fila["muestras_aceptadas"] == CONFIG_CORTA["cantidad_aceptacion"]
        assert fila["candidatos_generados"] >= fila["muestras_aceptadas"]
        assert fila["tasa_aceptacion_teorica"] == 0.5
        # Con 2000 muestras la holgura es amplia a proposito: la prueba
        # verifica el orden de magnitud, no hace inferencia estadistica.
        assert fila["tasa_aceptacion_observada"] == pytest.approx(0.5, abs=0.05)


def test_aceptacion_reporta_cuatro_uniformes_por_muestra():
    """Es el costo intrinseco del rechazo: 2 candidatos x 2 uniformes."""
    filas = medir_aceptacion(CONFIG_CORTA)

    for fila in filas:
        assert fila["uniformes_por_muestra"] == pytest.approx(
            2.0 * fila["candidatos_por_muestra"]
        )
        assert fila["uniformes_por_muestra"] == pytest.approx(4.0, abs=0.4)


def test_tiempos_cubren_los_dos_metodos_y_declaran_vectorizacion():
    filas = medir_tiempos(CONFIG_CORTA)

    assert len(filas) == 4  # 2 metodos x 2 tamanos
    for fila in filas:
        assert fila["mediana_s"] > 0.0
        assert fila["minimo_s"] <= fila["mediana_s"] <= fila["maximo_s"]
        assert fila["repeticiones"] == CONFIG_CORTA["repeticiones_rendimiento"]
        assert fila["microsegundos_por_muestra"] > 0.0
        # Se declara explicitamente cual metodo esta vectorizado: sin eso, la
        # comparacion de tiempos se malinterpreta como costo del metodo.
        assert fila["vectorizado"] is (fila["metodo"] == "inversa")


def test_no_se_fija_ningun_umbral_de_velocidad():
    """No se afirma que un metodo sea mas rapido: eso depende de la maquina.

    Las pruebas solo comprueban que la medicion existe y es coherente. El
    plan del proyecto prohibe umbrales rigidos de velocidad.
    """
    filas = medir_tiempos(CONFIG_CORTA)

    assert all(f["desviacion_s"] >= 0.0 for f in filas)
