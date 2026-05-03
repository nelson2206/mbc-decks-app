"""Orquestador multi-agente.

Coordina los 9 agentes del sistema mbc-decks usando Claude API:
  A1 · Orchestrator       - este servicio
  A2 · Researcher         - genera research_brief
  A3 · Structurer         - define narrative_skeleton
  A4 · Content writer     - escribe slide_content
  A5 · Visual designer    - mapea a layouts (slide_plan)
  A6 · Manager reviewer   - revisión calidad
  A7 · Partner consulting - revisión estratégica
  A8 · Partner tech/data  - revisión técnica
  A9 · Visual auditor     - bloqueador de branding hostil

Estados del deck en BD:
  draft → interviewing → researching → structuring → writing → visual → audit →
  (blocked|ready) → delivered
"""
from __future__ import annotations
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.core.anthropic_client import claude
from app.core.config import settings
from app.db.models import Deck
from app.services.knowledge import knowledge

logger = logging.getLogger(__name__)


def _load_archetype(archetype_id: str) -> dict:
    path = settings.archetypes_path / f"{archetype_id}.json"
    if not path.exists():
        raise ValueError(f"Archetype {archetype_id} not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_research(deck: Deck, db: Session) -> dict:
    """A2 · Researcher — produce research_brief.md."""
    deck.status = "researching"
    db.commit()

    brief = deck.deck_brief or {}
    user_message = (
        f"Genera un research_brief para una propuesta MBC.\n\n"
        f"Cliente: {deck.client_name}\n"
        f"Industria: {deck.industry}\n"
        f"Tema: {deck.topic}\n"
        f"Brief de la entrevista:\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
        f"Sigue el formato y reglas del prompt de sistema. Toda cifra debe llevar fuente o "
        f"marcarse como [ESTIMACIÓN — validar con cliente]."
    )
    output = claude.call_agent("researcher", user_message, max_tokens=4096)
    deck.research_brief = {"markdown": output}
    db.commit()
    return deck.research_brief


def run_structure(deck: Deck, db: Session) -> dict:
    """A3 · Structurer — produce narrative_skeleton.json."""
    deck.status = "structuring"
    db.commit()

    archetype = _load_archetype(deck.deck_type)
    research = (deck.research_brief or {}).get("markdown", "")
    brief = deck.deck_brief or {}

    user_message = (
        f"Adapta el archetype al brief específico del cliente y produce narrative_skeleton.json.\n\n"
        f"Archetype base:\n{json.dumps(archetype, ensure_ascii=False, indent=2)}\n\n"
        f"Brief del deck:\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
        f"Research brief:\n{research[:8000]}\n\n"
        f"Devuelve el JSON con cada slide adaptada al caso. Aplica las reglas MBB del prompt."
    )
    output = claude.call_agent("structurer", user_message, max_tokens=8192)
    # Best-effort JSON extraction
    try:
        skeleton = json.loads(output[output.index("{"):output.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        skeleton = {"raw": output}
    deck.narrative_skeleton = skeleton
    db.commit()
    return skeleton


def run_content(deck: Deck, db: Session) -> dict:
    """A4 · Content — produce slide_content.json. Usa knowledge base del tema."""
    deck.status = "writing"
    db.commit()

    concepts = knowledge.get_concepts(deck.topic)
    skeleton = deck.narrative_skeleton or {}
    brief = deck.deck_brief or {}

    extra_context = (
        f"## Knowledge base — Tema: {deck.topic}\n\n{concepts[:6000]}"
        if concepts else ""
    )
    user_message = (
        f"Redacta el contenido final de cada slide del esqueleto narrativo.\n\n"
        f"Brief: {json.dumps(brief, ensure_ascii=False, indent=2)[:3000]}\n\n"
        f"Esqueleto narrativo:\n{json.dumps(skeleton, ensure_ascii=False)[:8000]}\n\n"
        f"Devuelve un JSON con clave por slide_order. Aplica las reglas del prompt + contraste con knowledge base."
    )
    output = claude.call_agent("content", user_message, extra_system_context=extra_context, max_tokens=8192)
    try:
        content = json.loads(output[output.index("{"):output.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        content = {"raw": output}
    deck.slide_content = content
    db.commit()
    return content


def run_review(deck: Deck, db: Session, agent_name: str) -> str:
    """A6/A7/A8 · Reviewers — produce review_<agent>.md."""
    user_message = (
        f"Revisa el deck según tu rol ({agent_name}).\n\n"
        f"Cliente: {deck.client_name} · Industria: {deck.industry} · Tema: {deck.topic}\n\n"
        f"Brief: {json.dumps(deck.deck_brief, ensure_ascii=False)[:3000]}\n"
        f"Esqueleto: {json.dumps(deck.narrative_skeleton, ensure_ascii=False)[:5000]}\n"
        f"Contenido (preview): {json.dumps(deck.slide_content, ensure_ascii=False)[:5000]}\n\n"
        f"Aplica los criterios de tu prompt. Devuelve markdown estructurado con issues."
    )
    return claude.call_agent(agent_name, user_message, max_tokens=4096)


def run_full_pipeline(deck_id: str, db: Session) -> Deck:
    """Ejecuta el pipeline completo de A2 a A8 (sin A9 — A9 corre sobre el .pptx final)."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise ValueError(f"Deck {deck_id} not found")

    logger.info(f"Pipeline arranca para deck {deck_id} (cliente: {deck.client_name})")

    # A2 Researcher
    run_research(deck, db)
    # A3 Structurer
    run_structure(deck, db)
    # A4 Content
    run_content(deck, db)

    deck.status = "visual"
    db.commit()
    return deck


def run_reviews(deck_id: str, db: Session) -> dict[str, str]:
    """Ejecuta Manager + 2 Socios sobre un deck en estado 'visual' o posterior."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise ValueError(f"Deck {deck_id} not found")
    reviews = {
        "manager": run_review(deck, db, "manager"),
        "partner_consulting": run_review(deck, db, "partner_consulting"),
        "partner_tech": run_review(deck, db, "partner_tech"),
    }
    deck.review_consolidated = "\n\n---\n\n".join(
        f"# {name}\n\n{md}" for name, md in reviews.items()
    )
    db.commit()
    return reviews
