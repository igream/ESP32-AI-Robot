"""Utilidades de formato Word para los reportes (sobre python-docx y la skill de Ciencia de Datos UAEMéx).

- titulo(): encabezados con estilos reales Título 1/2/3 (alimentan el índice), Times New Roman negro.
- indice(): campo TOC vinculado; exportar() lo actualiza con Word.
- Ecuaciones nativas de Word (OMML): M.var/M.txt/M.frac/M.sub/M.par, ecuacion() (centrada y numerada) y parrafo_mixto() (texto + ecuaciones en línea).
- hipervinculo(), video_en_linea() (video en línea de Word con miniatura), tabla_gris() y todo_negro().
"""
import copy
import re
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

NS = nsdecls("w", "r", "wp", "a", "pic") + ' xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"'
FUENTE = "Times New Roman"
CUERPO = 9.5


# ------------------------------------------------------------------ texto
def _fmt_run(run, tam=CUERPO, negrita=False, cursiva=False, subrayado=False):
    run.font.name = FUENTE
    run._element.rPr.rFonts.set(qn("w:eastAsia"), FUENTE)
    run.font.size = Pt(tam)
    run.bold = negrita
    run.italic = cursiva
    run.underline = subrayado
    run.font.color.rgb = RGBColor(0, 0, 0)


def agregar_texto(p, texto, tam=CUERPO):
    """Añade texto con **negrita** y `código` (sin comillas) a un párrafo."""
    texto = texto.replace("`", "")
    for i, trozo in enumerate(texto.split("**")):
        if trozo:
            _fmt_run(p.add_run(trozo), tam, negrita=(i % 2 == 1))


def _estilo_titulos(doc):
    tam = {1: 10.5, 2: 9.5, 3: 9.0}
    for n in (1, 2, 3):
        st = doc.styles[f"Heading {n}"]
        st.font.name = FUENTE
        st.font.size = Pt(tam[n])
        st.font.bold = True
        st.font.italic = False
        st.font.color.rgb = RGBColor(0, 0, 0)
        rpr = st.element.get_or_add_rPr()
        fonts = rpr.find(qn("w:rFonts"))
        if fonts is None:
            fonts = parse_xml(f"<w:rFonts {nsdecls('w')}/>")
            rpr.append(fonts)
        for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            fonts.set(qn(a), FUENTE)
        for a in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if fonts.get(qn(a)) is not None:
                del fonts.attrib[qn(a)]


def titulo(doc, texto, nivel=1, espacio_antes=3.5, espacio_despues=1.5, salto_antes=False):
    """Encabezado con el estilo real de Word (Título 1/2/3): aparece en el panel de navegación y en el índice."""
    if not getattr(doc, "_estilos_ok", False):
        _estilo_titulos(doc)
        doc._estilos_ok = True
    p = doc.add_paragraph(style=f"Heading {nivel}")
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(espacio_antes), Pt(espacio_despues), 1.1
    pf.keep_with_next = True
    pf.page_break_before = salto_antes
    _fmt_run(p.add_run(texto), {1: 10.5, 2: 9.5, 3: 9.0}[nivel], negrita=True)
    return p


def parrafo(doc, texto, espacio_antes=0, espacio_despues=2.0, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY, tam=CUERPO):
    p = doc.add_paragraph()
    p.alignment = alineacion
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(espacio_antes), Pt(espacio_despues), 1.1
    agregar_texto(p, texto, tam)
    return p


# ------------------------------------------------------------------ hipervínculos
def hipervinculo(p, url, texto=None, tam=CUERPO, negrita=False):
    """Hipervínculo externo clicable, en negro y subrayado."""
    rid = p.part.relate_to(url, RT.HYPERLINK, is_external=True)
    h = parse_xml(f'<w:hyperlink {nsdecls("w", "r")} r:id="{rid}" w:history="1"/>')
    r = parse_xml(f'<w:r {nsdecls("w")}><w:rPr><w:rFonts w:ascii="{FUENTE}" w:hAnsi="{FUENTE}" w:eastAsia="{FUENTE}"/>'
                  f'{"<w:b/>" if negrita else ""}<w:color w:val="000000"/><w:sz w:val="{int(tam * 2)}"/><w:u w:val="single"/></w:rPr>'
                  f'<w:t xml:space="preserve">{escape(texto or url)}</w:t></w:r>')
    h.append(r)
    p._p.append(h)
    return h


