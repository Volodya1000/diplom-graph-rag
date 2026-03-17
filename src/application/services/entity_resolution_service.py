import uuid
from typing import List, Tuple
from src.domain.models import RawExtractedEntity, InstanceNode, SchemaClass, SchemaStatus
from src.domain.resolution_rules import EntityResolutionMatcher
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService


class EntityResolutionOrchestrator:
    def __init__(self, repo: IGraphRepository, embedder: IEmbeddingService, matcher: EntityResolutionMatcher):
        self.repo = repo
        self.embedder = embedder
        self.matcher = matcher

    async def process_entities(
            self, raw_entities: List[RawExtractedEntity], current_tbox: List[SchemaClass], chunk_id: str
    ) -> Tuple[List[InstanceNode], List[SchemaClass]]:

        instances = []
        new_classes = []
        tbox_names = {c.name.lower() for c in current_tbox}

        for raw in raw_entities:
            if raw.type.lower() not in tbox_names:
                new_classes.append(SchemaClass(name=raw.type, status=SchemaStatus.DRAFT))
                tbox_names.add(raw.type.lower())

            embedding = await self.embedder.embed_text(raw.name)
            candidates = await self.repo.find_candidates_by_vector(embedding)
            match_id = self.matcher.find_best_match(raw, candidates)

            inst = InstanceNode(
                instance_id=match_id if match_id else str(uuid.uuid4()),  # Генерируем новый ID если match_id=None
                name=raw.name,
                class_name=raw.type,
                chunk_id=chunk_id,
                embedding=embedding
            )
            instances.append(inst)

        return instances, new_classes