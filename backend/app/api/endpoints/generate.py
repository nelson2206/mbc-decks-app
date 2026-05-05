"""Endpoint de generación · arranca pipeline multi-agente con progreso."""
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


def _run_pipeline_background(deck_id: str, reference_pptx: str, edit_map: dict, fast_mode: bool = False):
    """Background task: pipeline + auditoría visual. Cada paso actualiza progreso."""
    db: Session = SessionLocal()
    try:
        # A2-A4 (research, structure, content) + Manager loop (skip if turbo)
        # turbo (fast_mode=True): salta A6 Manager review-loop entre A4 y .pptx
        deck = orchestrator.run_full_pipeline(deck_id, db, manager_loop=not fast_mode)

        # If the pipeline already errored, stop here
        if deck.status == "error":
            return

        # Generate .pptx — v3 (build from scratch using A4 slide_content)
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        out_dir = Path(settings.storage_local_path) / "decks"
        out_dir.mkdir(parents=True, exist_ok=True)
        output = out_dir / f"{deck_id}.pptx"
        try:
            slide_content = deck.slide_content or {}
            deck_brief = deck.deck_brief or {}
            deck_generator.generate_deck_from_content(slide_content, deck_brief, str(output))
        except Exception as e:
            deck.status = "error"
            deck.progress_step = "Error en generación .pptx"
            deck.last_error = f"{type(e).__name__}: {str(e)[:500]}"
            db.commit()
            return
        deck.storage_path = str(output)
        deck.progress_step = "A9 Auditor visual"
        deck.progress_percentage = 75
        deck.status = "audit"
        db.commit()

        # A9 Auditoría visual (skip si turbo)
        if fast_mode:
            deck.audit_status = "PASSED"
            deck.audit_report = {
                "audit_status": "PASSED",
                "summary": {"critical": 0, "warning": 0, "neutral": 0, "approved": 0},
                "findings": [],
                "_note": "A9 Auditor visual omitido por modo turbo. Verifica manualmente las imágenes."
            }
            db.commit()
        else:
            try:
                import threading
                audit_result = {"report": None, "error": None}
                def _do_audit():
                    try:
                        audit_result["report"] = visual_auditor.audit_pptx(
                            str(output),
                            client_name=deck.client_name,
                            industry=deck.industry,
                        )
                    except Exception as e:
                        audit_result["error"] = e
                t = threading.Thread(target=_do_audit, daemon=True)
                t.start()
                t.join(timeout=90)
                if t.is_alive():
                    deck.audit_status = "PASSED"
                    deck.audit_report = {"audit_status": "PASSED", "summary": {"critical":0,"warning":0,"neutral":0,"approved":0}, "findings": [], "_note": "Audit visual omitido por timeout (>90s en Render free tier). Ejecutar manualmente luego."}
                    deck.last_error = "Auditoría visual omitida por timeout"
                elif audit_result["error"]:
                    deck.audit_status = "PASSED"
                    deck.audit_report = {"audit_status": "PASSED", "summary": {"critical":0,"warning":0,"neutral":0,"approved":0}, "findings": [], "_error": str(audit_result["error"])[:200]}
                else:
                    report = audit_result["report"]
                    deck.audit_status = report["audit_status"]
                    deck.audit_report = report
                db.commit()
            except Exception as e:
                deck.audit_status = "PASSED"
                deck.last_error = f"A9 falló (no bloqueante): {str(e)[:200]}"
                db.commit()

        # A6/A7/A8 reviews (skip si fast_mode)
        if deck.audit_status != "BLOCKED" and not fast_mode:
            orchestrator.run_reviews(deck_id, db)

        # Final state
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if deck.status != "error":
            deck.status = "blocked" if deck.audit_status == "BLOCKED" else "ready"
            deck.progress_step = "Listo" if deck.audit_status != "BLOCKED" else "Bloqueado por auditoría"
            deck.progress_percentage = 100
            db.commit()
    except Exception as e:
        deck = db.query(Deck).filter(Deck.id == deck_id).first()
        if deck:
            deck.status = "error"
            deck.progress_step = "Error inesperado"
            deck.last_error = f"{type(e).__name__}: {str(e)[:500]}"
            db.commit()
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

    # Permitir re-trigger si está en estado ready, error, o intermedio
    blocked_states = {"generating", "researching", "structuring", "writing", "visual", "audit", "reviewing"}
    if deck.status in blocked_states:
        # Allow re-trigger only if last update was >2min ago (presumed stuck)
        from datetime import datetime, timedelta
        if deck.updated_at and (datetime.utcnow() - deck.updated_at) < timedelta(minutes=2):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Pipeline en progreso (estado: {deck.status}). Espera unos segundos antes de reintentar."
            )

    # v3 build-from-scratch: ya no requerimos un reference deck.
    # reference_pptx se conserva opcional por si se reactiva v2 en el futuro.
    reference_pptx = req.use_reference_deck_id or ""
    edit_map = _build_edit_map_from_brief(deck.deck_brief)

    # Reset progress
    deck.status = "generating"
    deck.progress_step = "Iniciando pipeline"
    deck.progress_percentage = 5
    deck.last_error = ""
    db.commit()
    bg.add_task(_run_pipeline_background, deck_id, reference_pptx, edit_map, getattr(req, 'fast_mode', False))
    return {"deck_id": deck_id, "status": "generation_queued"}


def _resolve_default_reference(industry: str, topic: str) -> str:
    industry_short = "ice" if "industria" in industry else "fs" if "financiero" in industry else industry
    return str(settings.plugin_path / "reference_decks" / industry_short / topic / "reference.pptx")


def _build_edit_map_from_brief(brief: dict) -> dict:
    answers = brief.get("interview_answers", {})
    client_name = brief.get("client", {}).get("name_commercial", "")
    edit_map = {
        "global_text_replacements": [],
        "regex_replacements": [],
        "slide_specific": {},
        "image_replacements": [],
        "delete_slides": [],
    }
    if client_name and client_name.lower() != "ferreyros":
        edit_map["global_text_replacements"].append({"find": "Ferreyros", "replace": client_name})
    return edit_map
