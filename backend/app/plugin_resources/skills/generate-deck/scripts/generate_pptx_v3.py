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
    from pptx.util import Pt
except ImportError:
    print("python-pptx required", file=sys.stderr)
    sys.exit(1)


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


def generate_from_content(
    slide_content: dict,
    deck_brief: dict,
    output_path: str,
) -> str:
    """Construye el .pptx desde slide_content."""
    template = _ensure_pptx_template()
    prs = Presentation(str(template))
    _strip_existing_slides(prs)

    slides_data = slide_content.get("slides", [])
    if not slides_data:
        # Fallback: si slide_content tiene otra forma, intentar interpretarlo
        if isinstance(slide_content, list):
            slides_data = slide_content
        elif "raw" in slide_content:
            # Si A4 devolvió algo no parseable, generar deck mínimo
            slides_data = [{
                "order": 1, "layout_kind": "cover",
                "title": deck_brief.get("deck", {}).get("title_working", "Deck"),
                "subtitle": deck_brief.get("client", {}).get("name_commercial", ""),
                "bullets": [], "note": "Fallback porque A4 no devolvió JSON parseable",
            }]

    n_layouts = len(prs.slide_layouts)
    for s in sorted(slides_data, key=lambda x: x.get("order", 0)):
        layout_kind = s.get("layout_kind", "context")
        layout_idx = LAYOUT_KIND_TO_INDEX.get(layout_kind, 17)  # default: contenido texto
        if layout_idx >= n_layouts:
            layout_idx = 17
        layout = prs.slide_layouts[layout_idx]
        slide = prs.slides.add_slide(layout)

        title = s.get("title", "")
        subtitle = s.get("subtitle", "")
        bullets = s.get("bullets", []) or []

        # Set title
        if title and slide.shapes.title is not None:
            slide.shapes.title.text = title

        # Set bullets / body
        if bullets:
            _set_bullets_in_body(slide, bullets)
        elif subtitle:
            _set_bullets_in_body(slide, [subtitle])

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
