"""
Test for attribution feature's should_overwrite behavior.

This test verifies that the attribution feature respects the should_overwrite
configuration setting to preserve existing user-provided values.
"""

import pandas as pd

from graal.core.feature_interface import FeatureInput
from graal.features.attribution_feature import AttributionFeature


def test_attribution_overwrites_existing_values():
    """
    Test that attribution feature respects should_overwrite=False config.

    This test verifies that when should_overwrite is set to False in the attribution
    config, the feature preserves existing user-provided values and only fills in
    empty fields.
    """
    # Setup: Create test data with user-provided attribution values
    test_data = pd.DataFrame(
        {
            "amdt_idx": [0, 1, 2],
            "Corps amdt": ["Article 1er", "Article 2", "Article 3"],
            "Exposé amdt": [
                "Cet amendement vise à...",
                "Il est proposé de...",
                "Le présent amendement...",
            ],
            # User-provided attribution values (these should be preserved)
            "Affectation (email)": ["user1@example.com", "user2@example.com", ""],
            "Affectation (nom)": ["User One", "User Two", ""],
            "Entité Pilote": ["User Entity 1", "User Entity 2", ""],
        }
    )

    # Setup: Create config with should_overwrite disabled
    config = {
        "attribution": {
            "enabled": True,
            "project_name": "PLF",  # Using PLF as it's configured in tests
            "should_overwrite": False,  # This should prevent overwriting existing values
        }
    }

    # Setup: Create minimal config_excel for attribution
    # This mimics the structure from test_data config file
    config_excel = {
        "Infos Agents": pd.DataFrame(
            {
                "Prénom Nom": ["Default User", "User One", "User Two"],
                "Mail": [
                    "default@example.com",
                    "user1@example.com",
                    "user2@example.com",
                ],
                "Entité Pilote": ["Default Entity", "User Entity 1", "User Entity 2"],
            }
        ),
        "Mots clés": pd.DataFrame(
            {"Mots clés": ["test"], "Prénom Nom": ["Default User"]}
        ),
        "Acronymes": pd.DataFrame(
            {
                "Acronyme": ["AAH"],
                "Développement": ["allocation aux adultes handicapés"],
            }
        ),
        "Attribution par défaut": pd.DataFrame({"Prénom Nom": ["Default User"]}),
        "Code et Article": pd.DataFrame(
            {
                "Bureau": ["5B"],
                "Prénom Nom": ["Default User"],
                "Articles": ["1"],
                "Type": ["code"],
                "Valeur": ["Impôts"],
            }
        ),
    }

    # Store original values for comparison
    original_email_1 = test_data.loc[0, "Affectation (email)"]
    original_nom_1 = test_data.loc[0, "Affectation (nom)"]
    original_entity_1 = test_data.loc[0, "Entité Pilote"]

    original_email_2 = test_data.loc[1, "Affectation (email)"]
    original_nom_2 = test_data.loc[1, "Affectation (nom)"]
    original_entity_2 = test_data.loc[1, "Entité Pilote"]

    # Execute: Run attribution feature
    feature = AttributionFeature(config_excel=config_excel)
    feature_input = FeatureInput(amendments_df=test_data.copy(), config=config)

    result = feature.process(feature_input)
    result_df = result.amendments_df

    # Assert: User-provided values should be preserved (EXPECTED TO FAIL)
    # For amendments 1 and 2 which had user values, those values should remain
    assert result_df.loc[0, "Affectation (email)"] == original_email_1, (
        f"Attribution feature overwrote user-provided email for amendment 1. "
        f"Expected '{original_email_1}', got '{result_df.loc[0, 'Affectation (email)']}'. "
        f"BUG LOCATION: graal/attribution/attribution_handler.py:181"
    )

    assert result_df.loc[0, "Affectation (nom)"] == original_nom_1, (
        f"Attribution feature overwrote user-provided name for amendment 1. "
        f"Expected '{original_nom_1}', got '{result_df.loc[0, 'Affectation (nom)']}'. "
        f"BUG LOCATION: graal/attribution/attribution_handler.py:171"
    )

    assert result_df.loc[0, "Entité Pilote"] == original_entity_1, (
        f"Attribution feature overwrote user-provided entity for amendment 1. "
        f"Expected '{original_entity_1}', got '{result_df.loc[0, 'Entité Pilote']}'. "
        f"BUG LOCATION: graal/attribution/attribution_handler.py:182"
    )

    # Check second amendment as well
    assert result_df.loc[1, "Affectation (email)"] == original_email_2
    assert result_df.loc[1, "Affectation (nom)"] == original_nom_2
    assert result_df.loc[1, "Entité Pilote"] == original_entity_2

    # For amendment 3 which had empty values, attribution CAN write values
    assert result_df.loc[2, "Affectation (email)"] != ""
    assert result_df.loc[2, "Affectation (nom)"] != ""
    assert result_df.loc[2, "Entité Pilote"] != ""


def test_attribution_with_should_overwrite_true():
    """
    Test that attribution feature overwrites values when should_overwrite=True.

    This test verifies that when should_overwrite is set to True (the default),
    the feature behaves as it always has, overwriting existing values with
    attribution results.

    This ensures backward compatibility is maintained.
    """
    # Setup: Create test data with user-provided attribution values
    test_data = pd.DataFrame(
        {
            "amdt_idx": [0],
            "Corps amdt": ["Article 1er"],
            "Exposé amdt": ["Cet amendement vise à..."],
            # Pre-existing values that should be overwritten
            "Affectation (email)": ["old@example.com"],
            "Affectation (nom)": ["Old User"],
            "Entité Pilote": ["Old Entity"],
        }
    )

    # Setup: Config with should_overwrite=True (default behavior)
    config = {
        "attribution": {
            "enabled": True,
            "project_name": "PLF",
            "should_overwrite": True,  # Explicitly enable overwriting
        }
    }

    # Setup: Minimal config_excel for attribution
    config_excel = {
        "Infos Agents": pd.DataFrame(
            {
                "Prénom Nom": ["New User"],
                "Mail": ["new@example.com"],
                "Entité Pilote": ["New Entity"],
            }
        ),
        "Mots clés": pd.DataFrame({"Mots clés": ["test"], "Prénom Nom": ["New User"]}),
        "Acronymes": pd.DataFrame(
            {
                "Acronyme": ["AAH"],
                "Développement": ["allocation aux adultes handicapés"],
            }
        ),
        "Attribution par défaut": pd.DataFrame({"Prénom Nom": ["New User"]}),
        "Code et Article": pd.DataFrame(
            {
                "Bureau": ["5B"],
                "Prénom Nom": ["New User"],
                "Articles": ["1"],
                "Type": ["code"],
                "Valeur": ["Impôts"],
            }
        ),
    }

    # Execute: Run attribution feature
    feature = AttributionFeature(config_excel=config_excel)
    feature_input = FeatureInput(amendments_df=test_data.copy(), config=config)

    result = feature.process(feature_input)
    result_df = result.amendments_df

    # Assert: Values should be overwritten with new attribution
    # Note: Attribution handler normalizes text to lowercase
    assert result_df.loc[0, "Affectation (nom)"].lower() == "new user"
    assert result_df.loc[0, "Affectation (email)"] == "new@example.com"
    assert result_df.loc[0, "Entité Pilote"].lower() == "new entity"
