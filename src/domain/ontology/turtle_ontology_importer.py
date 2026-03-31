from typing import List, Tuple
from rdflib import Graph, RDF, RDFS, OWL
from .schema import SchemaClass, SchemaRelation, SchemaStatus

# pip install rdflib  # один раз


class TurtleOntologyImporter:
    """Чистый домен: парсит только то, что мы экспортируем (классы + ObjectProperty)."""

    @staticmethod
    def from_ttl(ttl_text: str) -> Tuple[List[SchemaClass], List[SchemaRelation]]:
        g = Graph()
        g.parse(data=ttl_text, format="turtle")

        classes: List[SchemaClass] = []
        relations: List[SchemaRelation] = []

        # Классы
        for subj in g.subjects(RDF.type, OWL.Class):
            name = str(subj).split("#")[-1]
            comment = g.value(subj, RDFS.comment)
            parent = g.value(subj, RDFS.subClassOf)
            parent_name = str(parent).split("#")[-1] if parent else None

            classes.append(
                SchemaClass(
                    name=name,
                    status=SchemaStatus.DRAFT,
                    description=str(comment) if comment else "",
                    parent=parent_name,
                )
            )

        # ObjectProperty (может быть несколько domain/range)
        for prop in g.subjects(RDF.type, OWL.ObjectProperty):
            name = str(prop).split("#")[-1]
            domains = [str(d).split("#")[-1] for d in g.objects(prop, RDFS.domain)]
            ranges_ = [str(r).split("#")[-1] for r in g.objects(prop, RDFS.range)]
            comment = g.value(prop, RDFS.comment)

            for d in domains:
                for r in ranges_:
                    relations.append(
                        SchemaRelation(
                            source_class=d,
                            relation_name=name,
                            target_class=r,
                            status=SchemaStatus.DRAFT,
                            description=str(comment) if comment else "",
                        )
                    )

        return classes, relations
