import re

from pydantic import BaseModel

from .schema import SchemaClass, SchemaRelation


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = []
    merged_classes: list[SchemaClass]
    merged_relations: list[SchemaRelation]
    warnings: list[str] = []


class OntologyUpdateValidator:
    """100% бизнес-логика. Никаких репозиториев — только данные."""

    CLASS_NAME_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
    REL_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

    def validate_merge(
        self,
        current_classes: list[SchemaClass],
        current_relations: list[SchemaRelation],
        proposed_classes: list[SchemaClass],
        proposed_relations: list[SchemaRelation],
        class_usage: dict[str, int],  # name → count(Instance)
    ) -> ValidationResult:
        # 1. Merge (append-only)
        merged_classes = self._merge_classes(current_classes, proposed_classes)
        merged_relations = self._merge_relations(current_relations, proposed_relations)

        errors: list[str] = []
        warnings: list[str] = []

        # 2. Циклы
        if self._has_cycle(merged_classes):
            errors.append(
                "Обнаружен цикл в иерархии классов (человек предок животного и наоборот)",
            )

        # 3. Целостность ссылок
        class_set = {c.name for c in merged_classes}

        # Родители существуют
        errors.extend(
            f"Родитель {c.parent} класса {c.name} не существует"
            for c in merged_classes
            if c.parent and c.parent not in class_set
        )

        # Отношения ссылаются на существующие классы
        errors.extend(
            f"Отношение {r.relation_name} ссылается на несуществующий класс ({r.source_class} → {r.target_class})"
            for r in merged_relations
            if r.source_class not in class_set or r.target_class not in class_set
        )

        # 4. Запрет удаления используемых классов
        current_names = {c.name for c in current_classes}
        proposed_names = {c.name for c in proposed_classes}

        warnings.extend(
            f"Класс {deleted} удалён в TTL, но оставлен (используется в A-Box)"
            for deleted in current_names - proposed_names
            if class_usage.get(deleted, 0) > 0
        )

        # 5. Формат имён
        errors.extend(
            f"Неверный формат класса: {c.name} (должен быть CamelCase)"
            for c in proposed_classes
            if not self.CLASS_NAME_RE.match(c.name)
        )

        errors.extend(
            f"Неверный формат отношения: {r.relation_name} (UPPER_SNAKE_CASE)"
            for r in proposed_relations
            if not self.REL_NAME_RE.match(r.relation_name)
        )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            merged_classes=merged_classes,
            merged_relations=merged_relations,
            warnings=warnings,
        )

    def _merge_classes(
        self,
        current: list[SchemaClass],
        proposed: list[SchemaClass],
    ) -> list[SchemaClass]:
        by_name = {c.name: c.model_copy() for c in current}
        for p in proposed:
            if p.name in by_name:
                by_name[p.name].description = p.description
                by_name[p.name].parent = p.parent  # будет проверено на цикл позже
            else:
                by_name[p.name] = p.model_copy()
        return list(by_name.values())

    def _merge_relations(
        self,
        current: list[SchemaRelation],
        proposed: list[SchemaRelation],
    ) -> list[SchemaRelation]:
        def key(r: SchemaRelation) -> tuple[str, str, str]:
            return (
                r.source_class.lower(),
                r.relation_name.upper(),
                r.target_class.lower(),
            )

        by_key = {key(r): r.model_copy() for r in current}
        for p in proposed:
            k = key(p)
            if k in by_key:
                by_key[k].description = p.description
            else:
                by_key[k] = p.model_copy()
        return list(by_key.values())

    def _has_cycle(self, classes: list[SchemaClass]) -> bool:
        graph: dict[str, str] = {c.name.lower(): c.parent.lower() for c in classes if c.parent}

        def dfs(node: str, path: set[str]) -> bool:
            if node in path:
                return True
            if node not in graph:
                return False
            path.add(node)
            if dfs(graph[node], path):
                return True
            path.remove(node)
            return False

        return any(dfs(c.name.lower(), set()) for c in classes)
