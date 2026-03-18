"""
Постобработка документа: synonym resolution + merge.

Исправление: передаём фрагменты текста для контекста.
"""

import logging

from src.domain.interfaces.services.synonym_resolver import ISynonymResolver
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.graph_components.nodes import InstanceNode
from src.domain.value_objects.synonym_group import SynonymResolutionResult

logger = logging.getLogger(__name__)


class PostProcessingService:
    def __init__(
        self,
        instance_repo: IInstanceRepository,
        doc_repo: IDocumentRepository,
        synonym_resolver: ISynonymResolver,
        embedder: IEmbeddingService,
    ):
        self._instance_repo = instance_repo
        self._doc_repo = doc_repo
        self._synonym_resolver = synonym_resolver
        self._embedder = embedder

    async def resolve_synonyms(
        self,
        doc_id: str,
        document_context: str = "",
    ) -> SynonymResolutionResult:
        # 1. Все сущности документа
        instances = await self._instance_repo.get_instances_by_document(
            doc_id,
        )
        if len(instances) < 2:
            logger.info("⏭️ Менее 2 сущностей — пропуск synonym resolution")
            return SynonymResolutionResult()

        # 2. Фрагменты текста для контекста
        chunks = await self._doc_repo.get_chunks_by_document(doc_id)
        text_snippets = "\n---\n".join(
            c.text[:300] for c in chunks[:6]
        )

        logger.info(
            f"🔍 Post-processing: {len(instances)} entities, "
            f"{len(chunks)} chunks in doc {doc_id[:8]}…"
        )

        # 3. LLM анализ
        result = await self._synonym_resolver.find_synonym_groups(
            instances=instances,
            document_context=document_context,
            text_snippets=text_snippets,
        )

        if not result.groups:
            logger.info("✅ Синонимов не найдено")
            return result

        # 4. Merge каждой группы
        for group in result.groups:
            if len(group.instance_ids) < 2:
                continue

            canonical_id = group.instance_ids[0]
            alias_ids = group.instance_ids[1:]

            new_embedding = await self._embedder.embed_text(
                group.canonical_name,
            )

            logger.info(
                f"🔗 Merging: «{group.canonical_name}» "
                f"← {group.aliases} | reason: {group.reason}"
            )

            await self._instance_repo.merge_instances(
                canonical_id=canonical_id,
                canonical_name=group.canonical_name,
                alias_ids=alias_ids,
                aliases=group.aliases,
            )

            updated = InstanceNode(
                instance_id=canonical_id,
                name=group.canonical_name,
                class_name=group.canonical_type,
                chunk_id="",
                embedding=new_embedding,
            )
            await self._instance_repo.save_instance(updated)

        logger.info(
            f"✅ Synonym resolution: "
            f"merged={result.merged_count}, "
            f"kept={result.kept_count}, "
            f"groups={len(result.groups)}"
        )
        return result