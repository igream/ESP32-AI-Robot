#!/usr/bin/env python3
"""Genera el reporte de la Tarea 2 (docx + PDF) con el formato institucional de la skill de Ciencia de Datos
(Times New Roman, justificado 1.1, portada UAEMéx, tablas y figuras a 300 DPI), usando las secciones que pide
el enunciado de Robótica: portada, introducción, metodología, resultados, análisis y conclusiones, referencias IEEE.

Lee los datos reales de herramientas/tarea2/datos (pruebas.csv, pruebas_con_flash/, entrenamientos*.json).
Salida: docs/Tarea2/REPORTE_Tarea5.docx (+ .pdf si Word está instalado) y docs/Tarea2/img/*.png

Uso:  python herramientas/tarea2/reporte_tarea2.py [--sin-pdf]
"""
import csv
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mi
import matplotlib.pyplot as plt
import numpy as np

for _f in (sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8")
    except Exception:
        pass

SKILL = Path(r"C:/Users/feraz/AppData/Local/Claude-Data/claude_pzs8sxrjxfjjc/local-agent-mode-sessions/skills-plugin/"
             r"8c4a69bf-e7a6-4df9-b157-0ea95f3c1a60/acbf0647-9188-4452-ad50-c61dd1281eeb/skills/formato-ciencia-de-datos-uaemex")
sys.path.insert(0, str(SKILL / "scripts"))
from builder_documento_base import (cargar_plantilla_base, agregar_titulo_seccion, agregar_parrafo,  # noqa: E402
                                    insertar_imagen, crear_tabla, agregar_referencias_ieee, exportar_pdf_word)
from generador_graficos_base import configurar_estilo_uaemex, guardar_grafico  # noqa: E402

_crear_tabla = crear_tabla


def crear_tabla(*a, **k):
    """Igual que la de la skill, pero la tabla no se parte entre páginas y queda con su leyenda."""
    t = _crear_tabla(*a, **k)
    for fila in t.rows:
        for celda in fila.cells:
            for p in celda.paragraphs:
                p.paragraph_format.keep_with_next = True
    return t


RAIZ = Path(__file__).resolve().parents[2]
DATOS = Path(__file__).resolve().parent / "datos"
SALIDA = RAIZ / "docs" / "Tarea2"
IMG = SALIDA / "img"
OBJS = ["vasorojo", "jarraroja", "laptop"]
CUERPO = 9.5

# Datos de la portada que dependen del curso de Robótica (completar antes de entregar)
DOCENTE = "DR. EN C.I.E. JAIME GARCÍA GARCÍA"
GRUPO = "O1"
FECHA = "Toluca, Estado de México, 10 de noviembre de 2026"


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0, c - h), min(1, c + h)


def leer_pruebas(ruta):
    with open(ruta, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def resumen(filas):
    r = {}
    for o in OBJS:
        e = [x for x in filas if x["objeto"] == o and x["condicion"] == "entrenamiento"]
        t = [x for x in filas if x["objeto"] == o and x["condicion"] != "entrenamiento"]
        r[o] = (sum(x["acierto"] == "si" for x in e), len(e), sum(x["acierto"] == "si" for x in t), len(t))
    return r


# ------------------------------------------------------------------ figuras
def figura_muestras():
    configurar_estilo_uaemex(8.0)
    ejemplos = [("vasorojo", "vasorojo_034.jpg", "Vaso (55 cm)"),
                ("jarraroja", "jarraroja_034.jpg", "Jarra con cinta (55 cm)"),
                ("laptop", "laptop_030.jpg", "Laptop (75 cm)")]
    fig, axs = plt.subplots(1, 3, figsize=(6.0, 1.75))
    for ax, (o, f, t) in zip(axs, ejemplos):
        ax.imshow(mi.imread(DATOS / "dataset" / o / f))
        ax.axvline(40, color="#FACC15", lw=0.8)
        ax.axvline(280, color="#FACC15", lw=0.8)
        ax.set_title(t, fontsize=8)
        ax.axis("off")
    fig.tight_layout(pad=0.4)
    p = IMG / "fig1_muestras.png"
    guardar_grafico(fig, p)
    return p


def _mat(ax, m, etq, titulo, fmt="{:.0f}"):
    m = np.array(m, dtype=float)
    ax.imshow(m, cmap="Blues", vmin=0, vmax=max(100, m.max()) if m.max() <= 100 else m.max())
    ax.set_xticks(range(len(etq)))
    ax.set_yticks(range(len(etq)))
    ax.set_xticklabels(etq, rotation=30, ha="right", fontsize=7)
    ax.set_yticklabels(etq, fontsize=7)
    ax.set_xlabel("Predicho", fontsize=7.5)
    ax.set_ylabel("Real", fontsize=7.5)
    ax.set_title(titulo, fontsize=8)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, fmt.format(m[i, j]), ha="center", va="center", fontsize=7,
                    color="white" if m[i, j] > 0.55 * m.max() else "#0F172A")


