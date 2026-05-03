"""
generate_pptx.py — Motor de generación de presentaciones MBC

Toma como input:
  - slide_plan.json (output del Visual A5)
  - slide_content.json (output del Contenido A4)
  - deck_brief.json (output de la entrevista)
  - assets/template/PPT_MINSAIT_Template_esp.potx

Produce:
  - <output_path>.pptx con las slides generadas a partir de los layouts oficiales
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from pptx import Presentation
    from pptx.util import Pt, Inches, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    print("ERROR: python-pptx no está instalado. Run: pip install python-pptx Pillow --break-system-packages", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_DIR = SKILL_DIR.parent.parent
TEMPLATE_PATH = PLUGIN_DIR / "assets" / "template" / "PPT_MINSAIT_Template_esp.pptx"
TEMPLATE_PATH_POTX = PLUGIN_DIR / "assets" / "template" / "PPT_MINSAIT_Template_esp.potx"


def _ensure_pptx_template() -> Path:
    """Convert .potx to .pptx if needed (python-pptx requires .pptx)."""
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH
    if not TEMPLATE_PATH_POTX.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_PATH_POTX}")
    import zipfile
    with zipfile.ZipFile(TEMPLATE_PATH_POTX, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}
    ct = files["[Content_Types].xml"].decode("utf-8")
    ct = ct.replace(
        "application/vnd.openxmlformats-officedocument.presentationml.template.main+xml",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    )
    files["[Content_Types].xml"] = ct.encode("utf-8")
    with zipfile.ZipFile(TEMPLATE_PATH, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return TEMPLATE_PATH

with open(SKILL_DIR / "brand" / "colors.json") as f:
    COLORS = json.load(f)
with open(SKILL_DIR / "brand" / "typography.json") as f:
    TYPOGRAPHY = json.load(f)
with open(SKILL_DIR / "brand" / "layout_catalog.json") as f:
    LAYOUT_CATALOG = json.load(f)

PRUNO = RGBColor.from_string(COLORS["primary"]["pruno"]["hex"].lstrip("#"))
CERAMICA = RGBColor.from_string(COLORS["primary"]["ceramica"]["hex"].lstrip("#"))
BLANCO = RGBColor.from_string("FFFFFF")
MAGENTA = RGBColor.from_string(COLORS["accents"]["magenta"]["hex"].lstrip("#"))
LILA = RGBColor.from_string(COLORS["accents"]["lila"]["hex"].lstrip("#"))
AMAZONICO = RGBColor.from_string(COLORS["accents"]["amazonico"]["hex"].lstrip("#"))
FONT_FAMILY = TYPOGRAPHY["family"]


# ---------------------------------------------------------------------------
# Core generator
# ---------------------------------------------------------------------------
def generate_pptx(
    slide_plan: list[dict],
    slide_content: dict,
    deck_brief: dict,
    output_path: str,
) -> str:
    """Generate a .pptx from a slide plan + content + brief.

    slide_plan: list of slide instructions (output of A5 Visual)
    slide_content: dict mapping slide_order -> content (output of A4 Content)
    deck_brief: full brief (output of interview)
    output_path: where to save the final .pptx
    """
    template_path = _ensure_pptx_template()
    prs = Presentation(str(template_path))

    # Remove any pre-existing slides from the .potx (templates carry sample slides)
    _strip_existing_slides(prs)

    deck_title = deck_brief.get("deck", {}).get("title_working", "Documento")
    today_str = datetime.now().strftime("%d/%m/%Y")

    for slide_spec in sorted(slide_plan, key=lambda s: s["slide_order"]):
        layout_index = slide_spec["layout_index"]
        if layout_index < 0 or layout_index >= len(prs.slide_layouts):
            print(f"WARN: layout_index {layout_index} out of range, skipping slide {slide_spec['slide_order']}")
            continue

        layout = prs.slide_layouts[layout_index]
        slide = prs.slides.add_slide(layout)

        slide_order = slide_spec["slide_order"]
        content = slide_content.get(str(slide_order), slide_content.get(slide_order, {}))

        # Apply actions
        for action in slide_spec.get("actions", []):
            _apply_action(slide, action, content, deck_title, today_str)

        # Speaker notes
        speaker_notes = content.get("speaker_notes", "")
        if speaker_notes:
            notes_slide = slide.notes_slide
            notes_slide.notes_text_frame.text = speaker_notes

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    prs.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _strip_existing_slides(prs: Presentation) -> None:
    """Remove all existing slides from a presentation (templates often ship with sample slides)."""
    sldIdLst = prs.slides._sldIdLst  # noqa: SLF001
    slides_to_remove = list(sldIdLst)
    for sld in slides_to_remove:
        rId = sld.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
        prs.part.drop_rel(rId)
        sldIdLst.remove(sld)


def _apply_action(slide, action: dict, content: dict, deck_title: str, today: str) -> None:
    """Apply a single action to a slide."""
    target = action.get("target")
    action_type = action.get("action")

    if action_type == "set_text":
        text = action.get("text") or _resolve_target_text(target, content, deck_title, today)
        if text:
            _set_placeholder_text(slide, target, text)

    elif action_type == "set_bullets":
        bullets = action.get("bullets") or content.get("body", [])
        bullet_texts = [b["text"] if isinstance(b, dict) else str(b) for b in bullets]
        _set_placeholder_bullets(slide, target, bullet_texts)

    elif action_type == "insert_image":
        path = action.get("path")
        if path and Path(path).exists():
            _insert_image_in_slot(slide, target, path, action.get("max_width_M", 4))

    elif action_type == "set_footer":
        text = action.get("text") or f"MINSAIT • {deck_title} • {today}"
        _set_footer(slide, text)

    elif action_type == "set_page_number":
        n = action.get("n")
        if n is not None:
            _set_page_number(slide, str(n))

    elif action_type == "apply_color":
        # Optional: override color of a target element
        pass


def _resolve_target_text(target: str, content: dict, deck_title: str, today: str) -> str:
    """Resolve special targets like 'title', 'subtitle' from the content dict."""
    if target == "title":
        return content.get("title", "")
    if target == "subtitle":
        return content.get("subtitle", "")
    if target == "antetitle":
        return content.get("antetitle", "")
    if target == "footer":
        return f"MINSAIT • {deck_title} • {today}"
    return ""


def _set_placeholder_text(slide, target: str, text: str) -> None:
    """Set text in a placeholder identified by name pattern or index."""
    # Try by placeholder type / index
    if target == "title":
        if slide.shapes.title is not None:
            slide.shapes.title.text = text
            _force_font(slide.shapes.title.text_frame)
            return

    # Try by placeholder name match
    for shape in slide.placeholders:
        ph_name = (shape.name or "").lower()
        if target.lower() in ph_name or _is_target_match(target, shape):
            shape.text_frame.text = text
            _force_font(shape.text_frame)
            return

    # Fallback: try first text frame that's not the title
    for shape in slide.shapes:
        if shape.has_text_frame and shape != slide.shapes.title:
            if not shape.text_frame.text.strip():
                shape.text_frame.text = text
                _force_font(shape.text_frame)
                return


def _set_placeholder_bullets(slide, target: str, bullets: list[str]) -> None:
    """Set bulleted list in a placeholder."""
    placeholder = None
    for shape in slide.placeholders:
        ph_name = (shape.name or "").lower()
        if target and target.lower() in ph_name:
            placeholder = shape
            break

    if placeholder is None:
        # Fallback: use the first body placeholder
        for shape in slide.placeholders:
            if shape.placeholder_format.idx != 0:  # not title
                placeholder = shape
                break

    if placeholder is None or not placeholder.has_text_frame:
        return

    tf = placeholder.text_frame
    tf.clear()
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = bullet
        p.level = 0
    _force_font(tf)


def _force_font(text_frame) -> None:
    """Ensure all runs use ForFuture Sans."""
    for paragraph in text_frame.paragraphs:
        for run in paragraph.runs:
            run.font.name = FONT_FAMILY


def _is_target_match(target: str, shape) -> bool:
    """Heuristic match for special targets."""
    target = target.lower()
    if target == "body_placeholder_0":
        # First body placeholder (idx >= 1)
        return shape.placeholder_format.idx == 1
    if target == "body_placeholder_1":
        return shape.placeholder_format.idx == 2
    return False


def _insert_image_in_slot(slide, target: str, image_path: str, max_width_M: int) -> None:
    """Insert an image at the position of a slot. Replaces an existing picture placeholder if present."""
    try:
        from pptx.util import Inches
        # Search for a picture placeholder with matching name
        for shape in slide.placeholders:
            ph_name = (shape.name or "").lower()
            if target.lower() in ph_name:
                # Replace placeholder with the image
                left, top, width, height = shape.left, shape.top, shape.width, shape.height
                sp = shape._element  # noqa: SLF001
                sp.getparent().remove(sp)
                slide.shapes.add_picture(image_path, left, top, width, height)
                return
        # Fallback: place image at a sensible default position
        slide.shapes.add_picture(image_path, Inches(8), Inches(0.4), height=Inches(0.6))
    except Exception as e:
        print(f"WARN: could not insert image {image_path}: {e}")


def _set_footer(slide, text: str) -> None:
    """Set footer text if a footer placeholder exists."""
    for shape in slide.placeholders:
        if shape.placeholder_format.idx in (15, 16):  # PP_PLACEHOLDER.FOOTER usually
            if shape.has_text_frame:
                shape.text_frame.text = text
                _force_font(shape.text_frame)
                return


def _set_page_number(slide, n: str) -> None:
    """Set page number if a slide-number placeholder exists."""
    for shape in slide.placeholders:
        if shape.placeholder_format.idx in (12, 13):
            if shape.has_text_frame:
                shape.text_frame.text = n
                _force_font(shape.text_frame)
                return


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 5:
        print("Usage: python generate_pptx.py <slide_plan.json> <slide_content.json> <deck_brief.json> <output.pptx>")
        sys.exit(1)
    plan = json.load(open(sys.argv[1]))
    content = json.load(open(sys.argv[2]))
    brief = json.load(open(sys.argv[3]))
    out = sys.argv[4]
    path = generate_pptx(plan, content, brief, out)
    print(f"OK: deck generated at {path}")


if __name__ == "__main__":
    main()
