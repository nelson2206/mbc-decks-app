"""Wrapper sobre los motores de generación de .pptx."""
import sys
from pathlib import Path
from app.core.config import settings

sys.path.insert(0, str(settings.plugin_path / "skills" / "generate-deck" / "scripts"))

try:
    from generate_pptx_v2 import generate_from_reference  # type: ignore
    from generate_pptx_v3 import generate_from_content    # type: ignore
except ImportError as e:
    raise ImportError(f"Generators not found: {e}")


def generate_deck(
    reference_pptx: str,
    edit_map: dict,
    output_path: str,
    verbose: bool = False,
) -> dict:
    """v2: copy & edit reference. Útil cuando hay un deck base bien estructurado."""
    return generate_from_reference(reference_pptx, edit_map, output_path, verbose=verbose)


def generate_deck_from_content(
    slide_content: dict,
    deck_brief: dict,
    output_path: str,
) -> str:
    """v3: build from scratch usando slide_content del A4. PREFERIDO para evitar contaminación."""
    return generate_from_content(slide_content, deck_brief, output_path)
