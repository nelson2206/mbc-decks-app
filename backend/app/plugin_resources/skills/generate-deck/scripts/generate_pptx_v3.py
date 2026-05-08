"""
generate_pptx_v3.py — Build from scratch usando slide_content del A4.

A diferencia del v2 (que copia un reference deck), v3 construye el deck slide a slide
desde el contenido generado por A4 + el template Minsait limpio.

Ventaja: el contenido es 100% del tema solicitado, no contaminado por el deck de origen.

Inputs:
  - slide_content: dict {slides: [{order, layout_kind, title, subtitle, bullets, note}]}
  - deck_brief: dict con {client, deck.title, etc.}
  - output_path: ruta destino .pptx
"""
from __future__ import annotations
import json
import os
import re
import shutil
import stat
import sys
import zipfile
from pathlib import Path
from typing import Any, Optional

try:
    from pptx import Presentation
    from pptx.util import Pt, Inches, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    print("python-pptx required", file=sys.stderr)
    sys.exit(1)


# Paleta Minsait
PRUNO = RGBColor(0x4F, 0x06, 0x2A)
PRUNO_OSCURO = RGBColor(0x33, 0x04, 0x1B)
CERAMICA = RGBColor(0xE8, 0xDD, 0xD2)
MAGENTA = RGBColor(0xC8, 0x21, 0x7A)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)
GRIS_TEXTO = RGBColor(0x44, 0x44, 0x44)
NARANJA = RGBColor(0xE6, 0x6B, 0x1F)
VERDE = RGBColor(0x3A, 0x8C, 0x4F)


def _add_key_metric(slide, value: str, label: str, context: str = "", left=Inches(8.0), top=Inches(1.5), width=Inches(4.5), height=Inches(3.0)):
    """Caja grande con número clave (estilo consulting callout)."""
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    box.fill.solid()
    box.fill.fore_color.rgb = PRUNO
    box.line.color.rgb = PRUNO
    tf = box.text_frame
    tf.margin_top = Inches(0.2)
    tf.margin_left = Inches(0.3)
    tf.margin_right = Inches(0.3)
    tf.margin_bottom = Inches(0.2)
    tf.word_wrap = True
    # Value (big)
    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    r1 = p1.add_run()
    r1.text = value
    r1.font.size = Pt(54)
    r1.font.bold = True
    r1.font.color.rgb = BLANCO
    # Label
    p2 = tf.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    r2 = p2.add_run()
    r2.text = label
    r2.font.size = Pt(13)
    r2.font.color.rgb = BLANCO
    # Context (small)
    if context:
        p3 = tf.add_paragraph()
        p3.alignment = PP_ALIGN.CENTER
        r3 = p3.add_run()
        r3.text = context
        r3.font.size = Pt(9)
        r3.font.italic = True
        r3.font.color.rgb = CERAMICA


def _add_table(slide, headers: list, rows: list, left=Inches(0.5), top=Inches(2.5), width=Inches(12.3), height=Inches(4.0)):
    """Inserta una tabla nativa estilo consulting (header pruno, filas alternadas)."""
    if not headers or not rows:
        return
    n_cols = len(headers)
    n_rows = len(rows) + 1
    tbl_shape = slide.shapes.add_table(n_rows, n_cols, left, top, width, height)
    tbl = tbl_shape.table
    # Distribuir alturas uniformemente: header 0.45in, data rows iguales
    header_h = Inches(0.45)
    data_h = Inches(max(0.35, (height.inches - 0.45) / len(rows)))
    tbl.rows[0].height = header_h
    for i in range(1, n_rows):
        tbl.rows[i].height = data_h
    # Header row
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.text = ""
        cell.fill.solid()
        cell.fill.fore_color.rgb = PRUNO
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.12); cell.margin_right = Inches(0.08)
        cell.margin_top = Inches(0.06); cell.margin_bottom = Inches(0.06)
        tf = cell.text_frame
        para = tf.paragraphs[0]
        para.alignment = PP_ALIGN.LEFT
        r = para.add_run()
        r.text = str(h)
        r.font.bold = True
        r.font.size = Pt(11)
        r.font.color.rgb = BLANCO
    # Data rows
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            if j >= n_cols:
                break
            cell = tbl.cell(i, j)
            cell.fill.solid()
            # Total row destacada (last row)
            is_total = i == len(rows) and any(str(v).upper().strip() == "TOTAL" for v in row)
            if is_total:
                cell.fill.fore_color.rgb = PRUNO
            else:
                cell.fill.fore_color.rgb = BLANCO if i % 2 else CERAMICA
            cell.text = ""
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.margin_left = Inches(0.12); cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.04); cell.margin_bottom = Inches(0.04)
            tf = cell.text_frame
            tf.word_wrap = True
            para = tf.paragraphs[0]
            para.alignment = PP_ALIGN.LEFT
            r = para.add_run()
            r.text = str(val)
            r.font.size = Pt(10)
            r.font.color.rgb = BLANCO if is_total else GRIS_TEXTO
            r.font.bold = is_total


