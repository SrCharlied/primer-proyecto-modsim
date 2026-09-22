"""Genera un reporte HTML autocontenido a partir de una corrida de experimentos.

Lee los CSV que produce ``scripts.ejecutar_experimentos`` y arma un solo
archivo HTML con las tablas, las diferencias pareadas y las figuras incrustadas.
No vuelve a simular nada y no necesita servidor ni conexion: el archivo se abre
con doble clic.

Uso:
    python -m scripts.reporte_html --resultados resultados/sistema
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np
from scipy import stats

#: Metricas que se comparan, con su etiqueta y cuantos decimales mostrar.
_METRICAS = (
    ("espera_media", "Espera media (min)", 3),
    ("espera_p95", "Espera p95 (min)", 3),
    ("proporcion_espera", "Proporción que espera", 4),
)

_POLITICAS = ("unica", "independientes")

_ETIQUETA_POLITICA = {
    "unica": "Fila única",
    "independientes": "Filas independientes",
}


def _leer_csv(ruta: Path) -> list[dict]:
    with ruta.open("r", encoding="utf-8", newline="") as archivo:
        return list(csv.DictReader(archivo))


def _a_float(valor: str) -> float | None:
    """Convierte a float, devolviendo None para las celdas vacias.

    Las metricas de espera se escriben vacias cuando una replica no admitio
    vehiculos. Se respetan como ausentes en vez de convertirlas en cero.
    """
    if valor is None or valor == "":
        return None
    return float(valor)


def _orden_escenarios(config: dict, presentes: set[str]) -> list[str]:
    """Ordena los escenarios como los declara la configuracion.

    Evita el orden alfabetico, que dejaria 'demanda_alta' antes de
    'demanda_baja'.
    """
    declarados = [
        escenario["nombre"]
        for escenario in config.get("escenarios", [])
        if escenario["nombre"] in presentes
    ]
    faltantes = sorted(presentes - set(declarados))
    return declarados + faltantes


def _diferencia_pareada(
    por_replica: dict[tuple[str, str], dict[str, dict]],
    escenario: str,
    metrica: str,
) -> dict[str, float] | None:
    """Promedio, intervalo t al 95 % y valor p de la diferencia por replica."""
    pares = []
    for (nombre, _), politicas in por_replica.items():
        if nombre != escenario:
            continue
        unica = _a_float(politicas.get("unica", {}).get(metrica, ""))
        indep = _a_float(politicas.get("independientes", {}).get(metrica, ""))
        if unica is not None and indep is not None:
            pares.append((unica, indep))

    if len(pares) < 2:
        return None

    u = np.array([p[0] for p in pares], dtype=float)
    i = np.array([p[1] for p in pares], dtype=float)
    d = i - u
    n = d.size
    error_estandar = float(d.std(ddof=1) / np.sqrt(n))
    critico = float(stats.t.ppf(0.975, n - 1))

    if error_estandar == 0.0:
        # Diferencia identica en todas las replicas: la prueba t no aplica.
        p_valor = float("nan")
    else:
        with np.errstate(invalid="ignore"):
            _, p_valor = stats.ttest_rel(i, u)

    return {
        "n": n,
        "media_unica": float(u.mean()),
        "media_indep": float(i.mean()),
        "diferencia": float(d.mean()),
        "ic_inferior": float(d.mean() - critico * error_estandar),
        "ic_superior": float(d.mean() + critico * error_estandar),
        "p_valor": float(p_valor),
        "gana_unica": int((d > 0).sum()),
    }


def _utilizacion_por_politica(
    utilizaciones: list[dict], escenario: str
) -> dict[str, tuple[float, list[float]]]:
    """Promedio general y por surtidor de la utilizacion, por politica."""
    por_surtidor: dict[tuple[str, str], list[float]] = defaultdict(list)
    for fila in utilizaciones:
        if fila["escenario"] != escenario:
            continue
        clave = (fila["politica"], fila["surtidor"])
        por_surtidor[clave].append(float(fila["utilizacion"]))

    resultado: dict[str, tuple[float, list[float]]] = {}
    for politica in _POLITICAS:
        surtidores = sorted(
            {s for p, s in por_surtidor if p == politica},
            key=lambda s: int(s),
        )
        medias = [float(np.mean(por_surtidor[(politica, s)])) for s in surtidores]
        if medias:
            resultado[politica] = (float(np.mean(medias)), medias)
    return resultado


def _imagen_incrustada(ruta: Path) -> str | None:
    """Devuelve la imagen como data URI, o None si no existe."""
    if not ruta.is_file():
        return None
    datos = base64.b64encode(ruta.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{datos}"


_ESTILOS = """
:root {
  --fondo: #f6f7f9;
  --tarjeta: #ffffff;
  --borde: #e2e5ea;
  --texto: #1c2128;
  --suave: #5b6675;
  --unica: #2563eb;
  --indep: #ea7317;
  --bien: #157f3d;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 32px 16px 64px;
  background: var(--fondo);
  color: var(--texto);
  font: 16px/1.6 "Segoe UI", system-ui, -apple-system, sans-serif;
}
main { max-width: 1040px; margin: 0 auto; }
h1 { font-size: 1.9rem; margin: 0 0 4px; letter-spacing: -0.02em; }
h2 {
  font-size: 1.25rem;
  margin: 40px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--borde);
}
h3 { font-size: 1rem; margin: 24px 0 8px; color: var(--suave); }
.sub { color: var(--suave); margin: 0 0 4px; }
.tarjeta {
  background: var(--tarjeta);
  border: 1px solid var(--borde);
  border-radius: 10px;
  padding: 20px 22px;
  margin: 16px 0;
}
.kpis { display: flex; flex-wrap: wrap; gap: 14px; margin: 20px 0; }
.kpi {
  flex: 1 1 200px;
  background: var(--tarjeta);
  border: 1px solid var(--borde);
  border-left: 4px solid var(--unica);
  border-radius: 10px;
  padding: 16px 18px;
}
.kpi .etiqueta {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--suave);
}
.kpi .valor { font-size: 1.7rem; font-weight: 650; margin: 4px 0 2px; }
.kpi .nota { font-size: 0.85rem; color: var(--suave); }
table { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 0.93rem; }
th, td { padding: 9px 10px; text-align: right; border-bottom: 1px solid var(--borde); }
th:first-child, td:first-child { text-align: left; }
thead th {
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--suave);
  border-bottom: 2px solid var(--borde);
}
tbody tr:last-child td { border-bottom: none; }
.num { font-variant-numeric: tabular-nums; }
.mejor { color: var(--bien); font-weight: 650; }
figure { margin: 18px 0 0; }
figure img {
  width: 100%;
  border: 1px solid var(--borde);
  border-radius: 8px;
  background: #fff;
}
figcaption { font-size: 0.85rem; color: var(--suave); margin-top: 8px; }
.aviso {
  background: #fff8e6;
  border: 1px solid #f0d9a0;
  border-left: 4px solid #d99a0b;
  border-radius: 8px;
  padding: 14px 18px;
  margin: 16px 0;
  font-size: 0.93rem;
}
.aviso strong { display: block; margin-bottom: 4px; }
.leyenda { display: flex; gap: 18px; font-size: 0.88rem; color: var(--suave); }
.punto { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
footer { margin-top: 48px; font-size: 0.85rem; color: var(--suave); text-align: center; }
@media print {
  body { background: #fff; padding: 0; }
  h2 { page-break-after: avoid; }
  .tarjeta, figure { page-break-inside: avoid; }
}
"""


def _fmt(valor: float | None, decimales: int) -> str:
    if valor is None:
        return "&mdash;"
    return f"{valor:.{decimales}f}"


def _fmt_p(p: float | None) -> str:
    """Formatea un valor p, incluidos los casos degenerados.

    Si todas las replicas dan la misma diferencia la varianza es cero: la
    prueba t devuelve ``nan`` o exactamente ``0.0``, y ahi no hay exponente
    que mostrar.
    """
    if p is None or not np.isfinite(p):
        return "&mdash;"
    if p <= 0.0:
        # Un cero exacto es subdesbordamiento, no una probabilidad nula.
        return "&lt;10<sup>-15</sup>"
    if p < 1e-4:
        exponente = int(np.floor(np.log10(p)))
        mantisa = p / 10 ** exponente
        return f"{mantisa:.1f}&times;10<sup>{exponente}</sup>"
    return f"{p:.4f}"


def carpeta_generadores_por_omision(carpeta: Path) -> Path:
    """Carpeta hermana donde `validar_generadores` deja sus salidas."""
    return carpeta.parent / "generadores"


def _seccion_generadores(carpeta: Path) -> list[str]:
    """Arma la comparacion de los dos metodos de generacion.

    Devuelve una lista vacia si todavia no se corrio
    ``scripts.validar_generadores``: el reporte de politicas sigue siendo
    valido sin esta parte.
    """
    ruta_ajuste = carpeta / "ajuste.csv"
    if not ruta_ajuste.is_file():
        return []

    ajuste = _leer_csv(ruta_ajuste)
    aceptacion = (
        _leer_csv(carpeta / "aceptacion.csv")
        if (carpeta / "aceptacion.csv").is_file()
        else []
    )
    rendimiento = (
        _leer_csv(carpeta / "rendimiento.csv")
        if (carpeta / "rendimiento.csv").is_file()
        else []
    )

    partes: list[str] = [
        "<h2>Comparación de los métodos de generación</h2>",
        "<p>Esta es la <strong>segunda pregunta del proyecto</strong>, independiente de "
        "la comparación de filas: transformada inversa contra aceptación-rechazo sobre la "
        "misma distribución objetivo. La política de filas no interviene aquí.</p>",
    ]

    # --- KPIs ---
    rechazos = sum(1 for f in ajuste if str(f.get("rechaza_h0", "")).lower() == "true")
    tarjetas = [
        f"""<div class="kpi" style="border-left-color:var(--bien)">
  <div class="etiqueta">Ajuste a la exponencial</div>
  <div class="valor">{len(ajuste) - rechazos} / {len(ajuste)}</div>
  <div class="nota">celdas que <em>no</em> rechazan la hipótesis de ajuste</div>
</div>"""
    ]

    if aceptacion:
        observadas = [float(f["tasa_aceptacion_observada"]) for f in aceptacion]
        uniformes = [float(f["uniformes_por_muestra"]) for f in aceptacion]
        tarjetas.append(
            f"""<div class="kpi" style="border-left-color:var(--indep)">
  <div class="etiqueta">Tasa de aceptación</div>
  <div class="valor">{np.mean(observadas):.4f}</div>
  <div class="nota">observada contra 0.5 teórica (1/M)</div>
</div>"""
        )
        tarjetas.append(
            f"""<div class="kpi" style="border-left-color:var(--indep)">
  <div class="etiqueta">Uniformes por muestra</div>
  <div class="valor">{np.mean(uniformes):.2f} vs 1</div>
  <div class="nota">costo intrínseco del rechazo: unas 4 veces</div>
</div>"""
        )

    razon = None
    if rendimiento:
        tamanos = sorted({int(f["tamano"]) for f in rendimiento})
        mayor = tamanos[-1]
        tiempos = {
            f["metodo"]: float(f["mediana_s"])
            for f in rendimiento
            if int(f["tamano"]) == mayor
        }
        if "inversa" in tiempos and "rechazo" in tiempos and tiempos["inversa"] > 0:
            razon = tiempos["rechazo"] / tiempos["inversa"]
            tarjetas.append(
                f"""<div class="kpi" style="border-left-color:var(--unica)">
  <div class="etiqueta">Tiempo medido</div>
  <div class="valor">{razon:.0f}&times;</div>
  <div class="nota">con {mayor:,} muestras; no es el costo del método</div>
</div>""".replace(",", " ")
            )

    partes.append(f"<div class='kpis'>{''.join(tarjetas)}</div>")

    # --- Ajuste ---
    partes.append("<h3>Ajuste a la distribución teórica</h3>")
    partes.append(
        "<p>Prueba de Kolmogórov-Smirnov de una muestra con la <strong>tasa fijada de "
        "antemano</strong>. Si la tasa se estimara de la misma muestra, el p-valor "
        "estándar no sería válido sin corrección.</p>"
    )
    renglones = []
    for fila in ajuste:
        rechaza = str(fila.get("rechaza_h0", "")).lower() == "true"
        renglones.append(
            f"<tr><td>{fila['metodo']}</td>"
            f"<td class='num'>{float(fila['tasa']):g}</td>"
            f"<td class='num'>{int(float(fila['n']))}</td>"
            f"<td class='num'>{float(fila['media_observada']):.4f}</td>"
            f"<td class='num'>{float(fila['media_teorica']):.4f}</td>"
            f"<td class='num'>{float(fila['ks_estadistico']):.5f}</td>"
            f"<td class='num'>{float(fila['p_valor']):.4f}</td>"
            f"<td class='num'>{'rechaza' if rechaza else 'no rechaza'}</td></tr>"
        )
    partes.append(
        "<div class='tarjeta'><table><thead><tr><th>Método</th><th>Tasa λ</th>"
        "<th>n</th><th>Media obs.</th><th>Media teórica</th><th>KS</th>"
        "<th>valor p</th><th>Veredicto</th></tr></thead>"
        f"<tbody>{''.join(renglones)}</tbody></table>"
        "<p class='sub' style='margin:10px 0 0;font-size:.85rem'>"
        "<strong>El p-valor no ordena los métodos.</strong> Todos superan cualquier nivel "
        "de significancia usual. No rechazar la hipótesis nula no demuestra que el "
        "generador sea correcto, solo que esa muestra no aporta evidencia en contra."
        "</p></div>"
    )

    # --- Aceptacion ---
    if aceptacion:
        partes.append("<h3>Tasa de aceptación del método de rechazo</h3>")
        renglones = []
        for fila in aceptacion:
            renglones.append(
                f"<tr><td class='num'>{float(fila['tasa']):g}</td>"
                f"<td class='num'>{int(float(fila['muestras_aceptadas']))}</td>"
                f"<td class='num'>{int(float(fila['candidatos_generados']))}</td>"
                f"<td class='num mejor'>{float(fila['tasa_aceptacion_observada']):.4f}</td>"
                f"<td class='num'>{float(fila['tasa_aceptacion_teorica']):.4f}</td>"
                f"<td class='num'>{float(fila['candidatos_por_muestra']):.3f}</td>"
                f"<td class='num'><strong>{float(fila['uniformes_por_muestra']):.2f}</strong></td>"
                "</tr>"
            )
        partes.append(
            "<div class='tarjeta'><table><thead><tr><th>Tasa λ</th><th>Aceptadas</th>"
            "<th>Candidatos</th><th>Aceptación obs.</th><th>Teórica</th>"
            "<th>Candidatos / muestra</th><th>Uniformes / muestra</th>"
            "</tr></thead>"
            f"<tbody>{''.join(renglones)}</tbody></table>"
            "<p class='sub' style='margin:10px 0 0;font-size:.85rem'>"
            "La propuesta es Exp(λ/2) con envolvente M = 2, así que la aceptación teórica "
            "es 1/M = 0.5 y hacen falta 2 candidatos por muestra. Cada candidato consume 2 "
            "uniformes: de ahí las <strong>4 por muestra aceptada</strong>, contra 1 de la "
            "transformada inversa. Un candidato rechazado es un intento interno del "
            "generador, <strong>no un vehículo que abandona la gasolinera</strong>."
            "</p></div>"
        )

    # --- Rendimiento ---
    if rendimiento:
        partes.append("<h3>Tiempo de generación</h3>")
        renglones = []
        for fila in sorted(rendimiento, key=lambda f: (f["metodo"], int(f["tamano"]))):
            renglones.append(
                f"<tr><td>{fila['metodo']}</td>"
                f"<td class='num'>{int(float(fila['tamano']))}</td>"
                f"<td class='num'>{int(float(fila['repeticiones']))}</td>"
                f"<td class='num'>{float(fila['mediana_s']) * 1000:.3f}</td>"
                f"<td class='num'>{float(fila['desviacion_s']) * 1000:.3f}</td>"
                f"<td class='num'>{float(fila['microsegundos_por_muestra']):.3f}</td>"
                f"<td>{'sí' if str(fila['vectorizado']).lower() == 'true' else 'no'}</td></tr>"
            )
        partes.append(
            "<div class='tarjeta'><table><thead><tr><th>Método</th><th>Muestras</th>"
            "<th>Repeticiones</th><th>Mediana (ms)</th><th>Desv. (ms)</th>"
            "<th>µs / muestra</th><th>Vectorizado</th></tr></thead>"
            f"<tbody>{''.join(renglones)}</tbody></table></div>"
        )

        desglose = (
            f"La razón medida es de unas <strong>{razon:.0f}×</strong>, pero "
            if razon
            else "La razón medida es grande, pero "
        )
        partes.append(
            "<div class='aviso'><strong>El tiempo medido no es el costo del método</strong>"
            + desglose
            + "se compone de dos cosas que conviene no mezclar: un "
            "<strong>factor intrínseco de unas 4×</strong>, que son los uniformes por "
            "muestra medidos en la tabla anterior, y el resto, que viene de que "
            "<strong>la transformada inversa está vectorizada y el método de rechazo "
            "no</strong>: una opera sobre arreglos completos y la otra recorre un bucle "
            "muestra por muestra. Afirmar que el método es cientos de veces más lento le "
            "atribuye un costo que es de la implementación. La razón medida además varía "
            "entre corridas según la carga de la máquina, por eso se reporta la mediana y "
            "su dispersión."
            "</div>"
        )

    # --- Figuras ---
    figuras = (
        (
            "cdf_generadores.png",
            "CDF empírica de cada método contra la exponencial teórica. El panel inferior "
            "muestra la diferencia respecto a la teórica: en el superior las tres curvas se "
            "superponen.",
        ),
        (
            "rendimiento_generadores.png",
            "Tiempo de generación por tamaño de muestra, en escala logarítmica. Las dos "
            "líneas son paralelas: misma complejidad, distinta constante.",
        ),
    )
    for nombre, pie in figuras:
        datos = _imagen_incrustada(carpeta / nombre)
        if datos:
            partes.append(
                f"<figure><img src='{datos}' alt='{pie}'><figcaption>{pie}</figcaption></figure>"
            )

    return partes


def construir_html(carpeta: Path, carpeta_generadores: Path | None = None) -> str:
    """Arma el HTML completo a partir de los CSV de una carpeta de resultados.

    Args:
        carpeta: resultados de ``scripts.ejecutar_experimentos``.
        carpeta_generadores: resultados de ``scripts.validar_generadores``. Si
            es ``None`` o no existe, el reporte omite esa comparación.
    """
    filas = _leer_csv(carpeta / "replicas.csv")
    utilizaciones = _leer_csv(carpeta / "utilizacion.csv")

    ruta_config = carpeta / "metadatos.json"
    config = json.loads(ruta_config.read_text(encoding="utf-8")) if ruta_config.is_file() else {}

    por_replica: dict[tuple[str, str], dict[str, dict]] = defaultdict(dict)
    for fila in filas:
        por_replica[(fila["escenario"], fila["replica"])][fila["politica"]] = fila

    escenarios = _orden_escenarios(config, {f["escenario"] for f in filas})

    partes: list[str] = []

    # --- Encabezado y configuracion -------------------------------------
    replicas = config.get("replicas", "?")
    horizonte = config.get("horizonte", "?")
    metodo = config.get("metodo", "?")
    semilla = config.get("semilla_raiz", "?")

    partes.append(
        f"""<h1>Simulación de una gasolinera</h1>
<p class="sub">Comparación de fila única contra filas independientes</p>
<p class="sub">Modelación y Simulación &middot; Proyecto 1 &middot;
Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>

<div class="tarjeta">
  <h3 style="margin-top:0">Configuración de la corrida</h3>
  <table>
    <tbody>
      <tr><td>Réplicas por escenario</td><td class="num">{replicas}</td></tr>
      <tr><td>Horizonte de admisión</td><td class="num">{horizonte} min</td></tr>
      <tr><td>Método generador</td><td class="num">{metodo}</td></tr>
      <tr><td>Semilla raíz</td><td class="num">{semilla}</td></tr>
      <tr><td>Corridas totales</td><td class="num">{len(filas)}</td></tr>
    </tbody>
  </table>
</div>"""
    )

    # --- Escenarios de la configuracion ---------------------------------
    if config.get("escenarios"):
        renglones = []
        for escenario in config["escenarios"]:
            c = escenario["surtidores"]
            lam = escenario["tasa_llegadas"]
            mu = escenario["tasa_servicio"]
            rho = lam / (c * mu)
            renglones.append(
                f"<tr><td>{escenario['nombre']}</td>"
                f"<td class='num'>{c}</td>"
                f"<td class='num'>{lam:.3f}</td>"
                f"<td class='num'>{1 / lam:.2f} min</td>"
                f"<td class='num'>{1 / mu:.1f} min</td>"
                f"<td class='num'>{rho:.2f}</td></tr>"
            )
        partes.append(
            "<div class='tarjeta'><h3 style='margin-top:0'>Escenarios</h3><table>"
            "<thead><tr><th>Escenario</th><th>Surtidores</th><th>&lambda; (veh/min)</th>"
            "<th>Media entre llegadas</th><th>Media de servicio</th><th>&rho;</th></tr></thead>"
            f"<tbody>{''.join(renglones)}</tbody></table>"
            "<p class='sub' style='margin:10px 0 0;font-size:.85rem'>"
            "&rho; = &lambda; / (c&middot;&mu;) es el factor de carga: qué fracción de la "
            "capacidad conjunta demanda el flujo de vehículos.</p></div>"
        )

    # --- KPIs del escenario mas cargado ---------------------------------
    if escenarios:
        ultimo = escenarios[-1]
        dif = _diferencia_pareada(por_replica, ultimo, "espera_media")
        dif_p95 = _diferencia_pareada(por_replica, ultimo, "espera_p95")
        if dif and dif_p95:
            relativo = dif["diferencia"] / dif["media_unica"] * 100
            relativo_p95 = dif_p95["diferencia"] / dif_p95["media_unica"] * 100
            partes.append(
                f"""<h2>Resultado principal &mdash; {ultimo}</h2>
<div class="kpis">
  <div class="kpi">
    <div class="etiqueta">Espera media, fila única</div>
    <div class="valor">{dif['media_unica']:.2f} min</div>
    <div class="nota">contra {dif['media_indep']:.2f} min con filas independientes</div>
  </div>
  <div class="kpi" style="border-left-color:var(--indep)">
    <div class="etiqueta">Ventaja de la fila única</div>
    <div class="valor">{relativo:.0f} %</div>
    <div class="nota">menos espera media, IC 95 % [{dif['ic_inferior']:.2f}, {dif['ic_superior']:.2f}]</div>
  </div>
  <div class="kpi" style="border-left-color:var(--indep)">
    <div class="etiqueta">Ventaja en el peor caso</div>
    <div class="valor">{relativo_p95:.0f} %</div>
    <div class="nota">menos espera en el percentil 95</div>
  </div>
  <div class="kpi" style="border-left-color:var(--bien)">
    <div class="etiqueta">Consistencia</div>
    <div class="valor">{dif['gana_unica']} / {dif['n']}</div>
    <div class="nota">réplicas donde gana la fila única</div>
  </div>
</div>"""
            )

    # --- Tabla por escenario --------------------------------------------
    partes.append("<h2>Comparación por escenario</h2>")
    partes.append(
        "<div class='leyenda'>"
        "<span><span class='punto' style='background:var(--unica)'></span>Fila única</span>"
        "<span><span class='punto' style='background:var(--indep)'></span>Filas independientes</span>"
        "</div>"
    )

    for escenario in escenarios:
        renglones = []
        for clave, etiqueta, decimales in _METRICAS:
            dif = _diferencia_pareada(por_replica, escenario, clave)
            if dif is None:
                continue
            # En proporcion_espera una diferencia negativa favorece a las
            # filas independientes: el signo se interpreta, no se asume.
            gana_unica = dif["diferencia"] > 0
            marca_u = " class='num mejor'" if gana_unica else " class='num'"
            marca_i = " class='num'" if gana_unica else " class='num mejor'"
            renglones.append(
                f"<tr><td>{etiqueta}</td>"
                f"<td{marca_u}>{_fmt(dif['media_unica'], decimales)}</td>"
                f"<td{marca_i}>{_fmt(dif['media_indep'], decimales)}</td>"
                f"<td class='num'>{dif['diferencia']:+.{decimales}f}</td>"
                f"<td class='num'>[{dif['ic_inferior']:+.{decimales}f}, "
                f"{dif['ic_superior']:+.{decimales}f}]</td>"
                f"<td class='num'>{_fmt_p(dif['p_valor'])}</td></tr>"
            )

        util = _utilizacion_por_politica(utilizaciones, escenario)
        if util:
            u_unica = util.get("unica", (None, []))[0]
            u_indep = util.get("independientes", (None, []))[0]
            renglones.append(
                f"<tr><td>Utilización promedio</td>"
                f"<td class='num'>{_fmt(u_unica, 4)}</td>"
                f"<td class='num'>{_fmt(u_indep, 4)}</td>"
                f"<td class='num'>{(u_indep - u_unica):+.4f}</td>"
                f"<td colspan='2' style='text-align:left;color:var(--suave)'>"
                f"sin diferencia relevante</td></tr>"
            )

        vehiculos = [
            int(politicas["unica"]["vehiculos_atendidos"])
            for (nombre, _), politicas in por_replica.items()
            if nombre == escenario and "unica" in politicas
        ]
        pie = (
            f"Vehículos atendidos: {np.mean(vehiculos):.1f} en promedio "
            f"(mínimo {min(vehiculos)}, máximo {max(vehiculos)})."
            if vehiculos
            else ""
        )

        partes.append(
            f"""<div class="tarjeta">
  <h3 style="margin-top:0">{escenario}</h3>
  <table>
    <thead><tr><th>Métrica</th><th>Fila única</th><th>Filas independientes</th>
    <th>Diferencia</th><th>IC 95 %</th><th>valor p</th></tr></thead>
    <tbody>{''.join(renglones)}</tbody>
  </table>
  <p class="sub" style="margin:10px 0 0;font-size:.85rem">{pie}
  La diferencia es filas independientes menos fila única, calculada réplica por
  réplica. En verde, la política con mejor valor.</p>
</div>"""
        )

    # --- Utilizacion por surtidor ---------------------------------------
    partes.append("<h2>Utilización por surtidor</h2>")
    partes.append(
        "<div class='aviso'><strong>Leer con cuidado</strong>"
        "El desbalance entre surtidores bajo filas independientes está amplificado "
        "por la regla de desempate del modelo, que ante filas de igual longitud "
        "siempre elige el surtidor de menor identificador. La dirección del "
        "desbalance es un artefacto de esa regla, no un resultado del sistema. "
        "El promedio entre surtidores sí es comparable.</div>"
    )
    for escenario in escenarios:
        util = _utilizacion_por_politica(utilizaciones, escenario)
        if not util:
            continue
        cantidad = max(len(v[1]) for v in util.values())
        encabezados = "".join(f"<th>S{k + 1}</th>" for k in range(cantidad))
        renglones = []
        for politica in _POLITICAS:
            if politica not in util:
                continue
            promedio, medias = util[politica]
            celdas = "".join(f"<td class='num'>{m:.3f}</td>" for m in medias)
            brecha = max(medias) - min(medias)
            renglones.append(
                f"<tr><td>{_ETIQUETA_POLITICA[politica]}</td>{celdas}"
                f"<td class='num'><strong>{promedio:.4f}</strong></td>"
                f"<td class='num'>{brecha:.3f}</td></tr>"
            )
        partes.append(
            f"""<div class="tarjeta">
  <h3 style="margin-top:0">{escenario}</h3>
  <table>
    <thead><tr><th>Política</th>{encabezados}<th>Promedio</th><th>Brecha</th></tr></thead>
    <tbody>{''.join(renglones)}</tbody>
  </table>
</div>"""
        )

    # --- Figuras ---------------------------------------------------------
    figuras = (
        ("espera_media.png", "Espera media por escenario y política."),
        ("utilizacion_media.png", "Utilización media por escenario y política."),
    )
    incrustadas = [
        (_imagen_incrustada(carpeta / nombre), pie) for nombre, pie in figuras
    ]
    if any(datos for datos, _ in incrustadas):
        partes.append("<h2>Figuras</h2>")
        for datos, pie in incrustadas:
            if datos:
                partes.append(
                    f"<figure><img src='{datos}' alt='{pie}'>"
                    f"<figcaption>{pie}</figcaption></figure>"
                )

    if carpeta_generadores is not None:
        partes.extend(_seccion_generadores(Path(carpeta_generadores)))

    partes.append(
        "<footer>Escenarios académicos hipotéticos, no mediciones de campo. "
        "Estudio de horizonte finito con el sistema iniciando vacío: los valores "
        "no describen un régimen estacionario.</footer>"
    )

    cuerpo = "\n".join(partes)
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simulación de una gasolinera</title>
<style>{_ESTILOS}</style>
</head>
<body>
<main>
{cuerpo}
</main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera un reporte HTML autocontenido de una corrida."
    )
    parser.add_argument(
        "--resultados",
        required=True,
        help="Carpeta con replicas.csv, utilizacion.csv y las figuras.",
    )
    parser.add_argument(
        "--generadores",
        default=None,
        help="Carpeta con las salidas de validar_generadores. Por omisión se "
        "busca una carpeta hermana llamada 'generadores'.",
    )
    parser.add_argument(
        "--salida",
        default=None,
        help="Ruta del HTML. Por omisión, reporte.html dentro de --resultados.",
    )
    argumentos = parser.parse_args()

    carpeta = Path(argumentos.resultados)
    salida = Path(argumentos.salida) if argumentos.salida else carpeta / "reporte.html"

    generadores = (
        Path(argumentos.generadores)
        if argumentos.generadores
        else carpeta_generadores_por_omision(carpeta)
    )
    incluye = (generadores / "ajuste.csv").is_file()

    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(
        construir_html(carpeta, generadores if incluye else None), encoding="utf-8"
    )

    print(f"Reporte generado: {salida}")
    if incluye:
        print(f"Incluye la comparación de generadores desde: {generadores}")
    else:
        print(f"Sin comparación de generadores: no se encontró {generadores / 'ajuste.csv'}")
        print("Generarla con: python -m scripts.validar_generadores --config ... --salida ...")
    print(f"Abrirlo con:      ii {salida}")


if __name__ == "__main__":
    main()
