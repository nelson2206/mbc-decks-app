"""Endpoints de gestión de decks: crear, listar, obtener, descargar."""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.models import StartDeckRequest, DeckOut, DeckListItem
from app.db.session import get_db
from app.db.models import User, Deck

router = APIRouter(prefix="/api/decks", tags=["decks"])


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


@router.get("/{deck_id}/download")
def download_deck(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck or not deck.storage_path or not os.path.exists(deck.storage_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Archivo no disponible")
    if deck.audit_status == "BLOCKED":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Deck bloqueado por A9 — resolver branding hostil primero")
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
