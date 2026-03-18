from collections import defaultdict
from typing import Dict, List
import re
from pydantic import BaseModel
from .shema import SchemaClass, SchemaRelation, SchemaStatus

class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = []
    merged_classes: List[SchemaClass]
    merged_relations: List[SchemaRelation]
    warnings: List[str] = []

class OntologyUpdateValidator:
    """100% бизнес-логика. Никаких репозиториев — только данные."""

    CLASS_NAME_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
    REL_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

    def validate_merge(
        self,
        current_classes: List[SchemaClass],
        current_relations: List[SchemaRelation],
        proposed_classes: List[SchemaClass],
        proposed_relations: List[SchemaRelation],
        class_usage: Dict[str, int],  # name → count(Instance)
    ) -> ValidationResult:
        # 1. Merge (append-only)
        merged_classes = self._merge_classes(current_classes, proposed_classes)
        merged_relations = self._merge_relations(current_relations, proposed_relations)

        errors: List[str] = []
        warnings: List[str] = []

        # 2. Циклы
        if self._has_cycle(merged_classes):
            errors.append("Обнаружен цикл в иерархии классов (человек предок животного и наоборот)")

        # 3. Целостность ссылок
        class_set = {c.name for c in merged_classes}
        for c in merged_classes:
            if c.parent and c.parent not in class_set:
                errors.append(f"Родитель {c.parent} класса {c.name} не существует")
        for r in merged_relations:
            if r.source_class not in class_set or r.target_class not in class_set:
                errors.append(f"Отношение {r.relation_name} ссылается на несуществующий класс")

        # 4. Запрет удаления используемых
        current_names = {c.name for c in current_classes}
        proposed_names = {c.name for c in proposed_classes}
        for deleted in current_names - proposed_names:
            if class_usage.get(deleted, 0) > 0:
                warnings.append(f"Класс {deleted} удалён в TTL, но оставлен (используется в A-Box)")

        # 5. Формат имён
        for c in proposed_classes:
            if not self.CLASS_NAME_RE.match(c.name):
                errors.append(f"Неверный формат класса: {c.name} (должен быть CamelCase)")
        for r in proposed_relations:
            if not self.REL_NAME_RE.match(r.relation_name):
                errors.append(f"Неверный формат отношения: {r.relation_name} (UPPER_SNAKE_CASE)")

        # 6. Нет самоссылок
        for r in proposed_relations:
            if r.source_class == r.target_class:
                errors.append(f"Самоссылка в отношении {r.relation_name}")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            merged_classes=merged_classes,
            merged_relations=merged_relations,
            warnings=warnings,
        )

    def _merge_classes(self, current: List[SchemaClass], proposed: List[SchemaClass]) -> List[SchemaClass]:
        by_name = {c.name: c.model_copy() for c in current}
        for p in proposed:
            if p.name in by_name:
                by_name[p.name].description = p.description
                by_name[p.name].parent = p.parent  # будет проверено на цикл позже
            else:
                by_name[p.name] = p.model_copy()
        return list(by_name.values())

    def _merge_relations(self, current: List[SchemaRelation], proposed: List[SchemaRelation]) -> List[SchemaRelation]:
        key = lambda r: (r.source_class.lower(), r.relation_name.upper(), r.target_class.lower())
        by_key = {key(r): r.model_copy() for r in current}
        for p in proposed:
            k = key(p)
            if k in by_key:
                by_key[k].description = p.description
            else:
                by_key[k] = p.model_copy()
        return list(by_key.values())

    def _has_cycle(self, classes: List[SchemaClass]) -> bool:
        graph: Dict[str, str] = {c.name.lower(): c.parent.lower() for c in classes if c.parent}
        visited = set()

        def dfs(node: str, path: set) -> bool:
            if node in path:
                return True
            if node not in graph:
                return False
            path.add(node)
            if dfs(graph[node], path):
                return True
            path.remove(node)
            return False

        for c in classes:
            if dfs(c.name.lower(), set()):
                return True
        return False