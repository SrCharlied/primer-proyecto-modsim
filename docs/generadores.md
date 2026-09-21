# Generadores exponenciales

**Responsable:** Denis — Persona 2

Este módulo genera los tiempos aleatorios que después utilizará la simulación de la gasolinera. El motor no genera aleatoriedad por su cuenta: recibe los tiempos ya calculados. Por eso, los dos métodos se implementan bajo una misma función pública:

```python
generar_exponenciales(metodo, tasa, cantidad, rng)
```

La tasa se expresa en sucesos por minuto. Para una variable exponencial con tasa `λ`, la media teórica es `1/λ` minutos.

## 1. Transformada inversa

La función de distribución acumulada de una exponencial es:

\[
F(x)=1-e^{-\lambda x}
\]

Si se genera `U ~ Uniforme[0,1)`, se puede despejar `X`:

\[
X=\frac{-\ln(1-U)}{\lambda}
\]

En el código se utiliza `log1p(-U)` en lugar de calcular `log(1-U)` directamente, porque es más estable numéricamente cuando `U` está cerca de cero.

Algoritmo:

```text
Generar U uniforme en [0,1)
X = -ln(1-U) / λ
Devolver X
```

Este método genera cada muestra de forma directa y no necesita descartar candidatos.

## 2. Aceptación-rechazo

La distribución objetivo también es exponencial con tasa `λ`:

\[
f(x)=\lambda e^{-\lambda x}
\]

Se utiliza como propuesta una exponencial más ancha con tasa `λ/2`:

\[
g(x)=\frac{\lambda}{2}e^{-\lambda x/2}
\]

La constante envolvente acordada es:

\[
M=2
\]

porque:

\[
\frac{f(x)}{g(x)}=2e^{-\lambda x/2}\leq 2
\]

Por lo tanto, para un candidato `Y`, la probabilidad de aceptación es:

\[
\frac{f(Y)}{Mg(Y)}=e^{-\lambda Y/2}
\]

El candidato se genera con:

\[
Y=\frac{-2\ln(1-U)}{\lambda}
\]

Algoritmo:

```text
Repetir:
    generar U y V uniformes independientes en [0,1)
    Y = -2 ln(1-U) / λ
    si V < exp(-λY/2):
        aceptar Y
```

La tasa de aceptación teórica es `1/M = 0.5`, por lo que se esperan aproximadamente dos candidatos por cada muestra aceptada. Un candidato rechazado no representa un vehículo perdido; únicamente es un intento interno del generador.

## 3. Contrato y reproducibilidad

Los dos métodos cumplen las mismas reglas:

- `metodo` debe ser `"inversa"` o `"rechazo"`.
- `tasa` debe ser real, positiva y finita.
- `cantidad` debe ser un entero no negativo.
- `rng` debe ser un `numpy.random.Generator` creado por quien llama.
- La salida es un arreglo unidimensional `float64`, de longitud exacta, finito y no negativo.
- El módulo no crea semillas internas ni utiliza el estado aleatorio global.
- Con la misma semilla, método y parámetros se reproduce exactamente la misma muestra dentro del mismo entorno.

Para aceptación-rechazo también se incluye el auxiliar:

```python
generar_rechazo_con_estadisticas(tasa, cantidad, rng)
```

Este devuelve las muestras y el número total de candidatos utilizados. Esa información permite que la parte de validación calcule posteriormente la tasa de aceptación observada.

## 4. Manejo de casos extremos

Pedir cero muestras devuelve un arreglo vacío. Si una tasa extremadamente pequeña provoca valores fuera del rango de `float64`, el generador reporta un `ErrorDeContrato`; no se recortan valores grandes ni se sustituyen infinitos por cero.

Las pruebas del módulo revisan parámetros inválidos, longitud, tipo de salida, reproducibilidad, muestras vacías, muestras grandes, el conteo de candidatos y un caso controlado donde aceptación-rechazo descarta un candidato antes de aceptar el siguiente.
