"""
Оркестратор Entity Resolution.

Изменение: зависит от IInstanceRepository вместо IGraphRepository (ISP).
"""

import uuid
import logging
from typing import Dict, List, Optional, Tuple

import Levenshtein as Lev

from src.domain.utils.normalize_predicate import normalize_predicate
from src.application.dtos.extraction_dtos import RawExtractedEntity, ResolvedTriple
from src.domain.interfaces.llm.llm_client import ExtractionResult
from src.domain.ontology.shema import SchemaStatus, SchemaClass, SchemaRelation
from src.domain.graph_components.nodes import InstanceNode
from src.domain.resolution_rules import EntityResolutionMatcher
from src.domain.ontology.schema_validator import SchemaValidator
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService

logger = logging.getLogger(__name__)


# =====================================================================
#  Кросс-чанковый реестр (без изменений)
# =====================================================================

class EntityRegistry:
    def __init__(self, levenshtein_threshold: float = 0.85):
        self._by_name: Dict[str, InstanceNode] = {}
        self._threshold = levenshtein_threshold

    def find(self, name: str) -> Optional[InstanceNode]:
        key = name.strip().lower()
        if key in self._by_name:
            return self._by_name[key]
        for existing_key, inst in self._by_name.items():
            if self._similarity(key, existing_key) >= self._threshold:
                return inst
        return None

    def register(self, name: str, instance: InstanceNode) -> None:
        key = name.strip().lower()
        if key not in self._by_name:
            self._by_name[key] = instance

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        return 1.0 - Lev.distance(a, b) / max(len(a), len(b))

    @property
    def all_instances(self) -> List[InstanceNode]:
        return list(self._by_name.values())

    def format_known_entities(self) -> str:
        if not self._by_name:
            return ""
        lines, seen = [], set()
        for inst in self._by_name.values():
            key = (inst.name, inst.class_name)
            if key not in seen:
                lines.append(f"• {inst.name} [{inst.class_name}]")
                seen.add(key)
        return "\n".join(lines)


# =====================================================================
#  Оркестратор
# =====================================================================

class EntityResolutionOrchestrator:
    def __init__(
        self,
        instance_repo: IInstanceRepository,       # ← ISP: только то, что нужно
        embedder: IEmbeddingService,
        matcher: EntityResolutionMatcher,
    ):
        self.instance_repo = instance_repo
        self.embedder = embedder
        self.matcher = matcher

    def create_registry(self) -> EntityRegistry:
        return EntityRegistry(
            levenshtein_threshold=self.matcher.levenshtein_threshold,
        )

    async def process_extraction(
        self,
        extraction: ExtractionResult,
        current_classes: List[SchemaClass],
        current_relations: List[SchemaRelation],
        chunk_id: str,
        registry: EntityRegistry,
    ) -> Tuple[
        List[InstanceNode],
        List[SchemaClass],
        List[ResolvedTriple],
        List[SchemaRelation],
    ]:
        instances: List[InstanceNode] = []
        new_classes: List[SchemaClass] = []
        tbox_names = {c.name.lower() for c in current_classes}
        chunk_name_map: Dict[str, InstanceNode] = {}

        # ---- 1. Сущности ----
        for raw in extraction.entities:
            type_clean = raw.type.strip()
            name_clean = raw.name.strip()
            name_lower = name_clean.lower()

            existing = registry.find(name_clean)
            if existing:
                chunk_name_map[name_lower] = existing
                instances.append(existing)
                continue

            if type_clean.lower() not in tbox_names:
                new_classes.append(
                    SchemaClass(name=type_clean, status=SchemaStatus.DRAFT)
                )
                tbox_names.add(type_clean.lower())

            embedding = await self.embedder.embed_text(name_clean)
            candidates = await self.instance_repo.find_candidates_by_vector(
                embedding,
            )

            match_id = self.matcher.find_best_match(
                RawExtractedEntity(name=name_clean, type=type_clean),
                candidates,
            )

            if match_id:
                matched = next(
                    (c for c in candidates if c.instance_id == match_id),
                    None,
                )
                inst = InstanceNode(
                    instance_id=match_id,
                    name=matched.name if matched else name_clean,
                    class_name=matched.class_name if matched else type_clean,
                    chunk_id=chunk_id,
                    embedding=embedding,
                )
            else:
                inst = InstanceNode(
                    instance_id=str(uuid.uuid4()),
                    name=name_clean,
                    class_name=type_clean,
                    chunk_id=chunk_id,
                    embedding=embedding,
                )

            registry.register(name_clean, inst)
            chunk_name_map[name_lower] = inst
            instances.append(inst)

        # ---- 2. Валидатор ----
        all_classes = list(current_classes) + new_classes
        all_relations = list(current_relations)
        validator = SchemaValidator(all_classes, all_relations)

        # ---- 3. Тройки ----
        resolved_triples: List[ResolvedTriple] = []
        new_relations: List[SchemaRelation] = []
        seen_rel_keys: set = set()

        for triple in extraction.triples:
            predicate = normalize_predicate(triple.predicate)
            src_inst = self._find_instance(triple.subject, chunk_name_map)
            tgt_inst = self._find_instance(triple.object, chunk_name_map)

            if not src_inst or not tgt_inst:
                continue
            if src_inst.instance_id == tgt_inst.instance_id:
                continue

            if not validator.is_relation_allowed(
                src_inst.class_name, predicate, tgt_inst.class_name,
            ):
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

            resolved_triples.append(
                ResolvedTriple(
                    source_instance_id=src_inst.instance_id,
                    relation_name=predicate,
                    target_instance_id=tgt_inst.instance_id,
                    chunk_id=chunk_id,
                )
            )

        return instances, new_classes, resolved_triples, new_relations

    @staticmethod
    def _find_instance(
        entity_name: str,
        name_map: Dict[str, InstanceNode],
    ) -> Optional[InstanceNode]:
        key = entity_name.strip().lower()
        if key in name_map:
            return name_map[key]
        for k, inst in name_map.items():
            if not k or not key:
                continue
            sim = 1.0 - Lev.distance(key, k) / max(len(key), len(k))
            if sim >= 0.85:
                return inst
        return None