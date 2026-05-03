"""Pydantic models para request/response de la API."""
from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field


# --- Auth ---
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    full_name: str
    role: str


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: str = "consultant"


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    class Config:
        from_attributes = True


# --- Deck wizard ---
class StartDeckRequest(BaseModel):
    deck_type: str  # proposal_commercial, proposal_technical, etc.
    topic: str  # pmo, data_analytics, ia_genai, ...
    industry: str  # industria_consumo_energia, servicios_financieros
    title_working: str
    client_name: str


class InterviewQuestion(BaseModel):
    block: str
    question_id: str
    question: str
    type: str  # text, single_choice, multi_choice
    options: Optional[list[str]] = None
    required: bool = True


class InterviewAnswer(BaseModel):
    question_id: str
    answer: Any  # string o list


class InterviewSubmit(BaseModel):
    deck_id: str
    answers: dict[str, Any]


class GenerateRequest(BaseModel):
    deck_id: str
    use_reference_deck_id: Optional[str] = None  # opcional: si elegir un deck de referencia específico
    skip_audit: bool = False


class AuditRequest(BaseModel):
    deck_id: str


class AuditFinding(BaseModel):
    image_id: str
    appears_in_slides: list[int]
    severity: str  # CRITICAL, WARNING, NEUTRAL, APPROVED
    category: str
    description: str
    recommendation: str
    block_delivery: bool


class AuditReport(BaseModel):
    deck_id: str
    audit_status: str  # PASSED, BLOCKED_RECOMMENDED, BLOCKED
    summary: dict
    findings: list[AuditFinding]


# --- Decks ---
class DeckOut(BaseModel):
    id: str
    title: str
    deck_type: str
    topic: str
    industry: str
    client_name: str
    status: str
    audit_status: str
    storage_path: str
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class DeckListItem(BaseModel):
    id: str
    title: str
    client_name: str
    topic: str
    status: str
    audit_status: str
    updated_at: datetime
    class Config:
        from_attributes = True


# --- Credentials ---
class CredentialOut(BaseModel):
    id: str
    client: str
    industry: str
    topic: str
    year: Optional[int]
    storage_path: str
    metadata_json: dict
    class Config:
        from_attributes = True


class CredentialSearchRequest(BaseModel):
    topic: Optional[str] = None
    industry: Optional[str] = None
    client: Optional[str] = None
    keyword: Optional[str] = None
