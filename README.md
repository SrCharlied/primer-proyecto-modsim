# primer-proyecto-modsim

Simulación de una gasolinera. Primer proyecto de Modelación y Simulación.

Se responden dos preguntas **independientes**:

1. **Política de filas.** ¿Cómo cambian la espera y la utilización de los
   surtidores al organizar la atención en una **fila única** frente a **filas
   independientes**, bajo distintas demandas?
2. **Generación de aleatorios.** ¿Cómo se comparan dos métodos de generación
   de variables exponenciales: **transformada inversa directa** y
   **aceptación-rechazo** con propuesta Exp(λ/2) y M = 2?

> Las dos políticas de filas **no sustituyen** a los dos métodos generadores.
> Son comparaciones distintas y se reportan por separado.

## Estado

| Hito | Estado |
|---|---|
| **A — Base:** estructura, contratos, caso conocido | Listo |
| **B — Trabajo paralelo:** motor, generadores, validación, experimentos | Listo |
| **C — Integración** | Listo |
| **D — Evidencia e informe** | Resultados listos; informe y documentos en curso |

**El código está completo y probado**, con **152 pruebas en verde**. Los cinco
módulos de `gasolinera/` están implementados y las **dos preguntas del proyecto
tienen evidencia reproducible**: el experimento de filas corre en ~1.5 s y la
comparación de generadores en ~25 s.

Resultado principal: la **fila única** produce menor espera media y menor
percentil 95 en los tres niveles de demanda, con intervalos del 95 % que
excluyen el cero. La utilización promedio es prácticamente igual entre las dos
políticas, así que **no sirve para compararlas**. Los dos generadores son
estadísticamente equivalentes y difieren solo en costo. Los detalles están en
[`docs/Informe_gasolinera_borrador_revisado.md`](docs/Informe_gasolinera_borrador_revisado.md).

### Pendientes

| Pendiente | Responsable |
|---|---|
| `docs/validacion.md` | Diego |
| Barras de error en las figuras y orden por nivel de demanda | Micaela |
| `metadatos.json` con versiones y commit; `resumen.csv` con p95 y proporción | Micaela |
| Trasladar el informe al formato del curso (`docs/Sim.md`) | Todos |

Las salidas de `resultados/` no se versionan: se regeneran con el comando de la
sección de uso a partir de `configs/escenarios.json`.

## Instalación (Windows PowerShell)

Requiere Git y **Python 3.12** (el entorno de referencia usa 3.12.2).

```powershell
git clone https://github.com/SrCharlied/primer-proyecto-modsim.git
cd primer-proyecto-modsim
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

Si la activación está bloqueada por la política de ejecución, no hace falta
cambiar nada del sistema: se puede usar directamente el ejecutable del
entorno.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Ejecutar siempre desde la raíz del repositorio.

## Uso

```powershell
# Suite completa
python -m pytest -q

# Solo el motor y sus contratos
python -m pytest tests/test_contratos.py tests/test_simulacion.py -q
```

Experimento completo: 3 escenarios × 30 réplicas × 2 políticas. Genera los CSV,
`metadatos.json`, dos figuras y un **reporte HTML** con todo junto.

```powershell
python -m scripts.ejecutar_experimentos --config configs/escenarios.json --salida resultados/sistema
ii resultados\sistema\reporte.html
```

Comparación de los dos métodos de generación, que es la **segunda pregunta** del
proyecto y es independiente de la comparación de filas. Tarda ~25 s, casi todo en
el bucle de aceptación-rechazo:

```powershell
python -m scripts.validar_generadores --config configs/escenarios.json --salida resultados/generadores
```

Genera `ajuste.csv`, `aceptacion.csv`, `rendimiento.csv`, `metadatos.json` y dos
figuras. **Si esta carpeta existe, el reporte HTML la incluye solo**, así que
corriendo los dos comandos en orden queda un único archivo con todo:

```powershell
python -m scripts.ejecutar_experimentos --config configs/escenarios.json --salida resultados/sistema
python -m scripts.validar_generadores  --config configs/escenarios.json --salida resultados/generadores
python -m scripts.reporte_html --resultados resultados/sistema
ii resultados\sistema\reporte.html
```

El reporte es **un solo archivo autocontenido**: las figuras van incrustadas y no
carga nada de internet, así que se abre con doble clic en cualquier computadora y
sirve para presentar o imprimir a PDF desde el navegador.

## Estructura

```text
gasolinera/
  contratos.py      Tipos, unidades y validaciones compartidas   [Persona 1]
  simulacion.py     Motor determinista de las dos políticas      [Persona 1]
  generadores.py    Exponenciales: inversa y aceptación-rechazo  [Persona 2]
  validacion.py     Ajuste, tasa de aceptación y rendimiento     [Persona 3]
  experimentos.py   Escenarios, réplicas y exportación           [Persona 4]
  visualizacion.py  Figuras del informe                          [Persona 4]
