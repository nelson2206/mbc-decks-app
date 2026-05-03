"""
extract_credentials.py — Extractor de credenciales (casos de éxito) de un .pptx

Para cada slide identificable como "caso de éxito" en un deck fuente, genera:
  - <client>_<topic>.pptx — la slide individual como deck independiente
  - <client>_<topic>.json — metadata estructurada

Detección de slides de caso de éxito:
  - Heurística textual: presencia de palabras clave (cliente nombrado, "caso", "referencia",
    "implementación de", "Periodo de colaboración", "El Reto", etc.)
  - Heurística estructural: layouts marcados como "casos" en el template (40-43 en Komatsu deck)
  - Override manual via --slides flag

Uso:
    python extract_credentials.py <reference.pptx> --output-dir credenciales/pmo/ \
        --topic pmo --industry industria_consumo_energia

    # Slides específicas:
    python extract_credentials.py <reference.pptx> --output-dir credenciales/pmo/ \
        --topic pmo --industry industria_consumo_energia --slides 51,54,55,59,60,61,62,65,66
"""
from __future__ import annotations
import argparse
import json
import os
import re
import shutil
import stat
import sys
import zipfile
from pathlib import Path
from typing import Optional


# Heurísticas para identificar slides de casos de éxito
CREDENTIAL_KEYWORDS = [
    "El reto", "El Reto", "La solución", "La Solución",
    "Periodo de colaboración", "Periodo:", "Periodo ",
    "Servicio de", "Servicio:", "Implementación de",
    "Caso de éxito", "Caso de Éxito", "Referencia",
    "Sociedades:", "Cliente:", "Industria:",
    "PMO y GdC", "PMO en",
]


def is_credential_slide(text: str) -> bool:
    """Heuristic: does this slide look like a credential/case study?"""
    if not text or len(text) < 100:
        return False
    hits = sum(1 for kw in CREDENTIAL_KEYWORDS if kw.lower() in text.lower())
    return hits >= 2


def extract_slide_text(zf: zipfile.ZipFile, slide_num: int) -> str:
    sf = f"ppt/slides/slide{slide_num}.xml"
    if sf not in zf.namelist():
        return ""
    xml = zf.read(sf).decode("utf-8", errors="ignore")
    texts = re.findall(r"<a:t[^>]*>([^<]+)</a:t>", xml)
    return " ".join(t.strip() for t in texts)


def detect_client_and_year(slide_text: str, known_clients: list[str]) -> tuple[Optional[str], Optional[int]]:
    """Detect the client name and year from the slide's text."""
    client = None
    for c in known_clients:
        if c.lower() in slide_text.lower():
            client = c
            break
    year = None
    m = re.search(r"\b(20\d{2})\b", slide_text)
    if m:
        year = int(m.group(1))
    return client, year


def extract_single_slide_to_pptx(source_pptx: str, slide_num: int, output_pptx: str) -> bool:
    """Build a new .pptx containing only the requested slide (with its rels and media intact).

    Approach: copy the source, then trim presentation.xml + rels to keep only the target slide.
    """
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

    target_sld = sld_ids[slide_num - 1]
    # Remove all sldId entries except target
    new_pres = pres_xml
    for sld in sld_ids:
        if sld != target_sld:
            new_pres = new_pres.replace(sld, "", 1)
    files[pres_path] = new_pres.encode("utf-8")

    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for name, data in files.items():
            zout.writestr(name, data)
    return True


def make_id(client: Optional[str], slide_num: int, topic: str) -> str:
    """Generate a clean ID for the credential file."""
    if client:
        slug = re.sub(r"[^a-z0-9]+", "_", client.lower()).strip("_")
        return f"{slug}_{topic}_s{slide_num}"
    return f"unknown_{topic}_s{slide_num}"


def extract_credentials(
    source_pptx: str,
    output_dir: str,
    topic: str,
    industry: str,
    slide_numbers: Optional[list[int]] = None,
    auto_detect: bool = True,
    known_clients: Optional[list[str]] = None,
) -> list[dict]:
    """Extract credential slides from a deck and save each as individual .pptx + metadata.json."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if known_clients is None:
        # Load from minsait_clients_db
        skill_dir = Path(__file__).resolve().parent.parent
        with open(skill_dir / "brand" / "minsait_clients_db.json") as f:
            db = json.load(f)
        known_clients = []
        for region in ("clients_perú", "clients_internacional"):
            for c in db.get(region, []):
                known_clients.append(c["name"])
                known_clients.extend(c.get("aka", []))

    extracted = []
    with zipfile.ZipFile(source_pptx) as zf:
        all_slides = sorted(
            [n for n in zf.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=lambda p: int(re.search(r"slide(\d+)", p).group(1)),
        )
        total_slides = len(all_slides)

        if slide_numbers:
            target_slides = [n for n in slide_numbers if 1 <= n <= total_slides]
        elif auto_detect:
            target_slides = []
            for n in range(1, total_slides + 1):
                text = extract_slide_text(zf, n)
                if is_credential_slide(text):
                    target_slides.append(n)
        else:
            target_slides = []

        for slide_num in target_slides:
            text = extract_slide_text(zf, slide_num)
            client, year = detect_client_and_year(text, known_clients)
            cred_id = make_id(client, slide_num, topic)

            out_pptx = Path(output_dir) / f"{cred_id}.pptx"
            ok = extract_single_slide_to_pptx(source_pptx, slide_num, str(out_pptx))
            if not ok:
                continue

            # Metadata
            metadata = {
                "id": cred_id,
                "type": "credencial",
                "client": client or "[unknown — etiquetar manualmente]",
                "industry": industry,
                "topic_primary": topic,
                "year": year,
                "source_deck": Path(source_pptx).name,
                "source_slide_num": slide_num,
                "applicability": {
                    "industries_direct": [industry],
                    "topics_direct": [topic],
                },
                "default_inclusion": True,
                "anonymized": False,
                "slide_text_preview": text[:300],
                "added_by": "extract_credentials.py",
            }
            with open(Path(output_dir) / f"{cred_id}.json", "w") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            extracted.append(metadata)

    # Update or create _index.json
    index_path = Path(output_dir).parent / "_index.json"
    index = {"credentials": []}
    if index_path.exists():
        try:
            index = json.load(open(index_path))
        except Exception:
            pass
    existing_ids = {c["id"] for c in index.get("credentials", [])}
    for m in extracted:
        if m["id"] not in existing_ids:
            index["credentials"].append({
                "id": m["id"],
                "client": m["client"],
                "topic": m["topic_primary"],
                "industry": m["industry"],
                "year": m["year"],
                "path": f"{topic}/{m['id']}.pptx",
            })
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    return extracted


def main():
    p = argparse.ArgumentParser()
    p.add_argument("source_pptx")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--topic", required=True, help="e.g. pmo, data_analytics, ia_genai")
    p.add_argument("--industry", required=True, help="e.g. industria_consumo_energia, servicios_financieros")
    p.add_argument("--slides", default="", help="Comma-separated slide numbers (override auto-detection)")
    p.add_argument("--no-auto-detect", action="store_true")
    args = p.parse_args()

    slides = [int(s) for s in args.slides.split(",") if s.strip()] if args.slides else None
    extracted = extract_credentials(
        args.source_pptx,
        args.output_dir,
        args.topic,
        args.industry,
        slide_numbers=slides,
        auto_detect=not args.no_auto_detect,
    )
    print(f"Extraídas {len(extracted)} credenciales:")
    for m in extracted:
        print(f"  · {m['id']} (cliente: {m['client']}, slide {m['source_slide_num']})")


if __name__ == "__main__":
    main()
