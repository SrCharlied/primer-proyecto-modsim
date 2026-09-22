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


# --- comparacion de generadores -------------------------------------------


def _escribir_generadores(carpeta):
    """Deja en `carpeta` una corrida minima de validar_generadores."""
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "ajuste.csv").write_text(
        "metodo,tasa,n,media_observada,media_teorica,varianza_observada,"
        "varianza_teorica,ks_estadistico,p_valor,alpha,rechaza_h0\n"
        "inversa,1.0,500,0.99,1.0,1.01,1.0,0.02,0.51,0.05,False\n"
        "rechazo,1.0,500,1.01,1.0,0.99,1.0,0.03,0.33,0.05,False\n",
        encoding="utf-8",
    )
    (carpeta / "aceptacion.csv").write_text(
        "tasa,muestras_aceptadas,candidatos_generados,tasa_aceptacion_observada,"
        "tasa_aceptacion_teorica,candidatos_por_muestra,uniformes_por_muestra\n"
        "1.0,2000,4010,0.4988,0.5,2.005,4.01\n",
        encoding="utf-8",
    )
    (carpeta / "rendimiento.csv").write_text(
        "metodo,tasa,tamano,repeticiones,mediana_s,media_s,desviacion_s,"
        "minimo_s,maximo_s,microsegundos_por_muestra,vectorizado\n"
        "inversa,1.0,1000,5,0.0001,0.0001,0.0,0.0001,0.0002,0.1,True\n"
        "rechazo,1.0,1000,5,0.0100,0.0100,0.0,0.0090,0.0110,10.0,False\n",
        encoding="utf-8",
    )


def test_incluye_la_comparacion_de_generadores(tmp_path):
    _escribir_corrida(tmp_path)
    gen = tmp_path / "generadores"
    _escribir_generadores(gen)

    html = construir_html(tmp_path, gen)

    assert "Comparación de los métodos de generación" in html
    assert "rechazo" in html
    assert "Kolmog" in html
    # La tasa de aceptacion y su valor teorico deben aparecer juntos.
    assert "0.4988" in html
    assert "1/M" in html


def test_omite_los_generadores_si_no_se_corrieron(tmp_path):
    """El reporte de políticas sigue siendo válido sin esa parte."""
    _escribir_corrida(tmp_path)

    html = construir_html(tmp_path, tmp_path / "no_existe")

    assert "Comparación de los métodos de generación" not in html
    assert "Comparación por escenario" in html


def test_omite_los_generadores_si_no_se_pasa_la_carpeta(tmp_path):
    _escribir_corrida(tmp_path)
    _escribir_generadores(tmp_path / "generadores")

    html = construir_html(tmp_path)

    assert "Comparación de los métodos de generación" not in html


def test_declara_que_el_tiempo_no_es_el_costo_del_metodo(tmp_path):
    """Sin ese desglose, el 100x medido se lee como costo del algoritmo."""
    _escribir_corrida(tmp_path)
    gen = tmp_path / "generadores"
    _escribir_generadores(gen)

    html = construir_html(tmp_path, gen)

    assert "no es el costo del método" in html
    assert "4&times;" in html or "4×" in html
    assert "vectoriz" in html


def test_aclara_que_un_rechazo_no_es_un_vehiculo_perdido(tmp_path):
    _escribir_corrida(tmp_path)
    gen = tmp_path / "generadores"
    _escribir_generadores(gen)

    html = construir_html(tmp_path, gen)

    assert "no un vehículo que abandona la gasolinera" in html


def test_funciona_sin_las_figuras_de_generadores(tmp_path):
    _escribir_corrida(tmp_path, con_figuras=False)
    gen = tmp_path / "generadores"
    _escribir_generadores(gen)

    html = construir_html(tmp_path, gen)

    assert "data:image/png;base64," not in html
    assert "Comparación de los métodos de generación" in html
