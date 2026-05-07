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
    # Header row
    for j, h in enumerate(headers):
        cell = tbl.cell(0, j)
        cell.text = ""
        cell.fill.solid()
        cell.fill.fore_color.rgb = PRUNO
        tf = cell.text_frame
        p = tf.paragraphs[0]
        r = p.add_run()
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
            cell.fill.fore_color.rgb = BLANCO if i % 2 else CERAMICA
            cell.text = ""
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = str(val)
            r.font.size = Pt(10)
            r.font.color.rgb = GRIS_TEXTO


def _add_comparison(slide, left_label: str, right_label: str, left_items: list, right_items: list,
                    left=Inches(0.5), top=Inches(2.5), width=Inches(12.3), height=Inches(4.0)):
    """Dos columnas lado a lado (Hoy vs Después / Riesgo vs Mitigación)."""
    half_w = Inches((width.inches - 0.3) / 2)
    # Left column
    lc = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, half_w, height)
    lc.fill.solid()
    lc.fill.fore_color.rgb = CERAMICA
    lc.line.color.rgb = CERAMICA
    tf_l = lc.text_frame
    tf_l.margin_top = Inches(0.2); tf_l.margin_left = Inches(0.3); tf_l.margin_right = Inches(0.3)
    tf_l.word_wrap = True
    p_h = tf_l.paragraphs[0]
    r_h = p_h.add_run(); r_h.text = left_label.upper(); r_h.font.bold = True; r_h.font.size = Pt(13); r_h.font.color.rgb = PRUNO
    for item in left_items:
        p = tf_l.add_paragraph()
        r = p.add_run(); r.text = "  · " + str(item); r.font.size = Pt(10); r.font.color.rgb = GRIS_TEXTO
    # Right column
    right_left = Inches(left.inches + half_w.inches + 0.3)
    rc = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, right_left, top, half_w, height)
    rc.fill.solid()
    rc.fill.fore_color.rgb = PRUNO
    rc.line.color.rgb = PRUNO
    tf_r = rc.text_frame
    tf_r.margin_top = Inches(0.2); tf_r.margin_left = Inches(0.3); tf_r.margin_right = Inches(0.3)
    tf_r.word_wrap = True
    p_h2 = tf_r.paragraphs[0]
    r_h2 = p_h2.add_run(); r_h2.text = right_label.upper(); r_h2.font.bold = True; r_h2.font.size = Pt(13); r_h2.font.color.rgb = BLANCO
    for item in right_items:
        p = tf_r.add_paragraph()
        r = p.add_run(); r.text = "  · " + str(item); r.font.size = Pt(10); r.font.color.rgb = BLANCO


def _add_process_steps(slide, steps: list, left=Inches(0.5), top=Inches(3.0), width=Inches(12.3), height=Inches(2.5)):
    """Cadena horizontal de N pasos con flechas."""
    if not steps:
        return
    n = len(steps)
    box_w = (width.inches - (n - 1) * 0.2) / n
    for i, step in enumerate(steps):
        x = Inches(left.inches + i * (box_w + 0.2))
        b = slide.shapes.add_shape(MSO_SHAPE.PENTAGON if i < n - 1 else MSO_SHAPE.ROUNDED_RECTANGLE,
                                    x, top, Inches(box_w), height)
        b.fill.solid()
        b.fill.fore_color.rgb = PRUNO if i % 2 == 0 else MAGENTA
        b.line.color.rgb = PRUNO
        tf = b.text_frame
        tf.margin_top = Inches(0.2); tf.margin_left = Inches(0.2); tf.margin_right = Inches(0.2)
        tf.word_wrap = True
        # Step number
        p1 = tf.paragraphs[0]
        p1.alignment = PP_ALIGN.CENTER
        r1 = p1.add_run(); r1.text = f"FASE {step.get('step', i+1)}"
        r1.font.size = Pt(9); r1.font.color.rgb = CERAMICA
        # Label
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = str(step.get('label', ''))
        r2.font.size = Pt(15); r2.font.bold = True; r2.font.color.rgb = BLANCO
        # Description
        if step.get('description'):
            p3 = tf.add_paragraph()
            p3.alignment = PP_ALIGN.CENTER
            r3 = p3.add_run(); r3.text = str(step['description'])
            r3.font.size = Pt(9); r3.font.color.rgb = BLANCO


