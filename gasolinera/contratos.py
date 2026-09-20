"""Contratos publicos del simulador de gasolinera.

Este modulo define los tipos y las validaciones que comparten todos los
modulos del proyecto. Es deliberadamente pequeno y sin dependencias internas:
cualquier persona del equipo puede importarlo sin arrastrar el motor, los
generadores ni los experimentos.

Reglas de unidades, fijadas de una vez para todo el proyecto:

- El tiempo se mide en **minutos**.
- Las tasas se expresan en **sucesos por minuto**.
- Una tasa ``lam`` corresponde a una media ``1 / lam``. No son lo mismo y no
  se aceptan como sinonimos en ningun contrato.

Responsable: Persona 1 (Charlie). Nadie cambia estos contratos ni estas
unidades unilateralmente; ver docs/contratos.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

__all__ = [
    "ErrorDeContrato",
    "MetricasSimulacion",
    "METODOS",
    "METODO_INVERSA",
    "METODO_PERCENTIL",
    "METODO_RECHAZO",
    "PERCENTIL_ESPERA",
    "POLITICAS",
    "POLITICA_FILAS_INDEPENDIENTES",
    "POLITICA_FILA_UNICA",
    "RegistroVehiculo",
    "ResultadoSimulacion",
    "validar_entradas_simulacion",
    "validar_parametros_generador",
]


# --------------------------------------------------------------------------
# Vocabulario cerrado
# --------------------------------------------------------------------------

#: Una sola cola alimenta a todos los surtidores.
POLITICA_FILA_UNICA = "unica"

#: Cada surtidor tiene su propia cola y el vehiculo no se cambia de fila.
POLITICA_FILAS_INDEPENDIENTES = "independientes"

#: Unicas politicas que acepta el motor.
POLITICAS: tuple[str, ...] = (POLITICA_FILA_UNICA, POLITICA_FILAS_INDEPENDIENTES)

#: Transformada inversa directa: X = -ln(1 - U) / tasa.
METODO_INVERSA = "inversa"

#: Aceptacion-rechazo con propuesta Exp(tasa / 2) y constante envolvente M = 2.
METODO_RECHAZO = "rechazo"

#: Unicos metodos generadores que acepta el contrato de generadores.
METODOS: tuple[str, ...] = (METODO_INVERSA, METODO_RECHAZO)

#: Percentil de espera que se reporta en las metricas.
PERCENTIL_ESPERA = 95.0

#: Metodo de percentil acordado: interpolacion lineal entre los ordenes
#: estadisticos contiguos. Es el predeterminado de ``numpy.percentile``
#: (``method="linear"``). Queda fijado aqui para que el informe pueda citarlo
#: y para que nadie lo cambie sin actualizar el resto del proyecto.
METODO_PERCENTIL = "linear"


class ErrorDeContrato(ValueError):
    """Una entrada viola el contrato acordado.

    Hereda de ``ValueError`` a proposito: el codigo que solo quiera capturar
    ``ValueError`` sigue funcionando, y las pruebas pueden ser mas precisas
    cuando lo necesiten.
    """


# --------------------------------------------------------------------------
# Tipos de salida del motor
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegistroVehiculo:
    """Historia completa de un vehiculo admitido.

    ``espera`` y ``permanencia`` son propiedades derivadas, no campos
    almacenados: asi no pueden quedar desincronizadas de ``llegada``,
    ``inicio`` y ``fin``. Desde fuera se leen igual que cualquier atributo.
    """

    id: int
    llegada: float
    duracion_servicio: float
    surtidor: int
    inicio: float
    fin: float

    @property
    def espera(self) -> float:
        """Minutos entre la llegada y el inicio del servicio."""
        return self.inicio - self.llegada

    @property
    def permanencia(self) -> float:
        """Minutos entre la llegada y el fin del servicio."""
        return self.fin - self.llegada


@dataclass(frozen=True, slots=True)
class MetricasSimulacion:
    """Metricas agregadas de una corrida.

    Las metricas de espera son ``None`` cuando no hay ningun vehiculo
    admitido. No se sustituyen por cero: un cero seria una observacion
    inventada y contaminaria los promedios entre replicas. Al exportar a JSON
    ``None`` se escribe como ``null``.
    """

    #: Vehiculos admitidos dentro del horizonte. Se cuentan todos, incluso
    #: los que terminan de ser atendidos despues del cierre.
    vehiculos_atendidos: int
    espera_media: float | None
    #: Fraccion de vehiculos con espera estrictamente positiva.
    proporcion_espera: float | None
    #: Percentil 95 de la espera, calculado con METODO_PERCENTIL.
    espera_p95: float | None
    #: Fraccion del horizonte ocupada por cada surtidor, en orden de
    #: identificador. Siempre tiene longitud igual a la cantidad de
    #: surtidores, incluso si alguno nunca atendio.
    utilizacion: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class ResultadoSimulacion:
    """Salida completa de ``gasolinera.simulacion.simular``."""

    registros: tuple[RegistroVehiculo, ...]
    politica: str
    horizonte: float
    surtidores: int
    metricas: MetricasSimulacion


# --------------------------------------------------------------------------
# Validaciones
# --------------------------------------------------------------------------


def _validar_entero_positivo(valor: Any, nombre: str) -> int:
    # bool es subclase de int en Python; aceptarlo aqui seria un error
    # silencioso (True se convertiria en 1 surtidor).
    if isinstance(valor, bool) or not isinstance(valor, (int, np.integer)):
        raise ErrorDeContrato(
            f"{nombre} debe ser un entero; se recibio {type(valor).__name__}."
        )
    valor = int(valor)
    if valor <= 0:
        raise ErrorDeContrato(f"{nombre} debe ser positivo; se recibio {valor}.")
    return valor


def _validar_real_positivo(valor: Any, nombre: str) -> float:
    if isinstance(valor, bool) or not isinstance(
        valor, (int, float, np.integer, np.floating)
    ):
        raise ErrorDeContrato(
            f"{nombre} debe ser un numero real; se recibio {type(valor).__name__}."
        )
    valor = float(valor)
    if not np.isfinite(valor):
        raise ErrorDeContrato(f"{nombre} debe ser finito; se recibio {valor}.")
    if valor <= 0.0:
        raise ErrorDeContrato(f"{nombre} debe ser positivo; se recibio {valor}.")
    return valor


def _como_arreglo_1d(valor: Any, nombre: str) -> np.ndarray:
    """Copia ``valor`` a un arreglo 1-D de float64 y lo deja de solo lectura.

    Se copia siempre, incluso si ya era un ``ndarray`` de float64: marcar el
    arreglo original como no escribible seria modificar una entrada que
    pertenece a quien llama.
    """
    try:
        arreglo = np.array(valor, dtype=np.float64, copy=True)
    except (TypeError, ValueError) as exc:
        raise ErrorDeContrato(
            f"{nombre} debe poder convertirse a un arreglo de reales."
        ) from exc
    if arreglo.ndim != 1:
        raise ErrorDeContrato(
            f"{nombre} debe ser unidimensional; tiene {arreglo.ndim} dimensiones."
        )
    if not np.all(np.isfinite(arreglo)):
        raise ErrorDeContrato(f"{nombre} contiene valores no finitos (nan o inf).")
    arreglo.setflags(write=False)
    return arreglo


def validar_entradas_simulacion(
    llegadas: Any,
    servicios: Any,
    surtidores: Any,
    politica: Any,
    horizonte: Any,
) -> tuple[np.ndarray, np.ndarray, int, str, float]:
    """Valida las entradas de ``simular`` y devuelve copias normalizadas.

    Devuelve ``(llegadas, servicios, surtidores, politica, horizonte)`` con
    los arreglos ya convertidos a float64 y marcados de solo lectura. Las
    entradas originales no se modifican.

    Reglas verificadas:

    - ``politica`` pertenece a :data:`POLITICAS`.
    - ``surtidores`` es un entero positivo.
    - ``horizonte`` es un real positivo y finito.
    - ``llegadas`` y ``servicios`` son 1-D, finitos y de la misma longitud.
    - ``llegadas`` esta ordenado de forma no decreciente y contenido en
      ``[0, horizonte)``. El extremo derecho es abierto: un vehiculo que
      llega exactamente en el horizonte ya no se admite.
    - ``servicios`` es no negativo. Se admite el cero porque un servicio de
      duracion nula es un caso limite valido del modelo, no un error.

    Raises:
        ErrorDeContrato: si alguna regla no se cumple.
    """
    if politica not in POLITICAS:
        raise ErrorDeContrato(
            f"politica debe ser una de {POLITICAS}; se recibio {politica!r}."
        )
    surtidores = _validar_entero_positivo(surtidores, "surtidores")
    horizonte = _validar_real_positivo(horizonte, "horizonte")

    llegadas = _como_arreglo_1d(llegadas, "llegadas")
    servicios = _como_arreglo_1d(servicios, "servicios")

    if llegadas.size != servicios.size:
        raise ErrorDeContrato(
            "llegadas y servicios deben tener la misma longitud; "
            f"se recibio {llegadas.size} y {servicios.size}."
        )
    if llegadas.size > 0:
        if np.any(np.diff(llegadas) < 0.0):
            raise ErrorDeContrato(
                "llegadas debe estar ordenado de forma no decreciente."
            )
        if llegadas[0] < 0.0:
            raise ErrorDeContrato(
                f"llegadas no puede ser negativo; el minimo es {llegadas[0]}."
            )
        if llegadas[-1] >= horizonte:
            raise ErrorDeContrato(
                f"llegadas debe estar en [0, {horizonte}); el maximo es {llegadas[-1]}."
            )
        if np.any(servicios < 0.0):
            raise ErrorDeContrato(
                f"servicios no puede ser negativo; el minimo es {servicios.min()}."
            )

    return llegadas, servicios, surtidores, politica, horizonte


def validar_parametros_generador(
    metodo: Any,
    tasa: Any,
    cantidad: Any,
    rng: Any,
) -> tuple[str, float, int]:
    """Valida los parametros de ``generar_exponenciales``.

    Devuelve ``(metodo, tasa, cantidad)`` normalizados. ``rng`` se verifica
    pero se devuelve tal cual, porque es un objeto con estado que pertenece a
    quien llama: los generadores nunca lo reemplazan ni lo resiembran.

    A diferencia de ``surtidores``, ``cantidad`` admite el cero: pedir cero
    muestras es valido y debe devolver un arreglo vacio.

    Raises:
        ErrorDeContrato: si alguna regla no se cumple.
    """
    if metodo not in METODOS:
        raise ErrorDeContrato(
            f"metodo debe ser uno de {METODOS}; se recibio {metodo!r}."
        )
    tasa = _validar_real_positivo(tasa, "tasa")

    if isinstance(cantidad, bool) or not isinstance(cantidad, (int, np.integer)):
        raise ErrorDeContrato(
            f"cantidad debe ser un entero; se recibio {type(cantidad).__name__}."
        )
    cantidad = int(cantidad)
    if cantidad < 0:
        raise ErrorDeContrato(f"cantidad debe ser no negativa; se recibio {cantidad}.")

    if not isinstance(rng, np.random.Generator):
        raise ErrorDeContrato(
            "rng debe ser un numpy.random.Generator recibido desde afuera; "
            f"se recibio {type(rng).__name__}."
        )

    return metodo, tasa, cantidad