def figura_matrices_entrenamiento():
    configurar_estilo_uaemex(8.0)
    etq = ["vaso", "jarra", "laptop", "fondo"]
    antes = [[100, 0, 0, 0], [0, 100, 0, 0], [0, 0, 50, 50], [0, 0, 0, 100]]   # corrida 1, dataset v1 (Studio, %)
    despues = [[100, 0, 0, 0], [0, 100, 0, 0], [0, 0, 100, 0], [0, 0, 0, 100]]  # corrida final, dataset v3 (Studio, %)
    fig, axs = plt.subplots(1, 2, figsize=(5.2, 2.5))
    _mat(axs[0], antes, etq, "Antes (dataset v1, 60 ciclos)")
    _mat(axs[1], despues, etq, "Después (dataset v3, 100 ciclos)")
    fig.tight_layout(pad=0.5)
    p = IMG / "fig2_matrices_entrenamiento.png"
    guardar_grafico(fig, p)
    return p


def figura_pruebas(filas):
    configurar_estilo_uaemex(8.0)
    grupos = []
    for o in OBJS:
        s = [x for x in filas if x["objeto"] == o]
        grupos.append((o, sum(x["acierto"] == "si" for x in s), len(s)))
    ent = [x for x in filas if x["condicion"] == "entrenamiento"]
    otr = [x for x in filas if x["condicion"] != "entrenamiento"]
    grupos += [("posición\nentren.", sum(x["acierto"] == "si" for x in ent), len(ent)),
               ("otra pos.\no luz", sum(x["acierto"] == "si" for x in otr), len(otr)),
               ("global", sum(x["acierto"] == "si" for x in filas), len(filas))]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(6.0, 2.45), gridspec_kw={"width_ratios": [1.5, 1]})
    xs = np.arange(len(grupos))
    ex = [100 * k / n for _, k, n in grupos]
    lo = [100 * (k / n - wilson(k, n)[0]) for _, k, n in grupos]
    hi = [100 * (wilson(k, n)[1] - k / n) for _, k, n in grupos]
    a1.bar(xs, ex, yerr=[lo, hi], capsize=3, color="#1E3A8A", error_kw={"lw": 0.8})
    a1.set_xticks(xs)
    a1.set_xticklabels([g[0] for g in grupos], fontsize=6.5)
    a1.set_ylim(0, 108)
    a1.set_ylabel("Exactitud (%)", fontsize=8)
    a1.set_title("Exactitud con IC95 de Wilson", fontsize=8)
    for x, (_, k, n) in zip(xs, grupos):
        a1.text(x, 3, f"{k}/{n}", ha="center", color="white", fontsize=6.5)
    etq = ["vaso", "jarra", "laptop", "sin det."]
    cols = OBJS + ["sin_deteccion"]
    m = np.zeros((3, 4))
    for x in filas:
        m[OBJS.index(x["objeto"]), cols.index(x["etiqueta"])] += 1
    a2.imshow(m, cmap="Blues")
    a2.set_xticks(range(4))
    a2.set_xticklabels(etq, rotation=30, ha="right", fontsize=6.5)
    a2.set_yticks(range(3))
    a2.set_yticklabels(["vaso", "jarra", "laptop"], fontsize=6.5)
    a2.set_xlabel("Detectado", fontsize=7.5)
    a2.set_ylabel("Real", fontsize=7.5)
    a2.set_title("Matriz de confusión (45 pruebas)", fontsize=8)
    for i in range(3):
        for j in range(4):
            a2.text(j, i, f"{int(m[i, j])}", ha="center", va="center", fontsize=7, color="white" if m[i, j] > 8 else "#0F172A")
    fig.tight_layout(pad=0.5)
    p = IMG / "fig3_pruebas.png"
    guardar_grafico(fig, p)
    return p


