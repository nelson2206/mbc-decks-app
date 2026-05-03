"""
compose_deck.py — Motor de composición v3

Compone un deck completo seleccionando slides del slide_bank/ y credenciales/ según:
  - archetype (esqueleto narrativo)
  - deck_brief (contexto del cliente)
  - knowledge del tema

Pipeline:
  1. Cargar archetype del tema
  2. Para cada slide del archetype, consultar slide_bank/<tipologia>/ con filtros
  3. Para slides de credenciales, consultar credenciales/<tema>/ con filtros sectoriales
  4. Componer .pptx fusionando slides seleccionadas
  5. Aplicar reemplazos textuales contextuales (cliente, fechas, números)

Uso:
    python compose_deck.py --archetype proposal_technical --brief deck_brief.json \
        --output deck.pptx [--include-all-credentials]

Notas técnicas:
  - La fusión de slides desde múltiples .pptx requiere mergear slides + sus rels + sus media
  - Usa python-pptx para la composición fina y zipfile para el copy de assets vinculados
  - Mantiene los layouts originales de cada slide (preserva diseño 100%)
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

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_DIR = SKILL_DIR.parent.parent


def load_archetype(archetype_id: str) -> dict:
    path = SKILL_DIR / "archetypes" / f"{archetype_id}.json"
    return json.load(open(path))


def load_slide_bank_index() -> dict:
    path = PLUGIN_DIR / "slide_bank" / "_index.json"
    if not path.exists():
        return {"slides": []}
    return json.load(open(path))


def load_credentials_index() -> dict:
    path = PLUGIN_DIR / "credenciales" / "_index.json"
    if not path.exists():
        return {"credentials": []}
    return json.load(open(path))


# Mapeo de section del archetype → typology folder
SECTION_TO_TYPOLOGY = {
    "cover": "01_portadas",
    "objectives": "04_proposito",
    "index": "02_indices",
    "section_divider_1": "03_separatas", "section_divider_2": "03_separatas",
    "section_divider_3": "03_separatas", "section_divider_4": "03_separatas",
    "section_divider_5": "03_separatas",
    "context_situation": "05_contexto", "context_business": "05_contexto",
    "context_pains": "05_contexto", "context_opportunity": "05_contexto",
    "context_recap": "05_contexto", "industry_context": "05_contexto",
    "value_proposition_one_liner": "06_propuesta_valor",
    "value_proposition_pillars": "06_propuesta_valor",
    "solution_overview": "06_propuesta_valor",
    "approach_methodology": "07_metodologia", "methodology": "07_metodologia",
    "phases": "07_metodologia", "phases_detail": "07_metodologia",
    "timeline": "08_plan_trabajo", "timeline_gantt": "08_plan_trabajo",
    "milestones": "08_plan_trabajo", "kickoff_timeline": "08_plan_trabajo",
    "team": "09_equipo", "team_minsait": "09_equipo", "team_client": "09_equipo",
    "team_cv": "10_cv_individual", "leadership": "09_equipo",
    "risks_mitigation": "11_riesgos_mitigacion",
    "client_dependencies": "12_dependencias",
    "why_minsait": "13_diferenciacion",
    "investment": "14_inversion", "investment_breakdown": "14_inversion",
    "commercial_conditions": "14_inversion",
    "closing": "15_cierre",
}


def select_slide_for_section(
    section: str,
    archetype_section: dict,
    bank_index: dict,
    deck_brief: dict,
) -> Optional[dict]:
    """Pick the best slide from the bank for a given archetype section."""
    typology = SECTION_TO_TYPOLOGY.get(section)
    if not typology:
        return None

    candidates = [s for s in bank_index.get("slides", []) if s.get("typology") == typology]
    if not candidates:
        return None

    # Naive selection: first match. Future: rank by deck.industry/topic similarity, recency.
    return candidates[0]


def select_credentials(deck_brief: dict, cred_index: dict, max_n: int = 18) -> list[dict]:
    """Select credentials based on amplitude principle: include all related ones, capped."""
    target_topic = deck_brief.get("deck", {}).get("topic_primary") or deck_brief.get("deck", {}).get("topic", "").lower()
    target_industry = deck_brief.get("client", {}).get("industry", "")

    candidates = cred_index.get("credentials", [])

    direct = [c for c in candidates
              if c.get("topic") == target_topic and c.get("industry") == target_industry]
    adjacent = [c for c in candidates
                if c.get("topic") == target_topic and c not in direct]
    tangencial = [c for c in candidates if c not in direct and c not in adjacent][:5]

    selected = (direct + adjacent + tangencial)[:max_n]
    return selected


def merge_slide_into_deck(target_pptx: str, source_slide_pptx: str) -> None:
    """Append the slide(s) from source_slide_pptx into target_pptx.

    Note: this is a simplified merge that:
      - Copies the source's slide XML
      - Copies the source's slide rels
      - Copies the source's media (renaming if collision)
      - Adds entries to target's presentation.xml + rels

    For production use, recommend using `python-pptx` + manual XML manipulation.
    This function is a stub — implementations vary by use case.
    """
    # Placeholder: the full XML merging is non-trivial and beyond a simple script.
    # In practice, use:
    #   - python-pptx's `slides.add_slide` with a layout from the source's master
    #   - OR: programmatic copy of the .xml + rels with namespace remapping
    raise NotImplementedError(
        "Slide merging across decks requires advanced XML manipulation. "
        "For v3.0 we recommend: use a 'reference deck' approach (generate_pptx_v2) "
        "until a robust merge_slide tool is built. compose_deck.py is the architecture "
        "for v4.0."
    )


def compose(archetype_id: str, deck_brief: dict, output_pptx: str) -> dict:
    """Top-level composition. Returns a manifest of selected slides."""
    archetype = load_archetype(archetype_id)
    bank_index = load_slide_bank_index()
    cred_index = load_credentials_index()

    manifest = {
        "archetype": archetype_id,
        "deck_brief_summary": {
            "client": deck_brief.get("client", {}).get("name_commercial"),
            "topic": deck_brief.get("deck", {}).get("topic"),
            "industry": deck_brief.get("client", {}).get("industry"),
        },
        "slides_selected": [],
        "credentials_selected": [],
    }

    # Pick slides for each section of the archetype
    for section_def in archetype.get("skeleton", []):
        if section_def.get("required") is False:
            # Optional sections can be skipped if not relevant
            continue
        section = section_def.get("section", "")
        chosen = select_slide_for_section(section, section_def, bank_index, deck_brief)
        if chosen:
            manifest["slides_selected"].append({
                "section": section,
                "order": section_def.get("order"),
                "from_bank": chosen.get("id"),
                "typology": chosen.get("typology"),
                "source_deck": chosen.get("source_deck"),
            })

    # Pick credentials with amplitude
    selected_creds = select_credentials(deck_brief, cred_index, max_n=18)
    manifest["credentials_selected"] = [
        {"id": c["id"], "client": c["client"], "topic": c["topic"], "industry": c["industry"]}
        for c in selected_creds
    ]

    return manifest


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archetype", required=True)
    p.add_argument("--brief", required=True, help="Path to deck_brief.json")
    p.add_argument("--output", required=True)
    p.add_argument("--manifest-only", action="store_true",
                   help="Solo produce el manifest sin generar el .pptx (útil para v3.0 mientras la merge es WIP)")
    args = p.parse_args()

    brief = json.load(open(args.brief))
    manifest = compose(args.archetype, brief, args.output)

    manifest_path = Path(args.output).with_suffix(".manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"✅ Manifest generado: {manifest_path}")
    print(f"   {len(manifest['slides_selected'])} slides del banco seleccionadas")
    print(f"   {len(manifest['credentials_selected'])} credenciales incluidas")

    if not args.manifest_only:
        print("\nNOTA: La fusión de slides desde el banco a un deck final requiere lógica de merge XML.")
        print("Por ahora (v3.0) recomendamos generar con `generate_pptx_v2.py` + reference_deck,")
        print("y usar este script solo para validar la SELECCIÓN de slides.")


if __name__ == "__main__":
    main()
