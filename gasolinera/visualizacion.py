"""Figuras del informe.

PENDIENTE: Persona 4 (Micaela). Toda figura lleva unidades, parametros y
leyenda.
"""
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np


def graficar_espera_media(
    filas: list[dict],
    ruta_salida: str | Path,
) -> None:
    """Grafica la espera media por escenario y política."""
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    valores: dict[tuple[str, str], list[float]] = defaultdict(list)

    for fila in filas:
        espera = fila.get("espera_media")

        if espera is not None:
            clave = (fila["escenario"], fila["politica"])
            valores[clave].append(float(espera))

    escenarios = sorted(
        {escenario for escenario, _ in valores}
    )
    politicas = ["unica", "independientes"]

    posiciones = np.arange(len(escenarios))
    ancho = 0.36

    figura, eje = plt.subplots(figsize=(9, 5))

    for indice, politica in enumerate(politicas):
        promedios = []

        for escenario in escenarios:
            observaciones = valores.get((escenario, politica), [])
            promedio = (
                float(np.mean(observaciones))
                if observaciones
                else 0.0
            )
            promedios.append(promedio)

        desplazamiento = (indice - 0.5) * ancho

        eje.bar(
            posiciones + desplazamiento,
            promedios,
            width=ancho,
            label=politica,
        )

    eje.set_title("Espera media por escenario y política")
    eje.set_xlabel("Escenario")
    eje.set_ylabel("Espera media (minutos)")
    eje.set_xticks(posiciones)
    eje.set_xticklabels(escenarios)
    eje.legend(title="Política")
    eje.grid(axis="y", alpha=0.25)

    figura.tight_layout()
    figura.savefig(ruta_salida, dpi=150)
    plt.close(figura)
    
def graficar_utilizacion_media(
    utilizaciones: list[dict],
    ruta_salida: str | Path,
) -> None:
    """Grafica la utilización media por escenario y política."""
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    valores: dict[tuple[str, str], list[float]] = defaultdict(list)

    for fila in utilizaciones:
        clave = (fila["escenario"], fila["politica"])
        valores[clave].append(float(fila["utilizacion"]))

    escenarios = sorted(
        {escenario for escenario, _ in valores}
    )
    politicas = ["unica", "independientes"]

    posiciones = np.arange(len(escenarios))
    ancho = 0.36

    figura, eje = plt.subplots(figsize=(9, 5))

    for indice, politica in enumerate(politicas):
        promedios = []

        for escenario in escenarios:
            observaciones = valores.get((escenario, politica), [])
            promedio = (
                float(np.mean(observaciones))
                if observaciones
                else 0.0
            )
            promedios.append(promedio)

        desplazamiento = (indice - 0.5) * ancho

        eje.bar(
            posiciones + desplazamiento,
            promedios,
            width=ancho,
            label=politica,
        )

    eje.set_title("Utilización media por escenario y política")
    eje.set_xlabel("Escenario")
    eje.set_ylabel("Proporción de utilización")
    eje.set_ylim(0, 1)
    eje.set_xticks(posiciones)
    eje.set_xticklabels(escenarios)
    eje.legend(title="Política")
    eje.grid(axis="y", alpha=0.25)

    figura.tight_layout()
    figura.savefig(ruta_salida, dpi=150)
    plt.close(figura)