def figura_montaje():
    """Tres fotos reales: montaje físico, página de captura y página de pruebas."""
    nombres = ["T2 Area de trabajo física.jpeg", "T2 Interfaz recoleccion datos.jpeg", "T2 Interfaz testing.jpeg"]
    configurar_estilo_uaemex(font_size=8.0)
    fig = plt.figure(figsize=(8, 3.4))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.9, 0.62, 0.62], wspace=0.04)
    for i, n in enumerate(nombres):
        ax = fig.add_subplot(gs[i])
        ax.imshow(mi.imread(str(IMG / n)))
        ax.axis("off")
        ax.set_title("abc"[i] + ")", fontsize=8, loc="left")
    ruta = IMG / "fig_montaje.png"
    guardar_grafico(fig, str(ruta), dpi=300)
    return ruta


# ------------------------------------------------------------------ documento
def P(doc, texto, **kw):
    """Párrafo con **negrita** y *cursiva* simples."""
    frag = []
    texto = texto.replace("`", "")
    for i, trozo in enumerate(texto.split("**")):
        if not trozo:
            continue
        frag.append((trozo, i % 2 == 1, False, CUERPO))
    return agregar_parrafo(doc, frag, **kw)


def portada(doc):
    ps = doc.paragraphs

    def poner(p, texto):
        runs = p.runs
        runs[0].text = texto
        for r in runs[1:]:
            r.text = ""
    poner(ps[7], "Robótica")
    poner(ps[9], "Tarea 5")
    ps[10].runs[1].text = "DETECCIÓN DE OBJETOS CON ESP32-CAM Y EDGE IMPULSE"
    ps[15]._element.getparent().remove(ps[15]._element)        # integrante único
    ps = doc.paragraphs
    for p in ps:
        if p.text.strip() == "O1":
            poner(p, GRUPO)
        elif "LEDEZMA" in p.text:
            poner(p, "\t" + DOCENTE)
        elif p.text.startswith("Toluca"):
            poner(p, FECHA)
    # salto de página tras la portada
    doc.add_page_break()


