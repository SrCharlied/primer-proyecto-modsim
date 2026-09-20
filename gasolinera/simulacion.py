"""Motor determinista de la gasolinera.

PENDIENTE (Hito B, Persona 1 / Charlie): ``simular`` y ``calcular_metricas``
estan especificados pero **no implementados**. Las pruebas de
``tests/test_simulacion.py`` fallan a proposito: es el paso rojo del ciclo
TDD acordado en el plan, no un defecto.

El motor es estrictamente determinista: recibe las llegadas y las duraciones
ya sorteadas y **no genera aleatoriedad propia**. Esa separacion es lo que
permite pasar exactamente las mismas entradas a las dos politicas dentro de
una replica y comparar sin ruido adicional.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from gasolinera.contratos import (
    METODO_PERCENTIL,
    PERCENTIL_ESPERA,
    MetricasSimulacion,
    RegistroVehiculo,
    ResultadoSimulacion,
    validar_entradas_simulacion,
)

__all__ = ["calcular_metricas", "simular"]


def calcular_metricas(
    registros: tuple[RegistroVehiculo, ...],
    surtidores: int,
    horizonte: float,
) -> MetricasSimulacion:
    """Agrega los registros de una corrida en :class:`MetricasSimulacion`.

    Reglas acordadas:

    - ``vehiculos_atendidos`` cuenta **todos** los admitidos, incluidos los
      que terminan despues del cierre.
    - Las esperas entran completas al promedio, tambien las de quienes
      terminan despues del cierre.
    - La utilizacion se mide solo dentro de ``[0, horizonte)``: cada
      intervalo de servicio se recorta a esa ventana antes de sumarse, de
      modo que siempre queda en ``[0, 1]``.
    - Sin vehiculos, las metricas de espera son ``None`` y la utilizacion es
      cero en todos los surtidores.
    - ``espera_p95`` usa :data:`gasolinera.contratos.METODO_PERCENTIL`.

    PENDIENTE: implementar en el Hito B.
    """
    raise NotImplementedError(
        "calcular_metricas se implementa en el Hito B; ver docs/modelo.md."
    )


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

    PENDIENTE: implementar en el Hito B. Ver ``docs/modelo.md`` para las
    reglas de asignacion, desempate y cierre, y
    ``tests/fixtures/caso_pequeno.json`` para el caso calculado a mano.
    """
    # La validacion ya es parte del Hito A: se ejecuta aunque el motor aun no
    # exista, de modo que las pruebas de contrato pasen desde ahora.
    llegadas, servicios, surtidores, politica, horizonte = validar_entradas_simulacion(
        llegadas, servicios, surtidores, politica, horizonte
    )
    raise NotImplementedError(
        "simular se implementa en el Hito B; las reglas estan en docs/modelo.md."
    )
