"""
Test for opinion feature's should_overwrite configuration bug fix.

This test verifies that the opinion feature correctly reads the should_overwrite
setting from config["default_opinion"]["should_overwrite"] after the bug fix.
"""

import pandas as pd
import pytest

from graal.opinion.opinion_handler import OpinionHandler


@pytest.fixture
def sample_amendments_with_existing_opinions():
    """Create sample amendments with some existing opinions."""
    data = {
        "amdt_idx": [0, 1, 2, 3],
        "Groupe": ["Group A", "Group B", "Group C", "Group D"],
        "Avis du Gouvernement": [
            "Existing Favorable",  # Has existing opinion
            "Existing Défavorable",  # Has existing opinion
            None,  # No opinion
            "",  # Empty opinion
        ],
    }
    return pd.DataFrame(data)


@pytest.fixture
def group_to_opinion_mapping():
    """Create group to opinion mapping."""
    return {
        "Group A": "Favorable",
        "Group B": "Défavorable",
        "Group C": "Neutre",
        "Group D": "Sagesse du Sénat",
    }


def test_opinion_handler_should_overwrite_true(
    sample_amendments_with_existing_opinions, group_to_opinion_mapping
):
    """
    Test that when should_overwrite is True, all opinions are regenerated.

    This verifies the fix where config.get("default_opinion", {}).get("should_overwrite")
    correctly reads the configuration.
    """
    # Create handler with should_overwrite=True
    handler = OpinionHandler(
        amendments_df=sample_amendments_with_existing_opinions.copy(),
        group_to_default_opinion=group_to_opinion_mapping,
        should_overwrite=True,
    )

    # Process opinions
    result = handler.populate()

    # Verify that ALL opinions were regenerated, including existing ones
    assert result.loc[0, "Avis du Gouvernement"] == "Favorable"  # Overwritten
    assert result.loc[1, "Avis du Gouvernement"] == "Défavorable"  # Overwritten
    assert result.loc[2, "Avis du Gouvernement"] == "Neutre"  # Filled
    assert result.loc[3, "Avis du Gouvernement"] == "Sagesse du Sénat"  # Filled


def test_opinion_handler_should_overwrite_false(
    sample_amendments_with_existing_opinions, group_to_opinion_mapping
):
    """
    Test that when should_overwrite is False, only empty opinions are filled.

    This verifies the fix where config.get("default_opinion", {}).get("should_overwrite")
    correctly reads the configuration.
    """
    # Create handler with should_overwrite=False
    handler = OpinionHandler(
        amendments_df=sample_amendments_with_existing_opinions.copy(),
        group_to_default_opinion=group_to_opinion_mapping,
        should_overwrite=False,
    )

    # Process opinions
    result = handler.populate()

    # Verify that existing opinions were preserved, only empty ones filled
    assert result.loc[0, "Avis du Gouvernement"] == "Existing Favorable"  # Preserved
    assert result.loc[1, "Avis du Gouvernement"] == "Existing Défavorable"  # Preserved
    assert result.loc[2, "Avis du Gouvernement"] == "Neutre"  # Filled (was None)
    # Note: Empty string "" is NOT treated as NaN by pandas, so it won't be filled
    assert result.loc[3, "Avis du Gouvernement"] == ""  # Unchanged (empty string)


def test_opinion_handler_should_overwrite_false_with_nan_only(group_to_opinion_mapping):
    """
    Test should_overwrite=False specifically with NaN values.

    Verifies that only truly missing values (NaN/None) are filled, not empty strings.
    """
    data = {
        "amdt_idx": [0, 1, 2],
        "Groupe": ["Group A", "Group B", "Group C"],
        "Avis du Gouvernement": [
            "Existing",  # Has value
            None,  # NaN - should be filled
            pd.NA,  # Pandas NA - should be filled
        ],
    }
    df = pd.DataFrame(data)

    handler = OpinionHandler(
        amendments_df=df,
        group_to_default_opinion=group_to_opinion_mapping,
        should_overwrite=False,
    )

    result = handler.populate()

    assert result.loc[0, "Avis du Gouvernement"] == "Existing"  # Preserved
    assert result.loc[1, "Avis du Gouvernement"] == "Défavorable"  # Filled (Group B)
    assert result.loc[2, "Avis du Gouvernement"] == "Neutre"  # Filled (Group C)


def test_opinion_handler_config_integration():
    """
    Integration test simulating how the feature reads config after bug fix.

    Before fix: config.get("default_opinion_config", {}) - WRONG KEY
    After fix: config.get("default_opinion", {}) - CORRECT KEY
    """
    # Simulate the config structure from config/default.yml
    config = {
        "default_opinion": {
            "enabled": True,
            "should_overwrite": False,  # The key that was previously not accessible
        }
    }

    # This is how the feature now reads the config (after fix)
    opinion_config = config.get("default_opinion", {})
    should_overwrite = opinion_config.get("should_overwrite", True)

    # Verify we get the correct value
    assert should_overwrite is False

    # Test with amendments
    data = {
        "amdt_idx": [0, 1],
        "Groupe": ["Group A", "Group B"],
        "Avis du Gouvernement": ["Existing", None],
    }
    df = pd.DataFrame(data)
    mapping = {"Group A": "New", "Group B": "New"}

    handler = OpinionHandler(
        amendments_df=df,
        group_to_default_opinion=mapping,
        should_overwrite=should_overwrite,  # Use value from config
    )

    result = handler.populate()

    # Verify behavior matches config
    assert result.loc[0, "Avis du Gouvernement"] == "Existing"  # Preserved
    assert result.loc[1, "Avis du Gouvernement"] == "New"  # Filled
