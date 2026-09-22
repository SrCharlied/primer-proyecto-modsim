import argparse

from gasolinera.experimentos import (
    cargar_escenarios,
    ejecutar_experimentos,
    guardar_resultados,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ejecuta los experimentos de la gasolinera."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Ruta del archivo JSON de configuración.",
    )
    parser.add_argument(
        "--salida",
        required=True,
        help="Carpeta donde se guardarán los resultados.",
    )
    argumentos = parser.parse_args()

    config = cargar_escenarios(argumentos.config)
    filas, utilizaciones = ejecutar_experimentos(config)

    guardar_resultados(
        filas=filas,
        utilizaciones=utilizaciones,
        config=config,
        carpeta_salida=argumentos.salida,
    )

    print(f"Experimento terminado: {len(filas)} filas generadas.")
    print(f"Resultados guardados en: {argumentos.salida}")


if __name__ == "__main__":
    main()