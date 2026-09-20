# Modelo del sistema

Responsable: Persona 1 (Charlie). Documento de referencia para las reglas del
motor. Cualquier cambio se acuerda con el equipo antes de editarlo.

## 1. Qué se modela

Una gasolinera con varios surtidores idénticos. Los vehículos llegan, esperan
si hace falta, se atienden y se van. Se comparan dos formas de organizar la
espera:

- **Fila única** (`unica`): una sola cola alimenta a todos los surtidores.
- **Filas independientes** (`independientes`): cada surtidor tiene su propia
  cola y el vehículo no se cambia de fila.

## 2. Supuestos

- Tiempos entre llegadas exponenciales, con tasa constante dentro de cada
  escenario.
- Tiempos de servicio exponenciales, independientes entre vehículos e
  independientes de las llegadas.
- Surtidores idénticos e intercambiables.
- Sin abandono, sin prioridades y sin cambios de fila.
- Sin inventario, pagos, reabastecimiento, tipos de combustible ni carga
  parcial o completa.

**Limitación declarada.** La exponencial de servicio admite tiempos
arbitrariamente cortos y tiene cola larga: no modela litros ni un tiempo
mínimo de operación. Es una simplificación académica, no una descripción del
proceso real de despacho. Los parámetros que se usen sin medición de campo se
presentan como escenarios hipotéticos, nunca como datos observados.

## 3. Unidades

- Tiempo en **minutos**.
- Tasas en **sucesos por minuto**.
- Una tasa `λ` corresponde a una media `1/λ`. **No son sinónimos.** Es el
  error más fácil de cometer al leer un escenario y el más caro de detectar
  después.

## 4. Reglas de tiempo y cierre

1. El sistema arranca **vacío**. Es un estudio de **horizonte finito**, no de
   régimen estacionario.
2. La primera llegada ocurre después del primer tiempo entre llegadas. No se
   coloca automáticamente un vehículo en el instante cero.
3. Se admiten llegadas en `[0, horizonte)`. El extremo derecho es **abierto**:
   un vehículo que llega exactamente en el horizonte ya no entra.
4. Terminado el horizonte no se admiten más llegadas, pero **sí se termina de
   atender** a todos los admitidos.
5. Las métricas de espera incluyen a **todos los admitidos**, incluso a
   quienes terminan de ser atendidos después del cierre. Recortar sus esperas
   sesgaría el resultado justo en los escenarios más congestionados.
6. La **utilización** se mide únicamente dentro de `[0, horizonte)`: cada
   intervalo de servicio se recorta a esa ventana antes de sumarse. Así queda
   siempre en `[0, 1]`.
7. Las llegadas se procesan en orden. Ante llegadas simultáneas, desempata el
   **identificador del vehículo** (su posición en la lista de entrada).
8. Si una salida coincide exactamente con una llegada, el surtidor **se
   considera liberado**: el vehículo que llega no espera.

## 5. Política A — fila única

Al llegar un vehículo:

1. Se elige el surtidor con **menor próxima disponibilidad**.
2. Ante empate, gana el surtidor de **menor identificador**.
3. El servicio comienza en `max(llegada, disponibilidad del surtidor)`.
4. La disponibilidad del surtidor se actualiza al fin de ese servicio.

## 6. Política B — filas independientes

Al llegar un vehículo:

1. Para cada surtidor se cuentan los vehículos ya asignados cuyo **fin es
   posterior** al instante de esta llegada. Esto incluye al que está siendo
   atendido en ese momento.
2. Se elige el surtidor con **menor conteo**.
3. Ante empate, gana el surtidor de **menor identificador**.
4. El vehículo se queda en esa fila y se atiende después del último asignado
   a ese surtidor: el servicio comienza en `max(llegada, fin del último
   asignado)`.

**La decisión observa cantidad de vehículos, no sus duraciones futuras.** Un
conductor real ve cuántos autos hay delante, no cuánto va a tardar cada uno.
Elegir retrospectivamente la fila con menor tiempo total sería hacer trampa
con información que el conductor no tiene, y convertiría esta política en una
variante de la fila única.

## 7. Métricas

| Métrica | Definición |
|---|---|
| `vehiculos_atendidos` | Total de admitidos en `[0, horizonte)`, incluidos los que terminan después del cierre. |
| `espera_media` | Promedio de `inicio - llegada` sobre todos los admitidos. |
| `proporcion_espera` | Fracción de admitidos con espera **estrictamente** positiva. |
| `espera_p95` | Percentil 95 de la espera. |
| `utilizacion` | Por surtidor: tiempo ocupado dentro del horizonte dividido entre el horizonte. |

**Método de percentil.** Interpolación lineal entre los órdenes estadísticos
contiguos, es decir el predeterminado de `numpy.percentile`
(`method="linear"`). Queda fijado en `contratos.METODO_PERCENTIL` para que el
informe pueda citarlo y para que nadie lo cambie sin que se note.

