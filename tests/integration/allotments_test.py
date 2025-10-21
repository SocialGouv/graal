import logging
import logging.config

import pandas as pd
from unidecode import unidecode

from graal.allotment.allotment_handler import AllotmentHandler
from graal.clustering.clustering_service import ClusteringService
from graal.utils.amendment_pre_processor import AmendmentPreProcessor
from graal.utils.text_utils import remove_gage_sentences

logging.config.fileConfig("logging.conf")


def load_test_file_to_compare(
    excel_test_file_path: str, sheet_name: str
) -> pd.DataFrame:
    # Load directly from local filesystem for integration tests
    return pd.read_excel(excel_test_file_path, sheet_name=sheet_name)


def test_populate_allotments_ratio_matching_allotments() -> None:
    CONFIG_FILE = "tests/integration/test_data/Fichier de configuration GRAAL - Test integrations.xlsx"

    config_excel = pd.read_excel(CONFIG_FILE, sheet_name=None)
    acronym_mapping = AmendmentPreProcessor.load_acronyms(config_excel["Acronymes"])

    test_df = load_test_file_to_compare(
        "tests/integration/test_data/test_allotments.xlsx", "test1"
    )

    test_df["Allotissement"] = test_df["Allotissement"].apply(
        lambda x: None if pd.isna(x) else x
    )
    test_df["Exposé amdt"] = None
    test_df["Sort"] = None
    test_df["Réponse"] = None
    test_df["Lecture"] = "test_lecture"

    # Process the data frame as if it were a real lecture
    original_amendments_df = test_df.copy()
    original_amendments_df["Allotissement"] = None
    normalized_amdt_df = original_amendments_df.copy()

    normalized_amdt_df = AmendmentPreProcessor.drop_empty_rows_in_columns(
        amendments_df=normalized_amdt_df, columns_to_filter=["Corps amdt"]
    )
    normalized_amdt_df = AmendmentPreProcessor.replace_acronyms(
        amendments_df=normalized_amdt_df,
        acronym_mapping=acronym_mapping,
        columns_to_normalize=["Exposé amdt", "Corps amdt"],
    )
    normalized_amdt_df["Corps amdt"] = normalized_amdt_df["Corps amdt"].apply(
        lambda text: remove_gage_sentences(unidecode(text))
    )
    normalized_amdt_df = AmendmentPreProcessor.handle_common_amendment_bodies(
        amendments_df=normalized_amdt_df
    )
    normalized_amdt_df = AmendmentPreProcessor.normalize_amendments(
        amendments_df=normalized_amdt_df, columns_to_normalize=["Corps amdt"]
    )

    # Use the same thresholds as in the configuration
    tf_idf_threshold = 0.4
    similarity_threshold = 0.999

    allotted_amdt_clusters, _ = ClusteringService.get_clusters(
        normalized_amdt_df=normalized_amdt_df,
        group_by_columns=["Lecture"],
        eps=tf_idf_threshold,
        refinement_pct_threshold=similarity_threshold,
        text_column="Corps amdt",
    )

    normalized_amdt_df = AllotmentHandler.filter_amdts_to_keep_one_per_allotment(
        normalized_amdt_df=normalized_amdt_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
    )

    alloted_amendments_df = AllotmentHandler.populate(
        original_amendments_df=original_amendments_df,
        pipeline_result_amdt_df=normalized_amdt_df,
        allotted_amdt_clusters=allotted_amdt_clusters,
        columns_to_copy=[
            "Réponse",
            "Sort",
            "Commentaires",
            "Objet amdt",
            "Avis du Gouvernement",
            "Affectation (email)",
            "Affectation (nom)",
            "Entité Pilote",
        ],
    )

    # Now we must compare our results with the expected results (in test_df)
    merged_df = test_df.merge(
        alloted_amendments_df,
        on=["amdt_idx"],
        suffixes=("_test", "_algo"),
    )
    merged_df = merged_df.drop("Corps amdt_algo", axis=1)
    merged_df = merged_df.rename(columns={"Corps amdt_test": "Corps amdt"})

    total_nb_matches = 0
    total_nb_test_lot = 0
    for _i, row in merged_df.iterrows():
        algo = row["Allotissement_algo"].split(",") if row["Allotissement_algo"] else []
        test = row["Allotissement_test"].split(",") if row["Allotissement_test"] else []

        nb_matches = len([x for x in test if x in algo])
        nb_test_lot = len(test)
        if nb_matches != nb_test_lot:
            print(
                f"Row {_i} has different nb_matches and nb_test_lot: {nb_matches} vs {nb_test_lot}"
            )

        total_nb_matches += nb_matches
        total_nb_test_lot += nb_test_lot

    coverage_test_allotments = total_nb_matches / total_nb_test_lot
    logging.info(f"Total number of allotments: {total_nb_matches}")
    logging.info(f"Coverage test: {coverage_test_allotments}")

    assert coverage_test_allotments > 0.99