# ------------------------------------------------------------------ ecuaciones (OMML)
class M:
    """Constructores de ecuaciones de Word. Cada método devuelve un fragmento XML."""

    @staticmethod
    def var(t):                       # variable: cursiva automática de Word
        return f'<m:r><m:t xml:space="preserve">{escape(t)}</m:t></m:r>'

    @staticmethod
    def txt(t):                       # texto recto (unidades, PWM, etiquetas)
        return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr><m:t xml:space="preserve">{escape(t)}</m:t></m:r>'

    @staticmethod
    def frac(n, d):
        return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"

    @staticmethod
    def sub(b, s):
        return f"<m:sSub><m:e>{b}</m:e><m:sub>{s}</m:sub></m:sSub>"

    @staticmethod
    def sup(b, s):
        return f"<m:sSup><m:e>{b}</m:e><m:sup>{s}</m:sup></m:sSup>"

    @staticmethod
    def par(c):
        return f"<m:d><m:e>{c}</m:e></m:d>"


def _omath(xml):
    return parse_xml(f'<m:oMath {NS}>{xml}</m:oMath>')


def _sin_bordes(tabla):
    tblPr = tabla._tbl.tblPr
    tblPr.append(parse_xml(f'<w:tblBorders {nsdecls("w")}>' + "".join(
        f'<w:{b} w:val="nil"/>' for b in ("top", "left", "bottom", "right", "insideH", "insideV")) + "</w:tblBorders>"))


def ecuacion(doc, xml, numero):
    """Ecuación centrada (modo display de Word) con su número a la derecha, mediante una tabla sin bordes."""
    t = doc.add_table(rows=1, cols=3)
    t.autofit = False
    _sin_bordes(t)
    anchos = (0.55, 5.0, 0.55)
    for c, w in zip(t.rows[0].cells, anchos):
        c.width = Inches(w)
    centro = t.rows[0].cells[1].paragraphs[0]
    centro.alignment = WD_ALIGN_PARAGRAPH.CENTER
    centro.paragraph_format.space_before = centro.paragraph_format.space_after = Pt(1)
    centro._p.append(parse_xml(f'<m:oMathPara {NS}><m:oMath>{xml}</m:oMath></m:oMathPara>'))
    der = t.rows[0].cells[2].paragraphs[0]
    der.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    _fmt_run(der.add_run(f"({numero})"), CUERPO)
    for c in t.rows[0].cells:
        c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for p in c.paragraphs:
            p.paragraph_format.keep_with_next = True
    return t