def _add_comparison(slide, left_label: str, right_label: str, left_items: list, right_items: list,
                    left=Inches(0.5), top=Inches(2.5), width=Inches(12.3), height=Inches(4.0)):
    """Dos columnas lado a lado, items distribuidos uniformemente con bullets visibles."""
    half_w = Inches((width.inches - 0.3) / 2)

    def _build_col(box_left, label, items, fg_color, bg_color, bullet_color):
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, box_left, top, half_w, height)
        box.fill.solid(); box.fill.fore_color.rgb = bg_color
        box.line.color.rgb = bg_color
        # Header del bloque (en una caja de texto separada arriba dentro del bloque)
        hdr_h = Inches(0.7)
        hdr = slide.shapes.add_textbox(box_left, top, half_w, hdr_h)
        tf_h = hdr.text_frame
        tf_h.margin_top = Inches(0.18); tf_h.margin_left = Inches(0.3); tf_h.margin_right = Inches(0.3)
        ph = tf_h.paragraphs[0]; ph.alignment = PP_ALIGN.LEFT
        rh = ph.add_run(); rh.text = label.upper()
        rh.font.bold = True; rh.font.size = Pt(16); rh.font.color.rgb = fg_color
        # Items distribuidos
        items_top = Inches(top.inches + 0.85)
        items_h = Inches(height.inches - 1.0)
        items_box = slide.shapes.add_textbox(box_left, items_top, half_w, items_h)
        tf_i = items_box.text_frame
        tf_i.margin_top = Inches(0.1); tf_i.margin_left = Inches(0.4); tf_i.margin_right = Inches(0.3)
        tf_i.word_wrap = True
        for idx, item in enumerate(items):
            para = tf_i.paragraphs[0] if idx == 0 else tf_i.add_paragraph()
            para.space_after = Pt(10); para.space_before = Pt(0)
            # Bullet point manual
            r1 = para.add_run(); r1.text = "▪  "; r1.font.size = Pt(13); r1.font.color.rgb = bullet_color; r1.font.bold = True
            r2 = para.add_run(); r2.text = str(item); r2.font.size = Pt(13); r2.font.color.rgb = fg_color

    # Columna izquierda (cerámica fondo, pruno texto)
    _build_col(left, left_label, left_items, PRUNO, CERAMICA, MAGENTA)
    # Columna derecha (pruno fondo, blanco texto)
    right_left = Inches(left.inches + half_w.inches + 0.3)
    _build_col(right_left, right_label, right_items, BLANCO, PRUNO, MAGENTA)


def _add_process_steps(slide, steps: list, left=Inches(0.5), top=Inches(2.0), width=Inches(12.3), height=Inches(3.5)):
    """Cadena horizontal de N pasos. Cajas más altas (3.5in) para no dejar slide vacío."""
    if not steps:
        return
    n = len(steps)
    box_w = (width.inches - (n - 1) * 0.15) / n
    for i, step in enumerate(steps):
        x = Inches(left.inches + i * (box_w + 0.15))
        b = slide.shapes.add_shape(MSO_SHAPE.PENTAGON if i < n - 1 else MSO_SHAPE.ROUNDED_RECTANGLE,
                                    x, top, Inches(box_w), height)
        b.fill.solid()
        b.fill.fore_color.rgb = PRUNO if i % 2 == 0 else MAGENTA
        b.line.color.rgb = PRUNO
        tf = b.text_frame
        tf.margin_top = Inches(0.4); tf.margin_left = Inches(0.25); tf.margin_right = Inches(0.25)
        tf.margin_bottom = Inches(0.3)
        tf.word_wrap = True
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        # Step number
        p1 = tf.paragraphs[0]
        p1.alignment = PP_ALIGN.CENTER
        p1.space_after = Pt(8)
        r1 = p1.add_run(); r1.text = f"FASE {step.get('step', i+1)}"
        r1.font.size = Pt(11); r1.font.color.rgb = CERAMICA; r1.font.bold = True
        # Label
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.space_after = Pt(12)
        r2 = p2.add_run(); r2.text = str(step.get('label', ''))
        r2.font.size = Pt(20); r2.font.bold = True; r2.font.color.rgb = BLANCO
        # Description
        if step.get('description'):
            p3 = tf.add_paragraph()
            p3.alignment = PP_ALIGN.CENTER
            r3 = p3.add_run(); r3.text = str(step['description'])
            r3.font.size = Pt(11); r3.font.color.rgb = CERAMICA


