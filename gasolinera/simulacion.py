"""Motor determinista de la gasolinera.

Responsable: Persona 1 (Charlie).

El motor recibe las llegadas y las duraciones **ya sorteadas** y no genera
aleatoriedad propia. Esa separacion es lo que permite pasar exactamente las
mismas entradas a las dos politicas dentro de una replica y comparar sin
ruido adicional.

Las reglas de asignacion, desempate y cierre estan en docs/modelo.md. El caso
calculado a mano que las define operativamente esta en
tests/fixtures/caso_pequeno.json.
"""

from __future__ import annotations

from bisect import bisect_right
from typing import Any

import numpy as np

from gasolinera.contratos import (
    METODO_PERCENTIL,
    PERCENTIL_ESPERA,
    POLITICA_FILA_UNICA,
    MetricasSimulacion,
    RegistroVehiculo,
    ResultadoSimulacion,
    validar_entradas_simulacion,
)

__all__ = ["calcular_metricas", "simular"]

#: Una asignacion resuelta: (surtidor, inicio, fin).
_Asignacion = tuple[int, float, float]


# --------------------------------------------------------------------------
# Politicas de asignacion
# --------------------------------------------------------------------------


def _asignar_fila_unica(
    llegadas: np.ndarray, servicios: np.ndarray, surtidores: int
) -> list[_Asignacion]:
    """Una sola cola alimenta a todos los surtidores.

    Cada vehiculo va al surtidor que se libera antes. El empate se resuelve
    por el menor identificador de surtidor.
    """
    disponibilidad = [0.0] * surtidores
    asignaciones: list[_Asignacion] = []

    for llegada, duracion in zip(llegadas, servicios):
        llegada = float(llegada)
        # La clave (disponibilidad, id) deja el desempate a la vista en vez
        # de depender de que min() devuelva el primer minimo.
        surtidor = min(range(surtidores), key=lambda k: (disponibilidad[k], k))
        inicio = max(llegada, disponibilidad[surtidor])
        fin = inicio + float(duracion)
        disponibilidad[surtidor] = fin
        asignaciones.append((surtidor, inicio, fin))

    return asignaciones


def _asignar_filas_independientes(
    llegadas: np.ndarray, servicios: np.ndarray, surtidores: int
) -> list[_Asignacion]:
    """Cada surtidor tiene su propia cola y no se permite cambiar de fila.

    Al llegar, el vehiculo cuenta cuantos vehiculos de cada surtidor terminan
    **despues** de este instante (incluido el que esta siendo atendido) y se
    forma en la fila mas corta; el empate se resuelve por el menor
    identificador de surtidor. Despues se queda ahi, aunque otra fila se
    libere antes.

    La decision observa **cantidad de vehiculos, no duraciones futuras**: un
    conductor ve cuantos autos hay delante, no cuanto va a tardar cada uno.
    """
    # Fines de servicio ya asignados a cada surtidor. Quedan ordenados de
    # forma no decreciente porque cada servicio empieza en el fin del
    # anterior o despues, y las duraciones son no negativas.
    fines: list[list[float]] = [[] for _ in range(surtidores)]
    ultimo_fin = [0.0] * surtidores
    asignaciones: list[_Asignacion] = []

    for llegada, duracion in zip(llegadas, servicios):
        llegada = float(llegada)
        # Al estar ordenados, los pendientes son la cola de la lista que
        # queda estrictamente a la derecha de `llegada`. bisect_right deja
        # fuera los fines exactamente iguales: una salida simultanea a una
        # llegada libera el surtidor.
        pendientes = [len(fines[k]) - bisect_right(fines[k], llegada) for k in range(surtidores)]
        surtidor = min(range(surtidores), key=lambda k: (pendientes[k], k))

        inicio = max(llegada, ultimo_fin[surtidor])
        fin = inicio + float(duracion)
        fines[surtidor].append(fin)
        ultimo_fin[surtidor] = fin
        asignaciones.append((surtidor, inicio, fin))

    return asignaciones


# --------------------------------------------------------------------------
# Metricas
# --------------------------------------------------------------------------


