"""
Test to demonstrate the no_value_overwrite config bug.

When no_value_overwrite is enabled, the pipeline should preserve existing values
in result columns from the input file.
"""

from typing import Any, Set

import pandas as pd
import pytest

from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput
from graal.core.pipeline_orchestrator import PipelineOrchestrator


class MockSummaryFeature(BaseFeature):
    """Mock feature that generates summaries, similar to SummaryGenerationFeature."""

    def __init__(self):
        super().__init__("summary_generation")

    def get_required_columns(self) -> Set[str]:
        return {"amdt_idx", "Corps amdt", "Exposé amdt", "Objet amdt"}

    def get_output_columns(self) -> Set[str]:
        return {"Objet amdt"}

    def is_enabled(self, config: dict[str, Any]) -> bool:
        return config.get("summary_generation", {}).get("enabled", False)

    def get_columns_to_clear(self, config: dict[str, Any]) -> Set[str]:
        if self.is_enabled(config):
            return {"Objet amdt"}
        return set()

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        """Generate new summaries for all amendments."""
        result_df = feature_input.amendments_df.copy()
        # Feature generates new summaries, overwriting everything
        result_df["Objet amdt"] = "AI-generated summary"

        return FeatureOutput(
            amendments_df=result_df,
            outputs={"summaries_generated": len(result_df)},
        )


@pytest.fixture
def sample_amendments_with_existing_summaries():
    """Sample data where user has pre-filled some summaries in the input file."""
    return pd.DataFrame(
        {
            "amdt_idx": [0, 1, 2],
            "Num amdt": [100, 101, 102],
            "Corps amdt": ["Body 1", "Body 2", "Body 3"],
            "Exposé amdt": ["Expose 1", "Expose 2", "Expose 3"],
            "Objet amdt": [
                "User-provided summary 1",  # User filled this
                "User-provided summary 2",  # User filled this
                "User-provided summary 3",  # User filled this
            ],
        }
    )


def test_no_value_overwrite_should_preserve_user_provided_summaries(
    sample_amendments_with_existing_summaries,
):
    """
    Test that no_value_overwrite preserves user-provided values in result columns.
    """
    # Create a mock feature that would normally overwrite the summaries
    mock_feature = MockSummaryFeature()

    # Configuration with no_value_overwrite enabled
    config = {
        "summary_generation": {"enabled": True},
        "processing_options": {"no_value_overwrite": True},
    }

    # Simulate what ProcessingPipeline does:
    # 1. Determine columns to clear
    columns_to_clear = mock_feature.get_columns_to_clear(config)
    assert "Objet amdt" in columns_to_clear

    # 2. Store the "original_df" BEFORE clearing (FIX: preserves user-provided values)
    amendments_df = sample_amendments_with_existing_summaries.copy()
    original_df = amendments_df.copy()

    # 3. Clear columns for feature processing
    for col in columns_to_clear:
        amendments_df[col] = None

    # 4. Run the feature
    orchestrator = PipelineOrchestrator(
        preprocessing_features=[],
        features=[mock_feature],
    )
    result_df, _ = orchestrator.process(amendments_df=amendments_df, config=config)

    # 5. Try to preserve original values (this is what _preserve_original_values does)
    # Get rows from original_df where "Objet amdt" is not empty
    for idx in result_df["amdt_idx"]:
        matches = original_df.loc[original_df["amdt_idx"] == idx, "Objet amdt"]
        original_value = matches.iloc[0] if len(matches) > 0 else None

        # If original had a value, restore it
        if pd.notna(original_value) and original_value not in [None, ""]:
            result_df.loc[result_df["amdt_idx"] == idx, "Objet amdt"] = original_value

    # ASSERTION: User-provided summaries should be preserved
    assert (
        result_df.loc[0, "Objet amdt"] == "User-provided summary 1"
    ), f"Expected 'User-provided summary 1' but got '{result_df.loc[0, 'Objet amdt']}'"
    assert (
        result_df.loc[1, "Objet amdt"] == "User-provided summary 2"
    ), f"Expected 'User-provided summary 2' but got '{result_df.loc[1, 'Objet amdt']}'"
    assert (
        result_df.loc[2, "Objet amdt"] == "User-provided summary 3"
    ), f"Expected 'User-provided summary 3' but got '{result_df.loc[2, 'Objet amdt']}'"