def _add_quote(slide, text: str, attribution: str = "",
               left=Inches(1.5), top=Inches(2.5), width=Inches(10.3), height=Inches(3.5),
               on_dark: bool = False):
    """Cita destacada centrada. on_dark=True = fondo oscuro (closing pruno), on_dark=False = fondo claro."""
    text_color = BLANCO if on_dark else PRUNO
    attr_color = CERAMICA if on_dark else MAGENTA
    # Comilla decorativa grande arriba
    decor = slide.shapes.add_textbox(left, Inches(top.inches - 0.3), Inches(1.2), Inches(1.0))
    tfd = decor.text_frame
    pd = tfd.paragraphs[0]; pd.alignment = PP_ALIGN.LEFT
    rd = pd.add_run(); rd.text = '"'
    rd.font.size = Pt(80); rd.font.bold = True; rd.font.color.rgb = MAGENTA
    # Cita
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.5)
    p1 = tf.paragraphs[0]
    p1.alignment = PP_ALIGN.LEFT
    p1.space_after = Pt(20)
    r1 = p1.add_run(); r1.text = text
    r1.font.size = Pt(28); r1.font.italic = True; r1.font.color.rgb = text_color
    if attribution:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.LEFT
        r2 = p2.add_run(); r2.text = "— " + attribution
        r2.font.size = Pt(14); r2.font.color.rgb = attr_color; r2.font.bold = True


def _add_footnote(slide, text: str):
    """Footnote pequeño abajo del slide (fuente)."""
    if not text:
        return
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(6.95), Inches(8.5), Inches(0.3))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = text
    r.font.size = Pt(8); r.font.italic = True; r.font.color.rgb = GRIS_TEXTO


def _add_corporate_footer(slide, footer_text: str):
    """Footer corporativo formato brandbook: 'MINSAIT • Cliente · dd/mm/aaaa'.
    Posición: abajo izquierda · 8pt · ForFuture Sans · Pruno o Cerámica según fondo."""
    if not footer_text:
        return
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(7.2), Inches(8.0), Inches(0.25))
    tf = tb.text_frame
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.LEFT
    r = p.add_run(); r.text = footer_text
    r.font.size = Pt(8); r.font.color.rgb = PRUNO
    r.font.name = "ForFuture Sans"  # del brandbook


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_DIR = SKILL_DIR.parent.parent

TEMPLATE_PPTX = PLUGIN_DIR / "assets" / "template" / "PPT_MINSAIT_Template_esp.pptx"
TEMPLATE_POTX = PLUGIN_DIR / "assets" / "template" / "PPT_MINSAIT_Template_esp.potx"


# Mapeo layout_kind → índice en el catálogo de 40 layouts del template Minsait
LAYOUT_KIND_TO_INDEX = {
    "cover":             1,   # PORTADA - H - Pruno
    "cover_partner":     6,   # PORTADA - H - Pruno+Partner
    "objectives":        17,  # CONTENIDO - Texto - Ceramico (con antetítulo)
    "index":             12,  # ÍNDICE - Corto
    "index_long":        13,  # ÍNDICE - Largo
    "section_divider":   13,  # SEPARATA - Principal
    "context":           18,  # CONTENIDO - Texto - Sin antetitulo_Ceramico
    "key_idea":          28,  # CONTENIDO - Idea Principal - Pruno
    "proposal_pillars":  17,
    "methodology":       17,
    "timeline":          18,
    "team":              17,
    "risks":             17,
    "investment":        17,
    "closing":           34,  # CIERRE - Pruno
}


