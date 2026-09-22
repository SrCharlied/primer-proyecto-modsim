"""Compara los dos metodos de generacion de variables exponenciales.

Esta es la segunda pregunta del proyecto, independiente de la comparacion de
politicas de fila: transformada inversa contra aceptacion-rechazo, sobre la
misma distribucion objetivo.

Reporta tres cosas por separado, porque responden preguntas distintas:

- **Ajuste.** Si cada metodo produce realmente muestras exponenciales de la
  tasa pedida. Se mide con media, varianza y una prueba de
  Kolmogorov-Smirnov con la tasa **fijada de antemano**.
- **Costo por muestra.** Cuantos uniformes consume cada metodo. Es el costo
  intrinseco del algoritmo y no depende de la implementacion.
- **Tiempo de ejecucion.** Cuanto tarda cada uno en la practica. Aqui si
  influye que un metodo este vectorizado y el otro no, y eso se declara.

Uso:
    python -m scripts.validar_generadores --config configs/escenarios.json --salida resultados/generadores
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
from pathlib import Path

import numpy as np

from gasolinera.contratos import METODO_INVERSA, METODO_RECHAZO
from gasolinera.generadores import generar_exponenciales, generar_rechazo_con_estadisticas
from gasolinera.validacion import (
    cdf_empirica_vs_teorica,
    estadisticos_exponenciales,
    medir_rendimiento,
    prueba_bondad_ajuste,
    tasa_aceptacion_observada,
)
from gasolinera.visualizacion import (
    graficar_cdf_generadores,
    graficar_rendimiento_generadores,
)

#: Configuracion usada si el JSON no trae una seccion "generadores".
CONFIG_POR_OMISION: dict = {
    "tasas": [0.25, 1.0, 3.0],
    "cantidad_ajuste": 20000,
    "cantidad_aceptacion": 50000,
    "tamanos_rendimiento": [1000, 10000, 100000],
    "repeticiones_rendimiento": 15,
    "semilla_raiz": 7,
    "alpha": 0.05,
}

#: Uniformes que consume cada metodo por muestra aceptada. La inversa gasta
#: uno; el rechazo gasta dos por candidato y el conteo de candidatos se mide.
_UNIFORMES_POR_CANDIDATO = 2


def cargar_config(ruta: str | Path) -> dict:
    """Lee la seccion ``generadores`` del JSON, completando lo que falte."""
    config = dict(CONFIG_POR_OMISION)
    ruta = Path(ruta)
    if ruta.is_file():
        with ruta.open("r", encoding="utf-8") as archivo:
            completo = json.load(archivo)
        config.update(completo.get("generadores", {}))
    return config


def _rng(semilla_raiz: int, *etiquetas: object) -> np.random.Generator:
    """Genera un flujo reproducible e independiente por celda del estudio.

    Cada combinacion de metodo, tasa y tamano recibe su propio flujo derivado
    de la semilla raiz, de modo que agregar una celda no desplaza los numeros
    de las demas.
    """
    clave = [int(semilla_raiz)] + [abs(hash(e)) % (2**31) for e in etiquetas]
    return np.random.default_rng(np.random.SeedSequence(clave))


def medir_ajuste(config: dict) -> tuple[list[dict], list[dict]]:
    """Evalua el ajuste de cada metodo a la exponencial teorica.

    Returns:
        Las filas para ``ajuste.csv`` y las series para la figura de CDF.
    """
    filas: list[dict] = []
    series: list[dict] = []

    for metodo in (METODO_INVERSA, METODO_RECHAZO):
        for tasa in config["tasas"]:
            tasa = float(tasa)
            rng = _rng(config["semilla_raiz"], "ajuste", metodo, tasa)
            muestras = generar_exponenciales(
                metodo, tasa, int(config["cantidad_ajuste"]), rng
            )

            resumen = estadisticos_exponenciales(muestras, tasa)
            prueba = prueba_bondad_ajuste(muestras, tasa, alpha=float(config["alpha"]))

            filas.append(
                {
                    "metodo": metodo,
                    "tasa": tasa,
                    "n": resumen["n"],
                    "media_observada": resumen["media_observada"],
                    "media_teorica": resumen["media_teorica"],
                    "varianza_observada": resumen["varianza_observada"],
                    "varianza_teorica": resumen["varianza_teorica"],
                    "ks_estadistico": prueba["statistic"],
                    "p_valor": prueba["p_value"],
                    "alpha": prueba["alpha"],
                    # Se reporta el rechazo, no la "aceptacion" de H0: no
                    # rechazar no demuestra que el generador sea correcto.
                    "rechaza_h0": not prueba["acepta_h0"],
                }
            )

            x, empirica, teorica = cdf_empirica_vs_teorica(muestras, tasa)
            series.append(
                {
                    "metodo": metodo,
                    "tasa": tasa,
                    "x": x,
                    "cdf_empirica": empirica,
                    "cdf_teorica": teorica,
                }
            )

    return filas, series


def medir_aceptacion(config: dict) -> list[dict]:
    """Mide la tasa de aceptacion observada del metodo de rechazo.

    La teorica es ``1/M = 0.5``. De los candidatos observados se deduce
    cuantos uniformes cuesta cada muestra aceptada, que es el costo
    intrinseco del metodo.
    """
    filas: list[dict] = []
    cantidad = int(config["cantidad_aceptacion"])

    for tasa in config["tasas"]:
        tasa = float(tasa)
        rng = _rng(config["semilla_raiz"], "aceptacion", tasa)
        muestras, candidatos = generar_rechazo_con_estadisticas(tasa, cantidad, rng)

        observada = tasa_aceptacion_observada(candidatos, muestras.size)
        filas.append(
            {
                "tasa": tasa,
                "muestras_aceptadas": int(muestras.size),
                "candidatos_generados": int(candidatos),
                "tasa_aceptacion_observada": observada,
                "tasa_aceptacion_teorica": 0.5,
                "candidatos_por_muestra": candidatos / muestras.size,
                "uniformes_por_muestra": (
                    _UNIFORMES_POR_CANDIDATO * candidatos / muestras.size
                ),
            }
        )

    return filas


def medir_tiempos(config: dict) -> list[dict]:
    """Cronometra cada metodo en varios tamanos de muestra.

    Se excluye graficar y escribir archivos: solo se mide la generacion.
    Se reporta la mediana y la dispersion, no un unico valor, porque el
    tiempo de una sola corrida depende de la carga de la maquina.
    """
    filas: list[dict] = []
    tasa = 1.0

    for metodo in (METODO_INVERSA, METODO_RECHAZO):
        for tamano in config["tamanos_rendimiento"]:
            tamano = int(tamano)
            rng = _rng(config["semilla_raiz"], "tiempo", metodo, tamano)
            medicion = medir_rendimiento(
                generar_exponenciales,
                metodo,
                tasa,
                tamano,
                rng=rng,
                repeticiones=int(config["repeticiones_rendimiento"]),
            )

            filas.append(
                {
                    "metodo": metodo,
                    "tasa": tasa,
                    "tamano": tamano,
                    "repeticiones": medicion["repeticiones"],
                    "mediana_s": medicion["mediana"],
                    "media_s": medicion["media"],
                    "desviacion_s": medicion["desviacion_estandar"],
                    "minimo_s": medicion["minimo"],
                    "maximo_s": medicion["maximo"],
                    "microsegundos_por_muestra": medicion["mediana"] / tamano * 1e6,
                    "vectorizado": metodo == METODO_INVERSA,
                }
            )

    return filas


def _commit() -> str:
    """Identificador del commit actual, o cadena vacia si no se puede leer."""
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return salida.stdout.strip() if salida.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _versiones() -> dict[str, str]:
    """Versiones del entorno, para que el informe pueda citarlas."""
    versiones = {"python": platform.python_version(), "plataforma": platform.platform()}
    for nombre in ("numpy", "scipy", "matplotlib"):
        try:
            versiones[nombre] = __import__(nombre).__version__
        except Exception:  # noqa: BLE001 - una version ausente no debe abortar
            versiones[nombre] = "desconocida"
    return versiones


def _escribir_csv(ruta: Path, filas: list[dict]) -> None:
    if not filas:
        return
    with ruta.open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compara transformada inversa contra aceptacion-rechazo."
    )
    parser.add_argument("--config", required=True, help="Ruta del JSON de configuración.")
    parser.add_argument("--salida", required=True, help="Carpeta de resultados.")
    argumentos = parser.parse_args()

    config = cargar_config(argumentos.config)
    carpeta = Path(argumentos.salida)
    carpeta.mkdir(parents=True, exist_ok=True)

    print("Midiendo ajuste a la distribución teórica...")
    ajuste, series = medir_ajuste(config)

    print("Midiendo tasa de aceptación...")
    aceptacion = medir_aceptacion(config)

    print("Cronometrando la generación...")
    tiempos = medir_tiempos(config)

    _escribir_csv(carpeta / "ajuste.csv", ajuste)
    _escribir_csv(carpeta / "aceptacion.csv", aceptacion)
    _escribir_csv(carpeta / "rendimiento.csv", tiempos)

    with (carpeta / "metadatos.json").open("w", encoding="utf-8") as archivo:
        json.dump(
            {"configuracion": config, "versiones": _versiones(), "commit": _commit()},
            archivo,
            ensure_ascii=False,
            indent=2,
        )

    graficar_cdf_generadores(series, carpeta / "cdf_generadores.png")
    graficar_rendimiento_generadores(tiempos, carpeta / "rendimiento_generadores.png")

    print()
    print(f"Validación terminada: {len(ajuste)} celdas de ajuste, "
          f"{len(aceptacion)} de aceptación, {len(tiempos)} de rendimiento.")
    print(f"Resultados guardados en: {carpeta}")

    rechazos = [f for f in ajuste if f["rechaza_h0"]]
    if rechazos:
        print()
        print(f"ATENCIÓN: {len(rechazos)} celdas rechazan la hipótesis de ajuste.")
        for fila in rechazos:
            print(f"  {fila['metodo']} con tasa {fila['tasa']}: p = {fila['p_valor']:.4g}")
    else:
        print("Ninguna celda rechaza la hipótesis de ajuste.")


if __name__ == "__main__":
    main()