def _add_quote(slide, text: str, attribution: str = "",
               left=Inches(1.5), top=Inches(2.5), width=Inches(10.3), height=Inches(2.5)):
    """Cita destacada con borde lateral magenta."""
    # Bar lateral magenta
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Inches(0.1), height)
    bar.fill.solid(); bar.fill.fore_color.rgb = MAGENTA; bar.line.fill.background()
    # Text box al lado
    tb = slide.shapes.add_textbox(Inches(left.inches + 0.3), top, Inches(width.inches - 0.3), height)
    tf = tb.text_frame; tf.word_wrap = True
    p1 = tf.paragraphs[0]
    r1 = p1.add_run(); r1.text = '"' + text + '"'
    r1.font.size = Pt(20); r1.font.italic = True; r1.font.color.rgb = PRUNO
    if attribution:
        p2 = tf.add_paragraph()
        r2 = p2.add_run(); r2.text = "— " + attribution
        r2.font.size = Pt(11); r2.font.color.rgb = GRIS_TEXTO


def _add_footnote(slide, text: str):
    """Footnote pequeño abajo del slide."""
    if not text:
        return
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(12.3), Inches(0.3))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    r = p.add_run(); r.text = text
    r.font.size = Pt(8); r.font.italic = True; r.font.color.rgb = GRIS_TEXTO


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
        if has_table or has_comparison or has_process or has_quote:
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
            tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12.3), Inches(0.5))
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
            if title and slide.shapes.title is not None:
                slide.shapes.title.text = title

        # Layout de contenido según componentes presentes
        if has_table:
            tbl = s["table"]
            _add_table(slide, tbl.get("headers", []), tbl.get("rows", []),
                       top=Inches(1.4), height=Inches(4.5))
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
            _add_process_steps(slide, s["process_steps"],
                               top=Inches(1.5), height=Inches(2.0))
            # Bullets opcionales debajo
            if bullets:
                tb = slide.shapes.add_textbox(Inches(0.5), Inches(4.0), Inches(12.3), Inches(2.5))
                tf = tb.text_frame; tf.word_wrap = True
                for i, b in enumerate(bullets[:5]):
                    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    r = p.add_run(); r.text = "· " + str(b)
                    r.font.size = Pt(11); r.font.color.rgb = GRIS_TEXTO
        elif has_quote:
            q = s["quote"]
            try:
                _add_quote(slide, q.get("text", ""), q.get("attribution", ""))
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
                # Bullets a la izquierda (mitad ancho)
                if bullets:
                    tb = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(7.0), Inches(5.0))
                    tf = tb.text_frame; tf.word_wrap = True
                    for i, b in enumerate(bullets):
                        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                        r = p.add_run(); r.text = "· " + str(b)
                        r.font.size = Pt(13); r.font.color.rgb = GRIS_TEXTO
                # Metric a la derecha
                m = s["key_metric"]
                _add_key_metric(slide, m.get("value", ""), m.get("label", ""),
                                m.get("context", ""))
            else:
                # Solo bullets en el placeholder estándar
                if bullets:
                    _set_bullets_in_body(slide, bullets)
                elif subtitle:
                    _set_bullets_in_body(slide, [subtitle])

        # Footnote (opcional)
        if s.get("footnote"):
            _add_footnote(slide, s["footnote"])

        # Speaker notes
        note = s.get("note", "")
        if note:
            slide.notes_slide.notes_text_frame.text = note

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
