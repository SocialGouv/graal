"""Integration test for Commentaires column concatenation across multiple features."""

import logging
import random
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from graal.clustering.similarity_handler import SimilarityHandler
from graal.core.pipeline_orchestrator import PipelineOrchestrator
from graal.features.attribution_feature import AttributionFeature
from graal.features.similarities_within_lecture_feature import (
    SimilaritiesWithinLecturesFeature,
)
from graal.features.similarity_search_feature import SimilaritySearchFeature

logging.config.fileConfig("logging.conf")

TEST_DATA_DIR = Path("tests/integration/test_data")
CONFIG_FILE = TEST_DATA_DIR / "Fichier de configuration GRAAL - Test integrations.xlsx"


@pytest.fixture
def test_config_excel():
    """Load test configuration Excel file."""
    return pd.read_excel(CONFIG_FILE, sheet_name=None)


@pytest.fixture
def test_amendments_df():
    """Create test amendments that trigger multiple features."""
    np.random.seed(42)
    random.seed(42)

    return pd.DataFrame(
        {
            "amdt_idx": [0, 1],
            "Num amdt": [1, 2],
            "Num article": ["1", "1"],
            "origin_project": ["PLFSS_2024", "PLFSS_2024"],
            "Corps amdt": [
                "Rétablir les crédits de la mission Santé publique",
                "Rétablir les crédits de la mission Santé publique",
            ],
            "Exposé amdt": [
                "Il est proposé de rétablir les crédits de la mission Santé publique qui ont été supprimés",
                "Il est proposé de rétablir les crédits de la mission Santé publique qui ont été supprimés",
            ],
            "Affectation (email)": ["", ""],
            "Affectation (nom)": ["", ""],
            "Entité Pilote": ["", ""],
            "Commentaires": ["", ""],
            "Réponse": ["", ""],
            "Sort": ["", ""],
            "date_derniere_modif": [
                "2023-01-01 10:00:00.000",
                "2023-01-02 10:00:00.000",
            ],
        }
    )


@pytest.fixture
def similarity_db_file(tmp_path):
    """Create temporary similarity database."""
    old_amendments = pd.DataFrame(
        {
            "amdt_idx": [100, 101],
            "Num amdt": [100, 101],
            "Num article": ["1", "2"],
            "origin_project": ["PLFSS_2024", "PLFSS_2024"],
            "Corps amdt": [
                "Rétablir les crédits de la mission Santé publique",
                "Modifier l'article 2 concernant les dépenses de santé",
            ],
            "Exposé amdt": [
                "Il est proposé de rétablir les crédits",
                "Cet amendement vise à modifier les dispositions",
            ],
            "Réponse": ["Favorable", "Défavorable"],
            "Sort": ["Adopté", "Rejeté"],
            "Commentaires": ["Old comment 1", "Old comment 2"],
            "timestamp": [1672531200, 1672617600],
        }
    )

    preprocessed_old = SimilarityHandler.preprocess_for_similarity(old_amendments, {})
    db_path = tmp_path / "test_similarity_db.pkl"
    preprocessed_old.to_pickle(db_path)
    return db_path


def test_multiple_features_commentaires_concatenation(
    test_config_excel, test_amendments_df, similarity_db_file
):
    """Test that multiple features writing to Commentaires concatenate correctly."""
    amendments_df = test_amendments_df.copy()

    # Enable all three features that write to Commentaires
    config = {
        "attribution": {
            "enabled": True,
            "project_name": "PLFSS",
        },
        "similarities_within_lectures": {
            "enabled": True,
            "column": "Exposé amdt",
            "similarity_threshold": 0.3,
        },
        "similarity_search": {
            "enabled": True,
            "similarity_db_file": str(similarity_db_file),
            "clustering_similarity_thresholds": {
                "Exposé amdt": 0.2,
                "Corps amdt": 0.2,
            },
            "fuzzy_match_similarity_thresholds": {
                "Exposé amdt": 0.3,
                "Corps amdt": 0.3,
            },
            "similarity_threshold_overrides": {},
            "columns_to_copy": {
                "Réponse": {"enabled": True},
            },
        },
        "similarity_thresholds": {
            "tf_idf_threshold": 0.1,
        },
    }

    # Create and run orchestrator with all features
    orchestrator = PipelineOrchestrator(
        preprocessing_features=[],
        features=[
            AttributionFeature(config_excel=test_config_excel),
            SimilaritiesWithinLecturesFeature(config=config),
            SimilaritySearchFeature(config=config),
        ],
        concatenated_columns={"Commentaires"},
        concatenated_column_separator="\n",
    )

    result_df, _ = orchestrator.process(amendments_df, config)

    # Verify Commentaires column exists
    assert "Commentaires" in result_df.columns

    # Get actual comments
    comment_0 = result_df.loc[0, "Commentaires"]
    comment_1 = result_df.loc[1, "Commentaires"]

    # Expected comments - All three features should contribute:
    # 1. Attribution Feature: "Attribution par défaut"
    # 2. SimilaritiesWithin Feature: "Amdt similaires : X (100%)"
    # 3. SimilaritySearch Feature: "Copie de Réponse depuis..."

    # Amendment 0: Sees amendment 2 as similar, matches historical amendment 100
    expected_comment_0 = (
        "Attribution par défaut\n"
        "Amdt similaires : 2 (100%)\n"
        "Copie de Réponse depuis : PLFSS_2024\n"
        "Numéro d'amendement : 100\n"
        "Lecture : \n"
        "Organe : \n"
        "Colonne similaire : Corps amdt"
    )

    # Amendment 1: Sees amendment 1 as similar, matches historical amendment 100
    expected_comment_1 = (
        "Attribution par défaut\n"
        "Amdt similaires : 1 (100%)\n"
        "Copie de Réponse depuis : PLFSS_2024\n"
        "Numéro d'amendement : 100\n"
        "Lecture : \n"
        "Organe : \n"
        "Colonne similaire : Corps amdt"
    )

    # Direct string comparison - verify all three features contributed
    assert comment_0 == expected_comment_0, (
        f"Comment mismatch for amendment 0:\n"
        f"Expected:\n{expected_comment_0}\n\n"
        f"Got:\n{comment_0}"
    )

    assert comment_1 == expected_comment_1, (
        f"Comment mismatch for amendment 1:\n"
        f"Expected:\n{expected_comment_1}\n\n"
        f"Got:\n{comment_1}"
    )

    # Verify all three features contributed to comments
    assert "Attribution par défaut" in comment_0, "Attribution feature missing"
    assert "Amdt similaires" in comment_0, "SimilaritiesWithin feature missing"
    assert "Copie de Réponse depuis" in comment_0, "SimilaritySearch feature missing"
