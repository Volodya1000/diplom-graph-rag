"""
Integration: SeedTboxUseCase — полный happy path через все слои.
"""

import pytest
from src.application.use_cases.seed_tbox import SeedTboxUseCase


pytestmark = pytest.mark.integration


class TestSeedTboxHappyPath:

    async def test_first_seed_creates_all_elements(self, schema_repo):
        use_case = SeedTboxUseCase(schema_repo=schema_repo)

        count = await use_case.execute(force=False)

        assert count > 0
        classes = await schema_repo.get_tbox_classes()
        relations = await schema_repo.get_schema_relations()
        assert len(classes) >= 8  # минимум базовых
        assert len(relations) >= 15

    async def test_second_seed_without_force_adds_nothing(self, schema_repo):
        use_case = SeedTboxUseCase(schema_repo=schema_repo)
        await use_case.execute(force=False)

        count = await use_case.execute(force=False)

        assert count == 0

    async def test_seed_with_force_updates_existing(self, schema_repo):
        use_case = SeedTboxUseCase(schema_repo=schema_repo)
        await use_case.execute(force=False)

        count = await use_case.execute(force=True)

        assert count > 0