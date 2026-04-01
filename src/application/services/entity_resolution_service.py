import uuid
from typing import Dict, List, Optional, Tuple
import Levenshtein as Lev

from src.domain.models.extraction import (
    ExtractionResult,
    ResolvedTriple,
    RawExtractedEntity,
)
from src.domain.models.nodes import InstanceNode
from src.domain.ontology.schema import SchemaClass, SchemaRelation
from src.domain.ontology.schema_validator import SchemaValidator
from src.domain.resolution_rules import EntityResolutionMatcher
from src.domain.interfaces.repositories.instance_repository import IInstanceRepository
from src.domain.interfaces.services.graph_embedding_service import IEmbeddingService
from src.domain.utils.normalize_predicate import normalize_predicate


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
        instance_repo: IInstanceRepository,  # ← ISP: только то, что нужно
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
        resolved_triples: List[ResolvedTriple] = []

        # Индексируем разрешенные классы (приводим к нижнему регистру для сравнения)
        allowed_classes = {c.name.lower(): c.name for c in current_classes}
        chunk_name_map: Dict[str, InstanceNode] = {}
        validator = SchemaValidator(current_classes, current_relations)

        # ---- 1. Сущности ----
        for raw in extraction.entities:
            type_clean = raw.type.strip()
            name_clean = raw.name.strip()
            name_lower = name_clean.lower()

            # СТРОГОЕ ПРАВИЛО: Если класса нет в T-Box, мы просто пропускаем эту сущность.
            # Никаких генераций DRAFT или скатывания к Concept.
            if type_clean.lower() not in allowed_classes:
                continue

            # Используем каноническое написание класса из T-Box
            canonical_type = allowed_classes[type_clean.lower()]

            existing = registry.find(name_clean)
            if existing:
                chunk_name_map[name_lower] = existing
                instances.append(existing)
                continue

            embedding = await self.embedder.embed_text(name_clean)
            candidates = await self.instance_repo.find_candidates_by_vector(embedding)

            match_id = self.matcher.find_best_match(
                RawExtractedEntity(name=name_clean, type=canonical_type),
                candidates,
            )

            if match_id:
                matched = next(
                    (c for c in candidates if c.instance_id == match_id), None
                )
                inst = InstanceNode(
                    instance_id=match_id,
                    name=matched.name if matched else name_clean,
                    class_name=matched.class_name if matched else canonical_type,
                    chunk_id=chunk_id,
                    embedding=embedding,
                )
            else:
                inst = InstanceNode(
                    instance_id=str(uuid.uuid4()),
                    name=name_clean,
                    class_name=canonical_type,
                    chunk_id=chunk_id,
                    embedding=embedding,
                )

            registry.register(name_clean, inst)
            chunk_name_map[name_lower] = inst
            instances.append(inst)

        # ---- 2. Тройки ----
        for triple in extraction.triples:
            predicate = normalize_predicate(triple.predicate)
            src_inst = self._find_instance(triple.subject, chunk_name_map)
            tgt_inst = self._find_instance(triple.object, chunk_name_map)

            if not src_inst or not tgt_inst:
                continue
            if src_inst.instance_id == tgt_inst.instance_id:
                continue

            # СТРОГОЕ ПРАВИЛО: Если связь не разрешена T-Box (SchemaValidator),
            # мы полностью отбрасываем этот триплет. Никаких новых отношений в графе.
            if not validator.is_relation_allowed(
                src_inst.class_name, predicate, tgt_inst.class_name
            ):
                continue

            resolved_triples.append(
                ResolvedTriple(
                    source_instance_id=src_inst.instance_id,
                    relation_name=predicate,
                    target_instance_id=tgt_inst.instance_id,
                    chunk_id=chunk_id,
                )
            )

        # Возвращаем пустые списки для new_classes и new_relations,
        # так как мы больше не разрешаем LLM менять схему онтологии на лету.
        return instances, [], resolved_triples, []

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
