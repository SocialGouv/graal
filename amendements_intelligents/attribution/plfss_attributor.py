import logging
import re
from multiprocessing import Pool, cpu_count
from typing import Tuple

import numpy as np
import pandas as pd

from amendements_intelligents.attribution.attribution_matcher import AttributionMatcher


class PLFSSAttributor:
    def __init__(
        self,
        amendments_df: pd.DataFrame,
        articles_set: set[str],
        codes_articles_df: pd.DataFrame,
        codes_set: set[str],
        keywords_df: pd.DataFrame,
        latin_ordinals_set: set[str],
        max_code_length: int,
    ):
        self.matcher = AttributionMatcher()
        self.amendments_df = amendments_df
        self.articles_set = articles_set
        self.codes_articles_df = codes_articles_df
        self.codes_set = codes_set
        self.keywords_df = keywords_df
        self.latin_ordinals_set = latin_ordinals_set
        self.max_code_length = max_code_length
        self.best_matches_per_amdt = {}

    @staticmethod
    def update_affectation_row(row: pd.Series, keyword_matches_df: pd.DataFrame) -> str:
        affectation_names = row["Affectation (nom)"]
        keyword_affectation_names = set(
            keyword_matches_df.loc[row.name]["Affectation (nom)"]
            if row.name in keyword_matches_df.index
            else []
        )

        if affectation_names is np.nan or len(affectation_names) == 0:
            return ",".join(sorted(keyword_affectation_names))

        if len(affectation_names) == 1:
            return affectation_names[0]

        common_names = sorted(
            set(affectation_names).intersection(keyword_affectation_names)
        )
        if not common_names:
            return ",".join(sorted(affectation_names))
        return ",".join(common_names)

    def match_codes_and_articles_to_amendments(
        self,
    ) -> dict[Tuple[str, str], dict[str, set[str]]]:
        """Find the best matching codes and articles for each amendment."""
        matches_per_amdt = {}
        possible_ordinals_pattern = "|".join(
            sorted(self.latin_ordinals_set, reverse=True)
        )
        for _, row in self.amendments_df.iterrows():
            normalized_text = row["Corps amdt"]
            # TODO: Use a unique index that we generate ourselves when loading amendments instead of the composite of num amdt and lecture which is not reliable.
            num_amdt, lecture = row["Num amdt"], row["Lecture"]

            code_matches = re.findall(
                rf"code [\w']+(?:\s[\w']{{1,{self.max_code_length}}})*", normalized_text
            )
            matched_codes = {
                self.matcher.find_best_match(match, self.codes_set, threshold=60)
                for match in code_matches
                if match is not None
            }
            matched_codes = {code for code in matched_codes if code is not None}

            article_pattern = rf"(?:(?:l\.|articles?|Art\.))+(?: et |\s?(\d+(?:-\d+)*(?:\s?(?:{possible_ordinals_pattern}))?))+"
            article_matches = set(re.findall(article_pattern, normalized_text))
            matched_articles = article_matches.intersection(self.articles_set)

            if matched_codes and matched_articles:
                matches_per_amdt[(num_amdt, lecture)] = {
                    "matching_codes": matched_codes,
                    "matching_articles": matched_articles,
                }

        return matches_per_amdt

    def filter_matching_codes_and_articles(
        self, matches_per_amdt: dict[Tuple[str, str], dict[str, set[str]]]
    ) -> pd.DataFrame:
        """Retrieve rows from the codes and articles DataFrame that match the amendments."""
        matching_rows_df = pd.DataFrame(
            columns=[
                "Affectation (nom)",
                "Articles",
                "Code",
                "Corps amdt",
                "Num amdt",
                "Lecture",
                "Bureau",
            ]
        )

        for (num_amdt, lecture), matches in matches_per_amdt.items():
            matched_rows = self.codes_articles_df[
                self.codes_articles_df["Code"].isin(matches["matching_codes"])
                & self.codes_articles_df["Articles"].isin(matches["matching_articles"])
            ].copy()

            if not matched_rows.empty:
                matched_rows["Num amdt"] = num_amdt
                matched_rows["Lecture"] = lecture
                matched_rows["Corps amdt"] = self.amendments_df.loc[
                    (self.amendments_df["Num amdt"] == num_amdt)
                    & (self.amendments_df["Lecture"] == lecture),
                    "Corps amdt",
                ].values[0]
                matching_rows_df = pd.concat([matching_rows_df, matched_rows])

        return matching_rows_df

    def aggregate_matches_by_amendment(
        self, matching_rows_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Group matching rows by amendment and lecture."""
        return (
            matching_rows_df.groupby(["Num amdt", "Lecture"])
            .agg({"Affectation (nom)": lambda x: ",".join(sorted(set(x)))})
            .reset_index()
        )

    def match_keywords_to_amendments(self, threshold: int = 75) -> pd.DataFrame:
        """Find keyword matches for the amendments."""
        matcher = AttributionMatcher()
        keywords = set(self.keywords_df["Mots clés"].dropna())
        keyword_matches = self.parallel_keyword_matching(keywords, matcher, threshold)
        if not keyword_matches:
            return pd.DataFrame()

        return pd.DataFrame(keyword_matches).merge(
            self.keywords_df, left_on="Keyword", right_on="Mots clés"
        )

    def parallel_keyword_matching(
        self, keywords: set[str], matcher: AttributionMatcher, threshold: int
    ) -> list[dict[str, str]]:
        """Parallel fuzzy matching of keywords."""
        amendments = self.amendments_df.to_dict(orient="records")
        with Pool(cpu_count()) as pool:
            results = pool.starmap(
                matcher.fuzzy_match,
                [(amendment, keywords, threshold) for amendment in amendments],
            )
        return [match for sublist in results for match in sublist]

    def populate(self):
        # Step 1: Match codes and articles to amendments
        self.best_matches_per_amdt = self.match_codes_and_articles_to_amendments()
        matching_rows_df = self.filter_matching_codes_and_articles(
            self.best_matches_per_amdt
        )
        grouped_matching_df = self.aggregate_matches_by_amendment(matching_rows_df)
        amendments_df = self.amendments_df.set_index(["Num amdt", "Lecture"])
        if not grouped_matching_df.empty:
            amendments_df["Affectation (nom)"] = grouped_matching_df.set_index(
                ["Num amdt", "Lecture"]
            )["Affectation (nom)"]
            amendments_df["Affectation (nom)"] = amendments_df[
                "Affectation (nom)"
            ].str.split(",")
        amendments_df.reset_index(inplace=True)

        matched_count = len(self.best_matches_per_amdt)
        unmatched_count = len(amendments_df) - matched_count
        logging.info(f"# matched amendments: {matched_count}")
        logging.info(f"# amendments without a match: {unmatched_count}")

        # Step 2: Match keywords to amendments
        keyword_matches_df = self.match_keywords_to_amendments(threshold=95)
        if not keyword_matches_df.empty:
            keyword_matches_df.set_index(["Num amdt", "Lecture"], inplace=True)
            keyword_matches_df.sort_index(inplace=True)
            amendments_df.set_index(["Num amdt", "Lecture"], inplace=True)

            amendments_df["Affectation (nom)"] = amendments_df.apply(
                PLFSSAttributor.update_affectation_row,
                axis=1,
                keyword_matches_df=keyword_matches_df,
            )
            amendments_df.reset_index(inplace=True)
        return amendments_df
