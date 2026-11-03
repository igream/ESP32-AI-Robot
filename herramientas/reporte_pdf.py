"""Convierte docs/Tarea1/REPORTE.md a PDF con Microsoft Edge (sin instalar nada).

Uso:  python herramientas/reporte_pdf.py
Salida: docs/Tarea1/REPORTE.pdf

El Markdown y el diagrama Mermaid se dibujan en el navegador (marked y mermaid
desde jsdelivr), así que hace falta internet. Las imágenes con ruta relativa
se toman desde docs/Tarea1/.
"""
import json
import pathlib
import subprocess
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
MD = RAIZ / "docs" / "Tarea1" / "REPORTE.md"
HTML = MD.with_name("_reporte.html")
PDF = MD.with_suffix(".pdf")
EDGE = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

PLANTILLA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>Reporte Tarea 1</title>
<style>
  @page { size: Letter; margin: 2cm 1.8cm; }
  body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.5pt; line-height: 1.45; color: #111; }
  h1 { font-size: 20pt; margin-top: 0; } h2 { font-size: 14pt; border-bottom: 1px solid #999; margin-top: 1.4em; }
  h3 { font-size: 12pt; } table { border-collapse: collapse; width: 100%; margin: .6em 0; font-size: 9.5pt; }
  th, td { border: 1px solid #888; padding: 3px 6px; vertical-align: top; } th { background: #eee; }
  code { font-family: Consolas, monospace; font-size: 9pt; background: #f3f3f3; padding: 0 2px; }
  pre { background: #f6f6f6; padding: 8px; overflow-wrap: anywhere; white-space: pre-wrap; }
  blockquote { border-left: 3px solid #aaa; margin-left: 0; padding-left: 10px; color: #333; }
  img { max-width: 100%; } tr, img, pre, .mermaid { page-break-inside: avoid; }
  .mermaid { text-align: center; }
</style></head><body><div id="c"></div>
<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
  const md = __MD__;
  const r = new marked.Renderer();
  const code0 = r.code.bind(r);
  r.code = (code, lang, esc) => lang === "mermaid" ? '<div class="mermaid">' + code + '</div>' : code0(code, lang, esc);
  document.getElementById("c").innerHTML = marked.parse(md, { renderer: r });
  mermaid.initialize({ startOnLoad: false, theme: "neutral" });
  mermaid.run();
</script></body></html>"""


def main():
    edge = next((e for e in EDGE if pathlib.Path(e).exists()), None)
    if not edge:
        sys.exit("No se encontró Microsoft Edge.")
    texto = MD.read_text(encoding="utf-8")
    HTML.write_text(PLANTILLA.replace("__MD__", json.dumps(texto)), encoding="utf-8")
    subprocess.run([
        edge, "--headless", "--disable-gpu", "--no-pdf-header-footer",
        "--virtual-time-budget=15000", f"--print-to-pdf={PDF}", HTML.as_uri(),
    ], check=True, capture_output=True)
    HTML.unlink()
    print(f"PDF: {PDF}")


if __name__ == "__main__":
    main()
