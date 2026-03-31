import logging
from src.domain.interfaces.services.synonym_resolver import ISynonymResolver
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.repositories.document_repository import IDocumentRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.models.nodes import InstanceNode
from src.domain.models.synonym import SynonymResolutionResult
from src.config.rag_settings import RAGSettings

logger = logging.getLogger(__name__)


class PostProcessingService:
    def __init__(
        self,
        instance_repo: IInstanceRepository,
        doc_repo: IDocumentRepository,
        synonym_resolver: ISynonymResolver,
        embedder: IEmbeddingService,
        settings: RAGSettings,
    ):
        self._instance_repo = instance_repo
        self._doc_repo = doc_repo
        self._synonym_resolver = synonym_resolver
        self._embedder = embedder
        self._settings = settings

    async def resolve_synonyms(
        self, doc_id: str, document_context: str = ""
    ) -> SynonymResolutionResult:
        instances = await self._instance_repo.get_instances_by_document(doc_id)
        if len(instances) < 2:
            return SynonymResolutionResult()

        chunks = await self._doc_repo.get_chunks_by_document(doc_id)
        limit = self._settings.post_process_chunks_limit
        length = self._settings.post_process_snippet_length
        text_snippets = "\n---\n".join(c.text[:length] for c in chunks[:limit])

        result = await self._synonym_resolver.find_synonym_groups(
            instances=instances,
            document_context=document_context,
            text_snippets=text_snippets,
        )

        if not result.groups:
            return result

        for group in result.groups:
            if len(group.instance_ids) < 2:
                continue

            canonical_id = group.instance_ids[0]
            alias_ids = group.instance_ids[1:]
            new_embedding = await self._embedder.embed_text(group.canonical_name)

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

        return result
