from src.config.rag_settings import RAGSettings
from src.domain.models.search import RetrievalResult


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
            sections.append(self._build_communities_section(result.communities))

        if self.include_triples and result.triples:
            sections.append(self._build_triples_section(result.triples))

        if result.chunks:
            budget = self._settings.max_context_chars - sum(len(s) for s in sections)
            chunks_section = self._build_chunks_section(result.chunks, budget)
            if chunks_section:
                sections.append(chunks_section)

        return "\n\n".join(sections) if sections else "(контекст не найден)"

    def _build_communities_section(self, communities: list) -> str:
        lines = ["=== ОБЗОР ПО ТЕМАМ ==="]
        sorted_communities = sorted(communities, key=lambda x: x.relevance_score, reverse=True)
        # Устраняем PERF401: используем генератор списков + extend вместо append в цикле
        lines.extend([f"[Тема: {', '.join(c.key_entities[:5])}]\n{c.summary}" for c in sorted_communities])
        return "\n\n".join(lines)

    def _build_triples_section(self, triples: list) -> str:
        lines = ["=== ФАКТЫ ИЗ ГРАФА ЗНАНИЙ ==="]
        lines.extend(
            [f"• {t.subject} ({t.subject_type}) —{t.predicate}→ {t.object} ({t.object_type})" for t in triples],
        )
        return "\n".join(lines)

    def _build_chunks_section(self, chunks: list, budget: int) -> str | None:
        if budget <= 0:
            return None

        lines = ["=== РЕЛЕВАНТНЫЕ ФРАГМЕНТЫ ИЗ ДОКУМЕНТОВ ==="]
        used = 0

        for chunk in sorted(chunks, key=lambda c: c.score, reverse=True):
            if used + len(chunk.text) > budget:
                break

            src = chunk.source_filename or "Неизвестный_документ"
            pages_info = f"Стр. {chunk.start_page}"
            if chunk.start_page != chunk.end_page and chunk.end_page > 0:
                pages_info += f"-{chunk.end_page}"
            if chunk.start_page == 0:
                pages_info = "Стр. неизвестна"

            if chunk.headings:
                headings_path = " → ".join(chunk.headings)
                header = (
                    f"--- Фрагмент #{chunk.chunk_index} "
                    f"[Документ: {src}, {pages_info}, "
                    f'Заголовки: "{headings_path}"] ---'
                )
            else:
                header = f"--- Фрагмент #{chunk.chunk_index} [Документ: {src}, {pages_info}] ---"

            lines.append(f"{header}\n{chunk.text}")
            used += len(chunk.text)

        if len(lines) == 1:
            return None  # Если кроме заголовка "=== РЕЛЕВАНТНЫЕ ФРАГМЕНТЫ..." ничего не добавлено

        return "\n\n".join(lines)

    def get_stats(self, result: RetrievalResult) -> dict:
        return {
            "chunks_count": len(result.chunks),
            "triples_count": len(result.triples),
            "communities_count": len(result.communities),
            "metadata": result.metadata,
        }
