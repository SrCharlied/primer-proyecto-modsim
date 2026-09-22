"""Orquestacion de escenarios, replicas y exportacion de resultados.

PENDIENTE: Persona 4 (Micaela). Flujos RNG separados para llegadas y
servicios derivados de una semilla raiz con ``SeedSequence``; las mismas
entradas para ambas politicas en cada replica.
"""
import json
from pathlib import Path

import numpy as np
import csv

from gasolinera.generadores import generar_exponenciales
from gasolinera.simulacion import simular


def cargar_escenarios(ruta: str | Path) -> dict:
    """Carga la configuración de experimentos desde un archivo JSON."""
    ruta = Path(ruta)

    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def generar_entradas_replica(
    tasa_llegadas: float,
    tasa_servicio: float,
    horizonte: float,
    rng_llegadas: np.random.Generator,
    rng_servicios: np.random.Generator,
    metodo: str = "inversa",
) -> tuple[np.ndarray, np.ndarray]:
    """Genera llegadas hasta el horizonte y un servicio por vehículo."""
    tiempos_llegada: list[float] = []
    tiempos_servicio: list[float] = []
    tiempo_acumulado = 0.0

    while tiempo_acumulado < horizonte:
        intervalo = generar_exponenciales(
            metodo=metodo,
            tasa=tasa_llegadas,
            cantidad=1,
            rng=rng_llegadas,
        )[0]

        tiempo_acumulado += float(intervalo)

        if tiempo_acumulado < horizonte:
            tiempos_llegada.append(tiempo_acumulado)

            servicio = generar_exponenciales(
                metodo=metodo,
                tasa=tasa_servicio,
                cantidad=1,
                rng=rng_servicios,
            )[0]

            tiempos_servicio.append(float(servicio))

    return (
        np.asarray(tiempos_llegada, dtype=float),
        np.asarray(tiempos_servicio, dtype=float),
    )

def ejecutar_replica(
    escenario: dict,
    horizonte: float,
    metodo: str,
    semilla: int,
) -> dict:
    """Ejecuta una réplica usando las mismas entradas en ambas políticas."""
    secuencia = np.random.SeedSequence(semilla)
    semilla_llegadas, semilla_servicios = secuencia.spawn(2)

    rng_llegadas = np.random.default_rng(semilla_llegadas)
    rng_servicios = np.random.default_rng(semilla_servicios)

    llegadas, servicios = generar_entradas_replica(
        tasa_llegadas=escenario["tasa_llegadas"],
        tasa_servicio=escenario["tasa_servicio"],
        horizonte=horizonte,
        rng_llegadas=rng_llegadas,
        rng_servicios=rng_servicios,
        metodo=metodo,
    )

    resultado_unica = simular(
        llegadas=llegadas,
        servicios=servicios,
        surtidores=escenario["surtidores"],
        politica="unica",
        horizonte=horizonte,
    )

    resultado_independientes = simular(
        llegadas=llegadas,
        servicios=servicios,
        surtidores=escenario["surtidores"],
        politica="independientes",
        horizonte=horizonte,
    )

    return {
        "unica": resultado_unica,
        "independientes": resultado_independientes,
    }

def ejecutar_experimentos(config: dict) -> tuple[list[dict], list[dict]]:
    """Ejecuta todos los escenarios y réplicas definidos en la configuración."""
    filas: list[dict] = []
    utilizaciones: list[dict] = []

    escenarios = config["escenarios"]
    replicas = config["replicas"]

    cantidad_semillas = len(escenarios) * replicas
    semillas = np.random.SeedSequence(
        config["semilla_raiz"]
    ).spawn(cantidad_semillas)

    indice_semilla = 0

    for escenario in escenarios:
        for replica in range(1, replicas + 1):
            semilla = int(
                semillas[indice_semilla].generate_state(
                    1,
                    dtype=np.uint64,
                )[0]
            )
            indice_semilla += 1

            resultados = ejecutar_replica(
                escenario=escenario,
                horizonte=config["horizonte"],
                metodo=config["metodo"],
                semilla=semilla,
            )

            for politica, resultado in resultados.items():
                metricas = resultado.metricas

                filas.append(
                    {
                        "escenario": escenario["nombre"],
                        "replica": replica,
                        "politica": politica,
                        "vehiculos_atendidos": metricas.vehiculos_atendidos,
                        "espera_media": metricas.espera_media,
                        "proporcion_espera": metricas.proporcion_espera,
                        "espera_p95": metricas.espera_p95,
                    }
                )

                for surtidor, utilizacion in enumerate(
                    metricas.utilizacion,
                    start=1,
                ):
                    utilizaciones.append(
                        {
                            "escenario": escenario["nombre"],
                            "replica": replica,
                            "politica": politica,
                            "surtidor": surtidor,
                            "utilizacion": utilizacion,
                        }
                    )

    return filas, utilizaciones

def guardar_resultados(
    filas: list[dict],
    utilizaciones: list[dict],
    config: dict,
    carpeta_salida: str | Path,
) -> None:
    """Guarda métricas, utilización y configuración del experimento."""
    carpeta_salida = Path(carpeta_salida)
    carpeta_salida.mkdir(parents=True, exist_ok=True)

    columnas_replicas = [
        "escenario",
        "replica",
        "politica",
        "vehiculos_atendidos",
        "espera_media",
        "proporcion_espera",
        "espera_p95",
    ]

    with (carpeta_salida / "replicas.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas_replicas,
        )
        escritor.writeheader()
        escritor.writerows(filas)

    columnas_utilizacion = [
        "escenario",
        "replica",
        "politica",
        "surtidor",
        "utilizacion",
    ]

    with (carpeta_salida / "utilizacion.csv").open(
        "w",
        newline="",
        encoding="utf-8",
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas_utilizacion,
        )
        escritor.writeheader()
        escritor.writerows(utilizaciones)

    with (carpeta_salida / "metadatos.json").open(
        "w",
        encoding="utf-8",
    ) as archivo:
        json.dump(
            config,
            archivo,
            ensure_ascii=False,
            indent=2,
        )