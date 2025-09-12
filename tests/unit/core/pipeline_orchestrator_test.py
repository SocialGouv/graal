"""
Tests for PipelineOrchestrator parallel processing functionality.
"""

from typing import Any, Set

import pandas as pd
import pytest

from graal.core.feature_interface import BaseFeature, FeatureInput, FeatureOutput
from graal.core.pipeline_orchestrator import PipelineOrchestrator


class MockFeature(BaseFeature):
    """Mock feature for testing parallel processing."""

    def __init__(self, feature_name: str, should_fail: bool = False):
        super().__init__(feature_name)
        self.should_fail = should_fail
        self.process_called = False

    def get_required_columns(self) -> Set[str]:
        return {"amdt_idx", "Corps amdt"}

    def get_output_columns(self) -> Set[str]:
        return {f"{self.feature_name}_output"}

    def is_enabled(self, config: dict[str, Any]) -> bool:
        return config.get(self.feature_name, {}).get("enabled", True)

    def get_columns_to_clear(self, config: dict[str, Any]) -> Set[str]:
        if self.is_enabled(config):
            return self.get_output_columns()
        return set()

    def process(self, feature_input: FeatureInput) -> FeatureOutput:
        self.process_called = True

        if self.should_fail:
            raise Exception(f"Mock failure in {self.feature_name}")

        # Create output DataFrame with new column
        result_df = feature_input.amendments_df.copy()
        result_df[f"{self.feature_name}_output"] = f"processed_by_{self.feature_name}"

        return FeatureOutput(
            amendments_df=result_df, outputs={"processed_count": len(result_df)}
        )


@pytest.fixture
def test_df():
    """Set up test data."""
    return pd.DataFrame(
        {
            "amdt_idx": [1, 2, 3],
            "Corps amdt": ["Amendment 1", "Amendment 2", "Amendment 3"],
            "Exposé amdt": ["Expose 1", "Expose 2", "Expose 3"],
        }
    )


class TestPipelineOrchestratorParallel:
    """Test parallel processing in PipelineOrchestrator."""

    def test_parallel_processing_basic(self, test_df):
        """Test basic parallel processing with multiple features."""
        # Create mock features with different processing times
        feature1 = MockFeature("feature1")
        feature2 = MockFeature("feature2")
        feature3 = MockFeature("feature3")

        orchestrator = PipelineOrchestrator(
            preprocessing_features=[], features=[feature1, feature2, feature3]
        )

        config = {
            "parallel_processing": {"max_workers": 3},
            "feature1": {"enabled": True},
            "feature2": {"enabled": True},
            "feature3": {"enabled": True},
        }

        result_df, outputs = orchestrator.process(test_df, config)

        # Verify all features were called
        assert feature1.process_called
        assert feature2.process_called
        assert feature3.process_called

        # Verify output columns are present
        assert "feature1_output" in result_df.columns
        assert "feature2_output" in result_df.columns
        assert "feature3_output" in result_df.columns

        # Verify outputs were collected
        assert "feature1" in outputs
        assert "feature2" in outputs
        assert "feature3" in outputs

    def test_parallel_processing_with_failure(self, test_df):
        """Test parallel processing handles feature failures gracefully."""
        feature1 = MockFeature("feature1")
        feature2 = MockFeature("feature2", should_fail=True)
        feature3 = MockFeature("feature3")

        orchestrator = PipelineOrchestrator(
            preprocessing_features=[], features=[feature1, feature2, feature3]
        )

        config = {
            "parallel_processing": {"max_workers": 3},
            "feature1": {"enabled": True},
            "feature2": {"enabled": True},
            "feature3": {"enabled": True},
        }

        result_df, outputs = orchestrator.process(test_df, config)

        # Verify successful features still processed
        assert "feature1_output" in result_df.columns
        assert "feature3_output" in result_df.columns
        assert "feature2_output" not in result_df.columns

        # Verify outputs - successful features have data, failed feature has empty dict
        assert outputs["feature1"]["processed_count"] == 3
        assert outputs["feature3"]["processed_count"] == 3
        assert outputs["feature2"] == {}

    def test_no_enabled_features(self, test_df):
        """Test behavior when no features are enabled."""
        feature1 = MockFeature("feature1")
        feature2 = MockFeature("feature2")

        orchestrator = PipelineOrchestrator(
            preprocessing_features=[], features=[feature1, feature2]
        )

        config = {
            "parallel_processing": {"max_workers": 2},
            "feature1": {"enabled": False},
            "feature2": {"enabled": False},
        }

        result_df, outputs = orchestrator.process(test_df, config)

        # Should return original DataFrame unchanged
        pd.testing.assert_frame_equal(result_df, test_df)
        assert outputs == {}

        # Features should not have been called
        assert not feature1.process_called
        assert not feature2.process_called
