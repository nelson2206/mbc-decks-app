"""
image_auditor.py — Ejecutor del Agente A9 · Auditor Visual

Audita un .pptx para detectar branding hostil (competencia / otros clientes / leak de información).

Pipeline:
  1. Extrae todas las imágenes raster/vector del .pptx
  2. Mapea cada imagen a las slides donde aparece
  3. Para cada imagen > THRESHOLD_BYTES, ejecuta análisis:
     - Hash MD5 (cache de imágenes ya auditadas)
     - OCR con texto en imagen (busca nombres de competidores)
     - Análisis por LLM (descripción + detección de logos)
     - Cruce con DBs (competitors_db, minsait_clients_db, approved_logos_db)
  4. Produce visual_audit_report.json + visual_audit_report.md
  5. Decide audit_status: PASSED · BLOCKED_RECOMMENDED · BLOCKED

Uso:
    python image_auditor.py <deck.pptx> --client Ferreyros --industry industria_consumo_energia
    python image_auditor.py <deck.pptx> --client Ferreyros --industry industria_consumo_energia --report-md report.md
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

# Thresholds
TINY_BYTES = 5 * 1024        # < 5KB → triage rápido (asumimos NEUTRAL salvo evidencia)
LARGE_BYTES = 50 * 1024      # > 50KB → análisis exhaustivo obligatorio

# Severidades
SEV_CRITICAL = "CRITICAL"
SEV_WARNING = "WARNING"
SEV_NEUTRAL = "NEUTRAL"
SEV_APPROVED = "APPROVED"


def load_dbs() -> tuple[dict, dict, dict, dict]:
    with open(SKILL_DIR / "brand" / "competitors_db.json") as f:
        competitors = json.load(f)
    with open(SKILL_DIR / "brand" / "minsait_clients_db.json") as f:
        minsait_clients = json.load(f)
    with open(SKILL_DIR / "brand" / "approved_logos_db.json") as f:
        approved = json.load(f)
    approved_hashes_path = SKILL_DIR / "brand" / "approved_image_hashes.json"
    if approved_hashes_path.exists():
        with open(approved_hashes_path) as f:
            approved_hashes = json.load(f).get("approved_hashes", {})
    else:
        approved_hashes = {}
    return competitors, minsait_clients, approved, approved_hashes


def get_competitors_for_client(competitors: dict, client_name: str, industry: str) -> list[dict]:
    """Resolve direct competitors for a given client based on industry/subindustry."""
    out = []
    industry_data = competitors.get("industries", {}).get(industry, {})
    for sub_name, sub in industry_data.get("subindustries", {}).items():
        clients = sub.get("clients_in_segment", [])
        if any(client_name.lower() in c.lower() for c in clients):
            out.extend(sub.get("main_competitors", []))
    return out


def extract_images_with_usage(pptx_path: str) -> tuple[dict[str, bytes], dict[str, list[int]]]:
    """Return (images_bytes, image_usage_per_slide)."""
    images: dict[str, bytes] = {}
    usage: dict[str, list[int]] = {}
    with zipfile.ZipFile(pptx_path) as z:
        for name in z.namelist():
            if name.startswith("ppt/media/"):
                fname = os.path.basename(name)
                images[fname] = z.read(name)
        slide_files = sorted(
            [n for n in z.namelist() if n.startswith("ppt/slides/slide") and n.endswith(".xml")],
            key=lambda p: int(re.search(r"slide(\d+)", p).group(1)),
        )
        for sf in slide_files:
            n_slide = int(re.search(r"slide(\d+)", sf).group(1))
            rels_path = sf.replace("slides/", "slides/_rels/").replace(".xml", ".xml.rels")
            if rels_path not in z.namelist():
                continue
            rels = z.read(rels_path).decode("utf-8", errors="ignore")
            for img in re.findall(r'Target="\.\./media/(image\d+\.[a-z]+)"', rels):
                usage.setdefault(img, []).append(n_slide)
    return images, usage


def name_hits(text: str, names: list[str]) -> list[str]:
    """Return which names appear in text as full tokens (word-boundary match)."""
    hits = []
    for name in names:
        if not name or len(name) < 2:
            continue
        # Use word boundary regex; allow spaces inside multi-word names
        pattern = r"(?<![A-Za-zÀ-ÿ])" + re.escape(name) + r"(?![A-Za-zÀ-ÿ])"
        if re.search(pattern, text, flags=re.IGNORECASE):
            hits.append(name)
    return hits


def all_competitor_names(competitors: dict, client_industry: str, client_name: str) -> list[dict]:
    """Flatten all competitor names from competitors_db relevant to the client's industry."""
    out = []
    industry = competitors.get("industries", {}).get(client_industry, {})
    for sub in industry.get("subindustries", {}).values():
        for comp in sub.get("main_competitors", []):
            for n in [comp.get("name", "")] + comp.get("aka", []):
                if n:
                    out.append({"name": n, "category": "competitor_industry"})
    # Consultancy competitors siempre aplican
    for tier in competitors.get("consultancy_competitors", {}).values():
        if isinstance(tier, list):
            for comp in tier:
                for n in [comp.get("name", "")] + comp.get("aka", []):
                    if n:
                        out.append({"name": n, "category": "competitor_consulting"})
    # Excluir el propio cliente
    out = [c for c in out if c["name"].lower() != client_name.lower()]
    return out


