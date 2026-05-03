"""Wrapper sobre image_auditor.py del plugin para uso desde el backend."""
import sys
from pathlib import Path
from typing import Optional
from app.core.config import settings

# Inyectar el path del plugin para importar image_auditor
sys.path.insert(0, str(settings.plugin_path / "skills" / "generate-deck" / "scripts"))

try:
    from image_auditor import run_audit, render_md_report  # type: ignore
except ImportError as e:
    raise ImportError(
        f"image_auditor.py no encontrado. Asegúrate de copiar el plugin a "
        f"{settings.plugin_path}. Error: {e}"
    )


def audit_pptx(pptx_path: str, client_name: str, industry: str, cache_path: Optional[str] = None) -> dict:
    """Audit a deck and return the structured report dict."""
    return run_audit(pptx_path, client_name, industry, cache_path)


def render_report_md(report: dict) -> str:
    return render_md_report(report)
