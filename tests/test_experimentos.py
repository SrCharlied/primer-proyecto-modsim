import numpy as np

from gasolinera.experimentos import (
    cargar_escenarios,
    generar_entradas_replica,
)


def test_cargar_escenarios():
    config = cargar_escenarios("configs/escenarios.json")

    assert config["semilla_raiz"] == 2026
    assert config["replicas"] == 30
    assert len(config["escenarios"]) == 3


def test_generar_entradas_replica():
    secuencia = np.random.SeedSequence(12345)
    rng_llegadas, rng_servicios = [
        np.random.default_rng(semilla)
        for semilla in secuencia.spawn(2)
    ]

    llegadas, servicios = generar_entradas_replica(
        tasa_llegadas=0.2,
        tasa_servicio=0.1,
        horizonte=60.0,
        rng_llegadas=rng_llegadas,
        rng_servicios=rng_servicios,
        metodo="inversa",
    )

    assert isinstance(llegadas, np.ndarray)
    assert isinstance(servicios, np.ndarray)
    assert len(llegadas) == len(servicios)
    assert np.all(llegadas >= 0)
    assert np.all(llegadas < 60.0)
    assert np.all(np.diff(llegadas) >= 0)
    assert np.all(servicios >= 0)

def test_ejecutar_replica_compara_las_dos_politicas():
    from gasolinera.experimentos import ejecutar_replica

    escenario = {
        "nombre": "prueba",
        "tasa_llegadas": 0.2,
        "tasa_servicio": 0.1,
        "surtidores": 4,
    }

    resultados = ejecutar_replica(
        escenario=escenario,
        horizonte=60.0,
        metodo="inversa",
        semilla=12345,
    )

    assert set(resultados) == {"unica", "independientes"}

    unica = resultados["unica"]
    independientes = resultados["independientes"]

    assert unica.politica == "unica"
    assert independientes.politica == "independientes"
    assert unica.metricas.vehiculos_atendidos == independientes.metricas.vehiculos_atendidos

    llegadas_unica = [registro.llegada for registro in unica.registros]
    llegadas_independientes = [
        registro.llegada for registro in independientes.registros
    ]

    assert llegadas_unica == llegadas_independientes

def test_ejecutar_experimentos_genera_filas_de_resultados():
    from gasolinera.experimentos import ejecutar_experimentos

    config = {
        "semilla_raiz": 2026,
        "replicas": 2,
        "horizonte": 60.0,
        "metodo": "inversa",
        "escenarios": [
            {
                "nombre": "prueba",
                "tasa_llegadas": 0.2,
                "tasa_servicio": 0.1,
                "surtidores": 4,
            }
        ],
    }

    filas, utilizaciones = ejecutar_experimentos(config)

    # 1 escenario × 2 réplicas × 2 políticas
    assert len(filas) == 4

    # 4 surtidores para cada una de las cuatro simulaciones
    assert len(utilizaciones) == 16

    for fila in filas:
        assert fila["escenario"] == "prueba"
        assert fila["politica"] in {"unica", "independientes"}
        assert fila["vehiculos_atendidos"] >= 0

def test_guardar_resultados_crea_archivos(tmp_path):
    from gasolinera.experimentos import guardar_resultados

    filas = [
        {
            "escenario": "prueba",
            "replica": 1,
            "politica": "unica",
            "vehiculos_atendidos": 10,
            "espera_media": 2.5,
            "proporcion_espera": 0.4,
            "espera_p95": 6.0,
        }
    ]

    utilizaciones = [
        {
            "escenario": "prueba",
            "replica": 1,
            "politica": "unica",
            "surtidor": 1,
            "utilizacion": 0.75,
        }
    ]

    config = {
        "semilla_raiz": 2026,
        "replicas": 1,
        "horizonte": 60.0,
        "metodo": "inversa",
        "escenarios": [],
    }

    guardar_resultados(
        filas=filas,
        utilizaciones=utilizaciones,
        config=config,
        carpeta_salida=tmp_path,
    )

    assert (tmp_path / "replicas.csv").exists()
    assert (tmp_path / "utilizacion.csv").exists()
    assert (tmp_path / "metadatos.json").exists()
    