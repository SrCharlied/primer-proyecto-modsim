"""Pruebas de los generadores exponenciales de Denis."""

import numpy as np
import pytest

from gasolinera.contratos import (
    ErrorDeContrato,
    METODO_INVERSA,
    METODO_RECHAZO,
)

from gasolinera.generadores import (
    generar_exponenciales,
    generar_rechazo_con_estadisticas,
)


@pytest.mark.parametrize(
    "metodo",
    [METODO_INVERSA, METODO_RECHAZO],
)
def test_devuelve_arreglo_con_longitud_correcta(metodo):

    rng = np.random.default_rng(123)

    muestras = generar_exponenciales(
        metodo,
        0.5,
        100,
        rng,
    )

    assert isinstance(muestras, np.ndarray)
    assert muestras.shape == (100,)
    assert muestras.dtype == np.float64
    assert np.all(np.isfinite(muestras))
    assert np.all(muestras >= 0.0)


@pytest.mark.parametrize(
    "metodo",
    [METODO_INVERSA, METODO_RECHAZO],
)
def test_cantidad_cero_devuelve_arreglo_vacio(metodo):

    rng = np.random.default_rng(123)

    muestras = generar_exponenciales(
        metodo,
        1.0,
        0,
        rng,
    )

    assert muestras.shape == (0,)
    assert muestras.dtype == np.float64


@pytest.mark.parametrize(
    "metodo",
    [METODO_INVERSA, METODO_RECHAZO],
)
def test_misma_semilla_reproduce_la_misma_muestra(metodo):

    a = generar_exponenciales(
        metodo,
        0.8,
        50,
        np.random.default_rng(2026),
    )

    b = generar_exponenciales(
        metodo,
        0.8,
        50,
        np.random.default_rng(2026),
    )

    assert np.array_equal(a, b)


@pytest.mark.parametrize(
    "metodo",
    [METODO_INVERSA, METODO_RECHAZO],
)
def test_el_generador_no_reinicia_la_semilla(metodo):

    rng = np.random.default_rng(55)

    primera = generar_exponenciales(
        metodo,
        1.0,
        20,
        rng,
    )

    segunda = generar_exponenciales(
        metodo,
        1.0,
        20,
        rng,
    )

    assert not np.array_equal(primera, segunda)


@pytest.mark.parametrize(
    ("metodo", "tasa", "cantidad", "rng"),
    [
        (
            "otro",
            1.0,
            10,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            0.0,
            10,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            -1.0,
            10,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            np.inf,
            10,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            np.nan,
            10,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            1.0,
            -1,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            1.0,
            3.5,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            1.0,
            True,
            np.random.default_rng(1),
        ),
        (
            METODO_INVERSA,
            1.0,
            10,
            None,
        ),
    ],
)
def test_parametros_invalidos_se_rechazan(
    metodo,
    tasa,
    cantidad,
    rng,
):

    with pytest.raises(ErrorDeContrato):
        generar_exponenciales(
            metodo,
            tasa,
            cantidad,
            rng,
        )


def test_rechazo_cuenta_intentos_y_puede_rechazar_antes_de_aceptar():

    rng = np.random.default_rng(5)

    muestras, candidatos = generar_rechazo_con_estadisticas(
        1.0,
        1,
        rng,
    )

    assert muestras.shape == (1,)
    assert candidatos == 2


def test_rechazo_vacio_no_gasta_numeros_aleatorios():

    rng = np.random.default_rng(99)
    referencia = np.random.default_rng(99)

    muestras, candidatos = generar_rechazo_con_estadisticas(
        1.0,
        0,
        rng,
    )

    assert muestras.shape == (0,)
    assert candidatos == 0

    assert rng.random() == referencia.random()