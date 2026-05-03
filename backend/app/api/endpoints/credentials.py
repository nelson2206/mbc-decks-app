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
