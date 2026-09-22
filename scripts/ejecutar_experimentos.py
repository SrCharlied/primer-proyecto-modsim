import argparse
from pathlib import Path

from gasolinera.experimentos import (
    cargar_escenarios,
    ejecutar_experimentos,
    guardar_resultados,
)
from gasolinera.visualizacion import (
    graficar_espera_media,
    graficar_utilizacion_media,
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

    carpeta_salida = Path(argumentos.salida)

    guardar_resultados(
        filas=filas,
        utilizaciones=utilizaciones,
        config=config,
        carpeta_salida=carpeta_salida,
    )

    graficar_espera_media(
        filas,
        carpeta_salida / "espera_media.png",
    )

    graficar_utilizacion_media(
        utilizaciones,
        carpeta_salida / "utilizacion_media.png",
    )

    print(f"Experimento terminado: {len(filas)} filas generadas.")
    print(f"Resultados guardados en: {carpeta_salida}")


if __name__ == "__main__":
    main()