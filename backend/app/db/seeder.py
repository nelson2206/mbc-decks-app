"""Seed de credenciales del corpus al startup del backend.

Idempotente: solo inserta credenciales que no existan ya.
"""
import json
import logging
from pathlib import Path
from sqlalchemy.orm import Session

from app.db.models import Credential

logger = logging.getLogger(__name__)


def seed_credentials(db: Session) -> int:
    """Carga seed_credentials.json a la tabla Credential. Retorna número de nuevas filas."""
    seed_path = Path(__file__).parent / "seed_credentials.json"
    if not seed_path.exists():
        logger.warning(f"Seed file not found: {seed_path}")
        return 0

    data = json.loads(seed_path.read_text(encoding="utf-8"))
    inserted = 0
    for item in data:
        cred_id = item.get("id")
        if not cred_id:
            continue
        existing = db.query(Credential).filter(Credential.id == cred_id).first()
        if existing:
            # Update metadata por si cambió (idempotente)
            existing.client = item.get("client", existing.client)
            existing.industry = item.get("industry", existing.industry)
            existing.topic = item.get("topic", existing.topic)
            existing.year = item.get("year", existing.year)
            existing.metadata_json = item.get("metadata_json", existing.metadata_json)
            continue
        db.add(Credential(
            id=cred_id,
            client=item.get("client","Cliente"),
            industry=item.get("industry","industria_consumo_energia"),
            topic=item.get("topic","pmo"),
            year=item.get("year"),
            storage_path=item.get("storage_path",""),
            metadata_json=item.get("metadata_json", {}),
            is_active=True,
        ))
        inserted += 1
    db.commit()
    logger.info(f"Seed credenciales: {inserted} nuevas insertadas (total seed: {len(data)})")
    return inserted
