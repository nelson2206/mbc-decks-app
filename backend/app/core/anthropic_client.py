"""Wrapper sobre Anthropic Claude API.

Centraliza llamadas a Claude para los 9 agentes del sistema multi-agente.
Cada agente tiene su prompt de sistema cargado desde plugin_resources/skills/generate-deck/prompts/.
"""
from __future__ import annotations
import base64
from pathlib import Path
from typing import Any, Optional

from anthropic import Anthropic
from app.core.config import settings


class ClaudeClient:
    """Wrapper sobre Anthropic SDK con gestión de prompts y modelos por agente."""

    def __init__(self, api_key: Optional[str] = None):
        self.client = Anthropic(api_key=api_key or settings.anthropic_api_key)
        self.prompts_dir = settings.prompts_path
        self._prompts_cache: dict[str, str] = {}

    def _load_prompt(self, agent_name: str) -> str:
        """Load system prompt from prompts/<agent>.md."""
        if agent_name in self._prompts_cache:
            return self._prompts_cache[agent_name]
        path = self.prompts_dir / f"{agent_name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt for {agent_name} not found at {path}")
        prompt = path.read_text(encoding="utf-8")
        self._prompts_cache[agent_name] = prompt
        return prompt

    def call_agent(
        self,
        agent_name: str,
        user_message: str,
        model: Optional[str] = None,
        max_tokens: int = 4096,
        extra_system_context: Optional[str] = None,
    ) -> str:
        """Invoke a specific agent with its system prompt."""
        system = self._load_prompt(agent_name)
        if extra_system_context:
            system = f"{system}\n\n## Contexto adicional\n\n{extra_system_context}"

        # Modelo por agente: agentes "pensantes" usan main, "operativos" usan fast
        if model is None:
            fast_agents = {"visual", "manager", "orchestrator", "visual_auditor"}
            model = settings.anthropic_model_fast if agent_name in fast_agents else settings.anthropic_model_main

        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    def call_with_image(
        self,
        agent_name: str,
        user_message: str,
        image_bytes: bytes,
        media_type: str,
        max_tokens: int = 1024,
    ) -> str:
        """Invoke an agent passing an image (used for A9 Visual Auditor with Claude Vision)."""
        system = self._load_prompt(agent_name)
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = self.client.messages.create(
            model=settings.anthropic_model_main,
            max_tokens=max_tokens,
            system=system,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                    {"type": "text", "text": user_message},
                ],
            }],
        )
        return response.content[0].text


# Singleton
claude = ClaudeClient()
