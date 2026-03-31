from collections import defaultdict
from typing import List
from src.domain.ontology.shema import SchemaClass, SchemaRelation

class TurtleOntologyExporter:
    """Чистый доменный класс — отвечает только за генерацию Turtle."""

    # ─── ИСПРАВЛЕННЫЕ КОНСТАНТЫ ───
    BASE_IRI = "http://example.org/gr_a3"
    PREFIX = f"{BASE_IRI}#"
    # ONTOLOGY_IRI — хранит базовый IRI онтологии (без '#')
    ONTOLOGY_IRI = BASE_IRI  # <- без '#' в конце онтологии

    HEADER = (
        f"@prefix : <{PREFIX}> .\n"
        f"@prefix owl: <http://www.w3.org/2002/07/owl#> .\n"
        f"@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        f"@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n\n"
        "# ============================================\n"
        "# GR_A3 Ontology — T-Box (только схема)\n"
        "# ============================================\n"
        f"<{ONTOLOGY_IRI}> a owl:Ontology ;\n"
        f"    rdfs:label \"GR_A3 Knowledge Graph Ontology\" ;\n"
        f"    rdfs:comment \"Экспортировано из проекта gr_a3\" .\n\n"
    )

    CLASSES_SECTION = "# ==================== КЛАССЫ ====================\n"
    PROPERTIES_SECTION = "# ==================== ОБЪЕКТНЫЕ СВОЙСТВА ====================\n"

    @classmethod
    def to_turtle(cls, classes: List[SchemaClass], relations: List[SchemaRelation]) -> str:
        """Основной публичный метод домена."""
        lines = [cls.HEADER, cls.CLASSES_SECTION]

        # Сортировка: CORE → DRAFT, по имени
        sorted_classes = sorted(classes, key=lambda c: (c.status.value, c.name))
        for c in sorted_classes:
            lines.append(cls._class_to_turtle(c))

        lines.append(cls.PROPERTIES_SECTION)

        # Группировка свойств по имени (domain/range могут быть множественными)
        prop_groups = cls._group_properties(relations)
        for name, data in sorted(prop_groups.items()):
            lines.append(cls._property_to_turtle(name, data))

        return "\n".join(lines)

    @staticmethod
    def _class_to_turtle(c: SchemaClass) -> str:
        lines = [f":{c.name} a owl:Class ;"]
        if c.description:
            comment_text = c.description.replace('"', '\\"')
            lines.append(f'    rdfs:comment "{comment_text}" ;')
        if c.parent:
            lines.append(f"    rdfs:subClassOf :{c.parent} ;")
        lines.append("    .")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _group_properties(relations: List[SchemaRelation]) -> dict:
        """Группирует по имени свойства: {name: {"domains": set, "ranges": set, "comment": str}}"""
        groups: defaultdict = defaultdict(lambda: {"domains": set(), "ranges": set(), "comment": ""})
        for r in relations:
            name = r.relation_name
            groups[name]["domains"].add(r.source_class)
            groups[name]["ranges"].add(r.target_class)
            if r.description:
                groups[name]["comment"] = r.description
        return dict(groups)

    @staticmethod
    def _property_to_turtle(name: str, data: dict) -> str:
        lines = [f":{name} a owl:ObjectProperty ;"]
        for d in sorted(data["domains"]):
            lines.append(f"    rdfs:domain :{d} ;")
        for r in sorted(data["ranges"]):
            lines.append(f"    rdfs:range :{r} ;")
        if data["comment"]:
            comment_text = data["comment"].replace('"', '\\"')
            lines.append(f'    rdfs:comment "{comment_text}" ;')
        lines.append("    .")
        lines.append("")
        return "\n".join(lines)