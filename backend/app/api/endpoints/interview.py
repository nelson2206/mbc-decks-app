"""Endpoints de entrevista guiada adaptativa por tema."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.models import InterviewSubmit
from app.db.session import get_db
from app.db.models import User, Deck
from app.services.knowledge import knowledge
from app.services.topic_labels import label_for

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.get("/topics")
def list_topics(current: User = Depends(get_current_user)):
    """Lista los temas con knowledge base disponible (con labels legibles)."""
    ids = knowledge.list_topics()
    return {"topics": [{"id": t, "label": label_for(t)} for t in ids]}


@router.get("/{deck_id}/questions")
def get_questions(deck_id: str, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Devuelve el guión de entrevista adaptativo para un deck (bloques 0-6 + bloque 7 del tema)."""
    deck = db.query(Deck).filter(Deck.id == deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")

    base_blocks = _BASE_INTERVIEW_BLOCKS
    topic_specific_md = knowledge.get_interview_questions(deck.topic) or ""
    return {
        "deck_id": deck_id,
        "topic": deck.topic,
        "base_blocks": base_blocks,
        "topic_specific_markdown": topic_specific_md,
    }


@router.post("/submit", status_code=status.HTTP_200_OK)
def submit_answers(req: InterviewSubmit, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    deck = db.query(Deck).filter(Deck.id == req.deck_id, Deck.owner_id == current.id).first()
    if not deck:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Deck no encontrado")

    brief = deck.deck_brief or {}
    brief["interview_answers"] = req.answers
    deck.deck_brief = brief
    deck.status = "interviewing_done"
    db.commit()
    return {"deck_id": deck.id, "status": deck.status, "answers_count": len(req.answers)}


# Bloques base (extraídos del interview.md). Para el MVP se hardcodean aquí; el bloque 7 viene del KB.
_BASE_INTERVIEW_BLOCKS = [
    {
        "block": "0_orientacion",
        "title": "Orientación del deck",
        "questions": [
            {"id": "P0_2", "question": "Tema/título de trabajo del deck", "type": "text"},
            {"id": "P0_3", "question": "Cliente / audiencia objetivo", "type": "text"},
            {"id": "P0_4", "question": "Fecha objetivo de entrega", "type": "date"},
            {"id": "P0_5", "question": "Longitud objetivo", "type": "single_choice",
             "options": ["ejecutiva (≤20 slides)", "estándar (30-45)", "extensa (50+)"]},
        ],
    },
    {
        "block": "1_cliente",
        "title": "Cliente y co-branding",
        "questions": [
            {"id": "P1_3", "question": "Logo del cliente (subir archivo)", "type": "file"},
            {"id": "P1_4", "question": "Color institucional primario (HEX o nombre)", "type": "text"},
            {"id": "P1_5", "question": "Imagen para portada o contexto (subir archivo)", "type": "file"},
            {"id": "P1_6", "question": "Persona de contacto (nombre + cargo)", "type": "text"},
        ],
    },
    {
        "block": "2_contexto",
        "title": "Contexto y reto",
        "questions": [
            {"id": "P2_1", "question": "Situación actual del cliente (3-5 frases)", "type": "textarea"},
            {"id": "P2_2", "question": "Tres dolores principales (uno por línea)", "type": "textarea"},
            {"id": "P2_3", "question": "Iniciativas previas y por qué no funcionaron (opcional)", "type": "textarea"},
            {"id": "P2_4", "question": "Evento detonante detrás del pedido", "type": "text"},
            {"id": "P2_5", "question": "Sponsor del cliente y qué necesita demostrar", "type": "textarea"},
        ],
    },
    {
        "block": "3_propuesta_valor",
        "title": "Propuesta de valor",
        "questions": [
            {"id": "P3_1", "question": "Answer first: ¿qué proponemos hacer en 1 frase?", "type": "text"},
            {"id": "P3_2", "question": "Tres pilares de la propuesta", "type": "textarea"},
            {"id": "P3_3", "question": "Resultados esperados (con métricas si las hay)", "type": "textarea"},
            {"id": "P3_4", "question": "Por qué Minsait y no un competidor (1-3 razones)", "type": "textarea"},
            {"id": "P3_5", "question": "Casos de éxito relevantes a citar", "type": "textarea"},
        ],
    },
    {
        "block": "4_metodologia",
        "title": "Metodología y ejecución",
        "questions": [
            {"id": "P4_1", "question": "Número de fases y entregable de cada una", "type": "textarea"},
            {"id": "P4_2", "question": "Duración total y por fase", "type": "text"},
            {"id": "P4_3", "question": "Equipo Minsait propuesto (Partner, Manager, Consultores...)", "type": "textarea"},
            {"id": "P4_4", "question": "Inputs / dependencias del cliente", "type": "textarea"},
            {"id": "P4_5", "question": "Riesgos principales y mitigación", "type": "textarea"},
        ],
    },
    {
        "block": "5_inversion",
        "title": "Inversión",
        "questions": [
            {"id": "P5_1", "question": "Honorarios totales (monto + moneda)", "type": "text"},
            {"id": "P5_2", "question": "Modalidad de facturación", "type": "single_choice",
             "options": ["por fase", "mensual", "por hito", "ad-hoc", "híbrida"]},
            {"id": "P5_3", "question": "Condiciones comerciales (validez, gastos no incluidos)", "type": "textarea"},
        ],
    },
]
