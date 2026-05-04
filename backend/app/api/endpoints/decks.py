"""Endpoints de gestión de decks: crear, listar, obtener, descargar."""
import os
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.models import StartDeckRequest, DeckOut, DeckListItem
from app.db.session import get_db
from app.db.models import User, Deck
from app.services import deck_generator
from app.core.config import settings

router = APIRouter(prefix="/api/decks", tags=["decks"])
logger = logging.getLogger(__name__)


@router.post("", response_model=DeckOut, status_code=status.HTTP_201_CREATED)
def create_deck(req: StartDeckRequest, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = Deck(
        owner_id=current.id,
        title=req.title_working,
        deck_type=req.deck_type,
        topic=req.topic,
        industry=req.industry,
        client_name=req.client_name,
        status="draft",
        deck_brief={"deck": {
            "type": req.deck_type, "topic": req.topic, "title_working": req.title_working,
        }, "client": {"name_commercial": req.client_name, "industry": req.industry}},
    )
    db.add(deck)
    db.commit()
    db.refresh(deck)
    return deck


@router.get("", response_model=list[DeckListItem])
def list_decks(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Deck).filter(Deck.owner_id == current.id).order_by(Deck.updated_at.desc()).all()


@router.get("/{deck_id}", response_model=DeckOut)
def get_deck(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")
    return deck


def _regenerate_pptx(deck: Deck, db: Session) -> str:
    """Regenera el .pptx desde slide_content + reference. Usado cuando /tmp se borró."""
    industry_short = "ice" if "industria" in deck.industry else "fs" if "financiero" in deck.industry else deck.industry
    reference = settings.plugin_path / "reference_decks" / industry_short / deck.topic / "reference.pptx"
    if not reference.exists():
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            f"No se encontró deck de referencia para topic={deck.topic} industry={deck.industry}")

    out_dir = Path(settings.storage_local_path) / "decks"
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / f"{deck.id}.pptx"

    # Construir edit_map con reemplazos básicos del cliente
    brief = deck.deck_brief or {}
    client_name = brief.get("client", {}).get("name_commercial", "") or deck.client_name
    edit_map = {
        "global_text_replacements": [],
        "regex_replacements": [],
        "slide_specific": {},
        "image_replacements": [],
        "delete_slides": [],
    }
    if client_name and client_name.lower() != "ferreyros":
        edit_map["global_text_replacements"].append({"find": "Ferreyros", "replace": client_name})

    deck_generator.generate_deck(str(reference), edit_map, str(output))
    deck.storage_path = str(output)
    db.commit()
    logger.info(f"Re-generado .pptx para deck {deck.id} en {output}")
    return str(output)


@router.get("/{deck_id}/download")
def download_deck(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")
    if deck.audit_status == "BLOCKED":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Deck bloqueado por A9 — resolver branding hostil primero")

    # Regenerar si el archivo no existe (filesystem efímero)
    if not deck.storage_path or not os.path.exists(deck.storage_path):
        # Pero solo si tenemos slide_content en BD (sino, el pipeline debe correr de nuevo)
        if not deck.slide_content or len(str(deck.slide_content)) < 50:
            raise HTTPException(status.HTTP_404_NOT_FOUND,
                "El archivo no existe y el contenido del deck no está en BD. Reintenta la generación.")
        try:
            _regenerate_pptx(deck, db)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to regenerate .pptx for deck {deck_id}: {e}")
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                                f"No se pudo regenerar el archivo: {str(e)[:200]}")

    fname = f"{deck.client_name}_{deck.topic}_{deck.id[:8]}.pptx"
    return FileResponse(deck.storage_path, filename=fname,
                        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation")


@router.delete("/{deck_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_deck(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")
    db.delete(deck)
    db.commit()


@router.post("/{deck_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_deck(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cancela un deck en proceso. El orchestrator chequea entre pasos y aborta."""
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")
    in_progress_states = {"generating","researching","structuring","writing","visual","audit","reviewing"}
    if deck.status not in in_progress_states:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"El deck no está en progreso (estado actual: {deck.status})")
    deck.status = "cancelled"
    deck.progress_step = "Cancelado por usuario"
    deck.last_error = "Cancelado manualmente desde la UI"
    db.commit()
    return {"deck_id": deck.id, "status": "cancelled"}
