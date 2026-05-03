"""
generate_pptx_v2.py — Motor de "copy & edit" sobre un deck de referencia

Toma un deck de referencia ya diseñado (de reference_decks/<industria>/<tema>/reference.pptx),
hace una copia exacta y reemplaza textos / imágenes específicas para adaptarlo al cliente target.

PRESERVA 100% DEL DISEÑO ORIGINAL: visores, contenedores, fotos, infografías, layouts compuestos,
tablas, gráficos, líneas decorativas, agrupaciones, animaciones.

Inputs:
  - reference_pptx: ruta del deck base (.pptx)
  - edit_map: diccionario con instrucciones de edición:
      {
        "global_text_replacements": [
            {"find": "Komatsu", "replace": "Ferreyros"},
            {"find": "Komatsu Mitsui", "replace": "Ferreyros S.A."},
            {"find": "2025", "replace": "2026"},
            ...
        ],
        "regex_replacements": [
            {"pattern": r"S/\.\s*\d+,\d+", "replace": "S/. 685,000"}
        ],
        "slide_specific": {
            "1": {"replacements": [{"find": "OLD", "replace": "NEW"}]},
            ...
        },
        "image_replacements": [
            {"original_filename": "image5.png", "new_path": "/path/to/ferreyros_logo.png"}
        ],
        "delete_slides": [49, 65, 66]
      }
  - output_path: dónde guardar el deck final

Uso:
    from generate_pptx_v2 import generate_from_reference
    out = generate_from_reference(
        reference_pptx="reference_decks/ice/pmo/reference.pptx",
        edit_map=json.load(open("edit_map.json")),
        output_path="output.pptx",
    )
"""
from __future__ import annotations
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any


def generate_from_reference(
    reference_pptx: str,
    edit_map: dict,
    output_path: str,
    verbose: bool = True,
) -> dict:
    """Generate a new .pptx by copying a reference deck and applying edits.

    Returns a stats dict with details about the operation.
    """
    src = Path(reference_pptx)
    dst = Path(output_path)
    if not src.exists():
        raise FileNotFoundError(f"Reference not found: {src}")

    # Step 1: copy the .pptx (preserves entire structure)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    # Ensure destination is writable (shutil.copy preserves source permissions which may be read-only)
    import os, stat
    os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    # Step 2: rewrite slide XMLs with edits
    stats = {
        "reference": str(src),
        "output": str(dst),
        "global_replacements_applied": 0,
        "regex_replacements_applied": 0,
        "slide_specific_replacements_applied": 0,
        "slides_deleted": [],
        "images_replaced": 0,
    }

    # Read all xml files in memory, modify, then re-save the zip
    with zipfile.ZipFile(dst, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}

    # Identify slides
    slide_files = sorted(
        [n for n in files if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
        key=lambda p: int(re.search(r"slide(\d+)\.xml", p).group(1)),
    )

    # Apply text replacements per slide
    global_reps = edit_map.get("global_text_replacements", [])
    regex_reps = edit_map.get("regex_replacements", [])
    slide_specific = edit_map.get("slide_specific", {})

    for sf in slide_files:
        slide_num = int(re.search(r"slide(\d+)\.xml", sf).group(1))
        xml = files[sf].decode("utf-8")

        # Apply slide-specific FIRST (more targeted)
        ss = slide_specific.get(str(slide_num)) or slide_specific.get(slide_num)
        if ss:
            for rep in ss.get("replacements", []):
                count = xml.count(rep["find"])
                if count:
                    xml = xml.replace(rep["find"], rep["replace"])
                    stats["slide_specific_replacements_applied"] += count
                    if verbose:
                        print(f"  slide {slide_num}: '{rep['find'][:40]}' → '{rep['replace'][:40]}' ({count}x)")

        # Apply global text replacements
        for rep in global_reps:
            count = xml.count(rep["find"])
            if count:
                xml = xml.replace(rep["find"], rep["replace"])
                stats["global_replacements_applied"] += count

        # Apply regex replacements
        for rep in regex_reps:
            xml, n = re.subn(rep["pattern"], rep["replace"], xml)
            stats["regex_replacements_applied"] += n

        files[sf] = xml.encode("utf-8")

    # Image replacements
    for img_rep in edit_map.get("image_replacements", []):
        original = img_rep["original_filename"]
        new_path = Path(img_rep["new_path"])
        if not new_path.exists():
            print(f"WARN: image {new_path} not found, skipping")
            continue
        media_key = f"ppt/media/{original}"
        if media_key in files:
            files[media_key] = new_path.read_bytes()
            stats["images_replaced"] += 1
            if verbose:
                print(f"  image: {original} → {new_path.name}")

    # Slide deletion (best-effort: clear content but keep XML structure)
    delete_slides = set(edit_map.get("delete_slides", []))
    if delete_slides:
        # Slide deletion in pptx is complex; for now we mark slides for removal
        # via presentation.xml relationship. Implementation: rebuild presentation.xml.
        _delete_slides(files, delete_slides, stats)

    # Re-save the zip
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)

    if verbose:
        print(f"\n✅ Generated: {dst}")
        print(f"   Global replacements: {stats['global_replacements_applied']}")
        print(f"   Regex replacements:  {stats['regex_replacements_applied']}")
        print(f"   Slide-specific:      {stats['slide_specific_replacements_applied']}")
        print(f"   Images replaced:     {stats['images_replaced']}")
        print(f"   Slides deleted:      {len(stats['slides_deleted'])}")

    return stats


def _delete_slides(files: dict, slides_to_delete: set[int], stats: dict) -> None:
    """Remove slides from presentation.xml and slide rels."""
    pres_path = "ppt/presentation.xml"
    pres_rels_path = "ppt/_rels/presentation.xml.rels"
    if pres_path not in files:
        return

    pres_xml = files[pres_path].decode("utf-8")
    rels_xml = files[pres_rels_path].decode("utf-8")

    # Find ordered list of sldId entries
    sld_id_pattern = re.compile(r'<p:sldId\s+id="\d+"\s+r:id="(rId\d+)"\s*/>')
    sld_ids = sld_id_pattern.findall(pres_xml)

    # Map rId -> slide file
    rel_pattern = re.compile(r'<Relationship[^/]*Id="(rId\d+)"[^/]*Target="(slides/slide\d+\.xml)"')
    rel_map = dict(rel_pattern.findall(rels_xml))

    for slide_num in sorted(slides_to_delete, reverse=True):
        # Position in ordered list = slide_num (1-indexed)
        if 0 < slide_num <= len(sld_ids):
            rid = sld_ids[slide_num - 1]
            target = rel_map.get(rid)
            # Remove from presentation.xml
            pattern = re.compile(rf'<p:sldId\s+id="\d+"\s+r:id="{rid}"\s*/>')
            pres_xml = pattern.sub("", pres_xml)
            stats["slides_deleted"].append(slide_num)

    files[pres_path] = pres_xml.encode("utf-8")


def main():
    if len(sys.argv) < 4:
        print("Usage: python generate_pptx_v2.py <reference.pptx> <edit_map.json> <output.pptx>")
        sys.exit(1)
    ref = sys.argv[1]
    edit_map = json.load(open(sys.argv[2]))
    out = sys.argv[3]
    stats = generate_from_reference(ref, edit_map, out, verbose=True)
    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
