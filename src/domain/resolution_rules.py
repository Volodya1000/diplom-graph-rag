from typing import List, Optional
from src.domain.models import RawExtractedEntity, InstanceNode
import Levenshtein


class EntityResolutionMatcher:
    """Чистая логика Entity Resolution (без БД)"""

    def __init__(self, levenshtein_threshold: float = 0.85):
        self.levenshtein_threshold = levenshtein_threshold

    def find_best_match(self, target: RawExtractedEntity, candidates: List[InstanceNode]) -> Optional[str]:
        target_name_clean = target.name.strip().lower()

        for candidate in candidates:
            # Правило 1: Тип T-Box должен совпадать
            if target.type.lower() != candidate.class_name.lower():
                continue

            candidate_name_clean = candidate.name.strip().lower()
            # Правило 2: Точное совпадение
            if target_name_clean == candidate_name_clean:
                return candidate.instance_id

            # Правило 3: Левенштейн
            distance = Levenshtein.distance(target_name_clean, candidate_name_clean)
            max_len = max(len(target_name_clean), len(candidate_name_clean))
            similarity = 1 - (distance / max_len)

            if similarity >= self.levenshtein_threshold:
                return candidate.instance_id

        return None