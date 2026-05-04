"""Wrapper sobre Anthropic Claude API con timeout + logging detallado."""
from __future__ import annotations
import base64
import logging
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from anthropic import Anthropic
from app.core.config import settings

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Wrapper sobre Anthropic SDK con timeout estricto y logging."""

    def __init__(self, api_key: Optional[str] = None):
        # Timeout explícito: 90s para evitar que requests se cuelguen indefinidamente
        self.client = Anthropic(
            api_key=api_key or settings.anthropic_api_key,
            timeout=httpx.Timeout(90.0, connect=10.0),
            max_retries=2,
        )
        self.prompts_dir = settings.prompts_path
        self._prompts_cache: dict[str, str] = {}

    def _load_prompt(self, agent_name: str) -> str:
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
        system = self._load_prompt(agent_name)
        if extra_system_context:
            system = f"{system}\n\n## Contexto adicional\n\n{extra_system_context}"

        if model is None:
            fast_agents = {"visual", "manager", "orchestrator", "visual_auditor"}
            model = settings.anthropic_model_fast if agent_name in fast_agents else settings.anthropic_model_main

        logger.info(f"[{agent_name}] Iniciando llamada a {model} · prompt {len(user_message)} chars · system {len(system)} chars · max_tokens {max_tokens}")
        t0 = time.time()
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_message}],
            )
            text = response.content[0].text
            elapsed = time.time() - t0
            logger.info(f"[{agent_name}] OK · {elapsed:.1f}s · output {len(text)} chars · tokens in/out {response.usage.input_tokens}/{response.usage.output_tokens}")
            return text
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"[{agent_name}] FAILED después de {elapsed:.1f}s · {type(e).__name__}: {str(e)[:300]}")
            raise

    def call_with_image(
        self,
        agent_name: str,
        user_message: str,
        image_bytes: bytes,
        media_type: str,
        max_tokens: int = 1024,
    ) -> str:
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


claude = ClaudeClient()
