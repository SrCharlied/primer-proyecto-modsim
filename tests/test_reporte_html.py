"""Pruebas del reporte HTML autocontenido."""

import json

import pytest

from scripts.reporte_html import construir_html


def _escribir_corrida(carpeta, con_figuras=True):
    """Deja en `carpeta` una corrida minima de 2 replicas y 2 surtidores."""
    (carpeta / "metadatos.json").write_text(
        json.dumps(
            {
                "semilla_raiz": 7,
                "replicas": 2,
                "horizonte": 60.0,
                "metodo": "inversa",
                "escenarios": [
                    {
                        "nombre": "demanda_alta",
                        "tasa_llegadas": 0.4,
                        "tasa_servicio": 0.1,
                        "surtidores": 2,
                    },
                    {
                        "nombre": "demanda_baja",
                        "tasa_llegadas": 0.1,
                        "tasa_servicio": 0.1,
                        "surtidores": 2,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    renglones = ["escenario,replica,politica,vehiculos_atendidos,espera_media,proporcion_espera,espera_p95"]
    for escenario in ("demanda_alta", "demanda_baja"):
        for replica in (1, 2):
            renglones.append(f"{escenario},{replica},unica,10,2.0,0.5,6.0")
            renglones.append(f"{escenario},{replica},independientes,10,3.0,0.4,9.0")
    (carpeta / "replicas.csv").write_text("\n".join(renglones) + "\n", encoding="utf-8")

    renglones = ["escenario,replica,politica,surtidor,utilizacion"]
    for escenario in ("demanda_alta", "demanda_baja"):
        for replica in (1, 2):
            for politica, valores in (("unica", (0.5, 0.5)), ("independientes", (0.8, 0.2))):
                for surtidor, valor in enumerate(valores, start=1):
                    renglones.append(
                        f"{escenario},{replica},{politica},{surtidor},{valor}"
                    )
    (carpeta / "utilizacion.csv").write_text("\n".join(renglones) + "\n", encoding="utf-8")

    if con_figuras:
        # PNG valido de 1x1 pixel, suficiente para probar la incrustacion.
        import base64

        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8AARAAA//8DAAX"
            "+Av7f0m0AAAAASUVORK5CYII="
        )
        (carpeta / "espera_media.png").write_bytes(png)
        (carpeta / "utilizacion_media.png").write_bytes(png)


def test_genera_html_completo(tmp_path):
    _escribir_corrida(tmp_path)

    html = construir_html(tmp_path)

    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert 'lang="es"' in html


def test_no_depende_de_recursos_externos(tmp_path):
    """El reporte debe abrirse sin conexion: nada de CDN ni archivos aparte."""
    _escribir_corrida(tmp_path)

    html = construir_html(tmp_path)

    assert "http://" not in html
    assert "https://" not in html
    # Las figuras van incrustadas, no referenciadas por ruta.
    assert html.count("data:image/png;base64,") == 2
    assert "src='espera_media.png'" not in html


def test_respeta_el_orden_de_la_configuracion(tmp_path):
    """Los escenarios siguen la configuracion, no el orden alfabetico."""
    _escribir_corrida(tmp_path)

    html = construir_html(tmp_path)

    # demanda_alta se declara primero, aunque alfabeticamente iria despues.
    assert html.index("demanda_alta") < html.index("demanda_baja")


def test_marca_la_politica_ganadora_por_metrica(tmp_path):
    """Menor es mejor en las tres metricas, sea cual sea el signo."""
    _escribir_corrida(tmp_path)

    html = construir_html(tmp_path)

    # espera_media: unica 2.0 contra indep 3.0, gana unica.
    # proporcion_espera: unica 0.5 contra indep 0.4, gana independientes.
    # Ambas marcas deben aparecer.
    assert html.count("class='num mejor'") >= 2


def test_funciona_sin_figuras(tmp_path):
    """Si aun no se generaron las figuras, el reporte sale igual."""
    _escribir_corrida(tmp_path, con_figuras=False)

    html = construir_html(tmp_path)

    assert "data:image/png;base64," not in html
    assert "Comparación por escenario" in html


def test_replica_sin_vehiculos_no_se_vuelve_cero(tmp_path):
    """Una metrica vacia se omite del pareo, no entra como 0.0."""
    _escribir_corrida(tmp_path)
    ruta = tmp_path / "replicas.csv"
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    # Vacia las metricas de espera de la primera replica de demanda_alta.
    lineas[1] = "demanda_alta,1,unica,0,,,"
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    html = construir_html(tmp_path)

    assert "None" not in html
    assert "nan" not in html


def test_falla_claro_si_falta_el_csv(tmp_path):
    with pytest.raises(FileNotFoundError):
        construir_html(tmp_path)
