"""Endpoint de generación de deck — dispara el pipeline multi-agente."""
import os
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.models import GenerateRequest
from app.db.session import get_db, SessionLocal
from app.db.models import User, Deck
from app.services import orchestrator, deck_generator, visual_auditor
from app.core.config import settings

router = APIRouter(prefix="/api/generate", tags=["generate"])


def _run_pipeline_background(deck_id: str, reference_pptx: str, edit_map: dict):
    """Background task: corre el pipeline completo + auditoría visual."""
    db: Session = SessionLocal()
    try:
        # A2-A4 pipeline
        orchestrator.run_full_pipeline(deck_id, db)

        # Generar .pptx
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if not deck:
            return
        out_dir = Path(settings.storage_local_path) / "decks"
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / f"{deck_id}.pptx"
        deck_generator.generate_deck(reference_pptx, edit_map, str(output))
        deck.storage_path = str(output)
        deck.status = "audit"
        db.commit()

        # A9 Auditoría visual
        report = visual_auditor.audit_pptx(
            str(output),
            client_name=deck.client_name,
            industry=deck.industry,
        )
        deck.audit_status = report["audit_status"]
        deck.audit_report = report
        deck.status = "blocked" if report["audit_status"] == "BLOCKED" else "ready"
        db.commit()

        # A6/A7/A8 reviews
        if deck.audit_status != "BLOCKED":
            orchestrator.run_reviews(deck_id, db)
    finally:
        db.close()


@router.post("/{deck_id}", status_code=status.HTTP_202_ACCEPTED)
def generate_deck(
    deck_id: str,
    req: GenerateRequest,
    bg: BackgroundTasks,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")

    # Determinar reference deck a usar (default: usar el reference_decks/<industry>/<topic>/reference.pptx)
    reference_pptx = req.use_reference_deck_id or _resolve_default_reference(deck.industry, deck.topic)
    if not reference_pptx or not os.path.exists(reference_pptx):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"No se encontró deck de referencia para topic={deck.topic} industry={deck.industry}"
        )

    edit_map = _build_edit_map_from_brief(deck.deck_brief)

    deck.status = "generating"
    db.commit()
    bg.add_task(_run_pipeline_background, deck_id, reference_pptx, edit_map)
    return {"deck_id": deck_id, "status": "generation_queued"}


def _resolve_default_reference(industry: str, topic: str) -> str:
    """Resuelve el path del reference deck para topic × industry."""
    # Mapping simplificado: reference_decks/<industry>/<topic>/reference.pptx
    industry_short = "ice" if "industria" in industry else "fs" if "financiero" in industry else industry
    return str(settings.plugin_path / "reference_decks" / industry_short / topic / "reference.pptx")


def _build_edit_map_from_brief(brief: dict) -> dict:
    """Construye el edit_map.json a partir del brief de la entrevista."""
    answers = brief.get("interview_answers", {})
    client_name = brief.get("client", {}).get("name_commercial", "")

    edit_map = {
        "global_text_replacements": [],
        "regex_replacements": [],
        "slide_specific": {},
        "image_replacements": [],
        "delete_slides": [],
    }
    if client_name:
        edit_map["global_text_replacements"].append({
            "find": "[CLIENT_NAME]",
            "replace": client_name,
        })
    return edit_map
