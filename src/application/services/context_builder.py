"""
Сборщик контекста для LLM из RetrievalResult.
Отвечает за форматирование: чанки (с документами и страницами), тройки, community summaries.
"""

from src.domain.value_objects.search_context import RetrievalResult


class ContextBuilder:
    """Форматирует RetrievalResult → текстовый контекст для LLM."""

    def __init__(
        self,
        max_context_chars: int = 12_000,
        include_triples: bool = True,
        include_communities: bool = True,
    ):
        self.max_context_chars = max_context_chars
        self.include_triples = include_triples
        self.include_communities = include_communities

    def build(self, result: RetrievalResult) -> str:
        """Собирает контекст из всех источников."""
        sections: list[str] = []

        # 1. Community summaries (глобальный контекст — первым)
        if self.include_communities and result.communities:
            lines = ["=== ОБЗОР ПО ТЕМАМ ==="]
            for c in sorted(
                result.communities,
                key=lambda x: x.relevance_score,
                reverse=True,
            ):
                lines.append(f"[Тема: {', '.join(c.key_entities[:5])}]\n{c.summary}")
            sections.append("\n\n".join(lines))

        # 2. Тройки (структурированные факты)
        if self.include_triples and result.triples:
            lines = ["=== ФАКТЫ ИЗ ГРАФА ЗНАНИЙ ==="]
            for t in result.triples:
                lines.append(
                    f"• {t.subject} ({t.subject_type}) —{t.predicate}→ {t.object} ({t.object_type})"
                )
            sections.append("\n".join(lines))

        # 3. Чанки (текстовый контекст с указанием страниц)
        if result.chunks:
            lines = ["=== РЕЛЕВАНТНЫЕ ФРАГМЕНТЫ ИЗ ДОКУМЕНТОВ ==="]
            budget = self.max_context_chars - sum(len(s) for s in sections)
            used = 0
            for chunk in sorted(result.chunks, key=lambda c: c.score, reverse=True):
                if used + len(chunk.text) > budget:
                    break

                # Формируем источник со страницами
                src = chunk.source_filename or "Неизвестный_документ"
                pages_info = f"Стр. {chunk.start_page}"
                if chunk.start_page != chunk.end_page and chunk.end_page > 0:
                    pages_info += f"-{chunk.end_page}"
                if chunk.start_page == 0:
                    pages_info = "Стр. неизвестна"

                header = f"--- Фрагмент #{chunk.chunk_index} [Документ: {src}, {pages_info}] ---"
                lines.append(f"{header}\n{chunk.text}")
                used += len(chunk.text)

            sections.append("\n\n".join(lines))

        return "\n\n".join(sections) if sections else "(контекст не найден)"

    def get_stats(self, result: RetrievalResult) -> dict:
        return {
            "chunks_count": len(result.chunks),
            "triples_count": len(result.triples),
            "communities_count": len(result.communities),
            "metadata": result.metadata,
        }
