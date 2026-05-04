"""Orquestador multi-agente con tracking de progreso y manejo robusto de errores."""
from __future__ import annotations
import json
import logging
import traceback
from typing import Any

from sqlalchemy.orm import Session

from app.core.anthropic_client import claude
from app.core.config import settings
from app.db.models import Deck
from app.services.knowledge import knowledge

logger = logging.getLogger(__name__)


# Definición de los pasos del pipeline con su % de progreso
PIPELINE_STEPS = [
    ("researching",   "A2 Investigador",     10),
    ("structuring",   "A3 Estructurador",    25),
    ("writing",       "A4 Contenido",        50),
    ("visual",        "A5 Visual",           65),
    ("audit",         "A9 Auditor visual",   75),
    ("reviewing",     "A6/A7/A8 Revisores",  90),
    ("ready",         "Listo",               100),
]



def _check_cancelled(deck: Deck, db: Session) -> bool:
    """Refresca el deck desde la BD y retorna True si fue cancelado por el usuario."""
    db.refresh(deck)
    return deck.status == "cancelled"

def _set_progress(deck: Deck, db: Session, step_key: str, label: str, pct: int):
    """Update progress in DB so frontend can show it."""
    deck.status = step_key
    deck.progress_step = label
    deck.progress_percentage = pct
    deck.last_error = ""
    db.commit()


def _set_error(deck: Deck, db: Session, step_label: str, exc: Exception):
    """Mark deck as errored with the failing step and message."""
    deck.status = "error"
    deck.progress_step = f"Error en {step_label}"
    deck.last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
    db.commit()
    logger.error(f"Pipeline error en {step_label}: {exc}\n{traceback.format_exc()}")


def _load_archetype(archetype_id: str) -> dict:
    path = settings.archetypes_path / f"{archetype_id}.json"
    if not path.exists():
        raise ValueError(f"Archetype {archetype_id} not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_research(deck: Deck, db: Session) -> dict:
    """A2 Researcher."""
    _set_progress(deck, db, "researching", "A2 Investigador", 10)
    brief = deck.deck_brief or {}
    user_message = (
        f"Genera un research_brief para una propuesta MBC.\n\n"
        f"Cliente: {deck.client_name}\nIndustria: {deck.industry}\nTema: {deck.topic}\n"
        f"Brief de la entrevista:\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
        f"Toda cifra debe llevar fuente o marcarse como [ESTIMACIÓN]."
    )
    output = claude.call_agent("researcher", user_message, max_tokens=4096)
    deck.research_brief = {"markdown": output}
    db.commit()
    return deck.research_brief


def run_structure(deck: Deck, db: Session) -> dict:
    """A3 Structurer."""
    _set_progress(deck, db, "structuring", "A3 Estructurador", 25)
    archetype = _load_archetype(deck.deck_type)
    research = (deck.research_brief or {}).get("markdown", "")
    brief = deck.deck_brief or {}
    user_message = (
        f"Adapta el archetype al brief y produce narrative_skeleton.json.\n\n"
        f"Archetype:\n{json.dumps(archetype, ensure_ascii=False, indent=2)}\n\n"
        f"Brief:\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
        f"Research:\n{research[:6000]}\n\nDevuelve JSON puro con cada slide adaptada."
    )
    output = claude.call_agent("structurer", user_message, max_tokens=4096)
    try:
        skeleton = json.loads(output[output.index("{"):output.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        skeleton = {"raw": output}
    deck.narrative_skeleton = skeleton
    db.commit()
    return skeleton


def run_content(deck: Deck, db: Session) -> dict:
    """A4 Content."""
    _set_progress(deck, db, "writing", "A4 Contenido", 50)
    concepts = knowledge.get_concepts(deck.topic)
    skeleton = deck.narrative_skeleton or {}
    brief = deck.deck_brief or {}
    extra_context = (
        f"## Knowledge base — Tema: {deck.topic}\n\n{concepts[:6000]}"
        if concepts else ""
    )
    user_message = (
        f"Redacta el contenido final de cada slide.\n\n"
        f"Brief: {json.dumps(brief, ensure_ascii=False)[:3000]}\n\n"
        f"Esqueleto:\n{json.dumps(skeleton, ensure_ascii=False)[:8000]}\n\n"
        f"Devuelve JSON con clave por slide_order."
    )
    output = claude.call_agent("content", user_message,
                               extra_system_context=extra_context, max_tokens=5120)
    try:
        content = json.loads(output[output.index("{"):output.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        content = {"raw": output}
    deck.slide_content = content
    db.commit()
    return content


def run_review(deck: Deck, db: Session, agent_name: str) -> str:
    """A6/A7/A8 Reviewers."""
    user_message = (
        f"Revisa el deck según tu rol ({agent_name}).\n\n"
        f"Cliente: {deck.client_name} · Industria: {deck.industry} · Tema: {deck.topic}\n\n"
        f"Brief: {json.dumps(deck.deck_brief, ensure_ascii=False)[:2000]}\n"
        f"Esqueleto: {json.dumps(deck.narrative_skeleton, ensure_ascii=False)[:3000]}\n"
        f"Contenido: {json.dumps(deck.slide_content, ensure_ascii=False)[:3000]}\n\n"
        f"Devuelve markdown estructurado con issues."
    )
    return claude.call_agent(agent_name, user_message, max_tokens=4096)


def run_full_pipeline(deck_id: str, db: Session) -> Deck:
    """Pipeline completo con manejo de errores. Cada paso actualiza progreso en BD."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise ValueError(f"Deck {deck_id} not found")

    logger.info(f"Pipeline arranca para deck {deck_id} (cliente: {deck.client_name})")
    # Reset error state
    deck.last_error = ""
    db.commit()

    if _check_cancelled(deck, db):
        return deck
    try:
        run_research(deck, db)
    except Exception as e:
        _set_error(deck, db, "A2 Investigador", e)
        return deck

    if _check_cancelled(deck, db):
        return deck
    try:
        run_structure(deck, db)
    except Exception as e:
        _set_error(deck, db, "A3 Estructurador", e)
        return deck

    if _check_cancelled(deck, db):
        return deck
    try:
        run_content(deck, db)
    except Exception as e:
        _set_error(deck, db, "A4 Contenido", e)
        return deck

    _set_progress(deck, db, "visual", "A5 Visual", 65)
    return deck


def run_reviews(deck_id: str, db: Session, parallel: bool = True) -> dict[str, str]:
    """A6/A7/A8 Manager + 2 Socios. Por defecto en paralelo (3x más rápido)."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise ValueError(f"Deck {deck_id} not found")
    _set_progress(deck, db, "reviewing", "A6/A7/A8 Revisores (paralelo)", 90)
    reviews = {}
    agents = ("manager", "partner_consulting", "partner_tech")
    try:
        if parallel:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_agent = {executor.submit(run_review, deck, db, a): a for a in agents}
                for future in future_to_agent:
                    agent = future_to_agent[future]
                    try:
                        reviews[agent] = future.result(timeout=120)
                    except Exception as e:
                        reviews[agent] = f"⚠ Error en {agent}: {str(e)[:200]}"
        else:
            for agent in agents:
                reviews[agent] = run_review(deck, db, agent)
        deck.review_consolidated = "\n\n---\n\n".join(
            f"# {n}\n\n{md}" for n, md in reviews.items()
        )
        db.commit()
    except Exception as e:
        _set_error(deck, db, "Revisores", e)
    return reviews
