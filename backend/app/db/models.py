"""SQLAlchemy ORM models."""
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(50), default="consultant")  # consultant/manager/partner/admin
    hashed_password: Mapped[str] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    decks: Mapped[list["Deck"]] = relationship("Deck", back_populates="owner")


class Deck(Base):
    __tablename__ = "decks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    deck_type: Mapped[str] = mapped_column(String(50))  # proposal_commercial, proposal_technical, etc.
    topic: Mapped[str] = mapped_column(String(50))  # pmo, data_analytics, ia_genai, etc.
    industry: Mapped[str] = mapped_column(String(50))
    client_name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft/interviewing/researching/structuring/writing/visual/audit/blocked/ready/delivered
    deck_brief: Mapped[dict] = mapped_column(JSON, default=dict)
    research_brief: Mapped[dict] = mapped_column(JSON, default=dict)
    narrative_skeleton: Mapped[dict] = mapped_column(JSON, default=dict)
    slide_content: Mapped[dict] = mapped_column(JSON, default=dict)
    storage_path: Mapped[str] = mapped_column(String(500), default="")
    audit_status: Mapped[str] = mapped_column(String(50), default="pending")
    audit_report: Mapped[dict] = mapped_column(JSON, default=dict)
    review_consolidated: Mapped[str] = mapped_column(Text, default="")
    progress_step: Mapped[str] = mapped_column(String(50), default="")
    progress_percentage: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    owner: Mapped["User"] = relationship("User", back_populates="decks")


class Credential(Base):
    """Caso de éxito en la biblioteca."""
    __tablename__ = "credentials"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    client: Mapped[str] = mapped_column(String(200), index=True)
    industry: Mapped[str] = mapped_column(String(50), index=True)
    topic: Mapped[str] = mapped_column(String(50), index=True)
    year: Mapped[int] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
