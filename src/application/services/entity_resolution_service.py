"""
Оркестратор Entity Resolution с кросс-чанковым реестром
и валидацией троек по схеме.
"""

import uuid
import logging
from typing import Dict, List, Optional, Tuple

import Levenshtein as Lev

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


# =====================================================================
#  Кросс-чанковый реестр сущностей (живёт в рамках одного документа)
# =====================================================================

class EntityRegistry:
    """
    Локальный кеш сущностей для одного документа.
    Обеспечивает:
      - дедупликацию между чанками;
      - фиксацию типа (первый чанк побеждает).
    """

    def __init__(self, levenshtein_threshold: float = 0.85):
        self._by_name: Dict[str, InstanceNode] = {}      # lower(name) → inst
        self._threshold = levenshtein_threshold

    # ------------------------------------------------------------------

    def find(self, name: str) -> Optional[InstanceNode]:
        key = name.strip().lower()

        # Точное совпадение
        if key in self._by_name:
            return self._by_name[key]

        # Fuzzy-совпадение
        for existing_key, inst in self._by_name.items():
            sim = self._similarity(key, existing_key)
            if sim >= self._threshold:
                return inst

        return None

    # ------------------------------------------------------------------

    def register(self, name: str, instance: InstanceNode) -> None:
        key = name.strip().lower()
        if key not in self._by_name:
            self._by_name[key] = instance

    # ------------------------------------------------------------------

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        dist = Lev.distance(a, b)
        return 1.0 - dist / max(len(a), len(b))

    # ------------------------------------------------------------------

    @property
    def all_instances(self) -> List[InstanceNode]:
        return list(self._by_name.values())


