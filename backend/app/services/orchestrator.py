"""Orquestador multi-agente con tracking de progreso y manejo robusto de errores."""
from __future__ import annotations
import json
import logging
import traceback
from typing import Any

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.core.anthropic_client import claude
from app.core.config import settings
from app.db.models import Deck
from app.services.knowledge import knowledge

logger = logging.getLogger(__name__)


# Definición de los pasos del pipeline con su % de progreso
PIPELINE_STEPS = [
    ("researching",   "A2 Investigador",     10),
    ("structuring",   "A3 Estructurador",    25),
    ("writing",       "A4 Contenido",        50),
    ("visual",        "A5 Visual",           65),
    ("audit",         "A9 Auditor visual",   75),
    ("reviewing",     "A6/A7/A8 Revisores",  90),
    ("ready",         "Listo",               100),
]



def _check_cancelled(deck: Deck, db: Session) -> bool:
    """Refresca el deck desde la BD y retorna True si fue cancelado por el usuario."""
    db.refresh(deck)
    return deck.status == "cancelled"



def _extract_json(text: str) -> dict:
    """Extrae JSON de la respuesta del LLM, manejando ```json blocks, texto extra
    y JSON truncado (cierra strings/objetos/arrays incompletos best-effort)."""
    import re
    if not text:
        return {}
    # Strip ```json ... ``` markdown blocks
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        text = m.group(1).strip()
    text = text.strip()
    if not text.startswith('{'):
        try:
            start = text.index('{')
            text = text[start:]
        except ValueError:
            return {"raw": text}
    # Intentar parse directo
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Quitar trailing commas
    text2 = re.sub(r',(\s*[}\]])', r'\1', text)
    try:
        return json.loads(text2)
    except json.JSONDecodeError:
        pass
    # JSON truncado: cerrarlo best-effort.
    # Cuenta {, }, [, ], y comillas no escapadas para reconstruir el cierre.
    repaired = _repair_truncated_json(text)
    if repaired is not None:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass
    # Último recurso: guardar todo el raw (NO truncar a 5000)
    return {"raw": text}


def _repair_truncated_json(text: str) -> str | None:
    """Best-effort: cerrar un JSON cortado al final.
    Detecta strings sin cerrar, objetos/arrays abiertos y los completa."""
    in_string = False
    escape = False
    stack = []  # contains '{' or '['
    last_complete_end = -1
    for i, c in enumerate(text):
        if escape:
            escape = False
            continue
        if c == '\\':
            escape = True
            continue
        if c == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if c in '{[':
            stack.append(c)
        elif c == '}':
            if stack and stack[-1] == '{':
                stack.pop()
                if not stack:
                    last_complete_end = i
        elif c == ']':
            if stack and stack[-1] == '[':
                stack.pop()
                if not stack:
                    last_complete_end = i
    # Si llegamos al final con string abierta o stack pendiente, cerrar
    out = text
    if in_string:
        out += '"'
    # Quitar trailing comma antes de cerrar
    out = out.rstrip().rstrip(',')
    while stack:
        ch = stack.pop()
        out += '}' if ch == '{' else ']'
    return out if out != text else None


def _set_progress(deck: Deck, db: Session, step_key: str, label: str, pct: int):
    """Update progress in DB so frontend can show it."""
    deck.status = step_key
    deck.progress_step = label
    deck.progress_percentage = pct
    deck.last_error = ""
    db.commit()


def _set_error(deck: Deck, db: Session, step_label: str, exc: Exception):
    """Mark deck as errored with the failing step and message."""
    deck.status = "error"
    deck.progress_step = f"Error en {step_label}"
    deck.last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
    db.commit()
    logger.error(f"Pipeline error en {step_label}: {exc}\n{traceback.format_exc()}")


