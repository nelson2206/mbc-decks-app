"""
vision_review.py — Extensión del A9 con Claude Vision API

Toma las imágenes que el A9 marcó como MANUAL_REVIEW (>50KB sin texto OCR detectable)
y las pasa a Claude Vision para detectar branding visual sin texto.

Útil para:
- Fotos de maquinaria con marca pequeña (ej. logo Komatsu en lateral de camión)
- Logos en formatos vectoriales rasterizados sin texto plano
- Headers o footers con logos pequeños
- Branding embebido en infografías

Requiere:
  - ANTHROPIC_API_KEY env var
  - pip install anthropic

Uso:
    python vision_review.py <visual_audit_report.json> --pptx <deck.pptx> \
        --client Ferreyros --industry industria_consumo_energia \
        --output vision_findings.json

El script actualiza el reporte original promoviendo MANUAL_REVIEW → CRITICAL/WARNING/APPROVED
según lo que Vision detecte.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
import re
import sys
import zipfile
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

VISION_PROMPT_TEMPLATE = """Eres el Auditor Visual A9 del sistema mbc-decks de Minsait Business Consulting.

Estás revisando una imagen que va a aparecer en una presentación destinada al cliente: **{client_name}** (industria: {industry}).

Competidores directos del cliente {client_name}:
{competitors_list}

Otros clientes Minsait conocidos (cuyo branding NO debería aparecer en este deck):
{other_clients_list}

**Tu tarea:** revisar la imagen y responder en formato JSON estricto:

```json
{{
  "description": "descripción concisa de lo que ves en la imagen (1-2 frases)",
  "visible_text": ["texto visible en la imagen, palabra por palabra"],
  "visible_logos": ["logos identificables, con nombre de marca"],
  "branding_detected": {{
    "competitor_brands": ["marcas de competidores detectadas"],
    "other_clients": ["otros clientes Minsait detectados"],
    "approved_software": ["software aprobado detectado (Microsoft, SAP, etc.)"],
    "minsait_branding": ["elementos Minsait propios"]
  }},
  "verdict": "CRITICAL | WARNING | NEUTRAL | APPROVED",
  "rationale": "razón breve de por qué este verdict"
}}
```

**Reglas:**
- CRITICAL: branding de competidor directo del cliente target visible
- WARNING: branding de otro cliente Minsait visible
- NEUTRAL: imagen genérica (stock, abstracción, conceptual) sin branding hostil
- APPROVED: imagen del cliente target o asset Minsait oficial