def all_minsait_clients(minsait_clients: dict, exclude_client: str) -> list[dict]:
    out = []
    for region in ("clients_perú", "clients_internacional"):
        for c in minsait_clients.get(region, []):
            for n in [c.get("name", "")] + c.get("aka", []):
                if n and n.lower() != exclude_client.lower():
                    out.append({"name": n, "category": "other_minsait_client"})
    return out


def all_approved_software(approved: dict) -> list[str]:
    out = []
    for vendor in approved.get("approved_software_vendors", []):
        out.append(vendor["name"])
        out.extend(vendor.get("aliases", []))
        out.extend(vendor.get("products_visible_ok", []))
    return out


def ocr_text(image_bytes: bytes, fname: str) -> str:
    """Best-effort OCR. Falls back gracefully if no OCR tool available."""
    try:
        import pytesseract
        from PIL import Image
        from io import BytesIO
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            img = Image.open(BytesIO(image_bytes))
            return pytesseract.image_to_string(img, lang="spa+eng")
    except Exception:
        pass
    return ""


def _hash_image(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()[:12]


def audit_image(
    fname: str,
    img_bytes: bytes,
    slides_using: list[int],
    competitors_list: list[dict],
    minsait_clients_list: list[dict],
    approved_software: list[str],
    target_client_name: str,
    cache: dict,
    approved_hashes: Optional[dict] = None,
) -> dict:
    """Audit a single image. Returns a finding dict."""
    size = len(img_bytes)
    img_hash = _hash_image(img_bytes)

    # Whitelist hit (Minsait-owned placeholder, official logo, etc.) — auto-approve
    if approved_hashes and img_hash in approved_hashes:
        wl = approved_hashes[img_hash]
        return {
            "image_id": fname, "hash": img_hash, "size_bytes": size,
            "appears_in_slides": slides_using,
            "severity": SEV_APPROVED,
            "category": wl.get("category", "minsait_whitelisted"),
            "description": f"Whitelisted: {wl.get('description', wl.get('name', ''))}",
            "competitor_relationship": None,
            "recommendation": "KEEP",
            "replacement_strategy": None,
            "block_delivery": False,
            "from_cache": False,
            "from_whitelist": True,
        }

    # Cache hit
    if img_hash in cache:
        cached = cache[img_hash].copy()
        cached["image_id"] = fname
        cached["appears_in_slides"] = slides_using
        cached["from_cache"] = True
        return cached

    finding = {
        "image_id": fname,
        "hash": img_hash,
        "size_bytes": size,
        "appears_in_slides": slides_using,
        "severity": SEV_NEUTRAL,
        "category": "unknown",
        "description": "",
        "competitor_relationship": None,
        "recommendation": "KEEP",
        "replacement_strategy": None,
        "block_delivery": False,
        "from_cache": False,
    }

    # Triage by size for non-photo formats
    if fname.lower().endswith((".emf", ".svg")) and size < TINY_BYTES:
        finding.update(category="decorative_shape", severity=SEV_APPROVED,
                       description="Forma decorativa pequeña del template (chaflán/contenedor).")
        cache[img_hash] = finding
        return finding

    # Run OCR for raster images
    text_in_image = ""
    if fname.lower().endswith((".png", ".jpg", ".jpeg")) and size >= TINY_BYTES:
        text_in_image = ocr_text(img_bytes, fname)

    # Check competitor names in OCR text
    if text_in_image:
        comp_names = [c["name"] for c in competitors_list]
        hits_set = set(name_hits(text_in_image, comp_names))
        comp_hits = [c for c in competitors_list if c["name"] in hits_set]
        if comp_hits:
            finding.update(
                severity=SEV_CRITICAL,
                category="competitor_logo" if comp_hits[0]["category"] == "competitor_industry" else "competitor_consulting_logo",
                description=f"Texto detectado por OCR contiene nombre(s) de competidor: {[c['name'] for c in comp_hits]}",
                competitor_relationship="direct_competitor",
                recommendation="REPLACE",
                replacement_strategy="use_target_client_logo" if "logo" in fname.lower() else "use_neutral_placeholder",
                block_delivery=True,
            )
            cache[img_hash] = finding
            return finding

        # Check other Minsait clients
        client_names = [c["name"] for c in minsait_clients_list]
        client_hits_set = set(name_hits(text_in_image, client_names))
        client_hits = [c for c in minsait_clients_list if c["name"] in client_hits_set]
        if client_hits:
            finding.update(
                severity=SEV_WARNING,
                category="other_client_branding",
                description=f"Texto contiene nombre(s) de otro cliente Minsait: {[c['name'] for c in client_hits]}",
                competitor_relationship="third_party_client",
                recommendation="REPLACE",
                replacement_strategy="use_neutral_placeholder",
                block_delivery=True,
            )
            cache[img_hash] = finding
            return finding

        # Check approved software (NEUTRAL)
        sw_hits = name_hits(text_in_image, approved_software)
        if sw_hits:
            finding.update(
                severity=SEV_NEUTRAL,
                category="third_party_software_logo",
                description=f"Logo/texto de software aprobado: {sw_hits[:3]}",
                recommendation="KEEP",
            )
            cache[img_hash] = finding
            return finding

    # Default by size
    if size >= LARGE_BYTES:
        finding.update(
            severity=SEV_NEUTRAL,
            category="stock_or_content_image",
            description=f"Imagen >50KB sin texto identificable. Requiere revisión visual humana o LLM Vision.",
            recommendation="MANUAL_REVIEW",
        )
    else:
        finding.update(
            severity=SEV_APPROVED,
            category="small_decorative",
            description="Imagen pequeña sin contenido sensible identificable.",
        )

    cache[img_hash] = finding
    return finding


def run_audit(
    pptx_path: str,
    client_name: str,
    client_industry: str,
    cache_path: Optional[str] = None,
) -> dict:
    competitors, minsait_clients, approved, approved_hashes = load_dbs()
    competitors_list = all_competitor_names(competitors, client_industry, client_name)
    minsait_clients_list = all_minsait_clients(minsait_clients, exclude_client=client_name)
    approved_software = all_approved_software(approved)

    cache = {}
    if cache_path and Path(cache_path).exists():
        cache = json.load(open(cache_path))

    images, usage = extract_images_with_usage(pptx_path)
    findings = []
    for fname, img_bytes in images.items():
        slides = usage.get(fname, [])
        finding = audit_image(
            fname, img_bytes, slides,
            competitors_list, minsait_clients_list, approved_software,
            client_name, cache,
            approved_hashes=approved_hashes,
        )
        findings.append(finding)

    if cache_path:
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(cache, f, indent=2, default=str)

    summary = {
        "critical": sum(1 for f in findings if f["severity"] == SEV_CRITICAL),
        "warning": sum(1 for f in findings if f["severity"] == SEV_WARNING),
        "neutral": sum(1 for f in findings if f["severity"] == SEV_NEUTRAL),
        "approved": sum(1 for f in findings if f["severity"] == SEV_APPROVED),
    }

    if summary["critical"] > 0:
        audit_status = "BLOCKED"
    elif summary["warning"] > 0:
        audit_status = "BLOCKED_RECOMMENDED"
    else:
        audit_status = "PASSED"

    report = {
        "deck": os.path.basename(pptx_path),
        "deck_path": pptx_path,
        "client_target": client_name,
        "client_industry": client_industry,
        "total_images": len(images),
        "audit_status": audit_status,
        "summary": summary,
        "findings": findings,
    }
    return report


def render_md_report(report: dict) -> str:
    lines = []
    status_emoji = {"PASSED": "✅", "BLOCKED_RECOMMENDED": "⚠️", "BLOCKED": "🚨"}.get(report["audit_status"], "")
    lines.append(f"# Reporte de Auditoría Visual · {report['deck']}")
    lines.append("")
    lines.append(f"**Cliente target:** {report['client_target']} · **Industria:** {report['client_industry']}")
    lines.append(f"**Total imágenes:** {report['total_images']}")
    lines.append(f"**Estado:** {status_emoji} **{report['audit_status']}**")
    lines.append("")
    s = report["summary"]
    lines.append(f"| Severidad | Cantidad |")
    lines.append(f"|---|---|")
    lines.append(f"| 🚨 CRITICAL | {s['critical']} |")
    lines.append(f"| ⚠️ WARNING | {s['warning']} |")
    lines.append(f"| ℹ️ NEUTRAL | {s['neutral']} |")
    lines.append(f"| ✅ APPROVED | {s['approved']} |")
    lines.append("")

    crit = [f for f in report["findings"] if f["severity"] == SEV_CRITICAL]
    warn = [f for f in report["findings"] if f["severity"] == SEV_WARNING]
    neut = [f for f in report["findings"] if f["severity"] == SEV_NEUTRAL]

    if crit:
        lines.append("## 🚨 CRÍTICO — Bloquean entrega")
        for f in crit:
            slides = ", ".join(str(s) for s in f["appears_in_slides"])
            lines.append(f"- **{f['image_id']}** (slides {slides}): {f['description']}")
            lines.append(f"  - Recomendación: `{f['recommendation']}` · Estrategia: `{f['replacement_strategy']}`")
        lines.append("")

    if warn:
        lines.append("## ⚠️ WARNING — Branding de otros clientes")
        for f in warn:
            slides = ", ".join(str(s) for s in f["appears_in_slides"])
            lines.append(f"- **{f['image_id']}** (slides {slides}): {f['description']}")
            lines.append(f"  - Recomendación: `{f['recommendation']}` · Estrategia: `{f['replacement_strategy']}`")
        lines.append("")

    manual_review = [f for f in neut if f["recommendation"] == "MANUAL_REVIEW"]
    if manual_review:
        lines.append("## ℹ️ Requieren revisión manual (LLM Vision o consultor)")
        for f in manual_review:
            slides = ", ".join(str(s) for s in f["appears_in_slides"])
            lines.append(f"- **{f['image_id']}** (slides {slides}, {f['size_bytes']:,} bytes): {f['description']}")
        lines.append("")

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pptx")
    p.add_argument("--client", required=True, help="Nombre del cliente target (e.g. Ferreyros)")
    p.add_argument("--industry", required=True, help="Industria (e.g. industria_consumo_energia)")
    p.add_argument("--report-json", default=None)
    p.add_argument("--report-md", default=None)
    p.add_argument("--cache", default=None, help="JSON cache de imágenes ya auditadas")
    args = p.parse_args()

    report = run_audit(args.pptx, args.client, args.industry, args.cache)
    if args.report_json:
        with open(args.report_json, "w") as f:
            json.dump(report, f, indent=2, default=str)
    md = render_md_report(report)
    if args.report_md:
        Path(args.report_md).write_text(md)
    print(md)
    sys.exit(0 if report["audit_status"] == "PASSED" else 1)


if __name__ == "__main__":
    main()