def _load_archetype(archetype_id: str) -> dict:
    path = settings.archetypes_path / f"{archetype_id}.json"
    if not path.exists():
        raise ValueError(f"Archetype {archetype_id} not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def run_research(deck: Deck, db: Session) -> dict:
    """A2 Researcher."""
    _set_progress(deck, db, "researching", "A2 Investigador", 10)
    brief = deck.deck_brief or {}
    user_message = (
        f"Genera un research_brief para una propuesta MBC.\n\n"
        f"Cliente: {deck.client_name}\nIndustria: {deck.industry}\nTema: {deck.topic}\n"
        f"Brief de la entrevista:\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
        f"Toda cifra debe llevar fuente o marcarse como [ESTIMACIÓN]."
    )
    output = claude.call_agent("researcher", user_message, max_tokens=4096)
    deck.research_brief = {"markdown": output}
    flag_modified(deck, "research_brief")
    db.commit()
    return deck.research_brief


def run_structure(deck: Deck, db: Session) -> dict:
    """A3 Structurer."""
    _set_progress(deck, db, "structuring", "A3 Estructurador", 25)
    archetype = _load_archetype(deck.deck_type)
    research = (deck.research_brief or {}).get("markdown", "")
    brief = deck.deck_brief or {}
    user_message = (
        f"Adapta el archetype al brief y produce narrative_skeleton.json.\n\n"
        f"Archetype:\n{json.dumps(archetype, ensure_ascii=False, indent=2)}\n\n"
        f"Brief:\n{json.dumps(brief, ensure_ascii=False, indent=2)}\n\n"
        f"Research:\n{research[:6000]}\n\nDevuelve JSON puro con cada slide adaptada."
    )
    output = claude.call_agent("structurer", user_message, max_tokens=4096)
    skeleton = _extract_json(output)
    deck.narrative_skeleton = skeleton
    flag_modified(deck, "narrative_skeleton")
    db.commit()
    return skeleton


def run_content(deck: Deck, db: Session) -> dict:
    """A4 Content."""
    _set_progress(deck, db, "writing", "A4 Contenido", 50)
    concepts = knowledge.get_concepts(deck.topic)
    skeleton = deck.narrative_skeleton or {}
    brief = deck.deck_brief or {}
    extra_context = (
        f"## Knowledge base — Tema: {deck.topic}\n\n{concepts[:6000]}"
        if concepts else ""
    )
    user_message = (
        f"Redacta el contenido final de cada slide.\n\n"
        f"Brief: {json.dumps(brief, ensure_ascii=False)[:3000]}\n\n"
        f"Esqueleto:\n{json.dumps(skeleton, ensure_ascii=False)[:8000]}\n\n"
        f"Devuelve JSON con clave por slide_order."
    )
    output = claude.call_agent("content", user_message,
                               extra_system_context=extra_context, max_tokens=16384)
    content = _extract_json(output)
    deck.slide_content = content
    flag_modified(deck, "slide_content")
    db.commit()
    return content


def run_review(deck: Deck, db: Session, agent_name: str) -> str:
    """A6/A7/A8 Reviewers (versión single-thread)."""
    snapshot = _deck_snapshot(deck)
    return _run_review_from_snapshot(snapshot, agent_name)


def _deck_snapshot(deck: Deck) -> dict:
    """Extrae los datos del deck a un dict plano para uso thread-safe."""
    return {
        "client_name": deck.client_name,
        "industry": deck.industry,
        "topic": deck.topic,
        "deck_brief": deck.deck_brief,
        "narrative_skeleton": deck.narrative_skeleton,
        "slide_content": deck.slide_content,
    }


def _run_review_from_snapshot(snap: dict, agent_name: str) -> str:
    """Ejecuta una review usando solo el dict plano (no toca SQLAlchemy)."""
    user_message = (
        f"Revisa el deck según tu rol ({agent_name}).\n\n"
        f"Cliente: {snap['client_name']} · Industria: {snap['industry']} · Tema: {snap['topic']}\n\n"
        f"Brief: {json.dumps(snap['deck_brief'], ensure_ascii=False)[:2000]}\n"
        f"Esqueleto: {json.dumps(snap['narrative_skeleton'], ensure_ascii=False)[:3000]}\n"
        f"Contenido: {json.dumps(snap['slide_content'], ensure_ascii=False)[:3000]}\n\n"
        f"Devuelve markdown estructurado con issues."
    )
    return claude.call_agent(agent_name, user_message, max_tokens=4096)


def run_full_pipeline(deck_id: str, db: Session, manager_loop: bool = True) -> Deck:
    """Pipeline completo con manejo de errores. Cada paso actualiza progreso en BD.
    
    Si manager_loop=True (default), después de A4 se corre el Manager review.
    Si encuentra issues críticos/altos, se re-ejecuta A4 (o A3) con instrucciones
    específicas del Manager. Máximo 2 iteraciones de fix para evitar loops infinitos.
    """
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise ValueError(f"Deck {deck_id} not found")

    logger.info(f"Pipeline arranca para deck {deck_id} (cliente: {deck.client_name})")
    # Reset error state
    deck.last_error = ""
    db.commit()

    if _check_cancelled(deck, db):
        return deck
    try:
        run_research(deck, db)
    except Exception as e:
        _set_error(deck, db, "A2 Investigador", e)
        return deck

    if _check_cancelled(deck, db):
        return deck
    try:
        run_structure(deck, db)
    except Exception as e:
        _set_error(deck, db, "A3 Estructurador", e)
        return deck

    if _check_cancelled(deck, db):
        return deck
    try:
        run_content(deck, db)
    except Exception as e:
        _set_error(deck, db, "A4 Contenido", e)
        return deck

    # NUEVO · Manager review loop (después de A4, antes del .pptx)
    if manager_loop:
        for iteration in range(2):  # max 2 iterations
            if _check_cancelled(deck, db):
                return deck
            try:
                verdict = run_manager_review(deck, db, iteration)
            except Exception as e:
                logger.warning(f"Manager review falló (iter {iteration}): {e}. Continuando sin fix.")
                break
            if verdict.get("verdict") == "approved" or not (verdict.get("critical_issues") or verdict.get("high_issues")):
                logger.info(f"Manager APROBÓ el deck en iteración {iteration}")
                break
            # Hay issues. Aplicar fixes
            try:
                run_fix_iteration(deck, db, verdict, iteration)
            except Exception as e:
                logger.warning(f"Fix iteration falló: {e}. Continuando con lo que hay.")
                break

    _set_progress(deck, db, "visual", "A5 Visual", 65)
    return deck


def run_manager_review(deck: Deck, db: Session, iteration: int = 0) -> dict:
    """A6 Manager review · corre DESPUÉS de A4 antes del .pptx.
    Devuelve un dict con verdict + listas de issues que el orquestador parsea.
    """
    _set_progress(deck, db, "writing", f"A6 Manager review (iter {iteration+1})", 60)
    snap = _deck_snapshot(deck)
    md = _run_review_from_snapshot(snap, "manager")
    # Guardar el markdown completo en review_consolidated para que el usuario lo vea
    deck.review_consolidated = (deck.review_consolidated or "") + (
        f"\n\n---\n\n# Manager iteración {iteration+1}\n\n{md}" if iteration > 0 else f"# Manager iteración 1\n\n{md}"
    )
    flag_modified(deck, "review_consolidated") if hasattr(deck, "review_consolidated") else None
    db.commit()
    # Extraer JSON estructurado del output
    verdict = _extract_json(md)
    if not verdict or "verdict" not in verdict:
        # Si no logró parsear, asumir approved para no atascarse
        return {"verdict": "approved", "critical_issues": [], "high_issues": []}
    return verdict


def run_fix_iteration(deck: Deck, db: Session, verdict: dict, iteration: int = 0):
    """Re-ejecuta A4 (o A3) con las instrucciones del Manager para corregir issues."""
    issues_a4 = [i for i in (verdict.get("critical_issues") or []) + (verdict.get("high_issues") or [])
                 if i.get("fix_route") == "A4"]
    issues_a3 = [i for i in (verdict.get("critical_issues") or []) + (verdict.get("high_issues") or [])
                 if i.get("fix_route") == "A3"]
    
    # A3 fix (si hay issues estructurales) — re-ejecutar A3 con feedback
    if issues_a3:
        _set_progress(deck, db, "structuring", f"A3 Re-estructurando · fix iter {iteration+1}", 55)
        feedback = "FEEDBACK DEL MANAGER PARA CORREGIR:\n" + "\n".join(
            f"- Slide {i.get('slide','?')} · {i.get('field','')}: {i.get('issue','')}. Acción: {i.get('instruction','')}"
            for i in issues_a3
        )
        skeleton = deck.narrative_skeleton or {}
        brief = deck.deck_brief or {}
        user_message = (
            f"Tu narrative_skeleton anterior tenía issues. Re-armalo aplicando las correcciones.\n\n"
            f"{feedback}\n\n"
            f"Brief: {json.dumps(brief, ensure_ascii=False)[:2000]}\n"
            f"Esqueleto previo: {json.dumps(skeleton, ensure_ascii=False)[:5000]}\n\n"
            f"Devuelve narrative_skeleton.json corregido."
        )
        output = claude.call_agent("structurer", user_message, max_tokens=8192)
        new_skel = _extract_json(output)
        if new_skel and "raw" not in new_skel:
            deck.narrative_skeleton = new_skel
            flag_modified(deck, "narrative_skeleton")
            db.commit()
        # Tras corregir esqueleto, re-correr A4 también
        run_content(deck, db)
        return
    
    # A4 fix (issues de contenido) — re-ejecutar A4 con feedback
    if issues_a4:
        _set_progress(deck, db, "writing", f"A4 Corrigiendo · fix iter {iteration+1}", 60)
        feedback = "FEEDBACK DEL MANAGER PARA CORREGIR:\n" + "\n".join(
            f"- Slide {i.get('slide','?')} · {i.get('field','')}: {i.get('issue','')}. Acción: {i.get('instruction','')}"
            for i in issues_a4
        )
        skeleton = deck.narrative_skeleton or {}
        brief = deck.deck_brief or {}
        slide_content = deck.slide_content or {}
        concepts = knowledge.get_concepts(deck.topic)
        extra_context = (f"## Knowledge base — Tema: {deck.topic}\n\n{concepts[:6000]}" if concepts else "")
        user_message = (
            f"El slide_content anterior tenía issues. Corrígelo aplicando los fixes.\n\n"
            f"{feedback}\n\n"
            f"slide_content actual: {json.dumps(slide_content, ensure_ascii=False)[:8000]}\n\n"
            f"Devuelve slide_content.json corregido (mismo formato {{slides:[...]}})."
        )
        output = claude.call_agent("content", user_message,
                                   extra_system_context=extra_context, max_tokens=16384)
        new_content = _extract_json(output)
        if new_content and "raw" not in new_content:
            deck.slide_content = new_content
            flag_modified(deck, "slide_content")
            db.commit()


def run_reviews(deck_id: str, db: Session, parallel: bool = True) -> dict[str, str]:
    """A6/A7/A8 Manager + 2 Socios. Por defecto en paralelo (3x más rápido)."""
    deck = db.query(Deck).filter(Deck.id == deck_id).first()
    if not deck:
        raise ValueError(f"Deck {deck_id} not found")
    _set_progress(deck, db, "reviewing", "A7/A8 Socios (paralelo)", 90)
    reviews = {}
    # Manager ya corrió DENTRO de run_full_pipeline (entre A4 y A5).
    # Acá solo Partner Consulting + Partner Tech sobre el .pptx final.
    agents = ("partner_consulting", "partner_tech")
    # Tomar un snapshot del deck ANTES de spawnar threads. Las propiedades
    # SQLAlchemy no son thread-safe; cada thread debe trabajar con datos planos.
    snap = _deck_snapshot(deck)
    try:
        if parallel:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_agent = {executor.submit(_run_review_from_snapshot, snap, a): a for a in agents}
                for future in future_to_agent:
                    agent = future_to_agent[future]
                    try:
                        reviews[agent] = future.result(timeout=120)
                    except Exception as e:
                        reviews[agent] = f"⚠ Error en {agent}: {str(e)[:200]}"
        else:
            for agent in agents:
                reviews[agent] = _run_review_from_snapshot(snap, agent)
        partners_block = "\n\n---\n\n".join(
            f"# {n}\n\n{md}" for n, md in reviews.items()
        )
        # Appendear a lo que el Manager ya escribió (no sobrescribir)
        deck.review_consolidated = (deck.review_consolidated or "") + "\n\n---\n\n" + partners_block
        flag_modified(deck, "review_consolidated") if hasattr(deck, "review_consolidated") else None
        db.commit()
    except Exception as e:
        _set_error(deck, db, "Revisores", e)
    return reviews
