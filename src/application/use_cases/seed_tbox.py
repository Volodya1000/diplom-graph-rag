"""
Use Case: Инициализация базового T-Box + индексов.

Зависит только от ISchemaRepository (SRP + ISP).
"""

import logging

from src.domain.ontology.base_tbox import BASE_TBOX_CLASSES
from src.domain.ontology.base_tbox_relations import BASE_TBOX_RELATIONS
from src.domain.interfaces.repositories.schema_repository import ISchemaRepository

logger = logging.getLogger(__name__)


class SeedTboxUseCase:
    def __init__(self, schema_repo: ISchemaRepository):
        self.schema_repo = schema_repo

    async def execute(self, force: bool = False) -> int:
        await self.schema_repo.ensure_indexes()

        # ---- Классы ----
        current_classes = await self.schema_repo.get_tbox_classes()
        existing_names = {c.name.lower() for c in current_classes}

        classes_to_save = (
            list(BASE_TBOX_CLASSES)
            if force
            else [c for c in BASE_TBOX_CLASSES if c.name.lower() not in existing_names]
        )
        if classes_to_save:
            await self.schema_repo.save_tbox_classes(classes_to_save)

        # ---- Отношения ----
        current_rels = await self.schema_repo.get_schema_relations()
        existing_keys = {
            (r.source_class.lower(), r.relation_name.upper(), r.target_class.lower())
            for r in current_rels
        }

        rels_to_save = (
            list(BASE_TBOX_RELATIONS)
            if force
            else [
                r
                for r in BASE_TBOX_RELATIONS
                if (
                    r.source_class.lower(),
                    r.relation_name.upper(),
                    r.target_class.lower(),
                )
                not in existing_keys
            ]
        )
        if rels_to_save:
            await self.schema_repo.save_schema_relations(rels_to_save)

        total = len(classes_to_save) + len(rels_to_save)
        logger.info(
            f"✅ T-Box: {len(classes_to_save)} классов + {len(rels_to_save)} отношений"
            if total
            else "✅ T-Box уже содержит все базовые элементы"
        )
        return total
