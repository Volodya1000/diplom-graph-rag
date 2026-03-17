"""
Use Case: Инициализация базового T-Box в графе.

Можно вызвать:
  - через CLI:  python main.py seed-tbox
  - автоматически при ingest (если T-Box пуст)
"""

import logging
from typing import List

from src.domain.models import SchemaClass, SchemaStatus
from src.domain.ontology.base_tbox import BASE_TBOX_CLASSES
from src.domain.interfaces.repositories.graph_repository import IGraphRepository

logger = logging.getLogger(__name__)


class SeedTboxUseCase:
    def __init__(self, repo: IGraphRepository):
        self.repo = repo

    async def execute(self, force: bool = False) -> int:
        """
        Добавляет базовые классы T-Box в граф.

        Args:
            force: если True — обновляет описания существующих CORE-классов

        Returns:
            Количество добавленных/обновлённых классов
        """
        current_classes = await self.repo.get_tbox_classes()
        existing_names = {c.name.lower() for c in current_classes}

        if force:
            # При force — перезаписываем все CORE классы
            to_save = list(BASE_TBOX_CLASSES)
            logger.info(f"🔄 Force-режим: перезапись {len(to_save)} CORE-классов")
        else:
            # Добавляем только отсутствующие
            to_save = [
                cls for cls in BASE_TBOX_CLASSES
                if cls.name.lower() not in existing_names
            ]

        if not to_save:
            logger.info("✅ T-Box уже содержит все базовые классы")
            return 0

        await self.repo.save_tbox_classes(to_save)

        for cls in to_save:
            logger.info(f"  📌 {cls.name}: {cls.description}")

        logger.info(f"✅ T-Box: добавлено/обновлено {len(to_save)} классов")
        return len(to_save)