scripts/
  ejecutar_experimentos.py  Corre los escenarios y escribe todo   [Persona 4]
  validar_generadores.py    Compara inversa contra rechazo        [Persona 3]
  reporte_html.py           Reporte visual autocontenido          [Persona 1]
configs/            Escenarios                                   [Persona 4]
tests/              Pruebas y el caso pequeño calculado a mano
docs/               Modelo, contratos y documentos por módulo
resultados/         Salidas generadas (ignoradas por git)
```

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/Informe_gasolinera_borrador_revisado.md`](docs/Informe_gasolinera_borrador_revisado.md) | **Informe completo:** planteamiento, modelo, métodos, resultados medidos, análisis y conclusiones. Es el texto que se traslada a `docs/Sim.md`. |
| [`docs/Sim.md`](docs/Sim.md) | Informe en el formato del curso. Se trabaja en Word Online; esta copia es una instantánea. |
| [`docs/modelo.md`](docs/modelo.md) | Supuestos, unidades, reglas de cierre, las dos políticas, métricas y el caso conocido con su derivación paso a paso. |
| [`docs/contratos.md`](docs/contratos.md) | Firmas, tipos y reglas que comparten los cuatro módulos. |
| [`docs/generadores.md`](docs/generadores.md) | Derivación y algoritmos de los dos métodos de generación. |
| [`docs/experimentos.md`](docs/experimentos.md) | Configuración, reproducibilidad y archivos de salida. |

Falta `docs/validacion.md`, que escribe Persona 3.

## Reparto

| Persona | Responsabilidad |
|---|---|
| 1 — Charlie | Estructura, contratos y motor |
| 2 — Denis | Generadores exponenciales |
| 3 — Diego | Validación estadística y comparación de generadores |
| 4 — Micaela | Experimentos, visualización y demostración |

Revisiones cruzadas: Persona 2 revisa el motor, Persona 3 revisa los
generadores, Persona 4 revisa la reproducibilidad de la validación.

## Convenciones

- Código, documentación y mensajes de commit **en español**.
- Tiempo en **minutos**, tasas en **sucesos por minuto**. Una tasa `λ`
  corresponde a una media `1/λ`: no son sinónimos.
- **TDD:** se escribe la prueba, se confirma el fallo esperado, se implementa
  y se corre la suite afectada antes de integrar.
- Rutas relativas y `pathlib`. Nunca rutas absolutas de una computadora
  concreta.
- Nadie cambia contratos ni unidades unilateralmente.
- No se llenan módulos con éxitos falsos ni resultados inventados. Lo
  pendiente se marca como pendiente.

## Limitaciones declaradas

Los tiempos de servicio exponenciales son una **simplificación académica**:
admiten tiempos arbitrariamente cortos y tienen cola larga, así que no
modelan litros ni un tiempo mínimo de operación. Los parámetros que no
provengan de medición de campo se presentan como **escenarios hipotéticos**,
no como datos reales.
