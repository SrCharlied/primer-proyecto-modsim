from gasolinera.visualizacion import graficar_espera_media


def test_graficar_espera_media_crea_imagen(tmp_path):
    filas = [
        {
            "escenario": "baja",
            "politica": "unica",
            "espera_media": 1.0,
        },
        {
            "escenario": "baja",
            "politica": "independientes",
            "espera_media": 2.0,
        },
        {
            "escenario": "alta",
            "politica": "unica",
            "espera_media": 5.0,
        },
        {
            "escenario": "alta",
            "politica": "independientes",
            "espera_media": 8.0,
        },
    ]

    ruta = tmp_path / "espera_media.png"

    graficar_espera_media(filas, ruta)

    assert ruta.exists()
    assert ruta.stat().st_size > 0
    
def test_graficar_utilizacion_media_crea_imagen(tmp_path):
    from gasolinera.visualizacion import graficar_utilizacion_media

    utilizaciones = [
        {
            "escenario": "baja",
            "politica": "unica",
            "surtidor": 1,
            "utilizacion": 0.45,
        },
        {
            "escenario": "baja",
            "politica": "independientes",
            "surtidor": 1,
            "utilizacion": 0.50,
        },
        {
            "escenario": "alta",
            "politica": "unica",
            "surtidor": 1,
            "utilizacion": 0.90,
        },
        {
            "escenario": "alta",
            "politica": "independientes",
            "surtidor": 1,
            "utilizacion": 0.85,
        },
    ]

    ruta = tmp_path / "utilizacion_media.png"

    graficar_utilizacion_media(utilizaciones, ruta)

    assert ruta.exists()
    assert ruta.stat().st_size > 0