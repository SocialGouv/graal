import re

import numpy as np
import pandas as pd

from amendements_intelligents.attribution.attribution_data_loader import (
    AttributionDataLoader,
)
from amendements_intelligents.attribution.plfss_attributor import PLFSSAttributor
from amendements_intelligents.utils.plfss_pre_processor import PLFSSPreProcessor
from amendements_intelligents.utils.plfss_text_utils import AttributionTextNormalizer


class AffectationUpdater:
    @staticmethod
    def update(row: pd.Series, keyword_matches_df: pd.DataFrame) -> str:
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


def main():
    amendments_file = "data/PLFSS_2024.json"
    mappings_file = "data/mappings_attributions_aug_9.xlsx"
    output_file = "data/amendments_with_keyword_and_code_art_affectation.xlsx"
    YEAR = 2024

    amendments_df = PLFSSPreProcessor.load_plfss_json(
        input_files=[(amendments_file, YEAR)]
    )
    amendments_df = PLFSSPreProcessor.remap_columns_in_json_amendments(amendments_df)
    amendments_df = PLFSSPreProcessor.prepare_amendments_columns(amendments_df)

    amendments_df["Corps amdt"] = amendments_df["Corps amdt"].apply(
        lambda x: AttributionTextNormalizer.normalize_text(str(x))
    )

    excel_data = pd.read_excel(mappings_file, sheet_name=None)
    codes_articles_df = AttributionDataLoader.load_codes_and_articles(excel_data)
    keywords_df = AttributionDataLoader.load_keywords(excel_data)

    codes_set = set(codes_articles_df["Code"])
    max_code_length = codes_articles_df["Code"].str.len().max()
    articles_set = set(codes_articles_df["Articles"])
    pattern = re.compile(r"(?:\d+(?:-\d+)*)(?:\s(.+))?")
    latin_ordinals_set = {
        match.group(1)
        for article in articles_set
        if (match := pattern.match(article)) and match.group(1)
    }

    attributor = PLFSSAttributor(
        amendments_df=amendments_df,
        articles_set=articles_set,
        codes_articles_df=codes_articles_df,
        codes_set=codes_set,
        keywords_df=keywords_df,
        latin_ordinals_set=latin_ordinals_set,
        max_code_length=max_code_length,
    )

    # Step 1: Match codes and articles to amendments
    best_matches_per_amdt = attributor.match_codes_and_articles_to_amendments()
    matching_rows_df = attributor.filter_matching_codes_and_articles(
        best_matches_per_amdt
    )
    grouped_matching_df = attributor.aggregate_matches_by_amendment(matching_rows_df)
    amendments_df = attributor.integrate_code_article_matches_into_amendments(
        grouped_matching_df
    )

    matched_count = len(best_matches_per_amdt)
    unmatched_count = len(attributor.amendments_df) - matched_count
    print(f"# matched amendments: {matched_count}")
    print(f"# amendments without a match: {unmatched_count}")

    # Step 2: Match keywords to amendments
    keyword_matches_df = attributor.match_keywords_to_amendments(threshold=95)
    keyword_matches_df.set_index(["Num amdt", "Lecture"], inplace=True)
    keyword_matches_df.sort_index(inplace=True)
    amendments_df.set_index(["Num amdt", "Lecture"], inplace=True)

    amendments_df["Affectation (nom)"] = amendments_df["Affectation (nom)"].str.split(
        ","
    )

    amendments_df["Affectation (nom)"] = amendments_df.apply(
        AffectationUpdater.update, axis=1, keyword_matches_df=keyword_matches_df
    )

    amendments_df.reset_index(inplace=True)
    amendments_df.to_excel(output_file, index=False)
    print(
        f"Saved amendment with keyword and code/article affectation to: {output_file}"
    )


if __name__ == "__main__":
    main()