def construir():
    SALIDA.mkdir(parents=True, exist_ok=True)
    IMG.mkdir(parents=True, exist_ok=True)
    nuevas = leer_pruebas(DATOS / "pruebas.csv")
    viejas = leer_pruebas(DATOS / "pruebas_con_flash" / "pruebas.csv")
    rn, rv = resumen(nuevas), resumen(viejas)
    tn = sum(1 for x in nuevas if x["acierto"] == "si")
    tv = sum(1 for x in viejas if x["acierto"] == "si")
    f1 = figura_muestras()
    f2 = figura_matrices_entrenamiento()
    f3 = figura_pruebas(nuevas)

    doc = cargar_plantilla_base()
    portada(doc)

    # ---------------- 1. Introducción
    agregar_titulo_seccion(doc, "1. INTRODUCCIÓN")
    P(doc, "El aprendizaje automático en microcontroladores (**TinyML**) permite ejecutar un modelo directamente en un dispositivo de bajo "
           "consumo, lo que reduce la latencia, evita enviar imágenes a internet y permite operar sin conexión [4], [5]. **Edge Impulse** integra en "
           "una sola plataforma la captura de datos, el entrenamiento, la cuantización y la generación de código [2], y su familia de modelos "
           "**FOMO** (Faster Objects, More Objects) entrega el centroide de cada objeto en lugar del cuadro completo, a cambio de correr más rápido "
           "en hardware limitado [3], [11]. En esta práctica se entrenó un detector de tres objetos propios con la cámara de un **ESP32-CAM** "
           "(AI-Thinker, sensor OV3660), se desplegó como librería de Arduino y se midió su desempeño con 45 pruebas, siguiendo el video base [1]. "
           "Un vaso y una jarra transparentes con diseño rojo se eligieron a propósito por parecerse; el tercer objeto es una laptop negra. El objetivo "
           "es obtener un detector que funcione **sin internet** y analizar en qué condiciones acierta y en cuáles falla.")

    # ---------------- 2. Metodología
    agregar_titulo_seccion(doc, "2. METODOLOGÍA")
    agregar_titulo_seccion(doc, "2.1 Captura del dataset en condiciones controladas", nivel=2)
    P(doc, "Las fotos se tomaron con la cámara del propio robot (QVGA, 320×240, JPEG) por WiFi, desde una página para el celular servida por un "
           "script en la PC, en lugar de la librería Eloquent del video. La cámara quedó **fija a 10 cm de altura**, con una mesa plegable blanca como "
           "fondo a 30 cm detrás del objeto, un foco del cuarto contiguo como única luz y **sin flash**. Los objetos se colocaron en un punto marcado, "
           "a 55 cm de la cámara el vaso y la jarra y a 75 cm la laptop, que a 55–60 cm se salía del encuadre. El objeto se giró en cada toma y se "
           "verificó que quedara completo dentro del recorte central de 240×240 px que usa el modelo (Fit shortest axis, líneas amarillas de la "
           "Figura 1); las fotos con el objeto cortado se apartaron (37 en la primera captura). La Tabla 1 resume el dataset final.")
    crear_tabla(doc, ["Objeto", "Fotos", "Distancia", "Entren./Prueba", "Particularidad"],
                [["vasorojo", "60", "55 cm", "48 / 12", "Vaso transparente con diseño rojo"],
                 ["jarraroja", "60", "55 cm", "47 / 13", "Jarra transparente con diseño rojo; oreja con cinta amarilla, a ambos lados y de tres cuartos"],
                 ["laptop", "60", "75 cm", "48 / 12", "Negra, abierta unos 90°, girada unos 45° siempre al mismo lado"],
                 ["Total", "180", "—", "143 / 37", "Reparto automático 80 % / 20 % de Edge Impulse"]],
                anchos_columnas=[0.8, 0.5, 0.7, 0.95, 3.15], pie_tabla="Tabla 1. Dataset final (versión 3) y condiciones de captura.")
    insertar_imagen(doc, str(f1), ancho_pulgadas=5.4, pie_figura="Figura 1. Muestra de cada clase con el recorte central del modelo (líneas amarillas).")
    insertar_imagen(doc, str(figura_montaje()), ancho_pulgadas=5.6,
                    pie_figura="Figura 2. Montaje físico (cámara a 10 cm, fondo blanco), página de captura en el celular y página de las 45 pruebas.")

    agregar_titulo_seccion(doc, "2.2 Etiquetado y entrenamiento en Edge Impulse", nivel=2)
    P(doc, "Las imágenes se subieron con la CLI de Edge Impulse al proyecto público [enlace en la sección 5] y se etiquetaron con **un cuadro "
           "ajustado por imagen** (el de la jarra incluye la oreja). El impulse recorta al centro y reduce a **96×96 px**, usa el bloque **FOMO "
           "MobileNetV2 0.35** y se entrenó con tasa de aprendizaje 0.001, aumento de datos y cuantización int8. Se usó **RGB** y no escala de grises "
           "(justificación en la sección 4). El proceso fue iterativo (Tabla 2): con el dataset inicial la laptop se confundía con el fondo (F1 de 0.67); subir los "
           "ciclos de 60 a 100 no ayudó, y el diagnóstico apuntó a la captura (laptop demasiado grande y 12 cuadros fuera del recorte), así que se "
           "**recapturó la laptop a 75 cm**. Ya desplegado, la jarra se confundía con el vaso, por lo que se puso **cinta amarilla en la oreja**, se "
           "recapturaron las 60 fotos de la jarra, se reetiquetaron y se reentrenó. La Figura 3 muestra la matriz de confusión antes y después.")
    crear_tabla(doc, ["Iteración", "Cambio", "Ciclos", "F1 validación", "Prueba real (45)"],
                [["1", "Dataset v1 (laptop a 55 cm)", "60", "90.5 % (laptop 0.67)", "—"],
                 ["2", "Ajuste de un parámetro: más ciclos", "100", "90.0 % (laptop 0.60)", "—"],
                 ["3", "Dataset v2: laptop recapturada a 75 cm", "60 y 100", "100 %", f"{tv}/45 ({100 * tv / 45:.1f} %), con flash"],
                 ["4", "Dataset v3: cinta amarilla en la oreja de la jarra", "60 y 100", "100 %", f"{tn}/45 ({100 * tn / 45:.1f} %), sin flash"]],
                anchos_columnas=[0.65, 2.65, 0.65, 1.2, 1.0], pie_tabla="Tabla 2. Evolución del modelo. La validación de Edge Impulse usa solo 23 objetos, por lo que no basta para comparar.")
    insertar_imagen(doc, str(f2), ancho_pulgadas=4.4, pie_figura="Figura 3. Matriz de confusión de validación (%) antes y después del ajuste.")

    agregar_titulo_seccion(doc, "2.3 Despliegue en el ESP32-CAM", nivel=2)
    P(doc, "Se exportó la librería de Arduino (EON Compiler, int8) y se instaló como .ZIP. El sketch `deteccion_ei.ino` captura QVGA con el mismo "
           "volteo vertical que el robot, decodifica el JPEG a RGB888, recorta al centro, reduce a 96×96 y ejecuta el clasificador. Imprime por "
           "serie una línea por cuadro con **etiqueta, probabilidad y coordenadas (x, y)** del centroide (`DET;t;dsp;clasif;etiqueta;prob;cx;cy;w;h`) "
           "o `NONE`. Compila con el core ESP32 3.3.12 (el video usa 3.0.7) y ocupa 14 % de la flash y 12 % de la RAM. Hubo dos problemas: "
           "(a) en este core `fmt2rgb888` entrega los bytes en orden R, G, B y el ejemplo de Edge Impulse asume B, G, R, de modo que el vaso rojo "
           "llegaba al modelo como azul y no se detectaba nada; se corrigió y se verificó volcando por serie la imagen que ve el modelo; (b) el "
           "destello del LED al detectar iluminaba el cuadro siguiente (el dataset no usó flash) y calentaba el LED, por lo que se desactivó. "
           "Al detectar, el robot **hace un gesto**: si la misma clase domina en 2 de 3 cuadros, el vaso hace que asienta (adelante y atrás), la jarra que niega (giros "
           "izquierda, derecha, izquierda) y la laptop que da una vuelta completa (1.74 s, el tiempo de 360° calibrado en la Tarea 4 con PWM 140, unos 365°), con PWM limitado y una pausa de 3 s para no repetirlo. Una página para el celular, servida por el propio ESP32, muestra la foto, la clase detectada y el gesto en curso. **No se implementó el reto de la "
           "pantalla OLED** (extra opcional) porque el ESP32 sirve su propia página web: el celular se conecta a su red WiFi (`ESP32Det_Fer`) y muestra "
           "la foto del cuadro, la clase, la probabilidad, el gesto en curso, el contador y el registro de detecciones. Esa pantalla es más grande y "
           "legible que una OLED de 0.96\", no ocupa los pines I2C (GPIO14 y GPIO15 ya mueven los motores en este robot) y funciona sin computadora. "
           "**[Pendiente: describir la prueba autónoma con power bank y anexar fotos o video.]**")

    agregar_titulo_seccion(doc, "2.4 Pruebas", nivel=2)
    P(doc, "Con el robot conectado por USB, un script lee las líneas seriales y se hicieron **45 pruebas**: por objeto, 10 en la posición del "
           "entrenamiento (movimientos mínimos) y 5 en otra posición o con otra luz (más cerca, pegado al fondo, con linterna o lámpara). Cada "
           "prueba toma una ventana de 3 s (unos 3 cuadros) y registra la detección de mayor probabilidad; cuenta como acierto si coincide con el "
           "objeto. Se calcularon intervalos de Wilson al 95 % y pruebas exactas de Fisher.")

    # ---------------- 3. Resultados
    agregar_titulo_seccion(doc, "3. RESULTADOS")
    P(doc, f"El modelo final acertó **{tn} de 45 pruebas ({100 * tn / 45:.1f} %, IC95 {100 * wilson(tn, 45)[0]:.1f}–{100 * wilson(tn, 45)[1]:.1f} %)**. "
           "En la posición del entrenamiento acertó **30 de 30**, y en otra posición o luz **10 de 15** (Fisher, p = 0.002). La laptop acertó 15 de 15. "
           "En la jarra, el ajuste con cinta subió el acierto en la posición del entrenamiento de 6/10 a 10/10 (Tabla 3, tanda 1 = modelo sin cinta y con "
           "flash). La tabla completa de las 45 pruebas (objeto, prueba, etiqueta, probabilidad, coordenadas y acierto) está en el anexo.")
    filas = []
    for o in OBJS:
        a, na, b, nb = rn[o]
        k, n = a + b, na + nb
        lo, hi = wilson(k, n)
        av, nav, bv, nbv = rv[o]
        filas.append([o, f"{a}/{na}", f"{b}/{nb}", f"{k}/{n}", f"{100 * lo:.0f}–{100 * hi:.0f} %", f"{av + bv}/{nav + nbv}"])
    ke = sum(r[0] for r in rn.values())
    ko = sum(r[2] for r in rn.values())
    lo, hi = wilson(tn, 45)
    filas.append(["Global", f"{ke}/30", f"{ko}/15", f"{tn}/45", f"{100 * lo:.0f}–{100 * hi:.0f} %", f"{tv}/45"])
    crear_tabla(doc, ["Objeto", "Posición entren.", "Otra pos./luz", "Total", "IC95", "Tanda 1"], filas,
                anchos_columnas=[1.0, 1.1, 1.0, 0.8, 0.9, 0.8], pie_tabla="Tabla 3. Aciertos por objeto y condición (tanda 1: modelo sin cinta, con flash).")
    insertar_imagen(doc, str(f3), ancho_pulgadas=5.6, pie_figura="Figura 4. Exactitud por grupo y matriz de confusión de las 45 pruebas reales.")
    fallos = [x for x in nuevas if x["acierto"] != "si"]
    filas_f = [[f"{x['objeto']} {x['prueba']}", x["nota"] or "—", x["etiqueta"].replace("sin_deteccion", "sin detección"),
                f"{float(x['prob']):.2f}" if x["prob"] else "—"] for x in fallos]
    crear_tabla(doc, ["Prueba", "Condición", "Detectado", "Prob."], filas_f, anchos_columnas=[1.1, 3.4, 1.0, 0.6],
                pie_tabla="Tabla 4. Las pruebas fallidas (todas de la 11 a la 15 de cada objeto).")
    P(doc, "En el ESP32 cada cuadro tarda **798 ms** (26 ms de procesado y 772 ms de clasificación), unos **1.25 cuadros por segundo**, frente a los "
           "628 ms que estima Edge Impulse para un Cortex-M4F; el modelo usa 133 KB de RAM y 81 KB de flash según el estimador. La probabilidad de los "
           "aciertos (0.83 ± 0.13) fue algo mayor que la de los errores (0.71 ± 0.09), sin diferencia significativa (Mann-Whitney, p = 0.11), por lo que "
           "la probabilidad sola no sirve como filtro. Con n = 15 por objeto los intervalos son amplios.", espacio_antes=3)

    # ---------------- 4. Análisis y conclusiones
    agregar_titulo_seccion(doc, "4. ANÁLISIS Y CONCLUSIONES")
    P(doc, "**¿Por qué cámara fija, fondo constante y mismo punto?** Con unas 60 fotos por clase el modelo aprende todo lo que se repite en las imágenes, "
           "incluido el escenario; fijar la cámara, el fondo y la luz reduce la variación que no importa. Al cambiar la posición o la luz la exactitud "
           "bajó de 100 % (30/30) a 66.7 % (10/15): fallaron el objeto pegado al fondo, muy cerca de la cámara y con luz fuerte.")
    P(doc, "**¿Qué se confundió y qué se hizo?** Vaso y jarra, por tener el mismo color y diseño transparente: en la primera tanda 11 de las 15 pruebas "
           "de la jarra mostraron una etiqueta falsa de vaso y solo 9 acertaron. Subir ciclos no mejoró nada; lo que sí funcionó fue **añadir una marca "
           "distintiva (cinta amarilla en la oreja)** y reentrenar. Esa mejora viene de un marcador añadido y no de un modelo mejor, y el modelo puede "
           "apoyarse en el color de la cinta. La laptop mejoró al recapturarla a 75 cm. Con luz fuerte la jarra se detectó como laptop.")
    P(doc, "**¿Por qué escala de grises y no RGB?** Un cuadro en grises tiene un tercio de los datos de entrada (9,216 contra 27,648 valores), lo que "
           "reduce memoria y tiempo en un ESP32, y por eso lo recomienda el enunciado. En esta práctica se usó **RGB** de forma deliberada: (a) los "
           "objetos se distinguen sobre todo por el **color** (vaso y jarra son rojos, la laptop es negra y la marca que separa vaso de jarra es una cinta "
           "amarilla), y al pasar a grises el rojo y el amarillo se convierten en tonos parecidos y esa información se pierde; (b) los recursos "
           "alcanzan con RGB, pues el modelo usa 14 % de la flash, 133 KB de RAM estimados y 772 ms por clasificación, sin llegar a ningún límite del "
           "ESP32-CAM; y (c) el aumento de tamaño del modelo con RGB afecta solo a la primera capa. No se midió una corrida en grises, así que el "
           "ahorro y la posible pérdida de exactitud no están cuantificados y quedan como trabajo futuro.")
    P(doc, "**Ventajas de inferencia local.** Menor latencia, porque no hay viaje de ida y vuelta a un servidor; privacidad, porque las imágenes no salen "
           "del dispositivo; funcionamiento sin internet; y menor costo y consumo. A cambio, el modelo debe caber en la memoria y el cómputo del "
           "microcontrolador (1.25 cuadros por segundo en este caso).")
    P(doc, "**Aplicación industrial con (x, y).** Un clasificador de residuos: las coordenadas del centroide se convierten, con una calibración de la "
           "cámara fija sobre la banda, a posición en el plano de trabajo, y un brazo robótico toma la pieza con cinemática inversa y la deposita en el "
           "contenedor de su clase.")
    P(doc, "**Centroides de FOMO frente a cuadros delimitadores.** El centroide basta para el rumbo (el error de dirección es la distancia del centro "
           "a la mitad de la imagen), pero FOMO trabaja en celdas de 8×8 px sobre 96×96, tiene resolución gruesa y no da el tamaño real del objeto; "
           "un cuadro permite estimar la distancia por su ancho y decidir cuándo detenerse.")
    P(doc, "**Conclusiones.** Se logró un detector que corre completo en el ESP32-CAM, sin internet, con **88.9 %** de acierto en 45 pruebas y 100 % en la "
           "posición del entrenamiento. Su límite es la generalización: falla con cambios fuertes de distancia, fondo y luz, y distingue vaso de jarra "
           "solo gracias a un marcador. Para mejorarlo harían falta más fotos con esas variaciones, una evaluación con más pruebas y la comparación "
           "RGB contra grises.", espacio_antes=2)
    P(doc, "**Enlaces.** Repositorio: https://github.com/igream/ESP32-AI-Robot · Proyecto de Edge Impulse: "
           "https://studio.edgeimpulse.com/public/1159326/live")

    agregar_referencias_ieee(doc, [
        "The Professor Garcia, \u201cEntrenando IA desde cero para reconocer objetos nuevos con ESP32-CAM, Edge Impulse, Arduino,\u201d YouTube, "
        "11 dic. 2024. [Online]. Available: https://www.youtube.com/watch?v=9uhKfEK73nA",
        "Edge Impulse, \u201cAnnouncing Official Support for the Espressif ESP-EYE (ESP32),\u201d 27 abr. 2022. [Online]. Available: "
        "https://www.edgeimpulse.com/blog/announcing-official-support-for-the-espressif-esp-eye-esp32/",
        "Edge Impulse, \u201cAdd Sight to Your ESP32,\u201d 8 sep. 2021. [Online]. Available: https://www.edgeimpulse.com/blog/add-sight-to-your-esp32/",
        "R. Kallimani, K. Pai, P. Raghuwanshi, S. Iyer and O. L. A. L\u00f3pez, \u201cTinyML: Tools, applications, challenges, and future research "
        "directions,\u201d Multimedia Tools and Applications, vol. 83, no. 10, pp. 29015\u201329045, 2024 (publicado en l\u00ednea sep. 2023), "
        "doi: 10.1007/s11042-023-16740-9.",
        "P. P. Ray, \u201cA review on TinyML: State-of-the-art and prospects,\u201d J. King Saud Univ. \u2013 Comput. Inf. Sci., vol. 34, no. 4, "
        "pp. 1595\u20131623, abr. 2022, doi: 10.1016/j.jksuci.2021.11.019.",
    ])
    # [11] se numera aparte para conservar la numeración del enunciado
    agregar_parrafo(doc, [("[11] ", True, False, 8.0),
                          ("N. Badalyan, \u201cFOMO Edge Impulse detecte potato beetle,\u201d Hackster.io, 23 jun. 2022. [Online]. Available: "
                           "https://www.hackster.io/norik-badalyan/fomo-edge-impulse-detecte-potato-beetle-6ac2a7", False, False, 8.0)],
                    espacio_despues=1.5, interlineado=1.0)
    ruta = SALIDA / "REPORTE_Tarea5.docx"
    doc.save(str(ruta))
    print("Guardado", ruta)
    return ruta


if __name__ == "__main__":
    r = construir()
    if "--sin-pdf" not in sys.argv:
        print("PDF:", exportar_pdf_word(str(r)))