def calcular_metricas(
    registros: tuple[RegistroVehiculo, ...],
    surtidores: int,
    horizonte: float,
) -> MetricasSimulacion:
    """Agrega los registros de una corrida en :class:`MetricasSimulacion`.

    Reglas acordadas (ver docs/modelo.md):

    - ``vehiculos_atendidos`` cuenta **todos** los admitidos, incluidos los
      que terminan despues del cierre.
    - Las esperas entran completas al promedio, tambien las de quienes
      terminan despues del cierre. Recortarlas sesgaria el resultado justo
      en los escenarios mas congestionados.
    - La utilizacion se mide solo dentro de ``[0, horizonte)``: cada
      intervalo de servicio se recorta a esa ventana antes de sumarse.
    - Sin vehiculos, las metricas de espera son ``None`` y la utilizacion es
      cero en todos los surtidores.
    - ``espera_p95`` usa :data:`gasolinera.contratos.METODO_PERCENTIL`.
    """
    ocupado = [0.0] * surtidores
    for registro in registros:
        inicio = min(max(registro.inicio, 0.0), horizonte)
        fin = min(max(registro.fin, 0.0), horizonte)
        ocupado[registro.surtidor] += fin - inicio

    # Los intervalos de un mismo surtidor no se solapan, asi que la suma no
    # puede pasar del horizonte. El min() solo absorbe el ultimo bit de
    # error de punto flotante acumulado al sumar.
    utilizacion = tuple(min(1.0, tiempo / horizonte) for tiempo in ocupado)

    if not registros:
        # Sin observaciones la espera no es estimable. No se devuelve 0.0:
        # un cero se promediaria entre replicas como una espera real.
        return MetricasSimulacion(
            vehiculos_atendidos=0,
            espera_media=None,
            proporcion_espera=None,
            espera_p95=None,
            utilizacion=utilizacion,
        )

    esperas = np.fromiter(
        (registro.espera for registro in registros), dtype=np.float64, count=len(registros)
    )
    return MetricasSimulacion(
        vehiculos_atendidos=len(registros),
        espera_media=float(esperas.mean()),
        # Estrictamente positiva: quien es atendido al llegar no "espera".
        proporcion_espera=float(np.count_nonzero(esperas > 0.0) / esperas.size),
        espera_p95=float(
            np.percentile(esperas, PERCENTIL_ESPERA, method=METODO_PERCENTIL)
        ),
        utilizacion=utilizacion,
    )


# --------------------------------------------------------------------------
# Punto de entrada
# --------------------------------------------------------------------------


def simular(
    llegadas: Any,
    servicios: Any,
    surtidores: Any,
    politica: Any,
    horizonte: Any,
) -> ResultadoSimulacion:
    """Simula la atencion de una lista de vehiculos bajo una politica de filas.

    Args:
        llegadas: instantes de llegada en minutos, ordenados de forma no
            decreciente y contenidos en ``[0, horizonte)``.
        servicios: duraciones de servicio en minutos, no negativas y de la
            misma longitud que ``llegadas``.
        surtidores: cantidad entera positiva de surtidores identicos.
        politica: ``"unica"`` o ``"independientes"``.
        horizonte: fin de la ventana de admision, en minutos.

    Returns:
        ResultadoSimulacion con un registro por vehiculo admitido, en el
        mismo orden en que llegaron, y las metricas agregadas.

    Raises:
        ErrorDeContrato: si las entradas violan el contrato.

    No modifica las entradas y no consume ninguna fuente de aleatoriedad.
    """
    llegadas, servicios, surtidores, politica, horizonte = validar_entradas_simulacion(
        llegadas, servicios, surtidores, politica, horizonte
    )

    if politica == POLITICA_FILA_UNICA:
        asignaciones = _asignar_fila_unica(llegadas, servicios, surtidores)
    else:
        asignaciones = _asignar_filas_independientes(llegadas, servicios, surtidores)

    registros = tuple(
        RegistroVehiculo(
            id=identificador,
            llegada=float(llegada),
            duracion_servicio=float(duracion),
            surtidor=surtidor,
            inicio=inicio,
            fin=fin,
        )
        for identificador, (llegada, duracion, (surtidor, inicio, fin)) in enumerate(
            zip(llegadas, servicios, asignaciones)
        )
    )

    return ResultadoSimulacion(
        registros=registros,
        politica=politica,
        horizonte=horizonte,
        surtidores=surtidores,
        metricas=calcular_metricas(registros, surtidores, horizonte),
    )
