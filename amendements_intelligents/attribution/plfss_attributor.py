import re
from multiprocessing import Pool, cpu_count
from typing import Dict, List, Set, Tuple

import pandas as pd
from pydantic import FilePath

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.attribution_matcher import AttributionMatcher
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_text_utils import AttributionTextNormalizer


class PLFSSAttributor:
    def __init__(self):
        self.data_loader = AttributionDataLoader()
        self.matcher = AttributionMatcher()
        self.codes_set: Set[str] = set()
        self.articles_set: Set[str] = set()
        self.latin_ordinals_set: Set[str] = set()
        self.max_code_length = 0
        self.amendments_df = None

    def _load_amendments(self, amendments_file: FilePath) -> None:
        """Load amendments data from a file."""
        if amendments_file.endswith(".json"):
            pre_processor = PLFSSPreProcessor
            amendments_df = pre_processor.load_plfss_json(
                input_files=[(amendments_file, None)]
            )
            amendments_df = pre_processor.remap_columns_in_json_amendments(
                amendments_df=amendments_df
            )
            self.amendments_df = pre_processor.prepare_amendments_columns(
                amendments_df=amendments_df
            )
        elif amendments_file.endswith(".xlsx"):
            self.amendments_df = pre_processor.load_plfss_excel(
                input_file=amendments_file
            )
        else:
            raise ValueError(f"Unsupported file format: {amendments_file}")
        self.amendments_df["Corps amdt"] = self.amendments_df["Corps amdt"].apply(
            lambda x: AttributionTextNormalizer.normalize_text(str(x))
        )

    def load_data(self, mappings_file: str, amendments_file: FilePath):
        """Load mappings and amendments data."""
        self.data_loader.load_mappings(mappings_file)
        self._load_amendments(amendments_file)
        self._prepare_data_sets()

    def _prepare_data_sets(self):
        """Prepare the code, article, and ordinals sets."""
        self.codes_set = set(self.data_loader.codes_articles_df["Code"])
        self.max_code_length = (
            self.data_loader.codes_articles_df["Code"].str.len().max()
        )
        self.articles_set = set(self.data_loader.codes_articles_df["Articles"])
        self._extract_latin_ordinals()

    def _extract_latin_ordinals(self):
        """Extract and store Latin ordinals from article texts."""
        pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
        self.latin_ordinals_set = {
            match.group(1)
            for article in self.articles_set
            if (match := pattern.match(article)) and match.group(1)
        }

    def match_codes_and_articles_to_amendments(
        self,
    ) -> Dict[Tuple[str, str], Dict[str, Set[str]]]:
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
        self, matches_per_amdt: Dict[Tuple[str, str], Dict[str, Set[str]]]
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
            matched_rows = self.data_loader.codes_articles_df[
                self.data_loader.codes_articles_df["Code"].isin(
                    matches["matching_codes"]
                )
                & self.data_loader.codes_articles_df["Articles"].isin(
                    matches["matching_articles"]
                )
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

    def integrate_code_article_matches_into_amendments(
        self, grouped_matching_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Update amendments DataFrame with matching codes and articles."""
        updated_df = self.amendments_df.set_index(["Num amdt", "Lecture"])
        updated_df["Affectation (nom)"] = grouped_matching_df.set_index(
            ["Num amdt", "Lecture"]
        )["Affectation (nom)"]
        return updated_df.reset_index()

    def match_keywords_to_amendments(self, threshold: int = 75) -> pd.DataFrame:
        """Find keyword matches for the amendments."""
        matcher = AttributionMatcher()
        keywords = set(self.data_loader.keywords_df["Mots clés"].dropna())
        keyword_matches = self.parallel_keyword_matching(keywords, matcher, threshold)
        return pd.DataFrame(keyword_matches).merge(
            self.data_loader.keywords_df, left_on="Keyword", right_on="Mots clés"
        )

    def parallel_keyword_matching(
        self, keywords: Set[str], matcher: AttributionMatcher, threshold: int
    ) -> List[Dict[str, str]]:
        """Parallel fuzzy matching of keywords."""
        amendments = self.amendments_df.to_dict(orient="records")
        with Pool(cpu_count()) as pool:
            results = pool.starmap(
                matcher.fuzzy_match,
                [(amendment, keywords, threshold) for amendment in amendments],
            )
        return [match for sublist in results for match in sublist]
