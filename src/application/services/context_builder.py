from src.domain.models.search import RetrievalResult
from src.config.rag_settings import RAGSettings


class ContextBuilder:
    def __init__(
        self,
        settings: RAGSettings,
        include_triples: bool = True,
        include_communities: bool = True,
    ):
        self._settings = settings
        self.include_triples = include_triples
        self.include_communities = include_communities

    def build(self, result: RetrievalResult) -> str:
        sections: list[str] = []

        if self.include_communities and result.communities:
            lines = ["=== ОБЗОР ПО ТЕМАМ ==="]
            for c in sorted(
                result.communities, key=lambda x: x.relevance_score, reverse=True
            ):
                lines.append(f"[Тема: {', '.join(c.key_entities[:5])}]\n{c.summary}")
            sections.append("\n\n".join(lines))

        if self.include_triples and result.triples:
            lines = ["=== ФАКТЫ ИЗ ГРАФА ЗНАНИЙ ==="]
            for t in result.triples:
                lines.append(
                    f"• {t.subject} ({t.subject_type}) —{t.predicate}→ {t.object} ({t.object_type})"
                )
            sections.append("\n".join(lines))

        if result.chunks:
            lines = ["=== РЕЛЕВАНТНЫЕ ФРАГМЕНТЫ ИЗ ДОКУМЕНТОВ ==="]
            budget = self._settings.max_context_chars - sum(len(s) for s in sections)
            used = 0
            for chunk in sorted(result.chunks, key=lambda c: c.score, reverse=True):
                if used + len(chunk.text) > budget:
                    break

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
