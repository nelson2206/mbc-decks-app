"""Wrapper sobre generate_pptx_v2.py para usar desde el backend."""
import sys
from pathlib import Path
from app.core.config import settings

sys.path.insert(0, str(settings.plugin_path / "skills" / "generate-deck" / "scripts"))

try:
    from generate_pptx_v2 import generate_from_reference  # type: ignore
except ImportError as e:
    raise ImportError(f"generate_pptx_v2.py no encontrado: {e}")


def generate_deck(
    reference_pptx: str,
    edit_map: dict,
    output_path: str,
    verbose: bool = False,
) -> dict:
    """Genera un .pptx aplicando edit_map sobre reference_pptx."""
    return generate_from_reference(reference_pptx, edit_map, output_path, verbose=verbose)
