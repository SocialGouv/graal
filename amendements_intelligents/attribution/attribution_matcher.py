from typing import Optional, Set

from rapidfuzz import fuzz


class AttributionMatcher:
    def find_best_match(
        self, target_text: str, candidates: Set[str], threshold: int
    ) -> Optional[str]:
        """Find the best matching string in a set based on a similarity threshold."""
        best_match = max(
            candidates,
            key=lambda candidate: fuzz.partial_ratio(target_text, candidate),
            default=None,
        )
        if best_match and fuzz.partial_ratio(target_text, best_match) > threshold:
            return best_match
        return None

    def fuzzy_match(
        self, amendment: dict, keywords: Set[str], threshold: int
    ) -> list[dict[str, str]]:
        """Perform fuzzy matching of keywords against amendment text."""
        num_amdt, lecture, text = (
            amendment["Num amdt"],
            amendment["Lecture"],
            amendment["Corps amdt"],
        )
        return [
            {"Num amdt": num_amdt, "Lecture": lecture, "Keyword": keyword}
            for keyword in keywords
            if fuzz.partial_ratio(keyword, text) >= threshold
        ]