def parrafo_mixto(doc, items, espacio_antes=0, espacio_despues=2.0):
    """Párrafo justificado con texto (str, admite **negrita**) y ecuaciones en línea (tuple ('m', xml))."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing = Pt(espacio_antes), Pt(espacio_despues), 1.1
    for it in items:
        if isinstance(it, tuple):
            p._p.append(_omath(it[1]))
        else:
            agregar_texto(p, it)
    return p


def en_linea(xml):
    return ("m", xml)


# ------------------------------------------------------------------ video en línea de Word
def video_en_linea(doc, url_video, url_embed, miniatura, ancho_pulgadas=4.2, descripcion="Video"):
    """Inserta un 'video en línea' de Word: miniatura con enlace al video (se reproduce desde Word)."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.keep_with_next = True
    run = p.add_run()
    inline = run.add_picture(str(miniatura), width=Inches(ancho_pulgadas))
    rid_img = inline._inline.graphic.graphicData.pic.blipFill.blip.embed
    rid_link = p.part.relate_to(url_video, RT.HYPERLINK, is_external=True)
    rid_vid = p.part.relate_to(url_embed, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/video", is_external=True)
    pic = inline._inline.graphic.graphicData.pic
    cNvPr = pic.nvPicPr.cNvPr
    cNvPr.append(parse_xml(f'<a:hlinkClick {nsdecls("a", "r")} r:id="{rid_link}"/>'))
    nvPr = pic.nvPicPr.find(qn("pic:nvPr"))
    if nvPr is None:
        nvPr = parse_xml(f'<pic:nvPr {nsdecls("pic")}/>')
        pic.nvPicPr.append(nvPr)
    nvPr.append(parse_xml(f'<a:videoFile {nsdecls("a", "r")} r:link="{rid_vid}"/>'))
    dp = inline._inline.docPr
    dp.set("name", "Video en línea")
    dp.set("descr", descripcion)
    dp.append(parse_xml(f'<a:hlinkClick {nsdecls("a", "r")} r:id="{rid_link}"/>'))
    return p


# ------------------------------------------------------------------ índice, tablas y color
def indice(doc, titulo_texto="ÍNDICE"):
    """Título del índice (sin entrar en él) y campo TOC de Título 1-2 vinculado; exportar() lo actualiza."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    _fmt_run(p.add_run(titulo_texto), 10.5, negrita=True)
    p = doc.add_paragraph()
    r = p.add_run()
    r._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin" w:dirty="true"/>'))
    r2 = p.add_run()
    r2._r.append(parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText>'))
    r3 = p.add_run()
    r3._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="separate"/>'))
    r4 = p.add_run("Haz clic derecho y elige «Actualizar campo» para generar el índice.")
    _fmt_run(r4, CUERPO)
    r5 = p.add_run()
    r5._r.append(parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="end"/>'))


def tabla_gris(tabla, gris="D9D9D9"):
    """Encabezado gris con texto negro (la skill lo pone oscuro con texto blanco)."""
    for celda in tabla.rows[0].cells:
        tcPr = celda._tc.get_or_add_tcPr()
        for shd in tcPr.findall(qn("w:shd")):
            tcPr.remove(shd)
        tcPr.append(parse_xml(f'<w:shd {nsdecls("w")} w:val="clear" w:color="auto" w:fill="{gris}"/>'))
        for p in celda.paragraphs:
            for r in p.runs:
                r.font.color.rgb = RGBColor(0, 0, 0)
                r.bold = True


def todo_negro(doc, desde=0):
    """Pone en negro todo el texto del cuerpo (párrafos, tablas y vínculos), salvo la portada (los primeros `desde` párrafos)."""
    cuerpo = doc.element.body
    for i, r in enumerate(cuerpo.iter(qn("w:r"))):
        rPr = r.find(qn("w:rPr"))
        if rPr is None:
            rPr = parse_xml(f"<w:rPr {nsdecls('w')}/>")
            r.insert(0, rPr)
        for c in rPr.findall(qn("w:color")):
            rPr.remove(c)
        rPr.append(parse_xml(f'<w:color {nsdecls("w")} w:val="000000"/>'))


# ------------------------------------------------------------------ exportación con Word
VBS = r"""
Set-StrictMode -Off
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Open('{docx}')
foreach ($t in $doc.TablesOfContents) {{ $t.Update() }}
foreach ($n in -20,-21) {{
  try {{
    $st = $doc.Styles.Item($n)
    $st.Font.Name = 'Times New Roman'; $st.Font.Size = 9.5; $st.Font.Color = 0
    $st.ParagraphFormat.SpaceAfter = 1; $st.ParagraphFormat.SpaceBefore = 0
  }} catch {{ }}
}}
$doc.Fields.Update() | Out-Null
foreach ($t in $doc.TablesOfContents) {{ $t.Update() }}
$doc.Save()
$doc.SaveAs([ref]'{pdf}', [ref]17)
$doc.Close()
$word.Quit()
"""


def exportar(ruta_docx):
    """Actualiza el índice y los campos con Word, guarda el .docx y exporta el PDF (con enlaces y marcadores)."""
    ruta_docx = str(Path(ruta_docx).resolve())
    pdf = ruta_docx.replace(".docx", ".pdf")
    script = VBS.format(docx=ruta_docx.replace("'", "''"), pdf=pdf.replace("'", "''"))
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True)
    return pdf
