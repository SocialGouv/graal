import numpy as np

from amendements_intelligents.attribution.plfss_attributor import PLFSSAttributor


def update_affectation(row, keyword_matches):
    affectation_names = row["Affectation (nom)"]
    keyword_affectation_names = set(
        keyword_matches.loc[row.name, "Affectation (nom)"]
        if row.name in keyword_matches.index
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
    mappings_file = "data/mappings_attributions_aug_7.xlsx"
    output_file = "data/amendments_with_keyword_and_code_art_affectation.xlsx"

    attributor = PLFSSAttributor()
    attributor.load_data(mappings_file, amendments_file)

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
    amendments_df.set_index(["Num amdt", "Lecture"], inplace=True)

    amendments_df["Affectation (nom)"] = amendments_df["Affectation (nom)"].str.split(
        ","
    )

    amendments_df["Affectation (nom)"] = amendments_df.apply(
        update_affectation, axis=1, keyword_matches=keyword_matches_df
    )

    amendments_df.reset_index(inplace=True)
    amendments_df.to_excel(output_file, index=False)
    print(
        f"Saved amendment with keyword and code/article affectation to: {output_file}"
    )


if __name__ == "__main__":
    main()
