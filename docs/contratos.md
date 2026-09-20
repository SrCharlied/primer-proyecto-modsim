# Contratos entre módulos

Responsable: Persona 1 (Charlie). Fuente de verdad: `gasolinera/contratos.py`.

Este documento existe para que las cuatro personas puedan trabajar en
paralelo sin coordinarse en cada paso. **Nadie cambia una firma, un nombre de
campo ni una unidad unilateralmente**: se propone, se acuerda y se actualiza
aquí y en el código en el mismo cambio.

## 1. Reglas generales

- Tiempo en **minutos**, tasas en **sucesos por minuto**.
- Los errores de contrato se lanzan como `ErrorDeContrato`, que hereda de
  `ValueError`. Quien solo quiera capturar `ValueError` sigue funcionando.
- Ningún módulo modifica las entradas que recibe.
- Ningún módulo usa el estado aleatorio global de NumPy ni resiembra el
  generador que le pasan.

## 2. Vocabulario cerrado

| Constante | Valor | Uso |
|---|---|---|
| `POLITICA_FILA_UNICA` | `"unica"` | Política A |
| `POLITICA_FILAS_INDEPENDIENTES` | `"independientes"` | Política B |
| `METODO_INVERSA` | `"inversa"` | Transformada inversa directa |
| `METODO_RECHAZO` | `"rechazo"` | Aceptación-rechazo, Exp(λ/2), M = 2 |
| `PERCENTIL_ESPERA` | `95.0` | Percentil reportado |
| `METODO_PERCENTIL` | `"linear"` | Interpolación lineal (`numpy.percentile`) |

Usar las constantes, no los literales. Si el equipo renombra una política, el
cambio se propaga solo.

## 3. Generadores — Persona 2 (Denis)

```python
def generar_exponenciales(metodo, tasa, cantidad, rng) -> numpy.ndarray:
    """Devuelve un numpy.ndarray unidimensional de muestras exponenciales."""
```

| Parámetro | Regla |
|---|---|
| `metodo` | `"inversa"` o `"rechazo"` |
| `tasa` | real positivo y finito |
| `cantidad` | entero **no negativo**; cero devuelve arreglo vacío |
| `rng` | `numpy.random.Generator` recibido desde afuera |

Salida: longitud **exacta** igual a `cantidad`, finita y no negativa, `float64`.

Reglas adicionales:

- No reiniciar semillas ni tocar el estado aleatorio global.
- Mismo método, misma semilla, mismos parámetros y mismo entorno reproducen
  exactamente la misma muestra.
- Usar `log1p(-U)` y uniformes en `[0, 1)` por cuidado numérico.
- No recortar tiempos grandes ni sustituir valores no finitos por cero: si
  una tasa extrema desborda el rango numérico, se reporta un error claro.

`validar_parametros_generador(metodo, tasa, cantidad, rng)` implementa estas
validaciones y devuelve `(metodo, tasa, cantidad)` normalizados. Llamarla al
inicio del generador evita reimplementar los mismos chequeos.

**Auxiliar permitido.** Persona 2 puede añadir
`generar_rechazo_con_estadisticas(tasa, cantidad, rng)` que devuelva muestras
y número de candidatos generados, y reutilizarlo desde el método público. El
contrato público no cambia. Un candidato rechazado es un intento del
generador, **no un vehículo perdido**.

## 4. Motor — Persona 1 (Charlie)

```python
def simular(llegadas, servicios, surtidores, politica, horizonte) -> ResultadoSimulacion:
    """No genera aleatoriedad."""
```

| Parámetro | Regla |
|---|---|
| `llegadas` | 1-D, finito, no decreciente, contenido en `[0, horizonte)` |
| `servicios` | 1-D, finito, no negativo, misma longitud que `llegadas` |
| `surtidores` | entero **positivo** |
| `politica` | `"unica"` o `"independientes"` |
| `horizonte` | real positivo y finito |

