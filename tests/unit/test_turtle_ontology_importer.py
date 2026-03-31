"""
Unit-тесты: парсинг Turtle → наши модели (без БД).
"""

import pytest
from src.domain.ontology.turtle_ontology_importer import TurtleOntologyImporter
from src.domain.ontology.schema import SchemaStatus


@pytest.fixture
def sample_ttl() -> str:
    return """@prefix : <http://example.org/gr_a3#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:gr_a3 a owl:Ontology .

:Person a owl:Class ;
    rdfs:comment "Люди и персонажи" .

:Employee a owl:Class ;
    rdfs:subClassOf :Person ;
    rdfs:comment "Сотрудники" .

:Organization a owl:Class ;
    rdfs:comment "Организации" .

:WORKS_AT a owl:ObjectProperty ;
    rdfs:domain :Person ;
    rdfs:range :Organization ;
    rdfs:comment "Работает в" .

:HAS_BOSS a owl:ObjectProperty ;
    rdfs:domain :Employee ;
    rdfs:range :Person .
"""


@pytest.fixture
def multi_domain_ttl() -> str:
    return """@prefix : <http://example.org/gr_a3#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

:LIKES a owl:ObjectProperty ;
    rdfs:domain :Person ;
    rdfs:domain :Animal ;
    rdfs:range :Product ;
    rdfs:range :Concept .
"""


class TestTurtleOntologyImporter:
    def test_parses_classes_correctly(self, sample_ttl):
        classes, _ = TurtleOntologyImporter.from_ttl(sample_ttl)

        assert len(classes) == 3
        names = {c.name for c in classes}
        assert {"Person", "Employee", "Organization"} == names

        person = next(c for c in classes if c.name == "Person")
        assert person.description == "Люди и персонажи"
        assert person.parent is None

        employee = next(c for c in classes if c.name == "Employee")
        assert employee.parent == "Person"
        assert employee.status == SchemaStatus.DRAFT

    def test_parses_relations_correctly(self, sample_ttl):
        _, relations = TurtleOntologyImporter.from_ttl(sample_ttl)

        assert len(relations) == 2

        works_at = next(r for r in relations if r.relation_name == "WORKS_AT")
        assert works_at.source_class == "Person"
        assert works_at.target_class == "Organization"
        assert works_at.description == "Работает в"
        assert works_at.status == SchemaStatus.DRAFT

        has_boss = next(r for r in relations if r.relation_name == "HAS_BOSS")
        assert has_boss.source_class == "Employee"
        assert has_boss.target_class == "Person"

    def test_handles_multiple_domains_ranges(self, multi_domain_ttl):
        _, relations = TurtleOntologyImporter.from_ttl(multi_domain_ttl)

        assert len(relations) == 4  # 2 домена × 2 ранга

        sources = {r.source_class for r in relations}
        targets = {r.target_class for r in relations}

        assert sources == {"Person", "Animal"}
        assert targets == {"Product", "Concept"}

    def test_empty_ttl_returns_empty_lists(self):
        classes, relations = TurtleOntologyImporter.from_ttl("")
        assert classes == []
        assert relations == []
