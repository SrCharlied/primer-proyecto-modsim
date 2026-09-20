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
| **B — Trabajo paralelo:** motor, generadores, validación, experimentos | En curso |
| **C — Integración** | Pendiente |
| **D — Evidencia e informe** | Pendiente |

`gasolinera/simulacion.py` está **especificado pero no implementado**. Las
pruebas de `tests/test_simulacion.py` fallan a propósito: es el paso rojo del
ciclo TDD acordado. Los módulos de `generadores.py`, `validacion.py`,
`experimentos.py` y `visualizacion.py` son marcadores que indican a quién le
corresponden.

No hay resultados cargados en el repositorio. Cuando los haya, se versionará
solo evidencia seleccionada junto con su configuración de reproducción.

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

# Solo lo que ya está terminado (Hito A)
python -m pytest tests/test_contratos.py -q
```

Los siguientes comandos son **interfaces por implementar**, no herramientas
disponibles todavía:

```powershell
python -m scripts.validar_generadores --config configs/escenarios.json --salida resultados/generadores
python -m scripts.ejecutar_experimentos --config configs/escenarios.json --salida resultados/sistema
```

## Estructura

```text
gasolinera/
  contratos.py      Tipos, unidades y validaciones compartidas   [Persona 1]
  simulacion.py     Motor determinista de las dos políticas      [Persona 1]
  generadores.py    Exponenciales: inversa y aceptación-rechazo  [Persona 2]
  validacion.py     Ajuste, tasa de aceptación y rendimiento     [Persona 3]
  experimentos.py   Escenarios, réplicas y exportación           [Persona 4]
  visualizacion.py  Figuras del informe                          [Persona 4]
scripts/            Puntos de entrada ejecutables
configs/            Escenarios                                   [Persona 4]
tests/              Pruebas y el caso pequeño calculado a mano
docs/               Modelo, contratos y documentos por módulo
resultados/         Salidas generadas (ignoradas por git)
```

## Documentación

| Documento | Contenido |
|---|---|
| [`docs/modelo.md`](docs/modelo.md) | Supuestos, unidades, reglas de cierre, las dos políticas, métricas y el caso conocido con su derivación paso a paso. |
| [`docs/contratos.md`](docs/contratos.md) | Firmas, tipos y reglas que comparten los cuatro módulos. |

Faltan `generadores.md`, `validacion.md`, `experimentos.md` e `informe.md`,
que escribe cada responsable.

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