def _ensure_pptx_template() -> Path:
    """Convertir .potx a .pptx si no existe."""
    if TEMPLATE_PPTX.exists():
        return TEMPLATE_PPTX
    if not TEMPLATE_POTX.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_POTX}")
    with zipfile.ZipFile(TEMPLATE_POTX, "r") as zin:
        files = {n: zin.read(n) for n in zin.namelist()}
    ct = files["[Content_Types].xml"].decode("utf-8")
    ct = ct.replace(
        "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    )
    files["[Content_Types].xml"] = ct.encode("utf-8")
    with zipfile.ZipFile(TEMPLATE_PPTX, "w", zipfile.ZIP_DEFLATED) as zout:
        for n, d in files.items():
            zout.writestr(n, d)
    return TEMPLATE_PPTX


def _strip_existing_slides(prs: Presentation):
    """Remover todas las slides preexistentes del template."""
    sld_id_lst = prs.slides._sldIdLst  # noqa
    to_remove = list(sld_id_lst)
    for sld in to_remove:
        rId = sld.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        prs.part.drop_rel(rId)
        sld_id_lst.remove(sld)


def _set_text_in_placeholder(slide, text: str, kinds: tuple[str, ...] = ("title",)):
    """Set text in any placeholder matching kinds (title, body, etc.)."""
    if not text:
        return
    # Try shapes.title first
    if "title" in kinds and slide.shapes.title is not None:
        slide.shapes.title.text = text
        return
    # Try other placeholders
    for shape in slide.placeholders:
        ph = shape.placeholder_format
        if ph.type is not None:
            ph_kind = str(ph.type).lower()
            if any(k in ph_kind for k in kinds):
                if shape.has_text_frame:
                    shape.text_frame.text = text
                    return


def _set_bullets_in_body(slide, bullets: list[str]):
    """Insert bullets in the first non-title placeholder."""
    if not bullets:
        return
    body_ph = None
    for shape in slide.placeholders:
        if shape.placeholder_format.idx != 0 and shape.has_text_frame:
            body_ph = shape
            break
    if body_ph is None:
        # Fallback: cualquier shape con text_frame que no sea el título
        for shape in slide.shapes:
            if shape.has_text_frame and shape != slide.shapes.title:
                body_ph = shape
                break
    if body_ph is None:
        return
    tf = body_ph.text_frame
    tf.clear()
    for i, b in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = b
        p.level = 0


def _normalize_bullets(body) -> list[str]:
    """A4 puede devolver bullets como list[str] o body como list[{type,text,...}].
    Esta función lo normaliza a list[str]."""
    if not body:
        return []
    if isinstance(body, str):
        return [body]
    out = []
    for item in body:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            if "text" in item:
                out.append(str(item["text"]))
            elif "key" in item and "value" in item:
                out.append(f"{item['key']}: {item['value']}")
            elif "label" in item and "value" in item:
                out.append(f"{item['label']}: {item['value']}")
    return out


def _normalize_slide(s: dict, order_hint: int = 0) -> dict:
    """Normaliza un slide al formato canónico que entiende este generador.
    Conserva TODOS los campos ricos: key_metric, table, comparison, process_steps, quote, footnote.
    """
    bullets_raw = s.get("bullets") or s.get("body") or s.get("content") or []
    return {
        "order": s.get("order") or s.get("slide_order") or order_hint,
        "layout_kind": s.get("layout_kind") or s.get("layout") or s.get("kind") or "context",
        "antetitle": s.get("antetitle") or "",
        "title": s.get("title") or "",
        "subtitle": s.get("subtitle") or "",
        "bullets": _normalize_bullets(bullets_raw),
        "key_metric": s.get("key_metric"),
        "table": s.get("table"),
        "comparison": s.get("comparison"),
        "process_steps": s.get("process_steps"),
        "quote": s.get("quote"),
        "footnote": s.get("footnote") or "",
        "note": s.get("note") or s.get("speaker_notes") or "",
    }


def _extract_slides_data(slide_content) -> list[dict]:
    """Extrae la lista de slides desde cualquiera de los formatos que A4 puede devolver:
       1) {"slides": [...]}
       2) [{...}, {...}]   (lista directa)
       3) {"1": {...}, "2": {...}}  (dict keyed by slide order — el formato real de A4 hoy)
       4) {"raw": "..."}   (parser falló)  -> []
    """
    if isinstance(slide_content, list):
        return [_normalize_slide(s, i+1) for i, s in enumerate(slide_content)]
    if not isinstance(slide_content, dict):
        return []
    if "slides" in slide_content and isinstance(slide_content["slides"], list):
        return [_normalize_slide(s, i+1) for i, s in enumerate(slide_content["slides"])]
    if "raw" in slide_content:
        return []
    # Caso 3: dict con claves "1", "2", ... o numéricas
    items = []
    for k, v in slide_content.items():
        if not isinstance(v, dict):
            continue
        try:
            order = int(k)
        except (ValueError, TypeError):
            order = v.get("order") or v.get("slide_order") or 0
        items.append((order, v))
    items.sort(key=lambda x: x[0])
    return [_normalize_slide(v, o or i+1) for i, (o, v) in enumerate(items)]


def generate_from_content(
    slide_content: dict,
    deck_brief: dict,
    output_path: str,
) -> str:
    """Construye el .pptx desde slide_content. Tolera múltiples formatos del A4."""
    template = _ensure_pptx_template()
    prs = Presentation(str(template))
    _strip_existing_slides(prs)

    slides_data = _extract_slides_data(slide_content)
    if not slides_data:
        # Último recurso: deck mínimo de 1 slide para que el flujo no falle
        slides_data = [{
            "order": 1, "layout_kind": "cover",
            "title": deck_brief.get("deck", {}).get("title_working", "Deck"),
            "subtitle": deck_brief.get("client", {}).get("name_commercial", ""),
            "bullets": [], "note": "Fallback: slide_content no tenía slides reconocibles. Revisar logs A4.",
        }]

    n_layouts = len(prs.slide_layouts)
    for s in sorted(slides_data, key=lambda x: x.get("order", 0)):
        layout_kind = s.get("layout_kind", "context")
        # Selección de layout más inteligente según los componentes presentes
        has_table = bool(s.get("table"))
        has_comparison = bool(s.get("comparison"))
        has_process = bool(s.get("process_steps"))
        has_metric = bool(s.get("key_metric"))
        has_quote = bool(s.get("quote"))
        # Para slides con elementos visuales grandes → usar layout BLANCO sin placeholders
        # para que no choquen con los shapes que dibujamos.
        # Closing+quote: layout PRUNO full impact
        if layout_kind == "closing" and has_quote:
            layout_idx = 32  # VACIA_Pruno (fondo pruno)
        elif has_table or has_comparison or has_process or has_quote:
            layout_idx = 31  # VACIA_Blanca
        elif has_metric:
            layout_idx = 19  # CONTENIDO - Texto - Blanco (con antetítulo)
        else:
            layout_idx = LAYOUT_KIND_TO_INDEX.get(layout_kind, 17)
        if layout_idx >= n_layouts:
            layout_idx = 17
        layout = prs.slide_layouts[layout_idx]
        slide = prs.slides.add_slide(layout)

        title = s.get("title", "")
        subtitle = s.get("subtitle", "")
        antetitle = s.get("antetitle", "")
        bullets = s.get("bullets", []) or []

        # Title — siempre lo intentamos en el placeholder del template, pero si el
        # layout es VACIA_Blanca no tiene title, así que lo dibujamos manualmente.
        if layout_idx in (30, 31, 32):  # VACIA layouts
            # Slide closing/quote: layout pruno full impact, todo el texto en blanco centrado
            is_closing = layout_kind in ("closing",) and has_quote
            if is_closing:
                # Título Gracias arriba, en blanco, centrado
                tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.8), Inches(12.3), Inches(1.2))
                tf = tb.text_frame
                p_t = tf.paragraphs[0]
                p_t.alignment = PP_ALIGN.CENTER
                r_t = p_t.add_run(); r_t.text = title
                r_t.font.size = Pt(48); r_t.font.bold = True; r_t.font.color.rgb = BLANCO
            else:
                tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.3), Inches(0.9))
                tf = tb.text_frame
                if antetitle:
                    p_a = tf.paragraphs[0]
                    r_a = p_a.add_run(); r_a.text = antetitle.upper()
                    r_a.font.size = Pt(10); r_a.font.color.rgb = MAGENTA; r_a.font.bold = True
                    p_t = tf.add_paragraph()
                else:
                    p_t = tf.paragraphs[0]
                r_t = p_t.add_run(); r_t.text = title
                r_t.font.size = Pt(22); r_t.font.bold = True; r_t.font.color.rgb = PRUNO
        else:
            # Cover: ajustar font size si título es largo para evitar overlap.
            is_cover = layout_kind in ("cover", "cover_partner")
            if title and slide.shapes.title is not None:
                slide.shapes.title.text = title
                # Si título largo, reducir font del placeholder
                if is_cover and len(title) > 50:
                    for para in slide.shapes.title.text_frame.paragraphs:
                        for run in para.runs:
                            # Reducir 30% para que quepa en 2 líneas
                            try:
                                if run.font.size and run.font.size.pt > 0:
                                    run.font.size = Pt(int(run.font.size.pt * 0.7))
                                else:
                                    run.font.size = Pt(28)
                            except Exception:
                                run.font.size = Pt(28)
                # Subtitle en placeholder secundario si existe
                if subtitle and is_cover:
                    for sh in slide.placeholders:
                        if sh.placeholder_format.idx != 0 and sh.has_text_frame and not sh.text_frame.text.strip():
                            try:
                                sh.text_frame.text = subtitle
                                break
                            except Exception:
                                pass

        # Layout de contenido según componentes presentes
        if has_table:
            tbl = s["table"]
            n_rows_data = len(tbl.get("rows", []))
            if n_rows_data <= 4:
                tbl_h = Inches(3.5)
            elif n_rows_data <= 6:
                tbl_h = Inches(4.5)
            else:
                tbl_h = Inches(5.2)
            _add_table(slide, tbl.get("headers", []), tbl.get("rows", []),
                       top=Inches(1.5), height=tbl_h)
            # Accent magenta solo en layouts VACIA (sin title placeholder propio)
            if layout_idx in (30, 31, 32):
                bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.05), Inches(2.0), Inches(0.05))
                bar.fill.solid(); bar.fill.fore_color.rgb = MAGENTA; bar.line.fill.background()
            # Si también hay bullets cortos, ponerlos abajo
            if bullets and len(bullets) <= 3:
                tb = slide.shapes.add_textbox(Inches(0.5), Inches(6.1), Inches(12.3), Inches(0.8))
                tf = tb.text_frame; tf.word_wrap = True
                for i, b in enumerate(bullets):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    r = p.add_run(); r.text = "· " + str(b)
                    r.font.size = Pt(10); r.font.color.rgb = GRIS_TEXTO
        elif has_comparison:
            c = s["comparison"]
            _add_comparison(slide,
                            c.get("left_label", "Hoy"),
                            c.get("right_label", "Después"),
                            c.get("left_items", []),
                            c.get("right_items", []),
                            top=Inches(1.4), height=Inches(4.8))
        elif has_process:
            n_steps = len(s.get("process_steps", []))
            # Si hay bullets, proceso compacto arriba (height 2.0in) y bullets abajo
            if bullets:
                _add_process_steps(slide, s["process_steps"],
                                    top=Inches(1.5), height=Inches(2.5))
                tb = slide.shapes.add_textbox(Inches(0.5), Inches(4.4), Inches(12.3), Inches(2.4))
                tf = tb.text_frame; tf.word_wrap = True
                tf.vertical_anchor = MSO_ANCHOR.TOP
                for i, b in enumerate(bullets[:5]):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    p.space_after = Pt(12)
                    r1 = p.add_run(); r1.text = "▪  "; r1.font.size = Pt(13); r1.font.color.rgb = MAGENTA; r1.font.bold = True
                    r2 = p.add_run(); r2.text = str(b); r2.font.size = Pt(13); r2.font.color.rgb = GRIS_TEXTO
            else:
                # Sin bullets · proceso ocupa más altura para no dejar slide vacío
                _add_process_steps(slide, s["process_steps"],
                                    top=Inches(1.8), height=Inches(4.5))
        elif has_quote:
            q = s["quote"]
            on_dark = layout_kind == "closing"
            try:
                _add_quote(slide, q.get("text", ""), q.get("attribution", ""), on_dark=on_dark)
            except Exception as ex:
                # Fallback: textbox simple si la cita falla
                tb = slide.shapes.add_textbox(Inches(1.0), Inches(2.5), Inches(11.3), Inches(3.0))
                tf = tb.text_frame; tf.word_wrap = True
                p1 = tf.paragraphs[0]; r1 = p1.add_run()
                r1.text = '"' + q.get("text", "") + '"'
                r1.font.size = Pt(20); r1.font.italic = True; r1.font.color.rgb = PRUNO
                if q.get("attribution"):
                    p2 = tf.add_paragraph(); r2 = p2.add_run()
                    r2.text = "— " + q["attribution"]
                    r2.font.size = Pt(11); r2.font.color.rgb = GRIS_TEXTO
            if bullets:
                tb = slide.shapes.add_textbox(Inches(1.5), Inches(5.5), Inches(10.3), Inches(1.5))
                tf = tb.text_frame; tf.word_wrap = True
                for i, b in enumerate(bullets[:3]):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    r = p.add_run(); r.text = "· " + str(b)
                    r.font.size = Pt(11); r.font.color.rgb = GRIS_TEXTO
        else:
            # Standard: bullets + key_metric a la derecha si existe
            if has_metric:
                # Bullets a la izquierda · vertical center (no top-aligned)
                if bullets:
                    tb = slide.shapes.add_textbox(Inches(0.5), Inches(1.6), Inches(7.0), Inches(4.8))
                    tf = tb.text_frame; tf.word_wrap = True
                    tf.vertical_anchor = MSO_ANCHOR.MIDDLE  # ← centrado vertical para llenar altura
                    for i, b in enumerate(bullets):
                        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                        p.space_after = Pt(14); p.space_before = Pt(0)
                        r1 = p.add_run(); r1.text = "▪  "; r1.font.size = Pt(14); r1.font.color.rgb = MAGENTA; r1.font.bold = True
                        r2 = p.add_run(); r2.text = str(b); r2.font.size = Pt(14); r2.font.color.rgb = GRIS_TEXTO
                # Metric a la derecha · ajustar tamaño y posición
                m = s["key_metric"]
                _add_key_metric(slide, m.get("value", ""), m.get("label", ""),
                                m.get("context", ""), left=Inches(8.0), top=Inches(1.8),
                                width=Inches(4.5), height=Inches(3.5))
            else:
                # Solo bullets en el placeholder estándar (vertical center si pocos)
                if bullets:
                    _set_bullets_in_body(slide, bullets)
                elif subtitle:
                    _set_bullets_in_body(slide, [subtitle])

        # Footnote (opcional, fuente)
        if s.get("footnote"):
            _add_footnote(slide, s["footnote"])

        # Footer corporativo "MINSAIT | <Cliente · Tema>" en slides de contenido
        if layout_kind not in ("cover", "cover_partner", "closing", "section_divider", "index", "index_long"):
            client = (deck_brief.get("client") or {}).get("name_commercial", "")
            topic_label = (deck_brief.get("deck") or {}).get("title_working", "")
            from datetime import datetime
            fecha = datetime.now().strftime("%m.%Y")
            # Formato brandbook: MINSAIT • Cliente · Tema · MM.YYYY
            parts = [f"MINSAIT • {client}"]
            if topic_label: parts.append(topic_label)
            parts.append(fecha)
            footer = " · ".join(parts)
            _add_corporate_footer(slide, footer)

        # Speaker notes
        note = s.get("note", "")
        if note:
            slide.notes_slide.notes_text_frame.text = note

    # POST-PROCESS · forzar fuente ForFuture Sans en TODOS los runs (regla brandbook)
    for slide in prs.slides:
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if not run.font.name:  # respetar si ya está set
                        run.font.name = "ForFuture Sans"
            # También iterar tablas
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        for para in cell.text_frame.paragraphs:
                            for run in para.runs:
                                if not run.font.name:
                                    run.font.name = "ForFuture Sans"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    if Path(output_path).exists():
        os.chmod(output_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    prs.save(output_path)
    return output_path


def main():
    if len(sys.argv) < 4:
        print("Usage: generate_pptx_v3.py <slide_content.json> <deck_brief.json> <output.pptx>")
        sys.exit(1)
    sc = json.load(open(sys.argv[1]))
    db = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    generate_from_content(sc, db, out)
    print(f"OK · generated {out}")


if __name__ == "__main__":
    main()