# =====================================================================
#  Оркестратор
# =====================================================================

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

    def create_registry(self) -> EntityRegistry:
        """Фабрика — создаёт реестр для нового документа."""
        return EntityRegistry(
            levenshtein_threshold=self.matcher.levenshtein_threshold,
        )

    # ------------------------------------------------------------------

    async def process_extraction(
        self,
        extraction: ExtractionResult,
        current_classes: List[SchemaClass],
        current_relations: List[SchemaRelation],
        chunk_id: str,
        registry: EntityRegistry,
    ) -> Tuple[
        List[InstanceNode],       # экземпляры (новые + переиспользованные)
        List[SchemaClass],        # новые DRAFT-классы
        List[ResolvedTriple],     # валидированные тройки
        List[SchemaRelation],     # новые DRAFT-отношения
    ]:
        instances: List[InstanceNode] = []
        new_classes: List[SchemaClass] = []
        tbox_names = {c.name.lower() for c in current_classes}

        # name_lower → InstanceNode  (для тройков этого чанка)
        chunk_name_map: Dict[str, InstanceNode] = {}

        # ---- 1. Обработка сущностей ----
        for raw in extraction.entities:
            type_clean = raw.type.strip()
            name_clean = raw.name.strip()
            name_lower = name_clean.lower()

            # 1а. Проверка реестра (кросс-чанк)
            existing = registry.find(name_clean)
            if existing:
                logger.debug(
                    f"♻️ Реестр: «{name_clean}» → "
                    f"{existing.instance_id} [{existing.class_name}]"
                )
                chunk_name_map[name_lower] = existing
                instances.append(existing)
                continue

            # 1б. Новый тип → DRAFT-класс
            if type_clean.lower() not in tbox_names:
                new_cls = SchemaClass(
                    name=type_clean,
                    status=SchemaStatus.DRAFT,
                )
                new_classes.append(new_cls)
                tbox_names.add(type_clean.lower())

            # 1в. Эмбеддинг + поиск кандидатов в БД
            embedding = await self.embedder.embed_text(name_clean)
            candidates = await self.repo.find_candidates_by_vector(embedding)

            match_id = self.matcher.find_best_match(
                RawExtractedEntity(name=name_clean, type=type_clean),
                candidates,
            )

            if match_id:
                # Нашли совпадение в БД — переиспользуем
                matched_cand = next(
                    (c for c in candidates if c.instance_id == match_id),
                    None,
                )
                if matched_cand:
                    logger.info(
                        f"🔗 DB match: «{name_clean}» → "
                        f"«{matched_cand.name}» [{matched_cand.class_name}]"
                    )
                    # Фиксируем тип из БД (первый побеждает)
                    inst = InstanceNode(
                        instance_id=match_id,
                        name=matched_cand.name,
                        class_name=matched_cand.class_name,
                        chunk_id=chunk_id,
                        embedding=embedding,
                    )
                else:
                    inst = InstanceNode(
                        instance_id=match_id,
                        name=name_clean,
                        class_name=type_clean,
                        chunk_id=chunk_id,
                        embedding=embedding,
                    )
            else:
                # Новая сущность
                inst = InstanceNode(
                    instance_id=str(uuid.uuid4()),
                    name=name_clean,
                    class_name=type_clean,
                    chunk_id=chunk_id,
                    embedding=embedding,
                )
                logger.info(
                    f"🆕 Новая сущность: «{name_clean}» [{type_clean}] "
                    f"id={inst.instance_id[:8]}…"
                )

            registry.register(name_clean, inst)
            chunk_name_map[name_lower] = inst
            instances.append(inst)

        # ---- 2. Валидатор схемы ----
        all_classes = list(current_classes) + new_classes
        all_relations = list(current_relations)
        validator = SchemaValidator(all_classes, all_relations)

        # ---- 3. Обработка троек ----
        resolved_triples: List[ResolvedTriple] = []
        new_relations: List[SchemaRelation] = []
        seen_rel_keys: set = set()

        for triple in extraction.triples:
            predicate = normalize_predicate(triple.predicate)

            src_inst = self._find_instance(triple.subject, chunk_name_map)
            tgt_inst = self._find_instance(triple.object, chunk_name_map)

            if not src_inst or not tgt_inst:
                logger.debug(
                    f"⏭️ Пропуск: «{triple.subject}» "
                    f"-[{predicate}]→ «{triple.object}» "
                    f"(сущность не найдена)"
                )
                continue

            if src_inst.instance_id == tgt_inst.instance_id:
                continue

            allowed = validator.is_relation_allowed(
                src_inst.class_name, predicate, tgt_inst.class_name,
            )

            if not allowed:
                rel_key = (
                    src_inst.class_name.lower(),
                    predicate,
                    tgt_inst.class_name.lower(),
                )
                if rel_key not in seen_rel_keys:
                    new_rel = SchemaRelation(
                        source_class=src_inst.class_name,
                        relation_name=predicate,
                        target_class=tgt_inst.class_name,
                        status=SchemaStatus.DRAFT,
                    )
                    new_relations.append(new_rel)
                    all_relations.append(new_rel)
                    seen_rel_keys.add(rel_key)
                    logger.info(
                        f"📝 DRAFT-отношение: "
                        f"{src_inst.class_name} →{predicate}→ "
                        f"{tgt_inst.class_name}"
                    )

            resolved_triples.append(
                ResolvedTriple(
                    source_instance_id=src_inst.instance_id,
                    relation_name=predicate,
                    target_instance_id=tgt_inst.instance_id,
                    chunk_id=chunk_id,
                )
            )

        return instances, new_classes, resolved_triples, new_relations

    # ------------------------------------------------------------------

    @staticmethod
    def _find_instance(
        entity_name: str,
        name_map: Dict[str, InstanceNode],
    ) -> Optional[InstanceNode]:
        key = entity_name.strip().lower()
        if key in name_map:
            return name_map[key]
        # Fuzzy fallback
        for k, inst in name_map.items():
            if not k or not key:
                continue
            dist = Lev.distance(key, k)
            sim = 1.0 - dist / max(len(key), len(k))
            if sim >= 0.85:
                return inst
        return None