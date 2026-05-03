"""Knowledge base loader. Carga concepts.md + interview_questions.md por tema."""
from pathlib import Path
from typing import Optional
from app.core.config import settings


class KnowledgeBase:
    """Lazy-loaded conocimiento por tema."""

    def __init__(self):
        self._cache: dict[str, dict[str, str]] = {}

    def get(self, topic: str) -> dict[str, str]:
        """Return concepts.md, frameworks.md, interview_questions.md as a dict."""
        if topic in self._cache:
            return self._cache[topic]
        topic_dir = settings.knowledge_path / topic
        kb = {}
        for fname in ("concepts.md", "frameworks.md", "metrics.md", "interview_questions.md", "minsait_differentiators.md"):
            p = topic_dir / fname
            if p.exists():
                kb[fname.replace(".md", "")] = p.read_text(encoding="utf-8")
        self._cache[topic] = kb
        return kb

    def get_concepts(self, topic: str) -> str:
        return self.get(topic).get("concepts", "")

    def get_interview_questions(self, topic: str) -> str:
        return self.get(topic).get("interview_questions", "")

    def list_topics(self) -> list[str]:
        if not settings.knowledge_path.exists():
            return []
        return sorted([p.name for p in settings.knowledge_path.iterdir() if p.is_dir()])


knowledge = KnowledgeBase()
