# Experimentos del sistema

## Objetivo

Comparar dos políticas de atención en una gasolinera:

- `unica`: todos los vehículos esperan en una sola fila.
- `independientes`: cada surtidor mantiene su propia fila.

La comparación principal estudia la espera y la utilización de los surtidores bajo diferentes niveles de demanda.

## Configuración

El archivo `configs/escenarios.json` define los parámetros reproducibles del experimento.

| Escenario | Tasa de llegadas | Tasa de servicio | Surtidores |
|---|---:|---:|---:|
| Demanda baja | 0.20 por minuto | 0.10 por minuto | 4 |
| Demanda media | 0.30 por minuto | 0.10 por minuto | 4 |
| Demanda alta | 0.38 por minuto | 0.10 por minuto | 4 |

Cada escenario utiliza:

- Horizonte de 480 minutos.
- 30 réplicas independientes.
- Semilla raíz 2026.
- Método de generación exponencial `inversa`.

Los parámetros representan escenarios académicos hipotéticos y no mediciones de una gasolinera real.

## Reproducibilidad

Se utiliza `numpy.random.SeedSequence` para derivar flujos aleatorios separados para llegadas y servicios.

En cada réplica se genera una sola lista de llegadas y una sola lista de duraciones de servicio. Esas mismas entradas se entregan a las políticas `unica` e `independientes`. Esto permite realizar una comparación pareada sin atribuir a la política diferencias ocasionadas por entradas aleatorias distintas.

La primera llegada ocurre después del primer tiempo entre llegadas. Solo se admiten llegadas estrictamente anteriores al horizonte.

## Métricas y archivos

El experimento genera:

- `replicas.csv`: métricas de cada réplica y política.
- `utilizacion.csv`: utilización de cada surtidor.
- `resumen.csv`: diferencias pareadas de espera e intervalos del 95 %.
- `metadatos.json`: configuración utilizada.
- `espera_media.png`: comparación gráfica de espera.
- `utilizacion_media.png`: comparación gráfica de utilización.

La diferencia pareada se define como:

```text
espera de filas independientes - espera de fila única
```

Un valor positivo significa que las filas independientes esperan mas.