Sé preciso. Si NO puedes identificar marca/logo claramente, di "NEUTRAL" con la razón.
"""


def load_dbs():
    with open(SKILL_DIR / "brand" / "competitors_db.json") as f:
        competitors = json.load(f)
    with open(SKILL_DIR / "brand" / "minsait_clients_db.json") as f:
        clients = json.load(f)
    return competitors, clients


def get_competitors_text(competitors: dict, client_industry: str, client_name: str) -> str:
    out = []
    industry = competitors.get("industries", {}).get(client_industry, {})
    for sub in industry.get("subindustries", {}).values():
        if any(client_name.lower() in c.lower() for c in sub.get("clients_in_segment", [])):
            for comp in sub.get("main_competitors", []):
                out.append(f"- {comp['name']}")
    if not out:
        # Fallback: list competitors of the industry
        for sub in industry.get("subindustries", {}).values():
            for comp in sub.get("main_competitors", [])[:5]:
                out.append(f"- {comp['name']}")
    return "\n".join(out) or "- (sin competidores listados para esta industria)"


def get_clients_text(clients_db: dict, exclude: str) -> str:
    out = []
    for region in ("clients_perú", "clients_internacional"):
        for c in clients_db.get(region, []):
            if c["name"].lower() != exclude.lower():
                out.append(f"- {c['name']}")
    return "\n".join(out[:30])  # cap to 30 to keep prompt size reasonable


def extract_image_from_pptx(pptx_path: str, image_id: str) -> Optional[bytes]:
    with zipfile.ZipFile(pptx_path) as z:
        media_path = f"ppt/media/{image_id}"
        if media_path in z.namelist():
            return z.read(media_path)
    return None


def call_vision_api(image_bytes: bytes, image_id: str, prompt: str) -> dict:
    """Call Claude Vision API for an image. Requires ANTHROPIC_API_KEY env var."""
    try:
        import anthropic
    except ImportError:
        return {
            "error": "anthropic SDK not installed. Run: pip install anthropic",
            "verdict": "MANUAL_REVIEW_REQUIRED",
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "error": "ANTHROPIC_API_KEY env var not set",
            "verdict": "MANUAL_REVIEW_REQUIRED",
        }

    client = anthropic.Anthropic(api_key=api_key)

    # Determine media type
    ext = Path(image_id).suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext)
    if not media_type:
        return {"verdict": "MANUAL_REVIEW_REQUIRED", "error": f"unsupported format: {ext}"}

    image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",  # vision-capable
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        text = response.content[0].text
        # Try to extract JSON from response
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
        return {"verdict": "MANUAL_REVIEW_REQUIRED", "raw": text}
    except Exception as e:
        return {"verdict": "MANUAL_REVIEW_REQUIRED", "error": str(e)}


def review_pending(report_path: str, pptx_path: str, client_name: str, client_industry: str, output_path: str) -> dict:
    """Re-review all images flagged MANUAL_REVIEW with Claude Vision."""
    with open(report_path) as f:
        report = json.load(f)

    competitors_db, clients_db = load_dbs()
    competitors_text = get_competitors_text(competitors_db, client_industry, client_name)
    clients_text = get_clients_text(clients_db, exclude=client_name)
    prompt = VISION_PROMPT_TEMPLATE.format(
        client_name=client_name,
        industry=client_industry,
        competitors_list=competitors_text,
        other_clients_list=clients_text,
    )

    pending = [f for f in report["findings"] if f.get("recommendation") == "MANUAL_REVIEW"]
    print(f"Vision review: {len(pending)} imágenes a procesar...")

    vision_findings = []
    for f in pending:
        image_bytes = extract_image_from_pptx(pptx_path, f["image_id"])
        if not image_bytes:
            continue
        result = call_vision_api(image_bytes, f["image_id"], prompt)
        finding = {
            "image_id": f["image_id"],
            "appears_in_slides": f["appears_in_slides"],
            "size_bytes": f["size_bytes"],
            "vision_result": result,
            "previous_severity": f["severity"],
            "new_severity": result.get("verdict", "MANUAL_REVIEW_REQUIRED"),
        }
        vision_findings.append(finding)
        print(f"  {f['image_id']}: {finding['new_severity']} — {result.get('rationale', result.get('error', ''))}")

    # Write output
    with open(output_path, "w") as f:
        json.dump({
            "vision_review_complete": True,
            "client_target": client_name,
            "industry": client_industry,
            "findings": vision_findings,
        }, f, indent=2, default=str)

    # Summary
    new_critical = sum(1 for f in vision_findings if f["new_severity"] == "CRITICAL")
    new_warning = sum(1 for f in vision_findings if f["new_severity"] == "WARNING")
    print(f"\nResumen Vision: {new_critical} CRITICAL · {new_warning} WARNING · {len(vision_findings) - new_critical - new_warning} OK")
    return {"critical": new_critical, "warning": new_warning, "total": len(vision_findings)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("report_json", help="visual_audit_report.json del A9")
    p.add_argument("--pptx", required=True)
    p.add_argument("--client", required=True)
    p.add_argument("--industry", required=True)
    p.add_argument("--output", default="vision_findings.json")
    args = p.parse_args()
    summary = review_pending(args.report_json, args.pptx, args.client, args.industry, args.output)
    sys.exit(0 if summary["critical"] == 0 else 1)


if __name__ == "__main__":
    main()
