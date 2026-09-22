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
from scripts.reporte_html import carpeta_generadores_por_omision, construir_html


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

    # El reporte se arma al final porque incrusta las figuras ya escritas.
    # Si ya se corrio validar_generadores, su comparacion se incluye sola.
    generadores = carpeta_generadores_por_omision(carpeta_salida)
    incluye_generadores = (generadores / "ajuste.csv").is_file()

    reporte = carpeta_salida / "reporte.html"
    reporte.write_text(
        construir_html(carpeta_salida, generadores if incluye_generadores else None),
        encoding="utf-8",
    )

    print(f"Experimento terminado: {len(filas)} filas generadas.")
    print(f"Resultados guardados en: {carpeta_salida}")
    print()
    print(f"Reporte visual: {reporte}")
    if not incluye_generadores:
        print("  (sin la comparación de generadores; correr scripts.validar_generadores)")
    print(f"Abrirlo con:    ii {reporte}")


if __name__ == "__main__":
    main()