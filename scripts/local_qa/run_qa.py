"""
Agente QA local para v3 generator.

Ejecuta TODOS los fixtures del folder fixtures/ a través de generate_pptx_v3,
valida estructuralmente cada .pptx generado y reporta pass/fail.

Uso:
    cd backend/  (o desde la raíz del repo)
    python scripts/local_qa/run_qa.py

NO consume tokens de API. Solo verifica el v3 generator y la pipeline visual.
"""
from __future__ import annotations
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "backend" / "app" / "plugin_resources" / "skills" / "generate-deck" / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
OUTPUT_DIR = REPO_ROOT / "scripts" / "local_qa" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from generate_pptx_v3 import generate_from_content
    from pptx import Presentation
except ImportError as e:
    print(f"ERROR importing: {e}")
    print(f"Verifica que python-pptx esté instalado: pip install python-pptx")
    sys.exit(1)


@dataclass
class TestResult:
    case_id: str
    passed: bool
    duration_s: float
    slides_generated: int
    slides_with_zero_shapes: int
    issues: list[str] = field(default_factory=list)
    components_found: dict[str, int] = field(default_factory=dict)
    output_path: str = ""


def validate_pptx(pptx_path: Path, meta: dict) -> TestResult:
    """Valida que el .pptx generado cumpla con las expectativas del fixture."""
    result = TestResult(
        case_id=meta["case_id"],
        passed=True,
        duration_s=0.0,
        slides_generated=0,
        slides_with_zero_shapes=0,
        output_path=str(pptx_path),
    )
    p = Presentation(str(pptx_path))
    slides = list(p.slides)
    result.slides_generated = len(slides)

    expected_min = meta.get("expected_min_slides", 0)
    if result.slides_generated < expected_min:
        result.issues.append(
            f"Slides generadas ({result.slides_generated}) < esperado mínimo ({expected_min})"
        )
        result.passed = False

    # Contar slides vacías y verificar shapes/textos
    for i, sl in enumerate(slides):
        n_shapes = len(sl.shapes)
        if n_shapes == 0:
            result.slides_with_zero_shapes += 1
            result.issues.append(f"Slide [{i+1}] tiene 0 shapes (vacía)")

        # Verificar si tiene algún texto significativo
        has_text = False
        for sh in sl.shapes:
            if sh.has_text_frame and sh.text_frame.text.strip():
                has_text = True
                break
        if not has_text and n_shapes > 0:
            result.issues.append(f"Slide [{i+1}] tiene shapes pero sin texto")

    if result.slides_with_zero_shapes > 0:
        result.passed = False

    # Verificar componentes ricos
    must_have = meta.get("must_have_components", [])
    components_count = {c: 0 for c in must_have}
    # Esto es heurístico: contamos shapes/tablas en el output
    for sl in slides:
        for sh in sl.shapes:
            try:
                if sh.has_table:
                    components_count.setdefault("table", 0)
                    components_count["table"] += 1
            except Exception:
                pass
    result.components_found = components_count

    for comp in must_have:
        if comp == "table" and components_count.get("table", 0) == 0:
            result.issues.append(f"Falta componente esperado: {comp}")
            result.passed = False
        # Para otros tipos (comparison, process_steps, key_metric, quote)
        # no podemos detectarlos directamente del .pptx, son shapes regulares.
        # Confiamos en que si el fixture los tiene en el JSON, v3 los renderea.

    return result


def run_one(fixture_path: Path) -> TestResult:
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    meta = fixture.get("_meta", {})
    case_id = meta.get("case_id", fixture_path.stem)

    out_pptx = OUTPUT_DIR / f"{case_id}.pptx"

    deck_brief = {
        "client": {"name_commercial": meta.get("client", "Cliente Test")},
        "deck": {"title_working": case_id},
        "industry": meta.get("industry", "all"),
        "topic": meta.get("topic", "pmo"),
    }

    t0 = time.time()
    try:
        generate_from_content(fixture, deck_brief, str(out_pptx))
    except Exception as e:
        return TestResult(
            case_id=case_id,
            passed=False,
            duration_s=time.time() - t0,
            slides_generated=0,
            slides_with_zero_shapes=0,
            issues=[f"Generación falló: {type(e).__name__}: {e}"],
        )

    result = validate_pptx(out_pptx, meta)
    result.duration_s = time.time() - t0
    return result


def main():
    print("=" * 70)
    print("  MBC Decks · QA local del v3 generator")
    print("=" * 70)

    fixtures = sorted(FIXTURES_DIR.glob("*.json"))
    if not fixtures:
        print(f"No se encontraron fixtures en {FIXTURES_DIR}")
        sys.exit(1)

    print(f"\nFixtures encontrados: {len(fixtures)}")
    for f in fixtures:
        print(f"  · {f.name}")

    print("\n" + "─" * 70)
    print("  Ejecutando...")
    print("─" * 70)

    results: list[TestResult] = []
    for f in fixtures:
        print(f"\n▶ {f.stem} ...", end=" ", flush=True)
        r = run_one(f)
        results.append(r)
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(f"{status} · {r.duration_s:.2f}s · {r.slides_generated} slides")
        if r.issues:
            for issue in r.issues[:3]:
                print(f"    ⚠ {issue}")

    # Reporte final
    print("\n" + "=" * 70)
    print("  RESUMEN")
    print("=" * 70)
    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total_time = sum(r.duration_s for r in results)
    print(f"  Total: {len(results)}  ·  Pass: {passed}  ·  Fail: {failed}")
    print(f"  Tiempo total: {total_time:.2f}s")
    print(f"  Output dir: {OUTPUT_DIR}")

    print("\nDetalle por test:")
    for r in results:
        icon = "✅" if r.passed else "❌"
        print(f"  {icon} {r.case_id:30s} · {r.slides_generated:2} slides · {r.duration_s:.2f}s")
        if not r.passed:
            for issue in r.issues:
                print(f"      ⚠ {issue}")

    # Reporte JSON
    report_path = OUTPUT_DIR / "qa_report.json"
    report = {
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "total_time_s": total_time,
        },
        "results": [
            {
                "case_id": r.case_id,
                "passed": r.passed,
                "duration_s": round(r.duration_s, 3),
                "slides_generated": r.slides_generated,
                "slides_with_zero_shapes": r.slides_with_zero_shapes,
                "issues": r.issues,
                "components_found": r.components_found,
                "output_path": r.output_path,
            }
            for r in results
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📊 Reporte JSON: {report_path}")
    print(f"📁 .pptx generados: {OUTPUT_DIR}")
    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
