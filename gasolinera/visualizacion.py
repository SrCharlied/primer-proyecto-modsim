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

def graficar_cdf_generadores(
    series: list[dict],
    ruta_salida: str | Path,
) -> None:
    """Compara la CDF empirica de cada metodo contra la exponencial teorica.

    Se dibuja un panel por tasa. Cada panel lleva las dos curvas empiricas y
    la teorica encima, porque lo que interesa es si las tres coinciden, no
    comparar los metodos entre si.

    Args:
        series: un diccionario por metodo y tasa, con las claves ``metodo``,
            ``tasa``, ``x``, ``cdf_empirica`` y ``cdf_teorica``.
        ruta_salida: archivo PNG a escribir.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    tasas = sorted({float(serie["tasa"]) for serie in series})
    figura, ejes = plt.subplots(
        2,
        len(tasas),
        figsize=(5.0 * len(tasas), 6.4),
        squeeze=False,
        gridspec_kw={"height_ratios": [2, 1]},
    )

    for columna, tasa in enumerate(tasas):
        arriba, abajo = ejes[0][columna], ejes[1][columna]
        del_panel = [s for s in series if float(s["tasa"]) == tasa]

        for serie in del_panel:
            # Se submuestrea solo para el dibujo: con 20 000 puntos la curva
            # se ve igual y el archivo pesa mucho menos.
            x = np.asarray(serie["x"], dtype=float)
            empirica = np.asarray(serie["cdf_empirica"], dtype=float)
            teorica = np.asarray(serie["cdf_teorica"], dtype=float)
            paso = max(1, x.size // 1500)

            arriba.plot(
                x[::paso], empirica[::paso], linewidth=1.6, label=f"empirica, {serie['metodo']}"
            )
            # El residuo es lo unico que se puede ver a simple vista: en el
            # panel de arriba las tres curvas se superponen.
            abajo.plot(
                x[::paso],
                (empirica - teorica)[::paso],
                linewidth=1.2,
                label=serie["metodo"],
            )

        if del_panel:
            x = np.asarray(del_panel[0]["x"], dtype=float)
            paso = max(1, x.size // 1500)
            arriba.plot(
                x[::paso],
                np.asarray(del_panel[0]["cdf_teorica"], dtype=float)[::paso],
                linestyle="--",
                color="black",
                linewidth=1.2,
                label="teorica",
            )

        arriba.set_title(f"tasa = {tasa:g} por minuto\n(media {1.0 / tasa:g} min)")
        arriba.set_ylabel("Probabilidad acumulada" if columna == 0 else "")
        arriba.set_ylim(0, 1)
        arriba.grid(alpha=0.25)
        arriba.legend(fontsize=8, loc="lower right")
        arriba.tick_params(labelbottom=False)

        abajo.axhline(0.0, color="black", linewidth=0.9)
        abajo.set_xlabel("Tiempo (minutos)")
        abajo.set_ylabel("Empirica - teorica" if columna == 0 else "")
        abajo.set_ylim(-0.02, 0.02)
        abajo.grid(alpha=0.25)
        abajo.legend(fontsize=8, loc="upper right")

    figura.suptitle(
        "CDF empirica contra exponencial teorica, por metodo de generacion\n"
        "Panel inferior: diferencia respecto a la teorica, en escala +/-0.02"
    )
    figura.tight_layout()
    figura.savefig(ruta_salida, dpi=150)
    plt.close(figura)


def graficar_rendimiento_generadores(
    filas: list[dict],
    ruta_salida: str | Path,
) -> None:
    """Grafica el tiempo de generacion por tamano de muestra y metodo.

    Los dos ejes van en escala logaritmica: los tamanos crecen por factores
    de diez y los tiempos abarcan varios ordenes de magnitud.

    Args:
        filas: diccionarios con ``metodo``, ``tamano`` y ``mediana_s``.
        ruta_salida: archivo PNG a escribir.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    por_metodo: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for fila in filas:
        por_metodo[str(fila["metodo"])].append(
            (float(fila["tamano"]), float(fila["mediana_s"]))
        )

    figura, eje = plt.subplots(figsize=(8, 5))

    for metodo in sorted(por_metodo):
        puntos = sorted(por_metodo[metodo])
        eje.plot(
            [p[0] for p in puntos],
            [p[1] for p in puntos],
            marker="o",
            linewidth=1.8,
            label=metodo,
        )

    eje.set_xscale("log")
    eje.set_yscale("log")
    eje.set_title("Tiempo de generacion por tamano de muestra")
    eje.set_xlabel("Muestras generadas")
    eje.set_ylabel("Tiempo (segundos, mediana de las repeticiones)")
    eje.grid(which="both", alpha=0.25)
    eje.legend(title="Metodo")

    figura.tight_layout()
    figura.savefig(ruta_salida, dpi=150)
    plt.close(figura)
