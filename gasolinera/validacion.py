"""Validación estadística y comparación de los dos generadores.

Este módulo implementa la parte de Persona 3 (Diego) del proyecto. La
validación se centra en tres observables principales:

- ajuste global de la muestra a la exponencial teórica;
- tasa de aceptación observada del metodo de rechazo;
- rendimiento comparativo usando ``time.perf_counter``.

La interfaz se diseña para poder usarse tanto desde tests automatizados como
desde scripts de analisis exploratorio, sin tocar el generador ni el motor.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import numpy as np
from scipy import stats

from gasolinera.generadores import generar_exponenciales, generar_rechazo_con_estadisticas

__all__ = [
    "estadisticos_exponenciales",
    "cdf_empirica_vs_teorica",
    "prueba_bondad_ajuste",
    "tasa_aceptacion_observada",
    "medir_rendimiento",
    "comparar_generadores",
    "analizar_generadores",
    "validar_generador",
]


def _normalizar_muestras(muestras: np.ndarray | list[float] | tuple[float, ...]) -> np.ndarray:
    """Convierte a un arreglo 1-D de float64, sin cambiar el contenido."""
    arreglo = np.asarray(muestras, dtype=np.float64)
    if arreglo.ndim != 1:
        raise ValueError("las muestras deben ser un arreglo unidimensional.")
    if not np.all(np.isfinite(arreglo)):
        raise ValueError("las muestras contienen valores finitos no válidos.")
    if np.any(arreglo < 0.0):
        raise ValueError("las muestras deben ser no negativas.")
    return arreglo


def estadisticos_exponenciales(muestras: np.ndarray | list[float], tasa: float) -> dict[str, float | int]:
    """Resumen estadistico de una muestra respecto a una Exponencial(tasa)."""
    if not np.isfinite(tasa) or tasa <= 0.0:
        raise ValueError("la tasa debe ser un real positivo y finito.")

    arreglo = _normalizar_muestras(muestras)
    n = arreglo.size
    media_obs = float(np.mean(arreglo)) if n else 0.0
    var_obs = float(np.var(arreglo, ddof=1)) if n > 1 else 0.0
    media_teorica = 1.0 / tasa
    var_teorica = media_teorica ** 2

    return {
        "n": int(n),
        "media_observada": media_obs,
        "varianza_observada": var_obs,
        "media_teorica": float(media_teorica),
        "varianza_teorica": float(var_teorica),
        "desvio_observado": float(np.sqrt(var_obs)) if n > 1 else 0.0,
        "desvio_teorico": float(np.sqrt(var_teorica)),
    }


def cdf_empirica_vs_teorica(
    muestras: np.ndarray | list[float],
    tasa: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Devuelve ``(x, cdf_empirica, cdf_teorica)`` para graficar."""
    arreglo = _normalizar_muestras(muestras)
    if arreglo.size == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64), np.array([], dtype=np.float64)

    x = np.sort(arreglo)
    cdf_empirica = np.arange(1, x.size + 1, dtype=np.float64) / x.size
    cdf_teorica = 1.0 - np.exp(-tasa * x)
    return x, cdf_empirica, cdf_teorica


def prueba_bondad_ajuste(
    muestras: np.ndarray | list[float],
    tasa: float,
    *,
    alpha: float = 0.05,
) -> dict[str, float | bool]:
    """Aplica la prueba KS una muestra contra una exponencial con tasa fija."""
    if not np.isfinite(alpha) or not (0.0 < alpha < 1.0):
        raise ValueError("alpha debe estar en (0, 1).")

    arreglo = _normalizar_muestras(muestras)
    if arreglo.size == 0:
        raise ValueError("se necesita al menos una muestra para la prueba de bondad de ajuste.")

    escala = 1.0 / tasa
    estadistico, p_valor = stats.kstest(arreglo, "expon", args=(0.0, escala))

    resumen = estadisticos_exponenciales(arreglo, tasa)
    resumen.update(
        {
            "statistic": float(estadistico),
            "p_value": float(p_valor),
            "alpha": float(alpha),
            "acepta_h0": bool(p_valor > alpha),
        }
    )
    return resumen


def tasa_aceptacion_observada(candidatos: int | np.integer, aceptadas: int | np.integer) -> float:
    """Calcula la fracción de candidatos aceptados en un metodo de rechazo."""
    total_candidatos = int(candidatos)
    total_aceptadas = int(aceptadas)
    if total_candidatos < 0 or total_aceptadas < 0:
        raise ValueError("candidatos y aceptadas deben ser no negativos.")
    if total_candidatos == 0:
        return 0.0
    return float(total_aceptadas) / float(total_candidatos)