**Sin vehículos admitidos.** `vehiculos_atendidos` es `0` y la utilización es
`0.0` en todos los surtidores, porque ambos son conteos observados. Las tres
métricas de espera son `None` (`null` en JSON): no son estimables. **No se
sustituyen por cero**, porque un cero se promediaría con las demás réplicas
como si fuera una espera realmente observada.

## 8. Caso conocido

El caso de `tests/fixtures/caso_pequeno.json` se derivó **aplicando las reglas
a mano**, no ejecutando el motor. Sirve como definición operativa del modelo:
si el motor y este caso discrepan, se revisa el motor.

**Entrada:** 2 surtidores, horizonte 12.5 minutos.

| id | llegada | duración |
|---|---|---|
| 0 | 1.0 | 10.0 |
| 1 | 1.5 | 2.0 |
| 2 | 2.0 | 2.0 |
| 3 | 2.5 | 1.0 |

### Fila única

| id | surtidor | inicio | fin | espera | razón |
|---|---|---|---|---|---|
| 0 | 0 | 1.0 | 11.0 | 0.0 | ambos libres, desempate por id de surtidor |
| 1 | 1 | 1.5 | 3.5 | 0.0 | s0 se libera en 11.0, s1 en 0.0 |
| 2 | 1 | 3.5 | 5.5 | 1.5 | s1 se libera antes (3.5 contra 11.0) |
| 3 | 1 | 5.5 | 6.5 | 3.0 | s1 sigue siendo el primero en liberarse |

- Esperas: `[0.0, 0.0, 1.5, 3.0]` → media `1.125`, proporción `0.5`.
- p95 sobre `[0.0, 0.0, 1.5, 3.0]`: posición `0.95·3 = 2.85` → `1.5 + 0.85·1.5 = 2.775`.
- Utilización s0: `[1.0, 11.0]` = 10.0 → `10.0/12.5 = 0.8`.
- Utilización s1: `2.0 + 2.0 + 1.0` = 5.0 → `5.0/12.5 = 0.4`.

### Filas independientes

| id | surtidor | inicio | fin | espera | razón |
|---|---|---|---|---|---|
| 0 | 0 | 1.0 | 11.0 | 0.0 | ambas filas vacías, desempate por id |
| 1 | 1 | 1.5 | 3.5 | 0.0 | s0 tiene 1 vehículo, s1 tiene 0 |
| 2 | 0 | 11.0 | 13.0 | 9.0 | empate 1 a 1 en 2.0, desempate por id |
| 3 | 1 | 3.5 | 4.5 | 1.0 | s0 tiene 2, s1 tiene 1 |

- Esperas: `[0.0, 0.0, 9.0, 1.0]` → media `2.5`, proporción `0.5`.
- p95 sobre `[0.0, 0.0, 1.0, 9.0]`: `1.0 + 0.85·8.0 = 7.8`.
- Utilización s0: `[1.0, 11.0]` más `[11.0, 13.0]` **recortado a 12.5** →
  `10.0 + 1.5 = 11.5` → `11.5/12.5 = 0.92`.
- Utilización s1: `2.0 + 1.0` = 3.0 → `3.0/12.5 = 0.24`.

### Por qué este caso

Con **exactamente las mismas entradas**, las dos políticas producen
resultados distintos. Eso es lo que se quiere medir en el proyecto y lo que
hace útil al fixture:

| | fila única | filas independientes |
|---|---|---|
| espera media | 1.125 | 2.5 |
| espera p95 | 2.775 | 7.8 |
| utilización | `[0.8, 0.4]` | `[0.92, 0.24]` |

El vehículo 2 es el caso interesante: en el instante 2.0 cada surtidor tiene
un vehículo pendiente, así que la política B desempata hacia el surtidor 0 y
lo deja esperando 9 minutos detrás de un servicio largo, aunque el surtidor 1
se libere en 3.5. La política A ve las disponibilidades y lo manda al
surtidor 1. Ese contraste es precisamente el costo de no poder cambiar de
fila.

Además, el servicio del vehículo 2 bajo la política B termina en 13.0, después
del cierre en 12.5: el caso ejercita a la vez el recorte de la utilización y
la inclusión de la espera de quien sale después del horizonte.

## 9. Casos límite acordados

- **Entrada vacía:** cero vehículos, utilización cero, métricas de espera `None`.
- **Un solo surtidor:** las dos políticas **deben coincidir**, porque una sola
  cola y una sola fila por surtidor son el mismo sistema. Es la prueba de
  sanidad más barata del motor.
- **Llegadas simultáneas:** se procesan en orden de identificador de vehículo.
- **Servicio de duración cero:** válido. Entra, se atiende y sale en el mismo
  instante.
- **Llegada exactamente en el horizonte:** rechazada por el contrato.
- El motor **no consume aleatoriedad**: recibe llegadas y duraciones ya
  sorteadas. Esa es la condición que permite pasar las mismas entradas a las
  dos políticas dentro de una réplica.
