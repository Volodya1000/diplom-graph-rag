"""
Оркестратор Entity Resolution + валидация троек по схеме.
"""

import uuid
import logging
from typing import Dict, List, Optional, Tuple

from src.domain.models import (
    ExtractionResult, InstanceNode,
    SchemaClass, SchemaRelation, SchemaStatus,
    ResolvedTriple, RawExtractedEntity,
    normalize_predicate,
)
from src.domain.resolution_rules import EntityResolutionMatcher
from src.domain.ontology.schema_validator import SchemaValidator
from src.domain.interfaces.repositories.graph_repository import IGraphRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService

logger = logging.getLogger(__name__)


class EntityResolutionOrchestrator:
    def __init__(
        self,
        repo: IGraphRepository,
        embedder: IEmbeddingService,
        matcher: EntityResolutionMatcher,
    ):
        self.repo = repo
        self.embedder = embedder
        self.matcher = matcher

    # ------------------------------------------------------------------
    async def process_extraction(
        self,
        extraction: ExtractionResult,
        current_classes: List[SchemaClass],
        current_relations: List[SchemaRelation],
        chunk_id: str,
    ) -> Tuple[
        List[InstanceNode],      # экземпляры
        List[SchemaClass],       # новые DRAFT-классы
        List[ResolvedTriple],    # валидированные тройки
        List[SchemaRelation],    # новые DRAFT-отношения
    ]:
        instances: List[InstanceNode] = []
        new_classes: List[SchemaClass] = []
        tbox_names = {c.name.lower() for c in current_classes}

        # (name_lower, type_lower) → InstanceNode
        name_to_instance: Dict[Tuple[str, str], InstanceNode] = {}

        # ---- 1. Обработка сущностей ----
        for raw in extraction.entities:
            type_clean = raw.type.strip()
            name_clean = raw.name.strip()
            type_lower = type_clean.lower()
            name_lower = name_clean.lower()

            key = (name_lower, type_lower)
            if key in name_to_instance:
                continue  # дубликат в этом чанке

            # Новый тип → DRAFT-класс
            if type_lower not in tbox_names:
                new_cls = SchemaClass(
                    name=type_clean,
                    status=SchemaStatus.DRAFT,
                )
                new_classes.append(new_cls)
                tbox_names.add(type_lower)

            # Эмбеддинг + поиск кандидатов
            embedding = await self.embedder.embed_text(name_clean)
            candidates = await self.repo.find_candidates_by_vector(embedding)
            match_id = self.matcher.find_best_match(
                RawExtractedEntity(name=name_clean, type=type_clean),
                candidates,
            )

            inst = InstanceNode(
                instance_id=match_id or str(uuid.uuid4()),
                name=name_clean,
                class_name=type_clean,
                chunk_id=chunk_id,
                embedding=embedding,
            )
            instances.append(inst)
            name_to_instance[key] = inst

        # ---- 2. Валидатор с учётом новых классов ----
        all_classes = list(current_classes) + new_classes
        all_relations = list(current_relations)
        validator = SchemaValidator(all_classes, all_relations)

        # ---- 3. Обработка троек ----
        resolved_triples: List[ResolvedTriple] = []
        new_relations: List[SchemaRelation] = []
        seen_rel_keys: set = set()

        for triple in extraction.triples:
            predicate = normalize_predicate(triple.predicate)

            source_inst = self._find_instance(
                triple.subject, name_to_instance
            )
            target_inst = self._find_instance(
                triple.object, name_to_instance
            )

            if not source_inst or not target_inst:
                logger.debug(
                    f"⏭️ Пропуск тройки: '{triple.subject}' "
                    f"-[{predicate}]-> '{triple.object}' "
                    f"(сущность не найдена)"
                )
                continue

            # Без самоссылок
            if source_inst.instance_id == target_inst.instance_id:
                continue

            # Проверка по схеме с учётом иерархии
            allowed = validator.is_relation_allowed(
                source_inst.class_name, predicate, target_inst.class_name,
            )

            if not allowed:
                # Автоматически создаём DRAFT-отношение
                rel_key = (
                    source_inst.class_name.lower(),
                    predicate,
                    target_inst.class_name.lower(),
                )
                if rel_key not in seen_rel_keys:
                    new_rel = SchemaRelation(
                        source_class=source_inst.class_name,
                        relation_name=predicate,
                        target_class=target_inst.class_name,
                        status=SchemaStatus.DRAFT,
                    )
                    new_relations.append(new_rel)
                    all_relations.append(new_rel)
                    seen_rel_keys.add(rel_key)
                    logger.info(
                        f"📝 Новое DRAFT-отношение: "
                        f"{source_inst.class_name} → {predicate} → "
                        f"{target_inst.class_name}"
                    )

            resolved_triples.append(
                ResolvedTriple(
                    source_instance_id=source_inst.instance_id,
                    relation_name=predicate,
                    target_instance_id=target_inst.instance_id,
                    chunk_id=chunk_id,
                )
            )

        return instances, new_classes, resolved_triples, new_relations

    # ------------------------------------------------------------------
    @staticmethod
    def _find_instance(
        entity_name: str,
        name_map: Dict[Tuple[str, str], InstanceNode],
    ) -> Optional[InstanceNode]:
        """Ищет экземпляр по имени (без привязки к типу)."""
        name_lower = entity_name.strip().lower()
        for (n, _t), inst in name_map.items():
            if n == name_lower:
                return inst
        return None