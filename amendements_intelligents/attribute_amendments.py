import re
from typing import Dict, Optional, Tuple

import pandas as pd
from rapidfuzz import fuzz
from unidecode import unidecode

from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor


def normalize_attrib_text(text: str) -> str:
    text = unidecode(text)
    text = text.strip().lower()
    text = re.sub(
        r"[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000\uFEFF]", " ", text
    )
    return text


def find_best_matching_in_set(
    text_to_match: str,
    set_to_match_against: set[str],
    threshold: Optional[int] = None,
) -> str:
    best_matching_in_set = None
    best_matching_ratio = 0

    for text_from_set in set_to_match_against:
        ratio = fuzz.partial_ratio(text_to_match, text_from_set)
        if ratio > best_matching_ratio and (not threshold or ratio > threshold):
            best_matching_in_set = text_from_set
            best_matching_ratio = ratio

    return best_matching_in_set


class PLFSSAttributor:
    def __init__(self):
        self.plfss_pre_processor = PLFSSPreProcessor()
        self.all_codes_set = set()
        self.all_articles_set = set()
        self.all_latin_ordinals_set = set()
        self.max_code_length = 0
        self.codes_and_articles: pd.DataFrame = None
        self.keywords: pd.DataFrame = None
        self.amendments_df: pd.DataFrame = None

    def _extract_latin_ordinals(self):
        article_latin_ordinal_pattern = r"(?:\d+(?:-\d+)*)(?:\s([\w\s]+))?"
        for article in self.all_articles_set:
            article_latin_ordinal_match = re.match(
                article_latin_ordinal_pattern, article
            )
            if article_latin_ordinal_match and article_latin_ordinal_match.group(1):
                self.all_latin_ordinals_set.add(article_latin_ordinal_match.group(1))

    def _load_codes_and_articles(self):
        self.codes_and_articles = self.excel_data["Code et Article"]
        self.codes_and_articles.rename(
            columns={"Prénom Nom": "Affectation (nom)"}, inplace=True
        )
        self.codes_and_articles["Articles"] = self.codes_and_articles["Articles"].apply(
            lambda x: normalize_attrib_text(str(x))
        )
        self.codes_and_articles["Code"] = self.codes_and_articles["Code"].apply(
            lambda x: normalize_attrib_text(str(x))
        )
        self.all_codes_set = set(self.codes_and_articles["Code"])
        self.max_code_length = self.codes_and_articles["Code"].map(len).max()
        self.all_articles_set = set(
            str(article) for article in self.codes_and_articles["Articles"]
        )
        self._extract_latin_ordinals()

    def _load_keywords(self):
        self.keywords = self.excel_data["Mots clés"]
        self.keywords["Mots clés"] = self.keywords["Mots clés"].apply(
            lambda x: normalize_attrib_text(str(x))
        )

    def load_mappings(self, mappings_excel_file: str):
        self.excel_data = pd.read_excel(mappings_excel_file, sheet_name=None)
        self._load_codes_and_articles()
        self._load_keywords()
        # TODO:
        # self._load_expertise()

    def load_amendments(self, amendments_json_file: str):
        self.plfss_pre_processor.load_plfss(amendments_json_file)
        self.plfss_pre_processor.clean_up_original_amendments()
        self.amendments_df = self.plfss_pre_processor.original_amendments_df.copy()

    def find_best_matching_codes_and_articles_per_amdt(
        self,
    ) -> Dict[Tuple[str, str], Dict[str, set[str]]]:
        best_matching_codes_and_articles_per_amdt = dict()
        possible_latin_ordinals = "|".join(
            sorted(self.all_latin_ordinals_set, reverse=True)
        )

        for index, corps_amdt in enumerate(self.amendments_df["Corps amdt"]):
            normalized_corps_amdt = normalize_attrib_text(corps_amdt)
            num_amdt = self.amendments_df.iloc[index]["Num amdt"]
            lecture = self.amendments_df.iloc[index]["Lecture"]

            code_matches = re.findall(
                rf"code [\w']+(?:\s[\w']{{1,{self.max_code_length}}})*",
                normalized_corps_amdt,
            )
            best_matching_codes = set()

            for code_match in code_matches:
                best_matching_code = find_best_matching_in_set(
                    code_match, self.all_codes_set, threshold=60
                )
                if best_matching_code:
                    best_matching_codes.add(best_matching_code)

            # This pattern is a bit gnarly unfortunately. You can play around with it here: https://regex101.com/r/p9Olem/3
            article_pattern = rf"(?:(?:l\.|articles?|Art\.))+(?: et |\s?(\d+(?:-\d+)*(?:\s?(?:{possible_latin_ordinals}))?))+"
            article_matches = re.findall(article_pattern, normalized_corps_amdt)

            best_matching_articles = set()

            for article_match in article_matches:
                if article_match in self.all_articles_set:
                    best_matching_articles.add(article_match)

            if best_matching_codes and best_matching_articles:
                best_matching_codes_and_articles_per_amdt[(num_amdt, lecture)] = {
                    "matching_codes": best_matching_codes,
                    "matching_articles": best_matching_articles,
                }

        return best_matching_codes_and_articles_per_amdt

    def get_rows_from_codes_and_articles_matches(
        self,
        best_matching_codes_and_articles_per_amdt: Dict[
            Tuple[str, str], Dict[str, set[str]]
        ],
    ) -> pd.DataFrame:
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

        for (
            (num_amdt, lecture),
            matching_codes_and_articles,
        ) in best_matching_codes_and_articles_per_amdt.items():
            matching_codes = matching_codes_and_articles["matching_codes"]
            matching_articles = matching_codes_and_articles["matching_articles"]

            matching_rows = self.codes_and_articles[
                (self.codes_and_articles["Code"].isin(matching_codes))
                & (self.codes_and_articles["Articles"].isin(matching_articles))
            ].copy()

            if len(matching_rows):
                matching_rows["Num amdt"] = num_amdt
                matching_rows["Lecture"] = lecture
                matching_rows["Corps amdt"] = self.amendments_df.loc[
                    (self.amendments_df["Num amdt"] == num_amdt)
                    & (self.amendments_df["Lecture"] == lecture),
                    "Corps amdt",
                ].values[0]
                matching_rows_df = pd.concat([matching_rows_df, matching_rows])

        return matching_rows_df


def main():
    amendments_file = "data/PLFSS_2024.json"
    mappings_file = "data/mappings_attributions_aug_7.xlsx"
    output_file = "data/matching_attributions.xlsx"

    processor = PLFSSAttributor()
    processor.load_mappings(mappings_file)
    processor.load_amendments(amendments_file)

    best_matching_codes_and_articles_per_amdt = (
        processor.find_best_matching_codes_and_articles_per_amdt()
    )
    matching_rows_df = processor.get_rows_from_codes_and_articles_matches(
        best_matching_codes_and_articles_per_amdt
    )

    nb_with_match = len(best_matching_codes_and_articles_per_amdt.keys())
    nb_without_match = len(processor.amendments_df["Corps amdt"]) - nb_with_match
    print(f"# matched amendements: {nb_with_match}")
    print(f"# amendements without a match: {nb_without_match}")

    matching_rows_df.to_excel(output_file, index=False)
    print(f"Saved matched results to: {output_file}")


if __name__ == "__main__":
    main()
