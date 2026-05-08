"""Test local del loop PM ↔ Manager McKinsey con llamadas REALES a Anthropic.

NO golpea Render · NO depende de la BD · solo lee fixture + llama Anthropic SDK.

Uso:
    export ANTHROPIC_API_KEY=sk-ant-...
    cd backend/  (o desde la raíz del repo)
    python scripts/local_qa/pm_test/run_pm_loop_local.py [fixture_path]

Default fixture: 01_belcorp_iagenai.json
Output: scripts/local_qa/pm_test/output/<fixture>_after_pm.pptx + report.json
"""
from __future__ import annotations
import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = REPO_ROOT / "backend" / "app" / "plugin_resources" / "skills" / "generate-deck" / "scripts"
PROMPTS_DIR = REPO_ROOT / "backend" / "app" / "plugin_resources" / "skills" / "generate-deck" / "prompts"
FIXTURES_DIR = REPO_ROOT / "scripts" / "local_qa" / "fixtures"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(SCRIPTS_DIR))

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY no está en el environment.")
    print("Export así: export ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

try:
    from anthropic import Anthropic
    import httpx
    from generate_pptx_v3 import generate_from_content
    from pptx import Presentation
except ImportError as e:
    print(f"ERROR importing: {e}")
    sys.exit(1)


client = Anthropic(timeout=httpx.Timeout(600.0, connect=15.0), max_retries=2)
SONNET = "claude-sonnet-4-6"
HAIKU = "claude-haiku-4-5-20251001"

# Tracker de tokens consumidos
TOKEN_USAGE = {"manager": [], "pm": [], "fixes": [], "total_in": 0, "total_out": 0}


def _load_prompt(name: str) -> str:
    return (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _call(model: str, system: str, user: str, max_tokens: int, label: str, use_stream: bool = False) -> tuple[str, dict]:
    """Wrapper de llamada a Anthropic con logging y tracking de tokens."""
    t0 = time.time()
    try:
        if use_stream or max_tokens > 4096:
            with client.messages.stream(model=model, max_tokens=max_tokens, system=system,
                                          messages=[{"role": "user", "content": user}]) as stream:
                parts = []
                for chunk in stream.text_stream:
                    parts.append(chunk)
                text = "".join(parts)
                final = stream.get_final_message()
                in_tok = final.usage.input_tokens
                out_tok = final.usage.output_tokens
        else:
            resp = client.messages.create(model=model, max_tokens=max_tokens, system=system,
                                           messages=[{"role": "user", "content": user}])
            text = resp.content[0].text
            in_tok = resp.usage.input_tokens
            out_tok = resp.usage.output_tokens
    except Exception as e:
        print(f"  ❌ ERROR en {label}: {type(e).__name__}: {e}")
        raise
    elapsed = time.time() - t0
    TOKEN_USAGE["total_in"] += in_tok
    TOKEN_USAGE["total_out"] += out_tok
    info = {"label": label, "model": model.split("-")[-1], "elapsed_s": round(elapsed, 1),
            "in_tokens": in_tok, "out_tokens": out_tok}
    print(f"  ✓ {label}: {info['model']} · {elapsed:.1f}s · in {in_tok} · out {out_tok}")
    return text, info


def _extract_json(text: str) -> dict:
    """Reusa la lógica del orchestrator: strip ```json blocks + repair."""
    import re
    if not text:
        return {}
    m = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if m:
        text = m.group(1).strip()
    text = text.strip()
    if not text.startswith('{'):
        try:
            text = text[text.index('{'):]
        except ValueError:
            return {"raw": text}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        text2 = re.sub(r',(\s*[}\]])', r'\1', text)
        try:
            return json.loads(text2)
        except json.JSONDecodeError:
            return {"raw": text[:5000]}


def run_manager_review(slide_content: dict, deck_brief: dict, iteration: int) -> tuple[dict, str]:
    """A6 Manager McKinsey (Sonnet)."""
    print(f"\n┌─ A6 Manager McKinsey · iter {iteration+1} ──────────────")
    sys = _load_prompt("manager")
    user = (
        f"Cliente: {deck_brief.get('client',{}).get('name_commercial','-')}\n"
        f"Tema: {deck_brief.get('topic','-')}\n\n"
        f"slide_content actual:\n{json.dumps(slide_content, ensure_ascii=False)[:6000]}\n\n"
        f"Devuelve tu análisis: párrafo + JSON al final."
    )
    text, info = _call(SONNET, sys, user, 4096, f"manager_iter_{iteration+1}")
    TOKEN_USAGE["manager"].append(info)
    verdict = _extract_json(text)
    print(f"└─ verdict: {verdict.get('verdict','?')} · approved: {verdict.get('approved', False)}")
    print(f"   blockers: {len(verdict.get('blockers',[]))} · high: {len(verdict.get('high_issues',[]))}")
    return verdict, text


def run_pm_planning(verdict: dict, slide_content: dict, history: list, iteration: int) -> dict:
    """A0 Project Manager (Haiku)."""
    print(f"\n┌─ A0 Project Manager · iter {iteration+1} ──────────────")
    sys = _load_prompt("project_manager")
    user = (
        f"Iteración {iteration+1} de 2.\n\n"
        f"VEREDICTO MANAGER:\n{json.dumps(verdict, ensure_ascii=False)[:5000]}\n\n"
        f"slide_content actual (preview):\n{json.dumps(slide_content, ensure_ascii=False)[:3000]}\n\n"
        f"HISTORIA: {json.dumps(history, ensure_ascii=False)[:2000] if history else '(primera iteración)'}\n\n"
        f"Devuelve PLAN como JSON estricto."
    )
    text, info = _call(HAIKU, sys, user, 2048, f"pm_iter_{iteration+1}")
    TOKEN_USAGE["pm"].append(info)
    plan = _extract_json(text)
    print(f"└─ plan: {len(plan.get('fix_plan',[]))} steps · escalate: {plan.get('escalate_to_user',False)}")
    return plan


def run_fix_step(step: dict, slide_content: dict, deck_brief: dict, iteration: int) -> dict:
    """Ejecuta un fix step: llama A2/A3/A4 según el agent del step."""
    agent = (step.get("agent") or "").upper()
    instruction = step.get("instruction", "")
    scope = step.get("scope", "")
    blocks = step.get("blocks_slides", [])
    print(f"\n┌─ Step {step.get('step')} · {agent} · {scope[:60]}")

    if agent == "A4":
        slides = slide_content.get("slides", [])
        target = [s for s in slides if s.get("order") in blocks] if blocks else slides
        sys = _load_prompt("content")
        user = (
            f"FIX REQUEST DEL PM (cambio puntual SOLO en slides {blocks}):\n\n"
            f"Scope: {scope}\nInstrucción: {instruction}\n\n"
            f"Slides afectados:\n{json.dumps(target, ensure_ascii=False)[:5000]}\n\n"
            f"Devuelve {{\"slides\":[...]}} con SOLO esos slides corregidos."
        )
        text, info = _call(SONNET, sys, user, 8192, f"fix_A4_step{step.get('step')}", use_stream=True)
        TOKEN_USAGE["fixes"].append(info)
        fixed = _extract_json(text)
        if fixed and "slides" in fixed:
            fixed_by_order = {s.get("order"): s for s in fixed["slides"]}
            slide_content["slides"] = [fixed_by_order.get(s.get("order"), s) for s in slides]
            print(f"└─ A4 fix OK · {len(fixed.get('slides',[]))} slides actualizados")
        else:
            print(f"└─ A4 fix devolvió JSON inválido (raw key); skip")
    elif agent == "A2":
        sys = _load_prompt("researcher")
        user = (
            f"FIX REQUEST DEL PM:\nScope: {scope}\nInstrucción: {instruction}\n"
            f"Cliente: {deck_brief.get('client',{}).get('name_commercial','-')}\n"
            f"Devuelve markdown corto con la respuesta puntual."
        )
        text, info = _call(SONNET, sys, user, 2048, f"fix_A2_step{step.get('step')}")
        TOKEN_USAGE["fixes"].append(info)
        slide_content.setdefault("_pm_research_fixes", []).append({"scope": scope, "answer": text})
        print(f"└─ A2 fix OK")
    elif agent == "A3":
        print(f"└─ A3 fix omitido (no relevante a este test)")
    else:
        print(f"└─ Agent {agent} no soportado, skip")
    return slide_content


def main():
    fixture_name = sys.argv[1] if len(sys.argv) > 1 else "01_belcorp_iagenai.json"
    fp = FIXTURES_DIR / fixture_name
    if not fp.exists():
        print(f"Fixture no encontrado: {fp}")
        sys.exit(1)

    print("=" * 70)
    print(f"  Test local PM↔Manager · fixture: {fixture_name}")
    print("=" * 70)

    fixture = json.loads(fp.read_text())
    meta = fixture.pop("_meta", {})
    deck_brief = {
        "client": {"name_commercial": meta.get("client", "Cliente")},
        "topic": meta.get("topic", "pmo"),
        "deck": {"title_working": meta.get("case_id", "")},
    }
    slide_content = fixture
    print(f"  Cliente: {deck_brief['client']['name_commercial']}")
    print(f"  Tema:    {deck_brief['topic']}")
    print(f"  Slides:  {len(slide_content.get('slides',[]))}")

    history: list = []
    final_verdict = None
    for iteration in range(2):
        # Manager review
        verdict, _ = run_manager_review(slide_content, deck_brief, iteration)
        final_verdict = verdict

        if verdict.get("approved") or verdict.get("verdict") == "approved":
            print(f"\n✅ Manager APROBÓ en iter {iteration+1}\n")
            break
        if not (verdict.get("blockers") or verdict.get("high_issues")):
            print(f"\n✅ Sin blockers · saliendo del loop\n")
            break

        # PM planea
        plan = run_pm_planning(verdict, slide_content, history, iteration)
        if plan.get("escalate_to_user") or not plan.get("fix_plan"):
            print(f"\n⚠ PM escaló: {plan.get('skip_reason','sin plan')}\n")
            break

        # Ejecuta cada step
        executed = []
        for step in plan["fix_plan"][:5]:
            try:
                slide_content = run_fix_step(step, slide_content, deck_brief, iteration)
                executed.append({"step": step.get("step"), "agent": step.get("agent"), "status": "ok"})
            except Exception as e:
                executed.append({"step": step.get("step"), "agent": step.get("agent"), "status": "error", "err": str(e)[:200]})

        history.append({"iteration": iteration+1,
                        "verdict_summary": plan.get("verdict_summary",""),
                        "steps_executed": executed})

    # Generar .pptx final
    out_pptx = OUTPUT_DIR / f"{fixture_name.replace('.json','')}_after_pm.pptx"
    generate_from_content(slide_content, deck_brief, str(out_pptx))

    # Reporte
    p = Presentation(str(out_pptx))
    n_slides = len(list(p.slides))

    report = {
        "fixture": fixture_name,
        "iterations_run": len(history) + (1 if final_verdict else 0),
        "final_verdict": (final_verdict or {}).get("verdict", "unknown"),
        "approved": (final_verdict or {}).get("approved", False),
        "history": history,
        "slides_in_output": n_slides,
        "output_pptx": str(out_pptx),
        "tokens": {
            "manager_calls": len(TOKEN_USAGE["manager"]),
            "pm_calls": len(TOKEN_USAGE["pm"]),
            "fix_calls": len(TOKEN_USAGE["fixes"]),
            "total_input": TOKEN_USAGE["total_in"],
            "total_output": TOKEN_USAGE["total_out"],
            "estimated_cost_usd": round(
                TOKEN_USAGE["total_in"] / 1_000_000 * 3.0
                + TOKEN_USAGE["total_out"] / 1_000_000 * 15.0, 4
            ),
        },
    }
    rp = OUTPUT_DIR / f"{fixture_name.replace('.json','')}_report.json"
    rp.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    print("\n" + "=" * 70)
    print("  RESUMEN")
    print("=" * 70)
    print(f"  Iteraciones: {report['iterations_run']}")
    print(f"  Veredicto final: {report['final_verdict']} · approved: {report['approved']}")
    print(f"  Slides en output: {n_slides}")
    print(f"  Tokens IN/OUT: {TOKEN_USAGE['total_in']:,} / {TOKEN_USAGE['total_out']:,}")
    print(f"  Costo aprox: ${report['tokens']['estimated_cost_usd']:.3f} USD")
    print(f"  📁 .pptx: {out_pptx}")
    print(f"  📊 report: {rp}")


if __name__ == "__main__":
    main()
