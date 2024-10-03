import logging
import re
from heapq import merge
from multiprocessing import Pool, cpu_count
from typing import Any

import numpy as np
import pandas as pd

from amendements_intelligents.attribution.attribution_matcher import AttributionMatcher


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
        ignore_interstitial_amdts: bool = True,
    ):
        codes_set = set(codes_articles_df["value"])
        max_code_length = max((len(code) for code in codes_set), default=2)
        laws_set = set(laws_articles_df["value"])
        max_law_length = max((len(law) for law in laws_set), default=2)
        ordonnances_set = set(ordonnances_articles_df["value"])
        max_ordonnance_length = max(
            (len(ordonnance) for ordonnance in ordonnances_set), default=2
        )
        articles_set = (
            set(codes_articles_df["Articles"])
            .union(set(laws_articles_df["Articles"]))
            .union(set(ordonnances_articles_df["Articles"]))
        )
        pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
        latin_ordinals_set = {
            match.group(1)
            for article in articles_set
            if (match := pattern.match(article)) and match.group(1)
        }
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
        self.latin_ordinals_set = latin_ordinals_set
        self.max_code_length = max_code_length
        self.max_law_length = max_law_length
        self.max_ordonnance_length = max_ordonnance_length
        self.attribution_mappings_when_empty = attribution_mappings_when_empty
        self.name_to_email_mapping = name_to_email_mapping
        self.ignore_interstitial_amdts = ignore_interstitial_amdts

    @staticmethod
    def update_with_keyword_matches(
        row: pd.Series, keyword_matches_df: pd.DataFrame
    ) -> list:
        current_attribution_names = row["Affectation (nom)"]
        value = (
            keyword_matches_df.loc[row.name]["Affectation (nom)"]
            if row.name in keyword_matches_df.index
            else []
        )
        keyword_attribution_names = set(
            value.values
            if hasattr(value, "values")
            else [value]
            if isinstance(value, str)
            else value
        )

        if not current_attribution_names:
            return sorted(keyword_attribution_names)

        if len(current_attribution_names) == 1:
            return list(current_attribution_names)

        common_names = sorted(
            set(current_attribution_names).intersection(keyword_attribution_names)
        )
        if not common_names:
            return sorted(current_attribution_names)
        return common_names

    def match_entities_and_articles_to_amendments(
        self, entity_type: str, entity_set: set[str], max_entity_length: int
    ) -> dict[str, dict[str, set[str]]]:
        """Find the best matching entities (codes or laws) and articles for each amendment."""
        matches_per_amdt = {}
        possible_ordinals_pattern = "|".join(
            sorted(self.latin_ordinals_set, reverse=True)
        )

        patterns = {
            "code": rf"code [\w']+(?:\s[\w']{{1,{max_entity_length}}})+",
            "law": rf"loi n.\s?[\w\s\-]{{1,{max_entity_length}}}",
            "ordonnance": rf"ordonnance n.\s?[\w\s\-]{{1,{max_entity_length}}}",
        }
        entity_pattern = patterns.get(entity_type, "")

        for _, row in self.amendments_df.iterrows():
            normalized_text = row["Corps amdt"]
            amdt_idx = row["amdt_idx"]

            entity_matches = re.findall(entity_pattern, normalized_text)
            matched_entities = {
                self.matcher.find_best_match(match, entity_set, threshold=60)
                for match in entity_matches
                if match is not None
            }
            matched_entities = {
                entity for entity in matched_entities if entity is not None
            }

            article_pattern = rf"(?:(?:l\.|articles?|art))+(?: et |\s?(\d+(?:-\d+)*(?:\s?(?:{possible_ordinals_pattern}))?))+"
            article_matches = set(re.findall(article_pattern, normalized_text))
            matched_articles = {
                article.strip() for article in article_matches
            }.intersection(self.articles_set)

            if matched_entities and matched_articles:
                matches_per_amdt[amdt_idx] = {
                    "matching_entities": matched_entities,
                    "matching_articles": matched_articles,
                }

        return matches_per_amdt

    def match_codes_and_articles_to_amendments(self) -> dict[str, dict[str, set[str]]]:
        """Find the best matching codes and articles for each amendment."""
        return self.match_entities_and_articles_to_amendments(
            entity_type="code",
            entity_set=self.codes_set,
            max_entity_length=self.max_code_length,
        )

    def match_laws_and_articles_to_amendments(self) -> dict[str, dict[str, set[str]]]:
        """Find the best matching laws and articles for each amendment."""
        return self.match_entities_and_articles_to_amendments(
            entity_type="law",
            entity_set=self.laws_set,
            max_entity_length=self.max_law_length,
        )

    def match_ordonnances_and_articles_to_amendments(
        self,
    ) -> dict[str, dict[str, set[str]]]:
        """Find the best matching ordonnances and articles for each amendment."""
        return self.match_entities_and_articles_to_amendments(
            entity_type="ordonnance",
            entity_set=self.ordonnances_set,
            max_entity_length=self.max_ordonnance_length,
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
            matched_codes = self.codes_articles_df[
                self.codes_articles_df["value"].isin(matches["matching_entities"])
                & self.codes_articles_df["Articles"].isin(matches["matching_articles"])
            ].copy()
            matched_laws = self.laws_articles_df[
                self.laws_articles_df["value"].isin(matches["matching_entities"])
                & self.laws_articles_df["Articles"].isin(matches["matching_articles"])
            ].copy()
            matched_ordonnances = self.ordonnances_articles_df[
                self.ordonnances_articles_df["value"].isin(matches["matching_entities"])
                & self.ordonnances_articles_df["Articles"].isin(
                    matches["matching_articles"]
                )
            ].copy()

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

    def match_keywords_to_amendments(self, threshold: int = 75) -> pd.DataFrame:
        """Find keyword matches for the amendments."""
        matcher = AttributionMatcher()
        keywords = set(self.keywords_df["Mots clés"].dropna())
        keyword_matches = self.parallel_keyword_fuzzy_matching(
            keywords, matcher, threshold
        )
        if not keyword_matches:
            return pd.DataFrame()

        return pd.DataFrame(keyword_matches).merge(
            self.keywords_df, left_on="Keyword", right_on="Mots clés"
        )

    def parallel_keyword_fuzzy_matching(
        self, keywords: set[str], matcher: AttributionMatcher, threshold: int
    ) -> list[dict[str, Any]]:
        """Parallel fuzzy matching of keywords."""
        amendments = self.amendments_df.to_dict(orient="records")
        with Pool(cpu_count()) as pool:
            results = pool.starmap(
                matcher.fuzzy_match,
                [(amendment, keywords, threshold) for amendment in amendments],
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
        # Step 1: Match codes and articles to amendments
        best_code_matches_per_amdt = self.match_codes_and_articles_to_amendments()
        best_law_matches_per_amdt = self.match_laws_and_articles_to_amendments()
        best_ordonnance_matches_per_amdt = (
            self.match_ordonnances_and_articles_to_amendments()
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
        amendments_df = self.amendments_df
        if "Commentaires" not in amendments_df.columns:
            amendments_df["Commentaires"] = ""

        if not grouped_matching_df.empty:
            amendments_df.set_index("amdt_idx", inplace=True)
            amendments_df["Affectation (nom)"] = grouped_matching_df.set_index(
                "amdt_idx"
            )["Affectation (nom)"]
            amendments_df["Affectation (nom)"] = amendments_df[
                "Affectation (nom)"
            ].apply(
                lambda x: x if isinstance(x, list) else [x] if pd.notnull(x) else []
            )

            ratio = AttributionPopulator.calculate_ratio_of_lists(amendments_df)
            logging.info(
                f"After articles, ratio of lists > 1 vs lists > 0 in 'Affectation (nom)': {ratio:.2f}"
            )

            amendments_df["Commentaires"] += amendments_df.apply(
                lambda row: f"Affectations possibles après affectation par articles : {', '.join(row['Affectation (nom)'])}\n"
                if row["Affectation (nom)"]
                else row.get("Commentaires", ""),
                axis=1,
            )
            amendments_df.reset_index(inplace=True)

        # Step 2: Match keywords to amendments
        keyword_matches_df = self.match_keywords_to_amendments(threshold=99)
        if not keyword_matches_df.empty:
            keyword_matches_df.set_index("amdt_idx", inplace=True)
            keyword_matches_df.sort_index(inplace=True)
            amendments_df.set_index("amdt_idx", inplace=True)

            amendments_df["Affectation (nom)"] = amendments_df.apply(
                AttributionPopulator.update_with_keyword_matches,
                axis=1,
                keyword_matches_df=keyword_matches_df,
            )

            ratio = AttributionPopulator.calculate_ratio_of_lists(amendments_df)
            logging.info(
                f"After keywords, ratio of lists > 1 vs lists > 0 in 'Affectation (nom)': {ratio:.2f}"
            )

            amendments_df["Commentaires"] += amendments_df.apply(
                lambda row: f"Affectations possibles après affectation par mots clés : {', '.join(row['Affectation (nom)'])}\n"
                if row["Affectation (nom)"]
                else row.get("Commentaires", ""),
                axis=1,
            )
            amendments_df.reset_index(inplace=True)

        # Step 3: If multiple attributions are present, choose one attribution at random and add the ones that were removed in the "Commentaires" column
        multiple_attributions = amendments_df[
            amendments_df["Affectation (nom)"].apply(
                lambda x: isinstance(x, list) and len(x) > 1
            )
        ]
        multiple_indices = multiple_attributions.index

        for index in multiple_indices:
            random_attribution = np.random.choice(
                amendments_df.at[index, "Affectation (nom)"],
            )
            removed_attributions = [
                attribution
                for attribution in amendments_df.at[index, "Affectation (nom)"]
                if attribution != random_attribution
            ]
            amendments_df.at[index, "Affectation (nom)"] = [random_attribution]
            attribution_comment = "Autres attributions possibles :\n- " + "\n- ".join(
                removed_attributions
            )
            AttributionPopulator.append_comment_to_amendment(
                amendments_df=amendments_df,
                index=index,
                attribution_comment=attribution_comment,
            )

        # Step 4: Fill in missing attributions
        missing_attributions = amendments_df[
            amendments_df["Affectation (nom)"].apply(
                lambda x: (isinstance(x, list) and len(x) == 0) or x is None
            )
        ]

        missing_indices = missing_attributions.index

        for index in missing_indices:
            random_attribution = np.random.choice(self.attribution_mappings_when_empty)
            amendments_df.at[index, "Affectation (nom)"] = [random_attribution]
            attribution_comment = "Attribution par défault"
            AttributionPopulator.append_comment_to_amendment(
                amendments_df=amendments_df,
                index=index,
                attribution_comment=attribution_comment,
            )

        # Finally, set the value of "Affectation (nom)" to the first (and only) element of the list
        # and we get the email address of the expert from self.name_to_email_mapping in "Affectation (email)"
        amendments_df["Affectation (nom)"] = amendments_df["Affectation (nom)"].apply(
            lambda x: x[0] if isinstance(x, list) and len(x) > 0 else None
        )
        amendments_df["Affectation (email)"] = amendments_df["Affectation (nom)"].apply(
            lambda x: self.name_to_email_mapping.get(x, "")
        )

        ratio = AttributionPopulator.calculate_ratio_of_lists(amendments_df)
        logging.info(
            f"At the end, ratio of lists > 1 vs lists > 0 in 'Affectation (nom)': {ratio:.2f}"
        )

        non_empty_email_count = (
            amendments_df["Affectation (email)"].str.len().gt(0).sum()
        )
        logging.info(
            f"Number of rows with non-empty 'Affectation (email)': {non_empty_email_count}"
        )

        # Not super proud of this since I am undoing a lot of the work I did above but I can't make
        # a pre-filtering step work for some reason so this will do (it's not a big time waste)
        if self.ignore_interstitial_amdts:
            amendments_df.loc[
                ~amendments_df["Num article"]
                .str.lower()
                .str.startswith("article add."),
                ["Affectation (nom)", "Affectation (email)"],
            ] = "", ""

        return amendments_df
