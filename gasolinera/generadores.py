"""Generadores de variables aleatorias con distribucion exponencial.

Este modulo implementa los dos metodos acordados por el equipo:

- ``inversa``: transformada inversa directa.
- ``rechazo``: aceptacion-rechazo con propuesta Exp(tasa / 2) y M = 2.

El generador uniforme ``rng`` siempre se recibe desde afuera para mantener
reproducibilidad y evitar estado aleatorio global.
"""

from __future__ import annotations

import numpy as np

from gasolinera.contratos import (
    ErrorDeContrato,
    METODO_INVERSA,
    METODO_RECHAZO,
    validar_parametros_generador,
)

__all__ = ["generar_exponenciales", "generar_rechazo_con_estadisticas"]


def _verificar_muestras_finitas(muestras: np.ndarray) -> np.ndarray:
    """Comprueba que las muestras producidas sean finitas y no negativas."""
    if not np.all(np.isfinite(muestras)):
        raise ErrorDeContrato(
            "la tasa produce valores fuera del rango numerico de float64."
        )

    if np.any(muestras < 0.0):
        raise ErrorDeContrato("el generador produjo una muestra negativa.")

    return muestras


def _generar_inversa(
    tasa: float,
    cantidad: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Genera Exp(tasa) mediante transformada inversa."""

    if cantidad == 0:
        return np.empty(0, dtype=np.float64)

    uniformes = rng.random(cantidad)

    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        muestras = -np.log1p(-uniformes) / tasa

    return _verificar_muestras_finitas(muestras)


def _generar_rechazo_sin_validar(
    tasa: float,
    cantidad: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int]:
    """Implementacion interna de aceptacion-rechazo."""

    if cantidad == 0:
        return np.empty(0, dtype=np.float64), 0

    muestras = np.empty(cantidad, dtype=np.float64)

    aceptadas = 0
    candidatos = 0

    while aceptadas < cantidad:

        u = rng.random()
        v = rng.random()

        with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
            candidato = -2.0 * np.log1p(-u) / tasa

        candidatos += 1

        if not np.isfinite(candidato) or candidato < 0.0:
            raise ErrorDeContrato(
                "la tasa produce valores fuera del rango numerico de float64."
            )

        prob_aceptacion = np.exp(-tasa * candidato / 2.0)

        if v < prob_aceptacion:
            muestras[aceptadas] = candidato
            aceptadas += 1

    return _verificar_muestras_finitas(muestras), candidatos


def generar_rechazo_con_estadisticas(
    tasa: float,
    cantidad: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, int]:
    """Genera Exp(tasa) por rechazo y devuelve tambien los candidatos usados."""

    _, tasa, cantidad = validar_parametros_generador(
        METODO_RECHAZO,
        tasa,
        cantidad,
        rng,
    )

    return _generar_rechazo_sin_validar(tasa, cantidad, rng)


def generar_exponenciales(
    metodo: str,
    tasa: float,
    cantidad: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Devuelve un arreglo 1-D de muestras exponenciales.

    Args:
        metodo: ``"inversa"`` o ``"rechazo"``.
        tasa: tasa positiva y finita, expresada en sucesos por minuto.
        cantidad: numero de muestras; puede ser cero.
        rng: instancia de ``numpy.random.Generator`` creada por quien llama.

    Returns:
        ``numpy.ndarray`` de ``float64`` con longitud ``cantidad``.

    Raises:
        ErrorDeContrato: si los parametros violan el contrato o si una tasa
        extrema produce resultados fuera del rango numerico de float64.
    """

    metodo, tasa, cantidad = validar_parametros_generador(
        metodo,
        tasa,
        cantidad,
        rng,
    )

    if metodo == METODO_INVERSA:
        return _generar_inversa(tasa, cantidad, rng)

    if metodo == METODO_RECHAZO:
        muestras, _ = _generar_rechazo_sin_validar(
            tasa,
            cantidad,
            rng,
        )
        return muestras

    raise ErrorDeContrato(f"metodo no soportado: {metodo!r}")