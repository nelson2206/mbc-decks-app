"""Endpoint de búsqueda de credenciales."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.api.deps import get_current_user
from app.api.models import CredentialOut
from app.db.session import get_db
from app.db.models import User, Credential

router = APIRouter(prefix="/api/credentials", tags=["credentials"])


@router.get("", response_model=list[CredentialOut])
def search_credentials(
    topic: str | None = Query(None),
    industry: str | None = Query(None),
    client: str | None = Query(None),
    keyword: str | None = Query(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Credential).filter(Credential.is_active == True)
    if topic:
        q = q.filter(Credential.topic == topic)
    if industry:
        q = q.filter(Credential.industry == industry)
    if client:
        q = q.filter(Credential.client.ilike(f"%{client}%"))
    if keyword:
        q = q.filter(or_(Credential.client.ilike(f"%{keyword}%"), Credential.id.ilike(f"%{keyword}%")))
    return q.order_by(Credential.year.desc().nullslast()).limit(100).all()


@router.get("/topics")
def list_topics(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Credential.topic).distinct().all()
    return {"topics": sorted([r[0] for r in rows if r[0]])}

@router.get("/{credential_id}")
def get_credential_detail(credential_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Detalle completo de una credencial para preview."""
    cred = db.query(Credential).filter(Credential.id == credential_id, Credential.is_active == True).first()
    if not cred:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(http_status.HTTP_404_NOT_FOUND, "Credencial no encontrada")
    md = cred.metadata_json or {}
    preview = md.get("slide_text_preview", "")
    # Estructurar preview en bullets
    import re
    parts = [p.strip() for p in re.split(r'\s*\|\s*|\s*\n\s*', preview) if p and p.strip() and len(p.strip()) > 5]
    return {
        "id": cred.id,
        "client": cred.client,
        "industry": cred.industry,
        "topic": cred.topic,
        "year": cred.year,
        "title": md.get("title", ""),
        "source_deck": md.get("source_deck", ""),
        "bullets": parts[:12],
        "raw_text": preview,
        "storage_path": cred.storage_path,
    }
