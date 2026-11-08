#!/usr/bin/env python3
"""Baja los datos de la Tarea 1 del robot y genera los resultados.

Uso (PC conectada al WiFi ESP32Car_Fer):
    python herramientas/tarea1_descargar.py
    python herramientas/tarea1_descargar.py --archivo ruta/tarea1.json   # sin robot

Guarda en docs/Tarea1/datos/:
    tarea1.json     documento completo (copia de GET /t1/datos)
    resultados.md   las mismas cuentas de la etapa E4 de la pagina /tarea1
    pruebas.csv     columnas de calibrar.py (sirve con "calibrar.py analizar")

Solo usa la biblioteca estandar.
"""
import argparse
import csv
import json
import math
import statistics as st
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "docs" / "Tarea1" / "datos"

MOV = {
    "adelante": ("Adelante", (1, 1), "pwm", "t_adelante", 2000),
    "atras": ("Atrás", (-1, -1), "pwm", "t_atras", 2000),
    "giro_izq": ("Giro izquierda", (-1, 1), "pwm_giro", "t90", 500),
    "giro_der": ("Giro derecha", (1, -1), "pwm_giro", "t90d", 500),
    "giro360": ("Giro 360° (izq.)", (-1, 1), "pwm_giro", "t360", 1800),
}
MOVE2 = ["adelante", "atras", "giro_izq", "giro_der", "giro360"]
MOVD = ["adelante", "ida_vuelta", "giro_izq", "giro_der", "giro360"]
COLS = ["fecha", "sesion", "tipo", "pwm_izq", "pwm_der", "ms", "ms_real", "trim_i", "trim_d",
        "avance_cm", "desviacion_cm", "angulo_deg", "dist_origen_cm", "voltaje", "superficie", "nota"]


def num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def nums(a):
    return [x for x in (a or []) if num(x)]


def media(a):
    return st.mean(a) if a else None


def f1(x, d=1):
    return f"{x:.{d}f}" if num(x) else "—"


