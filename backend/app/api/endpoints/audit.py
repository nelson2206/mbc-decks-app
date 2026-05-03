"""Endpoint de auditoría visual A9."""
import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.db.models import User, Deck
from app.services import visual_auditor

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.post("/{deck_id}")
def audit_deck(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")
    if not deck.storage_path or not os.path.exists(deck.storage_path):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Deck no tiene archivo .pptx generado todavía")
    report = visual_auditor.audit_pptx(deck.storage_path, deck.client_name, deck.industry)
    deck.audit_status = report["audit_status"]
    deck.audit_report = report
    if deck.audit_status == "BLOCKED":
        deck.status = "blocked"
    db.commit()
    return report


@router.get("/{deck_id}/report")
def get_audit_report(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")
    return {
        "deck_id": deck.id,
        "audit_status": deck.audit_status,
        "report": deck.audit_report,
    }
