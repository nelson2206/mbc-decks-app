"""
extract_typologies.py — Extractor de slides por TIPOLOGÍA narrativa

Identifica slides representativas de cada categoría narrativa (portada, índice, separata,
contexto, propuesta_valor, metodología, plan_trabajo, equipo, riesgos, inversión, cierre)
en uno o varios decks fuente, y las guarda como banco reutilizable.

Detección de tipología:
  - Por nombre de layout (cuando coincide con familia conocida del catálogo Minsait)
  - Por heurística textual (palabras clave en título)

Uso:
    python extract_typologies.py <reference.pptx> --output-dir slide_bank/

Es seguro re-ejecutar: solo agrega slides nuevas si su hash de texto no coincide con uno existente.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import zipfile
from pathlib import Path
from typing import Optional

# Mapeo familia layout → carpeta de tipología
FAMILY_TO_TYPOLOGY = {
    "cover": "01_portadas",
    "index": "02_indices",
    "section_divider": "03_separatas",
    "content_text": "05_contexto",  # default; refinar con heurística textual
    "content_image": "05_contexto",
    "content_split": "05_contexto",
    "key_idea": "06_propuesta_valor",
    "blank": "14_inversion",  # placeholders, suelen ir en sección financial
    "closing": "15_cierre",
}

# Heurística textual: palabras clave en título → typology override
TEXT_TYPOLOGY_RULES = [
    (r"objetivo[s]?\s+del\s+documento|propósito\s+de\s+la\s+colaboraci", "04_proposito"),
    (r"propos|propuesta\s+de\s+valor|nuestra\s+propuesta", "06_propuesta_valor"),
    (r"metodolog|enfoque|fases|fase\s+1|fase\s+2", "07_metodologia"),
    (r"plan\s+de\s+trabajo|cronograma|timeline|gantt|hitos", "08_plan_trabajo"),
    (r"equipo\s+de\s+proyecto|equipo\s+propuesto|nivel\s+estrat|partner|director|consultor", "09_equipo"),
    (r"experiencia|cv|formaci|certificaci", "10_cv_individual"),
    (r"riesgos?\s+y?\s*mitigaci|matriz\s+de\s+riesgos", "11_riesgos_mitigacion"),
    (r"dependenc|inputs?\s+req", "12_dependencias"),
    (r"por\s+qué\s+minsait|diferenciaci|valor\s+añadido", "13_diferenciacion"),
    (r"inversi[óo]n|honorarios|propuesta\s+econ|condiciones\s+comerciales", "14_inversion"),
    (r"contexto|entendimiento\s+del\s+reto|situaci[óo]n\s+actual|el\s+reto", "05_contexto"),
]


def load_layout_catalog():
    skill_dir = Path(__file__).resolve().parent.parent
    with open(skill_dir / "brand" / "layout_catalog.json") as f:
        return json.load(f)


def get_slide_text(zf: zipfile.ZipFile, slide_num: int) -> str:
    sf = f"ppt/slides/slide{slide_num}.xml"
    if sf not in zf.namelist():
        return ""
    xml = zf.read(sf).decode("utf-8", errors="ignore")
    texts = re.findall(r"<a:t[^>]*>([^<]+)</a:t>", xml)
    return " | ".join(t.strip() for t in texts if t.strip())


def get_slide_layout_name(zf: zipfile.ZipFile, slide_num: int) -> str:
    rels = f"ppt/slides/_rels/slide{slide_num}.xml.rels"
    if rels not in zf.namelist():
        return ""
    rels_xml = zf.read(rels).decode("utf-8", errors="ignore")
    m = re.search(r"slideLayouts/slideLayout(\d+)\.xml", rels_xml)
    if not m:
        return ""
    layout_xml_path = f"ppt/slideLayouts/slideLayout{m.group(1)}.xml"
    if layout_xml_path not in zf.namelist():
        return ""
    layout_xml = zf.read(layout_xml_path).decode("utf-8", errors="ignore")
    name_match = re.search(r'name="([^"]+)"', layout_xml)
    return name_match.group(1) if name_match else ""


def detect_typology(layout_name: str, slide_text: str, layout_catalog: list[dict]) -> str:
    """Decide which typology folder this slide belongs to."""
    # 1. Try by layout family
    family = ""
    for layout in layout_catalog:
        if layout["name"] == layout_name:
            family = layout.get("family", "")
            break
    base = FAMILY_TO_TYPOLOGY.get(family, "")

    # 2. Refinement by text (overrides family for content slides)
    for pattern, typology in TEXT_TYPOLOGY_RULES:
        if re.search(pattern, slide_text, re.IGNORECASE):
            return typology

    return base or "00_uncategorized"


def extract_single_slide(source_pptx: str, slide_num: int, output_pptx: str) -> bool:
    """Extract a single slide as a standalone .pptx."""
    src = Path(source_pptx)
    dst = Path(output_pptx)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, dst)
    os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    with zipfile.ZipFile(dst, "r") as zin:
        files = {name: zin.read(name) for name in zin.namelist()}
    pres_path = "ppt/presentation.xml"
    pres_xml = files[pres_path].decode("utf-8")
    sld_id_pattern = re.compile(r'(<p:sldId\s+id="\d+"\s+r:id="rId\d+"\s*/>)')
    sld_ids = sld_id_pattern.findall(pres_xml)
    if not (0 < slide_num <= len(sld_ids)):
        return False
    target = sld_ids[slide_num - 1]
    new_pres = pres_xml
    for sld in sld_ids:
        if sld != target:
            new_pres = new_pres.replace(sld, "", 1)
    files[pres_path] = new_pres.encode("utf-8")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return True


def text_hash(text: str) -> str:
    """Stable hash of normalized text for dedup."""
    norm = re.sub(r"\s+", " ", text.lower().strip())[:500]
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:12]


def extract_typologies(source_pptx: str, output_dir: str) -> dict:
    layout_catalog = load_layout_catalog().get("layouts", [])
    src_name = Path(source_pptx).stem

    counts: dict[str, int] = {}
    seen_hashes: set[str] = set()
    extracted = []

    # Pre-load existing index to avoid re-extracting duplicates
    index_path = Path(output_dir) / "_index.json"
    if index_path.exists():
        try:
            existing = json.load(open(index_path))
            for entry in existing.get("slides", []):
                seen_hashes.add(entry["text_hash"])
        except Exception:
            existing = {"slides": []}
    else:
        existing = {"slides": []}

    with zipfile.ZipFile(source_pptx) as zf:
        all_slides = sorted(
            [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=lambda p: int(re.search(r"slide(\d+)", p).group(1)),
        )
        for sf in all_slides:
            slide_num = int(re.search(r"slide(\d+)", sf).group(1))
            text = get_slide_text(zf, slide_num)
            if not text:
                continue
            t_hash = text_hash(text)
            if t_hash in seen_hashes:
                continue  # skip duplicates
            seen_hashes.add(t_hash)

            layout_name = get_slide_layout_name(zf, slide_num)
            typology = detect_typology(layout_name, text, layout_catalog)
            typology_dir = Path(output_dir) / typology
            cred_id = f"{src_name}_s{slide_num}_{t_hash}"
            out_pptx = typology_dir / f"{cred_id}.pptx"

            if extract_single_slide(source_pptx, slide_num, str(out_pptx)):
                meta = {
                    "id": cred_id,
                    "typology": typology,
                    "layout": layout_name,
                    "source_deck": src_name,
                    "source_slide": slide_num,
                    "text_hash": t_hash,
                    "text_preview": text[:200],
                    "path": f"{typology}/{cred_id}.pptx",
                }
                with open(typology_dir / f"{cred_id}.json", "w") as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
                extracted.append(meta)
                counts[typology] = counts.get(typology, 0) + 1

    # Update index
    existing.setdefault("slides", []).extend(extracted)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(index_path, "w") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    return counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source_pptx")
    p.add_argument("--output-dir", required=True)
    args = p.parse_args()
    counts = extract_typologies(args.source_pptx, args.output_dir)
    print(f"Extraídas slides de {Path(args.source_pptx).name}:")
    for typology, n in sorted(counts.items()):
        print(f"  {typology}: {n}")


if __name__ == "__main__":
    main()