`validar_entradas_simulacion(...)` devuelve copias `float64` de solo lectura,
sin tocar los arreglos originales.

### `RegistroVehiculo`

| Campo | Tipo | Nota |
|---|---|---|
| `id` | `int` | Posición en la lista de entrada |
| `llegada` | `float` | |
| `duracion_servicio` | `float` | |
| `surtidor` | `int` | En `[0, surtidores)` |
| `inicio` | `float` | `>= llegada` |
| `fin` | `float` | `inicio + duracion_servicio` |
| `espera` | `float` | Propiedad derivada: `inicio - llegada` |
| `permanencia` | `float` | Propiedad derivada: `fin - llegada` |

`espera` y `permanencia` son **propiedades**, no campos almacenados: así no
pueden quedar desincronizadas de los instantes. Desde fuera se leen igual que
cualquier atributo. El registro es inmutable (`frozen`).

### `MetricasSimulacion`

| Campo | Tipo | Sin vehículos |
|---|---|---|
| `vehiculos_atendidos` | `int` | `0` |
| `espera_media` | `float \| None` | `None` |
| `proporcion_espera` | `float \| None` | `None` |
| `espera_p95` | `float \| None` | `None` |
| `utilizacion` | `tuple[float, ...]` | ceros, longitud = surtidores |

`None` se escribe como `null` en JSON. **Nunca se sustituye por `0.0`**: un
cero se promediaría entre réplicas como una espera realmente observada.

### `ResultadoSimulacion`

`registros`, `politica`, `horizonte`, `surtidores`, `metricas`.

## 5. Validación — Persona 3 (Diego)

Consume `generar_exponenciales`. Reporta, por método:

- Ajuste: media, varianza, histograma o densidad, CDF empírica contra teórica
  y una prueba de bondad de ajuste con la tasa **fijada de antemano**. Si la
  tasa se estimara de la misma muestra, el p-valor estándar no es válido sin
  corrección.
- Para `rechazo`: tasa de aceptación observada y candidatos por muestra.
- Rendimiento: `time.perf_counter`, repeticiones, tamaños y tasas
  equivalentes, excluyendo gráficos y escritura de archivos. Se reporta
  mediana y dispersión, y se declara si un método se vectoriza y el otro no.

Las conclusiones de ajuste, rendimiento y complejidad se reportan por
separado. No rechazar una hipótesis no demuestra que el generador sea
correcto, y un p-valor mayor no significa mejor método.

Los experimentos estadísticos van separados de los tests de software, para
que la suite no falle al azar.

## 6. Experimentos — Persona 4 (Micaela)

Consume `simular` y `generar_exponenciales`. Salidas acordadas:

| Archivo | Contenido |
|---|---|
| `replicas.csv` | escenario, réplica, política, métricas |
| `utilizacion.csv` | escenario, réplica, política, surtidor, utilización |
| `resumen.csv` | agregados y diferencias pareadas entre políticas, con incertidumbre |
| `metadatos.json` | parámetros completos, semilla raíz, método, versiones, commit si está disponible |

Reglas:

- Flujos RNG **separados** para llegadas y servicios, derivados de una semilla
  raíz con `SeedSequence`. Se documenta la asignación por escenario y réplica.
- Las llegadas se generan hasta el horizonte, **no** hasta una cantidad
  arbitraria de clientes.
- En cada réplica, **las mismas entradas** van a las dos políticas. No se
  sortea otra duración al asignar el surtidor.
- La incertidumbre de las diferencias pareadas se estima con **réplicas
  independientes**, no tratando a todos los vehículos de una corrida como
  observaciones independientes.

Persona 4 propone las columnas definitivas y Charlie revisa compatibilidad.

## 7. Cómo proponer un cambio de contrato

1. Abrir el tema con el equipo antes de escribir código.
2. Cambiar `gasolinera/contratos.py`, este documento y las pruebas afectadas
   en el **mismo** cambio.
3. Correr la suite completa.
4. Avisar a quien consuma el contrato.
