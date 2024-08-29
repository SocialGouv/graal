import pandas as pd

from amendements_intelligents.populate_allotments import PLFSSAllotmentPopulator
from amendements_intelligents.utils.plfss_sheet_data_loader import PLFSSSheetDataLoader


def load_test_file_to_compare(
    excel_test_file_path: str, sheet_name: str
) -> pd.DataFrame:
    data_extractor = PLFSSSheetDataLoader(excel_test_file_path)
    return data_extractor.extract_sheet_data(sheet_name)


def test_populate_allotments_ratio_matching_allotments() -> None:
    test_df = load_test_file_to_compare(
        "tests/integration/test_data/test_populate_allotments_jul30.xlsx", "test1"
    )
    # test_df = load_test_file_to_compare("data/PLFSS_2024/.xlsx", "Sheet1")

    test_df["Allotissement"] = test_df["Allotissement"].apply(
        lambda x: None if pd.isna(x) else x
    )
    test_df["Exposé amdt"] = None
    test_df["Sort"] = None
    test_df["Réponse"] = None
    test_df["Lecture"] = "test_lecture"

    # Process the data frame as if it were a real PLFSS
    allotment_populator = PLFSSAllotmentPopulator()
    allotment_populator.plfss_pre_processor.original_amendments_df = test_df.copy()
    allotment_populator.plfss_pre_processor.original_amendments_df["Allotissement"] = (
        None
    )
    allotment_populator.plfss_pre_processor.work_amendments_df = (
        allotment_populator.plfss_pre_processor.original_amendments_df.copy()
    )

    allotment_populator.plfss_pre_processor.remove_empty_rows_for_given_columns(
        columns_to_filter_with=["Corps amdt"]
    )
    allotment_populator.plfss_pre_processor.handle_common_amendment_bodies()
    allotment_populator.plfss_pre_processor.normalize_plfss(
        columns_to_normalize=["Corps amdt"]
    )

    alloted_amendments_df = allotment_populator.populate()

    # Now we must compare our results with the expected results (in test_df)
    merged_df = test_df.merge(
        alloted_amendments_df,
        on=["Num article", "Num amdt"],
        suffixes=("_test", "_algo"),
    )
    merged_df = merged_df.drop("Corps amdt_algo", axis=1)
    merged_df = merged_df.rename(columns={"Corps amdt_test": "Corps amdt"})

    # test_output_file = "tests/integration/compare_allotments_test.xlsx"
    # not_detected_allotments = []
    # surplus_allotments = []

    total_nb_matches = 0
    total_nb_test_lot = 0
    total_nb_algo_lot = 0
    for _i, row in merged_df.iterrows():
        algo = row["Allotissement_algo"].split(",") if row["Allotissement_algo"] else []
        test = row["Allotissement_test"].split(",") if row["Allotissement_test"] else []

        nb_matches = len([x for x in test if x in algo])
        nb_test_lot = len(test)
        nb_algo_lot = len(algo)

        # if nb_matches != nb_test_lot:
        #     not_detected_allotments.append(
        #         {
        #             "Num amdt": row["Num amdt"],
        #             "Allotissement (Experts)": row["Allotissement_test"],
        #             "Allotissement (Machine)": row["Allotissement_algo"],
        #             "Num article": row["Num article"],
        #             "Corps amdt": row["Corps amdt"],
        #         }
        #     )
        # elif nb_algo_lot > nb_test_lot:
        #     surplus_allotments.append(
        #         {
        #             "Num amdt": row["Num amdt"],
        #             "Allotissement (Experts)": row["Allotissement_test"],
        #             "Allotissement (Machine)": row["Allotissement_algo"],
        #             "Num article": row["Num article"],
        #             "Corps amdt": row["Corps amdt"],
        #         }
        #     )

        total_nb_matches += nb_matches
        total_nb_test_lot += nb_test_lot

    # with pd.ExcelWriter(test_output_file) as writer:
    #     print(f"Saving comparison in {test_output_file}...")
    #     pd.DataFrame(not_detected_allotments).to_excel(
    #         writer, sheet_name="Allotissements manqués", index=False
    #     )
    #     pd.DataFrame(surplus_allotments).to_excel(
    #         writer, sheet_name="Allotissements en surplus", index=False
    #     )

    coverage_test_allotments = total_nb_matches / total_nb_test_lot
    print(f"Total number of allotments: {total_nb_matches}")
    print(f"Coverage test: {coverage_test_allotments}")

    assert coverage_test_allotments > 0.99
