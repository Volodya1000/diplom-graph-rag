"""
Гибридный Entity Resolution: Левенштейн + косинусное сходство.

Логика:
  1. Точное совпадение имени → безусловный match
  2. Очень высокий Левенштейн (≥0.95) → match (опечатки)
  3. Левенштейн ≥ порога + совпадение типа → match
  4. Иначе → нет совпадения
"""

from typing import List, Optional

import Levenshtein

from src.domain.models import RawExtractedEntity, InstanceNode


class EntityResolutionMatcher:
    def __init__(
        self,
        levenshtein_threshold: float = 0.85,
        strict_name_threshold: float = 0.95,
    ):
        self.levenshtein_threshold = levenshtein_threshold
        self.strict_name_threshold = strict_name_threshold

    # ------------------------------------------------------------------

    @staticmethod
    def _name_similarity(a: str, b: str) -> float:
        a_clean = a.strip().lower()
        b_clean = b.strip().lower()
        if not a_clean or not b_clean:
            return 0.0
        dist = Levenshtein.distance(a_clean, b_clean)
        max_len = max(len(a_clean), len(b_clean))
        return 1.0 - (dist / max_len)

    # ------------------------------------------------------------------

    def find_best_match(
        self,
        target: RawExtractedEntity,
        candidates: List[InstanceNode],
    ) -> Optional[str]:
        """
        Ищет лучшее совпадение среди кандидатов.

        Кандидаты уже отфильтрованы по векторному сходству
        (приходят из find_candidates_by_vector).

        Returns:
            instance_id лучшего совпадения или None.
        """
        target_name = target.name.strip().lower()
        target_type = target.type.strip().lower()

        best_id: Optional[str] = None
        best_score: float = 0.0

        for cand in candidates:
            cand_name = cand.name.strip().lower()
            cand_type = cand.class_name.strip().lower()

            sim = self._name_similarity(target_name, cand_name)

            # Правило 1: Точное совпадение имени → безусловный match
            if target_name == cand_name:
                return cand.instance_id

            # Правило 2: Очень высокий Левенштейн → match
            # (даже если тип другой — это скорее дрифт LLM)
            if sim >= self.strict_name_threshold:
                if sim > best_score:
                    best_score = sim
                    best_id = cand.instance_id
                continue

            # Правило 3: Высокий Левенштейн + совпадение типа → match
            if sim >= self.levenshtein_threshold and target_type == cand_type:
                if sim > best_score:
                    best_score = sim
                    best_id = cand.instance_id

        return best_id