"""Pruebas del motor determinista.

Responsable: Persona 1 (Charlie).

ESTADO: estas pruebas fallan a proposito. ``gasolinera.simulacion.simular``
todavia no esta implementado (Hito B). Es el paso rojo del ciclo TDD que fija
el plan: primero se escribe la prueba, se confirma el fallo esperado y
despues se implementa.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from gasolinera.contratos import (
    POLITICAS,
    POLITICA_FILA_UNICA,
    POLITICA_FILAS_INDEPENDIENTES,
    ErrorDeContrato,
)
from gasolinera.simulacion import simular

FIXTURE = Path(__file__).parent / "fixtures" / "caso_pequeno.json"


@pytest.fixture(scope="module")
def caso_pequeno() -> dict:
    """Caso calculado a mano; ver docs/modelo.md, seccion 'Caso conocido'."""
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def simular_caso(caso: dict, politica: str):
    entrada = caso["entrada"]
    return simular(
        entrada["llegadas"],
        entrada["servicios"],
        entrada["surtidores"],
        politica,
        entrada["horizonte"],
    )


def comparar_registros(obtenidos, esperados) -> None:
    assert len(obtenidos) == len(esperados)
    for obtenido, esperado in zip(obtenidos, esperados):
        contexto = f"vehiculo id={esperado['id']}"
        assert obtenido.id == esperado["id"], contexto
        assert obtenido.surtidor == esperado["surtidor"], contexto
        for campo in ("llegada", "duracion_servicio", "inicio", "fin", "espera", "permanencia"):
            assert getattr(obtenido, campo) == pytest.approx(esperado[campo]), (
                f"{contexto}, campo {campo}"
            )


def comparar_metricas(obtenidas, esperadas) -> None:
    assert obtenidas.vehiculos_atendidos == esperadas["vehiculos_atendidos"]
    assert obtenidas.espera_media == pytest.approx(esperadas["espera_media"])
    assert obtenidas.proporcion_espera == pytest.approx(esperadas["proporcion_espera"])
    assert obtenidas.espera_p95 == pytest.approx(esperadas["espera_p95"])
    assert list(obtenidas.utilizacion) == pytest.approx(esperadas["utilizacion"])


# --------------------------------------------------------------------------
# Caso conocido, calculado a mano
# --------------------------------------------------------------------------


@pytest.mark.parametrize("politica", POLITICAS)
def test_caso_conocido_reproduce_los_registros_calculados_a_mano(caso_pequeno, politica):
    resultado = simular_caso(caso_pequeno, politica)
    comparar_registros(resultado.registros, caso_pequeno["esperado"][politica]["registros"])


@pytest.mark.parametrize("politica", POLITICAS)
def test_caso_conocido_reproduce_las_metricas_calculadas_a_mano(caso_pequeno, politica):
    resultado = simular_caso(caso_pequeno, politica)
    comparar_metricas(resultado.metricas, caso_pequeno["esperado"][politica]["metricas"])


@pytest.mark.parametrize("politica", POLITICAS)
def test_el_resultado_conserva_los_parametros_de_la_corrida(caso_pequeno, politica):
    resultado = simular_caso(caso_pequeno, politica)
    assert resultado.politica == politica
    assert resultado.surtidores == caso_pequeno["entrada"]["surtidores"]
    assert resultado.horizonte == pytest.approx(caso_pequeno["entrada"]["horizonte"])


def test_las_dos_politicas_difieren_con_las_mismas_entradas(caso_pequeno):
    # Si este caso dejara de discriminar, el fixture ya no probaria nada.
    unica = simular_caso(caso_pequeno, POLITICA_FILA_UNICA)
    independientes = simular_caso(caso_pequeno, POLITICA_FILAS_INDEPENDIENTES)
    assert unica.metricas.espera_media != pytest.approx(
        independientes.metricas.espera_media
    )


# --------------------------------------------------------------------------
# Reglas de asignacion y desempate
# --------------------------------------------------------------------------


@pytest.mark.parametrize("politica", POLITICAS)
def test_con_un_surtidor_ambas_politicas_coinciden(politica):
    llegadas = [1.0, 2.0, 3.0, 4.0]
    servicios = [2.5, 1.0, 3.0, 0.5]
    resultado = simular(llegadas, servicios, 1, politica, 20.0)
    assert [registro.surtidor for registro in resultado.registros] == [0, 0, 0, 0]
    # Una sola cola y una sola fila por surtidor son el mismo sistema cuando
    # hay un unico surtidor.
    referencia = simular(llegadas, servicios, 1, POLITICA_FILA_UNICA, 20.0)
    assert [registro.inicio for registro in resultado.registros] == pytest.approx(
        [registro.inicio for registro in referencia.registros]
    )


@pytest.mark.parametrize("politica", POLITICAS)
def test_surtidores_libres_no_generan_espera(politica):
    resultado = simular([1.0, 2.0, 3.0], [1.0, 1.0, 1.0], 3, politica, 10.0)
    assert all(registro.espera == pytest.approx(0.0) for registro in resultado.registros)
    assert resultado.metricas.proporcion_espera == pytest.approx(0.0)


@pytest.mark.parametrize("politica", POLITICAS)
def test_el_primer_vehiculo_desempata_hacia_el_surtidor_de_menor_id(politica):
    resultado = simular([1.0], [1.0], 3, politica, 10.0)
    assert resultado.registros[0].surtidor == 0


@pytest.mark.parametrize("politica", POLITICAS)
def test_saturacion_con_un_surtidor_encola_en_orden_de_llegada(politica):
    resultado = simular([1.0, 2.0, 3.0], [5.0, 5.0, 5.0], 1, politica, 20.0)
    assert [registro.inicio for registro in resultado.registros] == pytest.approx(
        [1.0, 6.0, 11.0]
    )
    assert [registro.espera for registro in resultado.registros] == pytest.approx(
        [0.0, 4.0, 8.0]
    )
    assert resultado.metricas.espera_media == pytest.approx(4.0)


@pytest.mark.parametrize("politica", POLITICAS)
def test_llegadas_simultaneas_se_resuelven_por_identificador_de_vehiculo(politica):
    resultado = simular([2.0, 2.0], [3.0, 1.0], 2, politica, 10.0)
    assert [registro.id for registro in resultado.registros] == [0, 1]
    # El primero en la lista toma el surtidor de menor identificador.
    assert [registro.surtidor for registro in resultado.registros] == [0, 1]
    assert all(registro.espera == pytest.approx(0.0) for registro in resultado.registros)


@pytest.mark.parametrize("politica", POLITICAS)
def test_una_salida_simultanea_a_una_llegada_libera_el_surtidor(politica):
    # v0 termina exactamente en 3.0 y v1 llega en 3.0: no debe esperar.
    resultado = simular([1.0, 3.0], [2.0, 1.0], 1, politica, 10.0)
    assert resultado.registros[0].fin == pytest.approx(3.0)
    assert resultado.registros[1].inicio == pytest.approx(3.0)
    assert resultado.registros[1].espera == pytest.approx(0.0)


def test_filas_independientes_no_permiten_cambiar_de_fila(caso_pequeno):
    # v2 se compromete con el surtidor 0 porque tiene menos vehiculos, y se
    # queda ahi aunque el surtidor 1 se libere mucho antes (3.5 contra 11.0).
    resultado = simular_caso(caso_pequeno, POLITICA_FILAS_INDEPENDIENTES)
    v2 = resultado.registros[2]
    assert v2.surtidor == 0
    assert v2.inicio == pytest.approx(11.0)
    assert v2.espera == pytest.approx(9.0)


def test_fila_unica_asigna_al_surtidor_que_se_libera_antes(caso_pequeno):
    # Con las mismas entradas, la fila unica manda v2 al surtidor 1.
    resultado = simular_caso(caso_pequeno, POLITICA_FILA_UNICA)
    v2 = resultado.registros[2]
    assert v2.surtidor == 1
    assert v2.inicio == pytest.approx(3.5)


# --------------------------------------------------------------------------
# Cierre del horizonte
# --------------------------------------------------------------------------


def test_se_incluye_la_espera_de_quien_es_atendido_despues_del_cierre(caso_pequeno):
    resultado = simular_caso(caso_pequeno, POLITICA_FILAS_INDEPENDIENTES)
    horizonte = caso_pequeno["entrada"]["horizonte"]
    v2 = resultado.registros[2]
    assert v2.fin > horizonte
    assert v2.espera == pytest.approx(9.0)
    # Sigue contando como admitido y su espera entra al promedio.
    assert resultado.metricas.vehiculos_atendidos == 4
    assert resultado.metricas.espera_media == pytest.approx(2.5)


@pytest.mark.parametrize("politica", POLITICAS)
def test_la_utilizacion_esta_acotada_entre_cero_y_uno(caso_pequeno, politica):
    resultado = simular_caso(caso_pequeno, politica)
    assert len(resultado.metricas.utilizacion) == caso_pequeno["entrada"]["surtidores"]
    assert all(0.0 <= u <= 1.0 for u in resultado.metricas.utilizacion)


def test_la_utilizacion_recorta_el_servicio_que_cruza_el_horizonte(caso_pequeno):
    # v2 ocupa el surtidor 0 de 11.0 a 13.0, pero el horizonte cierra en 12.5:
    # solo cuentan 1.5 minutos. (10.0 + 1.5) / 12.5 = 0.92.
    resultado = simular_caso(caso_pequeno, POLITICA_FILAS_INDEPENDIENTES)
    assert resultado.metricas.utilizacion[0] == pytest.approx(0.92)


@pytest.mark.parametrize("politica", POLITICAS)
def test_un_surtidor_que_nunca_atiende_tiene_utilizacion_cero(politica):
    resultado = simular([1.0], [1.0], 3, politica, 10.0)
    assert resultado.metricas.utilizacion[1] == pytest.approx(0.0)
    assert resultado.metricas.utilizacion[2] == pytest.approx(0.0)


# --------------------------------------------------------------------------
# Casos limite y contrato
# --------------------------------------------------------------------------


@pytest.mark.parametrize("politica", POLITICAS)
def test_entrada_vacia_no_inventa_observaciones(politica):
    resultado = simular([], [], 3, politica, 10.0)
    assert resultado.registros == ()
    metricas = resultado.metricas
    assert metricas.vehiculos_atendidos == 0
    assert metricas.utilizacion == pytest.approx((0.0, 0.0, 0.0))
    # None, no 0.0: sin vehiculos la espera no es estimable.
    assert metricas.espera_media is None
    assert metricas.proporcion_espera is None
    assert metricas.espera_p95 is None


@pytest.mark.parametrize(
    ("llegadas", "servicios", "surtidores", "politica", "horizonte"),
    [
        ([1.0], [1.0], 1, "fifo", 10.0),
        ([1.0], [1.0], 0, "unica", 10.0),
        ([1.0], [1.0], 1, "unica", 0.0),
        ([1.0, 2.0], [1.0], 1, "unica", 10.0),
        ([2.0, 1.0], [1.0, 1.0], 1, "unica", 10.0),
        ([1.0], [-1.0], 1, "unica", 10.0),
        ([10.0], [1.0], 1, "unica", 10.0),
    ],
)
def test_las_entradas_invalidas_se_rechazan(llegadas, servicios, surtidores, politica, horizonte):
    with pytest.raises(ErrorDeContrato):
        simular(llegadas, servicios, surtidores, politica, horizonte)


@pytest.mark.parametrize("politica", POLITICAS)
def test_el_motor_no_modifica_las_entradas(politica):
    llegadas = np.array([1.0, 2.0, 3.0])
    servicios = np.array([4.0, 1.0, 2.0])
    copia_llegadas = llegadas.copy()
    copia_servicios = servicios.copy()

    simular(llegadas, servicios, 2, politica, 20.0)

    assert np.array_equal(llegadas, copia_llegadas)
    assert np.array_equal(servicios, copia_servicios)
    assert llegadas.flags.writeable
    assert servicios.flags.writeable


@pytest.mark.parametrize("politica", POLITICAS)
def test_el_motor_es_determinista(politica):
    # El motor no genera aleatoriedad: dos llamadas identicas deben producir
    # exactamente lo mismo, sin depender de ningun estado global.
    argumentos = ([1.0, 1.5, 2.0, 2.5], [10.0, 2.0, 2.0, 1.0], 2, politica, 12.5)
    primera = simular(*argumentos)
    np.random.seed(0)
    segunda = simular(*argumentos)
    assert primera.registros == segunda.registros
    assert primera.metricas == segunda.metricas


# --------------------------------------------------------------------------
# Invariantes de aceptacion
# --------------------------------------------------------------------------


@pytest.mark.parametrize("politica", POLITICAS)
def test_cada_vehiculo_se_atiende_exactamente_una_vez(politica):
    llegadas = [1.0, 1.0, 2.0, 3.5, 4.0, 4.0, 9.0]
    servicios = [3.0, 2.0, 0.5, 4.0, 1.0, 2.0, 6.0]
    resultado = simular(llegadas, servicios, 3, politica, 15.0)
    identificadores = [registro.id for registro in resultado.registros]
    assert identificadores == list(range(len(llegadas)))
    assert resultado.metricas.vehiculos_atendidos == len(llegadas)


@pytest.mark.parametrize("politica", POLITICAS)
def test_las_esperas_nunca_son_negativas_y_la_duracion_se_respeta(politica):
    llegadas = [1.0, 1.0, 2.0, 3.5, 4.0, 4.0, 9.0]
    servicios = [3.0, 2.0, 0.5, 4.0, 1.0, 2.0, 6.0]
    resultado = simular(llegadas, servicios, 3, politica, 15.0)
    for registro, duracion in zip(resultado.registros, servicios):
        assert registro.espera >= 0.0
        assert registro.inicio >= registro.llegada
        assert registro.fin - registro.inicio == pytest.approx(duracion)


@pytest.mark.parametrize("politica", POLITICAS)
def test_ningun_surtidor_atiende_dos_vehiculos_a_la_vez(politica):
    llegadas = [1.0, 1.0, 2.0, 3.5, 4.0, 4.0, 9.0]
    servicios = [3.0, 2.0, 0.5, 4.0, 1.0, 2.0, 6.0]
    resultado = simular(llegadas, servicios, 3, politica, 15.0)

    for surtidor in range(3):
        intervalos = sorted(
            (registro.inicio, registro.fin)
            for registro in resultado.registros
            if registro.surtidor == surtidor
        )
        for (_, fin_previo), (inicio, _) in zip(intervalos, intervalos[1:]):
            assert inicio >= fin_previo - 1e-12, f"solapamiento en el surtidor {surtidor}"


@pytest.mark.parametrize("politica", POLITICAS)
def test_los_surtidores_asignados_estan_dentro_del_rango(politica):
    resultado = simular([1.0, 1.0, 2.0], [3.0, 2.0, 1.0], 2, politica, 15.0)
    assert all(0 <= registro.surtidor < 2 for registro in resultado.registros)