def medir_rendimiento(
    funcion: Callable[..., object],
    *args: object,
    repeticiones: int = 30,
    **kwargs: object,
) -> dict[str, float | int | np.ndarray]:
    """Mide tiempos de ejecución con ``time.perf_counter`` y devuelve resumen."""
    if isinstance(repeticiones, bool) or not isinstance(repeticiones, (int, np.integer)):
        raise ValueError("repeticiones debe ser un entero positivo.")
    repeticiones = int(repeticiones)
    if repeticiones <= 0:
        raise ValueError("repeticiones debe ser positiva.")

    tiempos = np.empty(repeticiones, dtype=np.float64)
    for indice in range(repeticiones):
        inicio = time.perf_counter()
        funcion(*args, **kwargs)
        tiempos[indice] = time.perf_counter() - inicio

    return {
        "repeticiones": int(repeticiones),
        "tiempos": tiempos,
        "media": float(np.mean(tiempos)),
        "mediana": float(np.median(tiempos)),
        "desviacion_estandar": float(np.std(tiempos, ddof=1)) if repeticiones > 1 else 0.0,
        "minimo": float(np.min(tiempos)),
        "maximo": float(np.max(tiempos)),
    }


def comparar_generadores(
    tasa: float = 1.0,
    cantidad: int = 1000,
    semilla: int = 123,
    repeticiones: int = 10,
    tamanos: list[int] | tuple[int, ...] | None = None,
) -> dict[str, dict[str, object]]:
    """Compara el ajuste y el rendimiento de los dos metodos para un rango de tamaños."""
    if not np.isfinite(tasa) or tasa <= 0.0:
        raise ValueError("la tasa debe ser un real positivo y finito.")
    if isinstance(cantidad, bool) or not isinstance(cantidad, (int, np.integer)) or cantidad < 0:
        raise ValueError("cantidad debe ser un entero no negativo.")
    if not isinstance(semilla, (int, np.integer)):
        raise ValueError("semilla debe ser un entero.")

    if tamanos is None:
        tamanos = (100, 1000, 5000)
    tamanos = tuple(int(t) for t in tamanos)

    resumen: dict[str, dict[str, object]] = {}
    for metodo in ("inversa", "rechazo"):
        detalle = []
        for idx, tamano in enumerate(tamanos):
            rng = np.random.default_rng(int(semilla) + idx)
            if metodo == "inversa":
                muestras = generar_exponenciales(metodo, tasa, int(tamano), rng)
                aceptacion = None
            else:
                muestras, candidatos = generar_rechazo_con_estadisticas(float(tasa), int(tamano), rng)
                aceptacion = tasa_aceptacion_observada(candidatos, int(muestras.size))

            ajuste = estadisticos_exponenciales(muestras, tasa)
            prueba = prueba_bondad_ajuste(muestras, tasa)
            detalle.append(
                {
                    "cantidad": int(tamano),
                    "estadisticos": ajuste,
                    "bondad_ajuste": prueba,
                    "tasa_aceptacion": aceptacion,
                }
            )

        tiempos = medir_rendimiento(
            generar_exponenciales,
            metodo,
            tasa,
            cantidad,
            rng=np.random.default_rng(int(semilla) + 999),
            repeticiones=repeticiones,
        )
        resumen[metodo] = {
            "tamanos": tamanos,
            "detalle": detalle,
            "rendimiento": tiempos,
            "vectorizado": metodo == "inversa",
        }
    return resumen


def analizar_generadores(
    tasa: float = 1.0,
    cantidad: int = 5000,
    semilla: int = 42,
    repeticiones: int = 20,
) -> dict[str, object]:
    """Resumen completo para comparar ambos metodos con la misma tasa."""
    return comparar_generadores(
        tasa=tasa,
        cantidad=cantidad,
        semilla=semilla,
        repeticiones=repeticiones,
    )


def validar_generador(
    metodo: str,
    tasa: float,
    cantidad: int,
    rng: np.random.Generator,
    *,
    alpha: float = 0.05,
) -> dict[str, object]:
    """Evalúa un metodo rápido y devuelve ajuste y tasa de aceptación si aplica."""
    if metodo not in {"inversa", "rechazo"}:
        raise ValueError("metodo debe ser 'inversa' o 'rechazo'.")

    if metodo == "inversa":
        muestras = generar_exponenciales(metodo, tasa, cantidad, rng)
        tasa_aceptacion = None
    else:
        muestras, candidatos = generar_rechazo_con_estadisticas(tasa, cantidad, rng)
        tasa_aceptacion = tasa_aceptacion_observada(candidatos, muestras.size)

    return {
        "metodo": metodo,
        "tasa": float(tasa),
        "cantidad": int(cantidad),
        "estadisticos": estadisticos_exponenciales(muestras, tasa),
        "bondad_ajuste": prueba_bondad_ajuste(muestras, tasa, alpha=alpha),
        "tasa_aceptacion": tasa_aceptacion,
    }

