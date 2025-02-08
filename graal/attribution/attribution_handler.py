"""Handler for coordinating matchers and managing attributions."""

import logging
import logging.config
import random
from collections import Counter
from multiprocessing import Manager, Pool, cpu_count
from multiprocessing.managers import DictProxy
from typing import Optional

import pandas as pd

from graal.attribution.matchers.base_matcher import BaseMatcher
from graal.custom_types import AttributionColumns

logging.config.fileConfig("logging.conf")


class AttributionHandler:
    """Coordinates matchers and handles attribution logic."""

    def __init__(
        self,
        matchers: list[BaseMatcher],
        default_attributions: list[str],
        name_to_user_info_mapping: dict[str, dict[str, str]],
        columns_to_match_on: Optional[list[AttributionColumns]] = None,
    ):
        """
        Initialize the AttributionHandler.

        Args:
            matchers: List of matcher instances to use for finding attributions
            default_attributions: List of attribution names to use when no matches found
            name_to_user_info_mapping: Mapping of names to user info (email, entity)
            columns_to_match: List of column names to match against (default: ["Corps amdt", "Exposé amdt"])
        """
        self.matchers = matchers
        self.default_attributions = default_attributions
        self.name_to_user_info_mapping = name_to_user_info_mapping
        self.columns_to_match_on = columns_to_match_on or ["Corps amdt", "Exposé amdt"]

    def _get_matches_for_amendment(
        self, amendment: dict, column_name: str
    ) -> list[dict[str, str]]:
        """Get matches from all matchers for a single amendment and column."""
        all_matches = []
        for matcher in self.matchers:
            matches = matcher.match(amendment, column_name)
            if matches:
                all_matches.extend(matches)
        return all_matches

    def _select_match(self, matches: list[dict[str, str]]) -> Optional[str]:
        """
        Select a single attribution from multiple matches.

        Current strategy: Select the attribution that appears most often in matches.
        If there is a tie, select one of them at random.
        """
        if not matches:
            return None

        attribution_counts = Counter(match["attribution"] for match in matches)
        max_count = max(attribution_counts.values())
        most_common_attributions = [
            attribution
            for attribution, count in attribution_counts.items()
            if count == max_count
        ]

        return random.choice(most_common_attributions)

    def _get_attribution_comments(
        self, matches: list[dict[str, str]], selected_attribution: str
    ) -> str:
        """Generate attribution comments from matchers and selection process."""
        matches_excluding_selected = [
            match for match in matches if match["attribution"] != selected_attribution
        ]

        # Get matches for selected attribution
        selected_matches = [
            match for match in matches if match["attribution"] == selected_attribution
        ]

        # Group selected matches by matcher type
        full_comment = f"Affectation sélectionnée: {selected_attribution}"
        for matcher in self.matchers:
            matcher_matches = [
                match
                for match in selected_matches
                if match["matcher_type"] == matcher.matcher_type
            ]
            if matcher_matches:
                comment = matcher.get_attribution_comment(matcher_matches)
                full_comment = f"{full_comment}\n{comment}"

        # Add other matches
        for matcher in self.matchers:
            related_matches = [
                match
                for match in matches_excluding_selected
                if match["matcher_type"] == matcher.matcher_type
            ]
            if related_matches:
                comment = matcher.get_attribution_comment(related_matches)
                full_comment = (
                    f"{full_comment}\n\nAutres affectations possibles:\n{comment}"
                )

        return full_comment

    def _process_single_amendments(
        self, idx: int, shared_result_dict: DictProxy
    ) -> None:
        # Get matches from all matchers across specified columns
        amendment = shared_result_dict[idx]
        all_matches = []
        for column in self.columns_to_match_on:
            if column in amendment:
                matches = self._get_matches_for_amendment(amendment, column)
                if matches:
                    all_matches.extend(matches)

        # Select attribution and generate comments
        selected_attribution = self._select_match(all_matches)

        if selected_attribution:
            amendment["Affectation (nom)"] = selected_attribution
            comments = self._get_attribution_comments(all_matches, selected_attribution)
        else:  # No matches found, use default attribution
            amendment["Affectation (nom)"] = random.choice(self.default_attributions)
            comments = "Attribution par défaut"

        # Add user info
        user_info = self.name_to_user_info_mapping.get(
            amendment["Affectation (nom)"], {}
        )
        amendment["Affectation (email)"] = user_info.get("Mail", "")
        amendment["Entité Pilote"] = user_info.get("Entité Pilote", "")

        # Update comments
        if comments:
            current_comments = amendment["Commentaires"]
            amendment["Commentaires"] = (
                f"{current_comments}\n{comments}" if current_comments else comments
            )
        # Update the entire dictionary entry
        shared_result_dict[idx] = amendment

    def process_amendments(self, amendments_df: pd.DataFrame) -> pd.DataFrame:
        """
        Process amendments to determine attributions.

        Args:
            amendments_df: DataFrame containing amendments to process

        Returns:
            DataFrame with added attribution columns:
            - Affectation (nom): Selected attribution name
            - Affectation (email): Email for selected attribution
            - Entité Pilote: Entity for selected attribution
            - Commentaires: Attribution process comments
        """
        amendments_df["Commentaires"] = ""

        # Create a Manager to handle shared data
        manager = Manager()
        amendments = amendments_df.to_dict(orient="records")
        shared_result_dict = manager.dict(dict(enumerate(amendments)))

        with Pool(cpu_count()) as pool:
            pool.starmap(
                self._process_single_amendments,
                [(idx, shared_result_dict) for idx in range(len(amendments))],
            )

        # Convert shared_result_dict back to DataFrame
        amendments_df = pd.DataFrame.from_dict(shared_result_dict, orient="index")
        return amendments_df
