"""Pruebas del contrato compartido: tipos, unidades y validaciones.

Responsable: Persona 1 (Charlie). Estas pruebas no tocan el motor: fijan lo
que los cuatro modulos pueden dar por cierto.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from gasolinera.contratos import (
    METODO_INVERSA,
    METODO_PERCENTIL,
    METODO_RECHAZO,
    METODOS,
    PERCENTIL_ESPERA,
    POLITICA_FILA_UNICA,
    POLITICA_FILAS_INDEPENDIENTES,
    POLITICAS,
    ErrorDeContrato,
    MetricasSimulacion,
    RegistroVehiculo,
    ResultadoSimulacion,
    validar_entradas_simulacion,
    validar_parametros_generador,
)


# --------------------------------------------------------------------------
# Vocabulario cerrado
# --------------------------------------------------------------------------


def test_las_politicas_son_exactamente_dos_y_con_los_nombres_acordados():
    assert POLITICAS == ("unica", "independientes")
    assert POLITICA_FILA_UNICA == "unica"
    assert POLITICA_FILAS_INDEPENDIENTES == "independientes"


def test_los_metodos_generadores_son_exactamente_dos():
    assert METODOS == ("inversa", "rechazo")
    assert METODO_INVERSA == "inversa"
    assert METODO_RECHAZO == "rechazo"


def test_el_percentil_y_su_metodo_quedan_fijados_en_el_contrato():
    # Si alguien cambia esto, cambia el informe: debe ser una decision
    # explicita del equipo, no un efecto colateral.
    assert PERCENTIL_ESPERA == 95.0
    assert METODO_PERCENTIL == "linear"


def test_el_error_de_contrato_sigue_siendo_un_value_error():
    assert issubclass(ErrorDeContrato, ValueError)


# --------------------------------------------------------------------------
# RegistroVehiculo
# --------------------------------------------------------------------------


def test_registro_deriva_espera_y_permanencia_de_los_instantes():
    registro = RegistroVehiculo(
        id=7, llegada=2.0, duracion_servicio=3.0, surtidor=1, inicio=5.0, fin=8.0
    )
    assert registro.espera == pytest.approx(3.0)
    assert registro.permanencia == pytest.approx(6.0)


def test_registro_atendido_de_inmediato_no_espera():
    registro = RegistroVehiculo(
        id=0, llegada=4.0, duracion_servicio=1.0, surtidor=0, inicio=4.0, fin=5.0
    )
    assert registro.espera == pytest.approx(0.0)
    assert registro.permanencia == pytest.approx(1.0)


def test_registro_es_inmutable():
    registro = RegistroVehiculo(
        id=0, llegada=1.0, duracion_servicio=1.0, surtidor=0, inicio=1.0, fin=2.0
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        registro.inicio = 99.0  # type: ignore[misc]


def test_resultado_expone_los_campos_acordados():
    campos = {campo.name for campo in dataclasses.fields(ResultadoSimulacion)}
    assert campos == {"registros", "politica", "horizonte", "surtidores", "metricas"}


def test_metricas_admiten_none_cuando_no_hay_vehiculos():
    metricas = MetricasSimulacion(
        vehiculos_atendidos=0,
        espera_media=None,
        proporcion_espera=None,
        espera_p95=None,
        utilizacion=(0.0, 0.0),
    )
    # Explicitamente None, no 0.0: un cero seria una observacion inventada.
    assert metricas.espera_media is None
    assert metricas.vehiculos_atendidos == 0
    assert metricas.utilizacion == (0.0, 0.0)


# --------------------------------------------------------------------------
# validar_entradas_simulacion: casos validos
# --------------------------------------------------------------------------


def test_validacion_devuelve_arreglos_float64_normalizados():
    llegadas, servicios, surtidores, politica, horizonte = validar_entradas_simulacion(
        [1, 2, 3], [1, 1, 1], 2, "unica", 10
    )
    assert llegadas.dtype == np.float64
    assert servicios.dtype == np.float64
    assert isinstance(surtidores, int) and surtidores == 2
    assert politica == "unica"
    assert isinstance(horizonte, float) and horizonte == 10.0


def test_validacion_no_modifica_las_entradas_originales():
    llegadas_originales = np.array([1.0, 2.0, 3.0])
    servicios_originales = np.array([1.0, 1.0, 1.0])

    llegadas, servicios, *_ = validar_entradas_simulacion(
        llegadas_originales, servicios_originales, 2, "unica", 10.0
    )

    # Las copias son de solo lectura...
    assert not llegadas.flags.writeable
    assert not servicios.flags.writeable
    # ...pero los arreglos de quien llama siguen intactos y escribibles.
    assert llegadas_originales.flags.writeable
    assert servicios_originales.flags.writeable
    llegadas_originales[0] = 99.0
    assert llegadas[0] == pytest.approx(1.0)


def test_validacion_acepta_entrada_vacia():
    llegadas, servicios, *_ = validar_entradas_simulacion([], [], 3, "unica", 10.0)
    assert llegadas.size == 0
    assert servicios.size == 0


def test_validacion_acepta_llegadas_repetidas_y_servicio_cero():
    # Llegadas simultaneas y un servicio de duracion nula son casos limite
    # validos del modelo, no errores.
    llegadas, servicios, *_ = validar_entradas_simulacion(
        [2.0, 2.0, 2.0], [0.0, 1.0, 2.0], 2, "independientes", 10.0
    )
    assert llegadas.tolist() == [2.0, 2.0, 2.0]
    assert servicios[0] == pytest.approx(0.0)


def test_validacion_acepta_llegada_en_cero():
    llegadas, *_ = validar_entradas_simulacion([0.0], [1.0], 1, "unica", 5.0)
    assert llegadas[0] == pytest.approx(0.0)


def test_validacion_acepta_enteros_de_numpy_como_surtidores():
    *_, surtidores, _, _ = validar_entradas_simulacion(
        [1.0], [1.0], np.int64(4), "unica", 5.0
    )
    assert surtidores == 4


# --------------------------------------------------------------------------
# validar_entradas_simulacion: casos invalidos
# --------------------------------------------------------------------------


def test_politica_desconocida_es_rechazada():
    with pytest.raises(ErrorDeContrato, match="politica"):
        validar_entradas_simulacion([1.0], [1.0], 1, "fifo", 10.0)


@pytest.mark.parametrize("surtidores", [0, -1, 2.0, True, None, "2"])
def test_surtidores_invalidos_son_rechazados(surtidores):
    with pytest.raises(ErrorDeContrato, match="surtidores"):
        validar_entradas_simulacion([1.0], [1.0], surtidores, "unica", 10.0)


@pytest.mark.parametrize(
    "horizonte", [0.0, -5.0, float("inf"), float("nan"), None, "10"]
)
def test_horizonte_invalido_es_rechazado(horizonte):
    with pytest.raises(ErrorDeContrato, match="horizonte"):
        validar_entradas_simulacion([1.0], [1.0], 1, "unica", horizonte)


def test_longitudes_distintas_son_rechazadas():
    with pytest.raises(ErrorDeContrato, match="misma longitud"):
        validar_entradas_simulacion([1.0, 2.0], [1.0], 1, "unica", 10.0)


def test_llegadas_desordenadas_son_rechazadas():
    with pytest.raises(ErrorDeContrato, match="no decreciente"):
        validar_entradas_simulacion([3.0, 1.0], [1.0, 1.0], 1, "unica", 10.0)


def test_llegada_negativa_es_rechazada():
    with pytest.raises(ErrorDeContrato, match="negativo"):
        validar_entradas_simulacion([-1.0, 2.0], [1.0, 1.0], 1, "unica", 10.0)


def test_llegada_exactamente_en_el_horizonte_es_rechazada():
    # El intervalo de admision es [0, horizonte), con extremo derecho abierto.
    with pytest.raises(ErrorDeContrato, match=r"\[0, 10.0\)"):
        validar_entradas_simulacion([10.0], [1.0], 1, "unica", 10.0)


def test_llegada_posterior_al_horizonte_es_rechazada():
    with pytest.raises(ErrorDeContrato):
        validar_entradas_simulacion([1.0, 20.0], [1.0, 1.0], 1, "unica", 10.0)


def test_servicio_negativo_es_rechazado():
    with pytest.raises(ErrorDeContrato, match="servicios"):
        validar_entradas_simulacion([1.0], [-1.0], 1, "unica", 10.0)


@pytest.mark.parametrize("valor", [float("nan"), float("inf")])
def test_valores_no_finitos_son_rechazados(valor):
    with pytest.raises(ErrorDeContrato, match="no finitos"):
        validar_entradas_simulacion([1.0, valor], [1.0, 1.0], 1, "unica", 100.0)
    with pytest.raises(ErrorDeContrato, match="no finitos"):
        validar_entradas_simulacion([1.0, 2.0], [1.0, valor], 1, "unica", 100.0)


def test_arreglo_bidimensional_es_rechazado():
    with pytest.raises(ErrorDeContrato, match="unidimensional"):
        validar_entradas_simulacion([[1.0, 2.0]], [[1.0, 2.0]], 1, "unica", 10.0)


# --------------------------------------------------------------------------
# validar_parametros_generador
# --------------------------------------------------------------------------


def test_parametros_de_generador_validos_se_normalizan():
    rng = np.random.default_rng(0)
    metodo, tasa, cantidad = validar_parametros_generador("inversa", 2, np.int64(5), rng)
    assert metodo == "inversa"
    assert isinstance(tasa, float) and tasa == 2.0
    assert isinstance(cantidad, int) and cantidad == 5


def test_cantidad_cero_es_valida():
    rng = np.random.default_rng(0)
    _, _, cantidad = validar_parametros_generador("rechazo", 1.0, 0, rng)
    assert cantidad == 0


def test_metodo_generador_desconocido_es_rechazado():
    rng = np.random.default_rng(0)
    with pytest.raises(ErrorDeContrato, match="metodo"):
        validar_parametros_generador("box-muller", 1.0, 10, rng)


@pytest.mark.parametrize("tasa", [0.0, -1.0, float("inf"), float("nan"), None])
def test_tasa_invalida_es_rechazada(tasa):
    rng = np.random.default_rng(0)
    with pytest.raises(ErrorDeContrato, match="tasa"):
        validar_parametros_generador("inversa", tasa, 10, rng)


@pytest.mark.parametrize("cantidad", [-1, 1.5, True, None])
def test_cantidad_invalida_es_rechazada(cantidad):
    rng = np.random.default_rng(0)
    with pytest.raises(ErrorDeContrato, match="cantidad"):
        validar_parametros_generador("inversa", 1.0, cantidad, rng)


@pytest.mark.parametrize("rng", [None, 12345, np.random.RandomState(0)])
def test_rng_debe_ser_un_generator_de_numpy(rng):
    # Recibir la semilla en vez del generador llevaria a resembrar por dentro
    # y a perder la reproducibilidad coordinada del experimento.
    with pytest.raises(ErrorDeContrato, match="rng"):
        validar_parametros_generador("inversa", 1.0, 10, rng)
