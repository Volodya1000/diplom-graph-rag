"""
Валидатор онтологической схемы с поддержкой иерархии классов.

Принцип наследования:
  Если отношение WORKS_AT допустимо для Person → Organization,
  то оно автоматически допустимо для Employee → Company
  (если Employee ⊂ Person, Company ⊂ Organization).
"""

from typing import Dict, List, Set

from src.domain.ontology.schema import SchemaClass, SchemaRelation


class SchemaValidator:
    """Проверяет допустимость отношений с учётом иерархии классов."""

    def __init__(
        self,
        classes: List[SchemaClass],
        relations: List[SchemaRelation],
    ):
        self._classes: Dict[str, SchemaClass] = {c.name.lower(): c for c in classes}
        self._relations = relations

    # ------------------------------------------------------------------
    #  ИЕРАРХИЯ
    # ------------------------------------------------------------------

    def get_ancestors(self, class_name: str) -> Set[str]:
        """
        Возвращает множество имён класса и ВСЕХ его предков.
        Пример: get_ancestors("Company") → {"Company", "Organization"}
        """
        ancestors: Set[str] = set()
        current = class_name.lower()
        visited: Set[str] = set()

        while current in self._classes and current not in visited:
            visited.add(current)
            cls = self._classes[current]
            ancestors.add(cls.name)  # оригинальный регистр
            if cls.parent:
                current = cls.parent.lower()
            else:
                break

        return ancestors

    def get_descendants(self, class_name: str) -> Set[str]:
        """
        Возвращает множество имён класса и ВСЕХ его потомков.
        Пример: get_descendants("Organization") → {"Organization", "Company", "GovernmentOrg"}
        """
        target = class_name.lower()
        descendants: Set[str] = set()

        if target in self._classes:
            descendants.add(self._classes[target].name)

        queue = [target]
        visited: Set[str] = {target}

        while queue:
            current = queue.pop(0)
            for name_lower, cls in self._classes.items():
                if (
                    cls.parent
                    and cls.parent.lower() == current
                    and name_lower not in visited
                ):
                    visited.add(name_lower)
                    descendants.add(cls.name)
                    queue.append(name_lower)

        return descendants

    # ------------------------------------------------------------------
    #  ВАЛИДАЦИЯ ОТНОШЕНИЙ
    # ------------------------------------------------------------------

    def is_relation_allowed(
        self,
        source_type: str,
        predicate: str,
        target_type: str,
    ) -> bool:
        """
        Проверяет, допустимо ли отношение с учётом иерархии.

        Если WORKS_AT разрешено для Person → Organization,
        то для Employee → Company тоже разрешено
        (Employee наследует от Person, Company наследует от Organization).
        """
        source_ancestors = self.get_ancestors(source_type)
        target_ancestors = self.get_ancestors(target_type)
        predicate_norm = predicate.strip().upper()

        for rel in self._relations:
            if rel.relation_name.strip().upper() != predicate_norm:
                continue
            if (
                rel.source_class in source_ancestors
                and rel.target_class in target_ancestors
            ):
                return True

        return False

    def get_allowed_relations_for(
        self,
        source_type: str,
        target_type: str,
    ) -> List[SchemaRelation]:
        """Все допустимые отношения между двумя типами (с иерархией)."""
        source_ancestors = self.get_ancestors(source_type)
        target_ancestors = self.get_ancestors(target_type)

        return [
            rel
            for rel in self._relations
            if (
                rel.source_class in source_ancestors
                and rel.target_class in target_ancestors
            )
        ]

    # ------------------------------------------------------------------
    #  ФОРМАТИРОВАНИЕ ДЛЯ ПРОМПТА LLM
    # ------------------------------------------------------------------

    def format_hierarchy_tree(self) -> str:
        """Форматирует иерархию классов как дерево с отступами."""
        children_map: Dict[str, List[str]] = {}
        roots: List[str] = []

        for name_lower, cls in self._classes.items():
            if cls.parent:
                parent_lower = cls.parent.lower()
                children_map.setdefault(parent_lower, []).append(cls.name)
            else:
                roots.append(cls.name)

        lines: List[str] = []

        def _render(name: str, depth: int) -> None:
            cls = self._classes.get(name.lower())
            if not cls:
                return
            indent = "  " * depth
            prefix = "└ " if depth > 0 else "• "
            desc = f" — {cls.description}" if cls.description else ""
            lines.append(f"{indent}{prefix}{cls.name}{desc}")
            for child in sorted(children_map.get(name.lower(), [])):
                _render(child, depth + 1)

        for root in sorted(roots):
            _render(root, 0)

        return "\n".join(lines) if lines else "(типы не заданы)"

    def format_relations(self) -> str:
        """Форматирует допустимые отношения для промпта LLM."""
        if not self._relations:
            return "(допустимые отношения не заданы — предложи свои)"

        lines: List[str] = []
        for rel in self._relations:
            desc = f" — {rel.description}" if rel.description else ""
            lines.append(
                f"• {rel.source_class} → {rel.relation_name} → {rel.target_class}{desc}"
            )
        return "\n".join(lines)
