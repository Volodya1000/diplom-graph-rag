"""
Use Case: Инициализация базового T-Box (классы + отношения) в графе.

    python main.py seed-tbox
    python main.py seed-tbox --force --show
"""

import logging

from src.domain.ontology.base_tbox import BASE_TBOX_CLASSES, BASE_TBOX_RELATIONS
from src.domain.interfaces.repositories.graph_repository import IGraphRepository

logger = logging.getLogger(__name__)


class SeedTboxUseCase:
    def __init__(self, repo: IGraphRepository):
        self.repo = repo

    async def execute(self, force: bool = False) -> int:
        """
        Добавляет базовые классы и отношения T-Box в граф.

        Returns:
            Количество добавленных / обновлённых элементов.
        """
        # ---- Классы ----
        current_classes = await self.repo.get_tbox_classes()
        existing_names = {c.name.lower() for c in current_classes}

        if force:
            classes_to_save = list(BASE_TBOX_CLASSES)
            logger.info(
                f"🔄 Force: перезапись {len(classes_to_save)} CORE-классов"
            )
        else:
            classes_to_save = [
                cls for cls in BASE_TBOX_CLASSES
                if cls.name.lower() not in existing_names
            ]

        if classes_to_save:
            await self.repo.save_tbox_classes(classes_to_save)
            for cls in classes_to_save:
                parent_info = f" (→ {cls.parent})" if cls.parent else ""
                logger.info(f"  📌 {cls.name}{parent_info}: {cls.description}")

        # ---- Отношения ----
        current_relations = await self.repo.get_schema_relations()
        existing_rel_keys = {
            (
                r.source_class.lower(),
                r.relation_name.upper(),
                r.target_class.lower(),
            )
            for r in current_relations
        }

        if force:
            rels_to_save = list(BASE_TBOX_RELATIONS)
        else:
            rels_to_save = [
                rel for rel in BASE_TBOX_RELATIONS
                if (
                    rel.source_class.lower(),
                    rel.relation_name.upper(),
                    rel.target_class.lower(),
                )
                not in existing_rel_keys
            ]

        if rels_to_save:
            await self.repo.save_schema_relations(rels_to_save)
            for rel in rels_to_save:
                logger.info(
                    f"  🔗 {rel.source_class} → "
                    f"{rel.relation_name} → {rel.target_class}"
                )

        total = len(classes_to_save) + len(rels_to_save)

        if total == 0:
            logger.info("✅ T-Box уже содержит все базовые элементы")
        else:
            logger.info(
                f"✅ T-Box: {len(classes_to_save)} классов + "
                f"{len(rels_to_save)} отношений"
            )

        return total