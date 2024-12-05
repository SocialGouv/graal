"""
This module provides the AttributionPopulator class, which is responsible for populating attributions
for amendments based on matching codes, laws, ordonnances, and keywords. The class uses regular expressions
and keyword or sentence matching to identify relevant entities and articles within the text of amendments
and assigns attributions accordingly.
"""

import re
from multiprocessing import Pool, cpu_count
from typing import Any

import numpy as np
import pandas as pd

from graal.attribution.attribution_matcher import AttributionMatcher
from graal.custom_types import ColumnName, EntityType


class AttributionPopulator:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        attribution_mappings_when_empty: list[str],
        codes_articles_df: pd.DataFrame,
        laws_articles_df: pd.DataFrame,
        ordonnances_articles_df: pd.DataFrame,
        keywords_df: pd.DataFrame,
        name_to_email_mapping: dict[str, str],
        interstitial_only: bool = False,
    ):
        # Initialize sets and max lengths for codes, laws, and ordonnances
        codes_set = (
            set(codes_articles_df["value"])
            if codes_articles_df is not None and not codes_articles_df.empty
            else set()
        )

        laws_set = (
            set(laws_articles_df["value"])
            if laws_articles_df is not None and not laws_articles_df.empty
            else set()
        )

        ordonnances_set = (
            set(ordonnances_articles_df["value"])
            if ordonnances_articles_df is not None and not ordonnances_articles_df.empty
            else set()
        )

        # Combine articles from all sources
        articles_set = set()
        if "Articles" in codes_articles_df.columns:
            articles_set.update(codes_articles_df["Articles"])
        if "Articles" in laws_articles_df.columns:
            articles_set.update(laws_articles_df["Articles"])
        if "Articles" in ordonnances_articles_df.columns:
            articles_set.update(ordonnances_articles_df["Articles"])
        articles_set.discard("nan")

        self.patterns = {
            EntityType.CODE.value: [
                re.compile(
                    rf"code\s(?:general\sdes|des|du|de|de\sla|d')?\s?((?:{'|'.join(codes_set)}))"
                )
            ],
            EntityType.LAW.value: [
                re.compile(
                    r"\sloi\s(?:n.?(?:deg)?\s?)((?:(?:\d+-\d+)\s+)?du\s+(?:\d+\s\w+\s\d{4}))"
                ),
                re.compile(r"\sloi\s(du\s+(?:\d+\s\w+\s\d{4}))"),
            ],
            EntityType.ORDONNANCE.value: [
                re.compile(
                    r"ordonnance\s(?:n.?(?:deg)?\s?)((?:(?:\d+-\d+)\s+)?du\s+(?:\d+\s\w+\s\d{4}))"
                )
            ],
        }

        latin_ordinal_pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
        latin_ordinals_set = {
            match.group(1)
            for article in articles_set
            if (match := latin_ordinal_pattern.match(article)) and match.group(1)
        }
        possible_ordinals_pattern = "|".join(sorted(latin_ordinals_set, reverse=True))
        self.article_pattern = re.compile(
            rf"(?:(?:l\.|articles?|art\.?))(?:\set\s|\s?(\d+(?:-\d+)*(?:\s?(?:{possible_ordinals_pattern}))?))+"
        )

        self.matcher = AttributionMatcher()
        self.amendments_df = amendments_df
        self.articles_set = articles_set
        self.codes_articles_df = codes_articles_df
        self.laws_articles_df = laws_articles_df
        self.ordonnances_articles_df = ordonnances_articles_df
        self.codes_set = codes_set
        self.laws_set = laws_set
        self.ordonnances_set = ordonnances_set
        self.keywords_df = keywords_df
        self.attribution_mappings_when_empty = attribution_mappings_when_empty
        self.name_to_email_mapping = name_to_email_mapping
        self.interstitial_only = interstitial_only

    @staticmethod
    def update_with_keyword_matches(
        row: pd.Series, keyword_matches_df: pd.DataFrame, column_name: str
    ) -> pd.Series:
        current_attribution_names = row.get("Affectation (nom)", [])

        # If there is only one attribution, no need to update it
        if current_attribution_names and len(current_attribution_names) == 1:
            return row

        # Retrieve keyword attributions from keyword_matches_df
        keyword_attribution = (
            keyword_matches_df.at[row.name, "Affectation (nom)"]
            if row.name in keyword_matches_df.index
            else []
        )

        # Ensure keyword_attribution is a set of strings, handling different data types
        keyword_attribution_names = set(
            keyword_attribution
            if isinstance(keyword_attribution, list)
            else [keyword_attribution]
            if isinstance(keyword_attribution, str)
            else []
        )

        # Update "Affectation (nom)" based on conditions
        if not current_attribution_names:
            row["Affectation (nom)"] = sorted(keyword_attribution_names)
        else:
            intersecting_names = set(current_attribution_names).intersection(
                keyword_attribution_names
            )
            if intersecting_names:
                row["Affectation (nom)"] = sorted(intersecting_names)
            else:
                return row  # No intersecting names, no update

        # Update "Commentaires" if "Affectation (nom)" was modified
        if row["Affectation (nom)"]:
            row["Commentaires"] += (
                f"Affectations possibles après affectation par mots clés dans '{column_name}' : {', '.join(row['Affectation (nom)'])}\n"
            )

        return row

    def match_entities_and_articles_to_amendments(
        self,
        column_name_to_match: ColumnName,
        entity_patterns: list[re.Pattern[str]],
    ) -> dict[str, dict[str, set[str]]]:
        """Find the best matching entities (codes or laws) and articles for each amendment."""
        matches_per_amdt = {}

        for _, row in self.amendments_df.iterrows():
            normalized_text = row[column_name_to_match]
            amdt_idx = row["amdt_idx"]

            # Collect all entity matches for the given entity type
            matched_entities = set()
            for entity_pattern in entity_patterns:
                matches = re.findall(entity_pattern, normalized_text)
                if matches:
                    matched_entities.update(matches)
            if not matched_entities:
                continue

            article_matches = set(re.findall(self.article_pattern, normalized_text))
            matched_articles = {
                article.strip() for article in article_matches
            }.intersection(self.articles_set)

            if matched_articles:
                matches_per_amdt[amdt_idx] = {
                    "matching_entities": matched_entities,
                    "matching_articles": matched_articles,
                }

        return matches_per_amdt

    def match_codes_and_articles_to_amendments(
        self, column_name_to_match: ColumnName
    ) -> dict[str, dict[str, set[str]]]:
        """Find the best matching codes and articles for each amendment."""
        return self.match_entities_and_articles_to_amendments(
            column_name_to_match=column_name_to_match,
            entity_patterns=self.patterns.get(EntityType.CODE.value, []),
        )

    def match_laws_and_articles_to_amendments(
        self, column_name_to_match: ColumnName
    ) -> dict[str, dict[str, set[str]]]:
        """Find the best matching laws and articles for each amendment."""
        return self.match_entities_and_articles_to_amendments(
            column_name_to_match=column_name_to_match,
            entity_patterns=self.patterns.get(EntityType.LAW.value, []),
        )

    def match_ordonnances_and_articles_to_amendments(
        self, column_name_to_match: ColumnName
    ) -> dict[str, dict[str, set[str]]]:
        """Find the best matching ordonnances and articles for each amendment."""
        return self.match_entities_and_articles_to_amendments(
            column_name_to_match=column_name_to_match,
            entity_patterns=self.patterns.get(EntityType.ORDONNANCE.value, []),
        )

    def filter_matching_entities_and_articles(
        self, matches_per_amdt: dict[str, dict[str, set[str]]]
    ) -> pd.DataFrame:
        """Retrieve rows from the codes and articles DataFrame that match the amendments."""
        matching_rows_df = pd.DataFrame(
            columns=[
                "Affectation (nom)",
                "Articles",
                "value",
                "Corps amdt",
                "amdt_idx",
            ]
        )

        for amdt_idx, matches in matches_per_amdt.items():
            matched_codes = (
                self.codes_articles_df[
                    self.codes_articles_df["value"].isin(matches["matching_entities"])
                    & self.codes_articles_df["Articles"].isin(
                        matches["matching_articles"]
                    )
                ].copy()
                if "value" in self.codes_articles_df.columns
                else pd.DataFrame()
            )
            matched_laws = (
                self.laws_articles_df[
                    self.laws_articles_df["value"].isin(matches["matching_entities"])
                    & self.laws_articles_df["Articles"].isin(
                        matches["matching_articles"]
                    )
                ].copy()
                if "value" in self.laws_articles_df.columns
                else pd.DataFrame()
            )
            matched_ordonnances = (
                self.ordonnances_articles_df[
                    self.ordonnances_articles_df["value"].isin(
                        matches["matching_entities"]
                    )
                    & self.ordonnances_articles_df["Articles"].isin(
                        matches["matching_articles"]
                    )
                ].copy()
                if "value" in self.ordonnances_articles_df.columns
                else pd.DataFrame()
            )

            matched_rows = pd.concat([matched_codes, matched_laws, matched_ordonnances])

            if not matched_rows.empty:
                matched_rows["amdt_idx"] = amdt_idx
                matched_rows["Corps amdt"] = self.amendments_df.loc[
                    self.amendments_df["amdt_idx"] == amdt_idx, "Corps amdt"
                ].values[0]
                matching_rows_df = pd.concat([matching_rows_df, matched_rows])

        return matching_rows_df

    def aggregate_matches_by_amendment(
        self, matching_rows_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Group matching rows by amendment index."""
        return (
            matching_rows_df.groupby("amdt_idx")
            .agg({"Affectation (nom)": lambda x: list(sorted(set(x)))})
            .reset_index()
        )

    def match_keywords_to_amendments(
        self, column_name_to_match: ColumnName
    ) -> pd.DataFrame:
        """Find keyword matches for the amendments."""
        keywords = set(self.keywords_df["Mots clés"].dropna())
        keyword_matches = self.parallel_keyword_fuzzy_matching(
            column_name_to_match, keywords
        )
        if not keyword_matches:
            return pd.DataFrame()

        return pd.DataFrame(keyword_matches).merge(
            self.keywords_df, left_on="keyword", right_on="Mots clés"
        )

    def parallel_keyword_fuzzy_matching(
        self, column_name_to_match: ColumnName, keywords: set[str]
    ) -> list[dict[str, Any]]:
        """Parallel fuzzy matching of keywords."""
        amendments = self.amendments_df.to_dict(orient="records")
        with Pool(cpu_count()) as pool:
            results = pool.starmap(
                AttributionMatcher.fuzzy_match,
                [
                    (amendment, column_name_to_match, keywords)
                    for amendment in amendments
                ],
            )
        return [match for sublist in results for match in sublist]

    @staticmethod
    def append_comment_to_amendment(
        amendments_df: pd.DataFrame, index: int, attribution_comment: str
    ) -> None:
        if (
            "Commentaires" in amendments_df.columns
            and amendments_df.at[index, "Commentaires"]
            and pd.notna(amendments_df.at[index, "Commentaires"])
        ):
            amendments_df.at[index, "Commentaires"] += "\n" + attribution_comment
        else:
            amendments_df.at[index, "Commentaires"] = attribution_comment

    @staticmethod
    def calculate_ratio_of_lists(amendments_df: pd.DataFrame) -> float:
        """Calculate the ratio of lists with more than 1 element to lists with more than 0 elements."""
        count_lists_greater_than_1 = (
            amendments_df["Affectation (nom)"]
            .apply(lambda x: len(x) if isinstance(x, list) else 0)
            .gt(1)
            .sum()
        )
        count_lists_greater_than_0 = (
            amendments_df["Affectation (nom)"]
            .apply(lambda x: len(x) if isinstance(x, list) else 0)
            .gt(0)
            .sum()
        )

        return (
            (count_lists_greater_than_1 / count_lists_greater_than_0)
            if count_lists_greater_than_0 > 0
            else 0
        )

    def populate(self):
        # Step 0: Filter out interstitial amendments that should be ignored based on "Num article" if `interstitial_only` is True
        if self.interstitial_only:
            relevant_amendments_df = self.amendments_df[
                self.amendments_df["Num article"]
                .str.lower()
                .str.startswith("article add.")
            ].copy()
        else:
            relevant_amendments_df = self.amendments_df.copy()

        # Step 1: Match codes, laws, ordonnances and articles to amendments
        best_code_matches_per_amdt = self.match_codes_and_articles_to_amendments(
            column_name_to_match="Corps amdt"
        )
        best_law_matches_per_amdt = self.match_laws_and_articles_to_amendments(
            column_name_to_match="Corps amdt"
        )
        best_ordonnance_matches_per_amdt = (
            self.match_ordonnances_and_articles_to_amendments(
                column_name_to_match="Corps amdt"
            )
        )
        best_matches_per_amdt = {
            **best_code_matches_per_amdt,
            **best_law_matches_per_amdt,
            **best_ordonnance_matches_per_amdt,
        }
        matching_rows_df = self.filter_matching_entities_and_articles(
            best_matches_per_amdt
        )
        grouped_matching_df = self.aggregate_matches_by_amendment(matching_rows_df)

        # Working on the filtered amendments DataFrame
        relevant_amendments_df["Commentaires"] = ""
        if not grouped_matching_df.empty:
            relevant_amendments_df.set_index("amdt_idx", inplace=True)
            relevant_amendments_df["Affectation (nom)"] = grouped_matching_df.set_index(
                "amdt_idx"
            )["Affectation (nom)"]
            relevant_amendments_df["Affectation (nom)"] = relevant_amendments_df[
                "Affectation (nom)"
            ].apply(
                lambda x: x if isinstance(x, list) else [x] if pd.notnull(x) else []
            )

            relevant_amendments_df["Commentaires"] += relevant_amendments_df.apply(
                lambda row: f"Affectations possibles après affectation par articles : {', '.join(row['Affectation (nom)'])}\n"
                if row["Affectation (nom)"]
                else row.get("Commentaires", ""),
                axis=1,
            )
            relevant_amendments_df.reset_index(inplace=True)

        # Step 2: Match keywords to amendments on both "Corps amdt" and "Exposé amdt" columns
        for column_name in ["Corps amdt", "Exposé amdt"]:
            keyword_matches_df = self.match_keywords_to_amendments(
                column_name_to_match=column_name
            )
            if not keyword_matches_df.empty:
                keyword_matches_df.set_index("amdt_idx", inplace=True)
                keyword_matches_df.sort_index(inplace=True)
                relevant_amendments_df.set_index("amdt_idx", inplace=True)

                relevant_amendments_df = relevant_amendments_df.apply(
                    AttributionPopulator.update_with_keyword_matches,
                    axis=1,
                    keyword_matches_df=keyword_matches_df,
                    column_name=column_name,
                )
                relevant_amendments_df.reset_index(inplace=True)

        # Step 3: Handle multiple attributions and random selections
        multiple_attributions = relevant_amendments_df[
            relevant_amendments_df["Affectation (nom)"].apply(
                lambda x: isinstance(x, list) and len(x) > 1
            )
        ]
        multiple_indices = multiple_attributions.index

        for index in multiple_indices:
            random_attribution = np.random.choice(
                relevant_amendments_df.at[index, "Affectation (nom)"],
            )
            removed_attributions = [
                attribution
                for attribution in relevant_amendments_df.at[index, "Affectation (nom)"]
                if attribution != random_attribution
            ]
            relevant_amendments_df.at[index, "Affectation (nom)"] = [random_attribution]
            attribution_comment = "Autres attributions possibles :\n- " + "\n- ".join(
                removed_attributions
            )
            AttributionPopulator.append_comment_to_amendment(
                amendments_df=relevant_amendments_df,
                index=index,
                attribution_comment=attribution_comment,
            )

        # Step 4: Handle missing attributions
        missing_attributions = relevant_amendments_df[
            relevant_amendments_df["Affectation (nom)"].apply(
                lambda x: (isinstance(x, list) and len(x) == 0) or x is None
            )
        ]
        missing_indices = missing_attributions.index

        for index in missing_indices:
            random_attribution = np.random.choice(self.attribution_mappings_when_empty)
            relevant_amendments_df.at[index, "Affectation (nom)"] = [random_attribution]
            attribution_comment = "Attribution par défaut"
            AttributionPopulator.append_comment_to_amendment(
                amendments_df=relevant_amendments_df,
                index=index,
                attribution_comment=attribution_comment,
            )

        # Set the value of "Affectation (nom)" and populate emails
        relevant_amendments_df["Affectation (nom)"] = relevant_amendments_df[
            "Affectation (nom)"
        ].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None)
        relevant_amendments_df["Affectation (email)"] = relevant_amendments_df[
            "Affectation (nom)"
        ].apply(lambda x: self.name_to_email_mapping.get(x, ""))

        # Ensure 'amdt_idx' is set as the index for both DataFrames
        relevant_amendments_df.set_index("amdt_idx", inplace=True)
        self.amendments_df.set_index("amdt_idx", inplace=True)

        # Merge the relevant amendments back into the original DataFrame
        # Use `combine_first` to overwrite existing rows in `self.amendments_df` with `relevant_amendments_df`
        self.amendments_df = self.amendments_df.combine_first(relevant_amendments_df)

        # Reset the index to have 'amdt_idx' as a regular column, if needed
        self.amendments_df.reset_index(inplace=True)

        return self.amendments_df
