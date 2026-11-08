#!/usr/bin/env python3
"""Genera los anexos de la Tarea 5 (docx + PDF) con el formato institucional de la skill de Ciencia de Datos:

  ANEXO_A_Tabla_Resultados   las 45 pruebas (objeto, prueba, etiqueta, probabilidad, coordenadas, acierto)
  PROPUESTA_Integracion_Robot  1 página: cómo usar el detector en un robot móvil diferencial

Reutiliza las utilidades de reporte_tarea2.py. Salida en docs/Tarea2/.
Uso:  python herramientas/tarea2/anexos_tarea5.py [--sin-pdf]
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reporte_tarea2 as R  # noqa: E402  (configura rutas, estilos y UTF-8)
from reporte_tarea2 import (DATOS, IMG, SALIDA, P, agregar_parrafo, agregar_titulo_seccion, cargar_plantilla_base,  # noqa: E402
                            configurar_estilo_uaemex, crear_tabla, exportar_pdf_word, guardar_grafico, insertar_imagen,
                            leer_pruebas)

COND = {"entrenamiento": "Entrenamiento", "posicion": "Otra posición", "luz": "Otra luz"}


def sin_portada(doc):
    """Conserva cabezal, pie y márgenes institucionales, pero sin la portada."""
    for p in list(doc.paragraphs):
        p._element.getparent().remove(p._element)


def anexo_tabla():
    filas = leer_pruebas(DATOS / "pruebas.csv")
    doc = cargar_plantilla_base()
    sin_portada(doc)
    agregar_titulo_seccion(doc, "ANEXO A. TABLA DE RESULTADOS DE LAS 45 PRUEBAS")
    P(doc, "Detector FOMO (96×96, RGB, 100 ciclos) en el ESP32-CAM, sin flash. Por objeto, 10 pruebas en la posición del entrenamiento y 5 en otra "
           "posición o con otra luz. Cada prueba registra la detección de mayor probabilidad de una ventana de 3 s. Las coordenadas (x, y) son el "
           "centroide en píxeles de la entrada del modelo (96×96). Cuadros ok: cuadros de la ventana con la etiqueta correcta, sobre el total.")
    datos = []
    for x in filas:
        etq = x["etiqueta"].replace("sin_deteccion", "sin detección")
        prob = f"{float(x['prob']):.2f}" if x["prob"] else "—"
        xy = f"({float(x['x']):.0f}, {float(x['y']):.0f})" if x["x"] else "—"
        datos.append([x["objeto"], x["prueba"], COND.get(x["condicion"], x["condicion"]), etq, prob, xy,
                      "sí" if x["acierto"] == "si" else "no", f"{x['cuadros_ok']}/{x['cuadros']}", x["nota"] or ""])
    R._crear_tabla(doc, ["Objeto", "Prueba", "Condición", "Etiqueta detectada", "Prob.", "(x, y)", "Acierto", "Cuadros ok", "Observación"], datos,
                anchos_columnas=[0.7, 0.4, 0.8, 0.85, 0.4, 0.55, 0.45, 0.5, 1.5],
                pie_tabla="Tabla A1. Resultados de las 45 pruebas (modelo final, sin flash).")
    ruta = SALIDA / "ANEXO_A_Tabla_Resultados.docx"
    doc.save(str(ruta))
    return ruta


def diagrama():
    configurar_estilo_uaemex(7.5)
    fig, ax = plt.subplots(figsize=(6.1, 2.15))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 36)
    ax.axis("off")
    cajas = [(1, "Cámara\nOV3660\n320×240", "#E2E8F0"),
             (18, "ESP32-CAM\nFOMO 96×96\netiqueta, prob.,\ncentroide (x, y)", "#BFDBFE"),
             (37, "Lógica de control\nBUSCAR · ALINEAR ·\nACERCAR · ACCIÓN", "#FDE68A"),
             (58, "Cinemática\ndiferencial\nv, ω → vR, vL", "#BBF7D0"),
             (76, "ESP32 + L298N\nPWM por lado", "#FECACA"),
             (91, "Motores\nizq. / der.", "#E2E8F0")]
    anchos = [14, 16, 18, 15, 13, 8.5]
    for (x, t, c), w in zip(cajas, anchos):
        ax.add_patch(FancyBboxPatch((x, 14), w, 16, boxstyle="round,pad=0.4,rounding_size=1.2", fc=c, ec="#334155", lw=0.8))
        ax.text(x + w / 2, 22, t, ha="center", va="center", fontsize=6.6)
    for (x, _, _), w, (x2, _, _) in zip(cajas[:-1], anchos[:-1], cajas[1:]):
        ax.add_patch(FancyArrowPatch((x + w + 0.6, 22), (x2 - 0.6, 22), arrowstyle="-|>", mutation_scale=7, color="#0F172A", lw=0.9))
    ax.text(48, 33, "Percepción (Tarea 5)", ha="center", fontsize=7.5, fontweight="bold", color="#1E3A8A")
    ax.text(79, 33, "Movimiento (Tarea 4)", ha="center", fontsize=7.5, fontweight="bold", color="#166534")
    ax.plot([2, 55], [31.3, 31.3], color="#1E3A8A", lw=1)
    ax.plot([58, 99], [31.3, 31.3], color="#166534", lw=1)
    ax.text(50, 9.5, "UART / ESP-NOW: el ESP32-CAM envía la línea DET;…;etiqueta;prob;cx;cy", ha="center", fontsize=6.4, style="italic")
    ax.add_patch(FancyArrowPatch((97, 12.5), (8, 12.5), connectionstyle="arc3,rad=-0.28", arrowstyle="-|>", mutation_scale=7,
                                 color="#64748B", lw=0.8, linestyle="--"))
    ax.text(50, 1.2, "Realimentación: al moverse el robot, la imagen cambia y la siguiente detección corrige el rumbo", ha="center", fontsize=6.4)
    p = IMG / "fig_propuesta_bloques.png"
    guardar_grafico(fig, p)
    return p


def propuesta():
    fig = diagrama()
    doc = cargar_plantilla_base()
    sin_portada(doc)
    agregar_titulo_seccion(doc, "PROPUESTA DE INTEGRACIÓN DEL DETECTOR EN UN ROBOT MÓVIL DIFERENCIAL")
    P(doc, "El detector de la Tarea 5 funciona como **sensor de percepción** y el robot de la Tarea 4 como **capa de movimiento**. El ESP32-CAM detecta, "
           "un segundo ESP32 (WROOM-32D) controla los motores y ambos se comunican por UART, de modo que la visión (1.25 cuadros por segundo) no "
           "frena el control de los motores.")
    insertar_imagen(doc, str(fig), ancho_pulgadas=6.0, pie_figura="Figura P1. Diagrama de bloques: del cuadro de la cámara a los motores.")
    agregar_titulo_seccion(doc, "Sensor, lógica de control y acciones", nivel=2)
    P(doc, "**Sensor.** La cámara OV3660 a 10 cm del piso. Cada cuadro aporta la clase, la probabilidad y el centroide (cx, cy) en 96×96 px. Solo se "
           "acepta un objeto si aparece en **2 de 3 cuadros** consecutivos (en las pruebas hubo etiquetas falsas aisladas de un solo cuadro).")
    P(doc, "**Lógica.** Una máquina de estados: **BUSCAR** (sin detección, gira a la izquierda en pasos cortos y se detiene para capturar); **ALINEAR** (el "
           "error de rumbo es e = cx − 48; con una banda muerta de ±10 px, que es lo que varió la coordenada x en las pruebas, gira hacia el lado del "
           "error con ω = Kp·e); **ACERCAR** (avanza un paso corto y se detiene a esperar el siguiente cuadro, porque con 0.8 s de latencia no se puede "
           "avanzar sin ver); y **ACCIÓN** (al llegar, ejecuta el gesto de la clase). Como la cámara está a ras de piso, cy sirve de estimador de "
           "distancia, a validar con mediciones, ya que FOMO no entrega el tamaño del objeto.")
    P(doc, "**Cinemática.** La orden (v, ω) se convierte en velocidades por lado con vR = v + ωL/2 y vL = v − ωL/2 (inversas de v = (vR+vL)/2 y "
           "ω = (vR−vL)/L), usando L y los tiempos calibrados de la Tarea 4; el ESP32 de motores las traduce a PWM en el L298N.")
    crear = crear_tabla
    crear(doc, ["Estado", "Condición (salida del detector)", "Acción del robot"],
          [["BUSCAR", "NONE o sin confirmación", "Giro corto a la izquierda, pausa y nueva captura"],
           ["ALINEAR", "Objeto confirmado con |cx − 48| > 10 px", "Giro hacia el objeto con ω = Kp·(cx − 48)"],
           ["ACERCAR", "Objeto centrado y cy menor que el umbral", "Avance corto, parada y verificación"],
           ["ACCIÓN", "Objeto centrado y cy mayor o igual al umbral", "Gesto según la clase (ya implementado en el detector): vaso asiente, jarra niega, laptop gira una vuelta"]],
          anchos_columnas=[0.8, 2.5, 2.85], pie_tabla="Tabla P1. Máquina de estados y acciones propuestas.")
    P(doc, "**Riesgos y mitigación.** Confusión vaso/jarra (distinguir con la marca amarilla y la confirmación 2 de 3), falla con luz fuerte o objeto "
           "pegado al fondo (mantener la iluminación y no operar con el objeto a menos de la distancia de entrenamiento) y baja tasa de cuadros "
           "(mover y detenerse). Una variante con ESP32-S3 permitiría más cuadros por segundo.", espacio_antes=3)
    ruta = SALIDA / "PROPUESTA_Integracion_Robot.docx"
    doc.save(str(ruta))
    return ruta


if __name__ == "__main__":
    rutas = [anexo_tabla(), propuesta()]
    if "--sin-pdf" not in sys.argv:
        for r in rutas:
            print("PDF:", exportar_pdf_word(str(r)))