def get_json(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


class Doc:
    def __init__(self, d, cfg):
        self.d = d
        self.cfg = cfg
        self.t = d.get("tiempos", {})

    def tref(self, m):
        if m == "ida_vuelta":
            return f"{self.t.get('t_adelante')}/{self.t.get('t_atras')}"
        return str(self.t.get(MOV[m][3]))

    def vig(self, m):
        return [r for r in self.d.get("parteD", []) if r.get("mov") == m and r.get("tref") == self.tref(m)]

    def obsoletas(self):
        return [r for r in self.d.get("parteD", []) if r.get("tref") != self.tref(r.get("mov"))]

    def med(self, m, c):
        return media(nums([r["medido"].get(c) for r in self.vig(m)]))

    def calcular(self):
        f = self.d.get("fisicas", {})
        t = self.t
        r = {}
        L = media(nums(f.get("L_cm")))
        av = self.med("adelante", "avance_cm")
        msr = media(nums([x.get("ms_real") for x in self.vig("adelante")]))
        r["L"] = L
        r["v"] = av / (msr / 1000) if num(av) and num(msr) and msr > 0 else None

        def omega(m, clave):
            a = self.med(m, "angulo_deg")
            return a / (t[clave] / 1000) if num(a) and num(t.get(clave)) and t[clave] > 0 else None

        r["wi"] = omega("giro_izq", "t90")
        r["wd"] = omega("giro_der", "t90d")
        r["w360"] = omega("giro360", "t360")
        r["t90teo"] = math.pi * L / (4 * r["v"]) if num(L) and num(r["v"]) else None
        r["Lef"] = 2 * r["v"] / math.radians(r["wi"]) if num(r["v"]) and num(r["wi"]) and r["wi"] > 0 else None
        r["der"] = r["Lef"] / L if num(r["Lef"]) and num(L) else None
        r["err"] = []
        for m, n, c, obj, u in [("adelante", "Adelante", "avance_cm", 100, "cm"),
                                ("ida_vuelta", "Atrás (dist. al origen)", "dist_origen_cm", 0, "cm"),
                                ("giro_izq", "Izquierda", "angulo_deg", 90, "°"),
                                ("giro_der", "Derecha", "angulo_deg", 90, "°"),
                                ("giro360", "360°", "angulo_deg", 360, "°")]:
            a = nums([x["medido"].get(c) for x in self.vig(m)])
            mm = media(a)
            r["err"].append({"mov": m, "n": n, "a": a, "m": mm, "obj": obj, "u": u,
                             "e": mm - obj if num(mm) else None,
                             "pc": (mm - obj) / obj * 100 if num(mm) and obj else None})
        r["desv"] = nums([x["medido"].get("desviacion_cm") for x in self.vig("adelante")])
        vc = f.get("v_carga")
        r["vm"] = lambda pwm: pwm / 255 * (vc - 2) if num(vc) and num(pwm) else None
        return r

    def aviso_voltaje(self):
        v3 = nums([x.get("voltaje") for x in self.d.get("parteD", []) if x.get("tref") == self.tref(x.get("mov"))])
        v2 = []
        for m in MOVE2:
            at = [c for c in self.d.get("calib", []) if c.get("etapa") == "E2" and c.get("mov") == m]
            if at and num(at[-1].get("voltaje")):
                v2.append(at[-1]["voltaje"])
        if v2 and v3 and abs(media(v2) - media(v3)) > 0.5:
            return (f"El voltaje medio cambió {abs(media(v2) - media(v3)):.2f} V entre E2 ({media(v2):.2f} V) "
                    f"y E3 ({media(v3):.2f} V): los tiempos pueden haber dejado de valer.")
        return ""


def markdown(doc):
    c = doc.calcular()
    t = doc.t
    pwm = doc.cfg.get("pwm", 140)
    pwmg = doc.cfg.get("pwm_giro", 140)
    s = "# Resultados de la Tarea 1\n\n"
    av = doc.aviso_voltaje()
    if av:
        s += f"> ⚠ {av}\n\n"
    ob = doc.obsoletas()
    if ob:
        s += f"> ⚠ {len(ob)} repetición(es) de la Parte D usan un tiempo anterior y no se cuentan.\n\n"
    s += "### 6.2 Parte C – Rutinas de movimiento\n\n| # | Movimiento | PWM izq / der | Duración inicial | Duración calibrada |\n|---|---|---|---|---|\n"
    for i, m in enumerate(MOVE2, 1):
        n, sg, g, clave, ini = MOV[m]
        p = pwm if g == "pwm" else pwmg
        sx = lambda k: ("+" if k > 0 else "−") + str(p)
        s += f"| {i} | {n} | {sx(sg[0])} / {sx(sg[1])} | {ini} ms | {t.get(clave)} ms |\n"
    s += ("\n### 6.3 Parte D – Calibración y medición (3 repeticiones)\n\n"
          "| Movimiento | Tiempo (ms) | Resultado esperado | Medido (rep. 1 / 2 / 3) | Promedio | Error |\n|---|---|---|---|---|---|\n")

    def rep(m, k):
        return " / ".join(f1(r["medido"].get(k)) for r in doc.vig(m))

    e = c["err"]
    s += (f"| Adelante | {t.get('t_adelante')} | Línea recta de 1 m | Avance: {rep('adelante', 'avance_cm')} cm; "
          f"desviación lateral: {rep('adelante', 'desviacion_cm')} cm | {f1(e[0]['m'])} cm (desv. {f1(media(c['desv']))} cm) | {f1(e[0]['e'])} cm |\n")
    s += (f"| Atrás | {t.get('t_atras')} | Regreso al punto de inicio | Distancia al origen: {rep('ida_vuelta', 'dist_origen_cm')} cm "
          f"| {f1(e[1]['m'])} cm | {f1(e[1]['e'])} cm |\n")
    for m, n, tm, i, obj in [("giro_izq", "Izquierda", t.get("t90"), 2, "90°"), ("giro_der", "Derecha", t.get("t90d"), 3, "90°"),
                             ("giro360", "360°", t.get("t360"), 4, "360°")]:
        x = e[i]
        s += f"| {n} | {tm} | {obj} | {rep(m, 'angulo_deg')} ° | {f1(x['m'])}° | {f1(x['e'])}° ({f1(x['pc'])} %) |\n"
    f = doc.d.get("fisicas", {})
    s += (f"\n### Valores de la Parte E\n\n- L = {f1(c['L'], 2)} cm; v = {f1(c['v'], 2)} cm/s\n"
          f"- ω izquierda = {f1(c['wi'])} °/s; ω derecha = {f1(c['wd'])} °/s; ω 360° = {f1(c['w360'])} °/s\n"
          f"- t90 teórico = {f1(c['t90teo'] * 1000, 0) if num(c['t90teo']) else '—'} ms contra {t.get('t90')} ms medidos\n"
          f"- L efectiva = {f1(c['Lef'], 2)} cm; factor de derrape = {f1(c['der'], 2)}\n"
          f"- Voltaje de la batería: {f1(f.get('v_reposo'), 2)} V en reposo, {f1(f.get('v_carga'), 2)} V con carga\n"
          f"- Desviación lateral media en 1 m: {f1(media(c['desv']))} cm\n"
          f"- Voltaje medio al motor: {f1(c['vm'](pwm), 2)} V (adelante, PWM {pwm}), {f1(c['vm'](pwmg), 2)} V (giros, PWM {pwmg})\n"
          f"- Medidas físicas: ejes = {f1(media(nums(f.get('ejes_cm'))), 2)} cm; diámetro de llanta = {f1(media(nums(f.get('diam_cm'))), 2)} cm\n")
    return s


def escribir_csv(doc, ruta):
    filas = []

    def fila(e, tipo, nota):
        o = {"fecha": e.get("fecha"), "sesion": "", "tipo": tipo, "pwm_izq": e.get("pwm_l"), "pwm_der": e.get("pwm_r"),
             "ms": e.get("ms"), "ms_real": e.get("ms_real"), "trim_i": e.get("ti", 1), "trim_d": e.get("td", 1),
             "voltaje": e.get("voltaje"), "superficie": e.get("sup", "piso"), "nota": nota}
        o.update(e.get("medido", {}))
        filas.append(o)

    for e in doc.d.get("calib", []):
        m = e.get("mov")
        fila(e, "giro_izq" if m == "giro360" else m, ((e.get("nota") or "") + (" E2" if e.get("etapa") == "E2" else "")).strip())
    for e in doc.d.get("parteD", []):
        m = e.get("mov")
        fila(e, "giro_izq" if m == "giro360" else m,
             f"parteD rep {e.get('rep')}" + ("" if e.get("tref") == doc.tref(m) else " obsoleta"))
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    return len(filas)


def main():
    ap = argparse.ArgumentParser(description="Descarga los datos de la Tarea 1 y genera resultados.md")
    ap.add_argument("--url", default="http://192.168.4.1", help="dirección del robot")
    ap.add_argument("--archivo", help="usar este JSON en vez de pedirlo al robot")
    ap.add_argument("--salida", default=str(SALIDA), help="carpeta de salida")
    a = ap.parse_args()

    cfg = {}
    if a.archivo:
        d = json.loads(Path(a.archivo).read_text(encoding="utf-8"))
    else:
        try:
            d = get_json(a.url + "/t1/datos")
        except Exception as ex:
            sys.exit(f"No pude leer {a.url}/t1/datos ({ex}). ¿La PC está en el WiFi ESP32Car_Fer?")
        try:
            cfg = get_json(a.url + "/config")
        except Exception:
            pass
    if not d.get("version"):
        sys.exit("El robot no tiene datos de la Tarea 1 todavía (documento vacío).")
    out = Path(a.salida)
    out.mkdir(parents=True, exist_ok=True)
    (out / "tarea1.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    doc = Doc(d, cfg)
    (out / "resultados.md").write_text(markdown(doc), encoding="utf-8")
    n = escribir_csv(doc, out / "pruebas.csv")
    print(f"Guardado en {out}: tarea1.json, resultados.md, pruebas.csv ({n} filas)")
    est = d.get("estado", {})
    if est:
        print("Estado de las etapas:", ", ".join(f"{k}={v}" for k, v in est.items() if k in ("E0", "E1", "E2", "E3", "E4")))


if __name__ == "__main__":
    main()
