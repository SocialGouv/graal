from typing import Set

from graal.types import ColumnName


class AttributionMatcher:
    @staticmethod
    def fuzzy_match(
        amendment: dict, column_name_to_match: ColumnName, keywords: Set[str]
    ) -> list[dict[str, str]]:
        """Perform fuzzy matching of keywords against amendment text."""
        amdt_words = amendment[column_name_to_match].split()
        results = []
        for keyword in keywords:
            keyword_words = keyword.split()
            for word in keyword_words:
                # As soon as a word matches, make sure all the following words match, in order. If all of them do then record it.
                start_indexes = [i for i, w in enumerate(amdt_words) if w == word]
                for start_idx in start_indexes:
                    if start_idx != -1:
                        end_idx = start_idx + len(keyword_words)
                        if amdt_words[start_idx:end_idx] == keyword_words:
                            results.append(
                                {
                                    "amdt_idx": amendment["amdt_idx"],
                                    "keyword": keyword,
                                }
                            )
                            break
        return results
