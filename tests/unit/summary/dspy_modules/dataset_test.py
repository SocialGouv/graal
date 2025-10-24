"""
Tests for DSPy training dataset management utilities.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from graal.summary.dspy_modules.dataset import (
    AmendmentSummaryExample,
    clean_dataset,
    from_dataframe,
    get_dataset_statistics,
    load_dataset,
    save_dataset_to_s3,
    split_dataset,
    to_dataframe,
    validate_dataset,
)


@pytest.fixture
def sample_examples() -> list[AmendmentSummaryExample]:
    """Create sample training examples for testing."""
    return [
        AmendmentSummaryExample(
            expose_amdt="Cet amendement vise à modifier l'article L. 123-4",
            corps_amdt="À l'article L. 123-4, le mot 'test' est remplacé",
            summary="Modifier le code de la santé publique pour améliorer l'accès",
            metadata={"office": "office_A", "quality_score": 0.95},
        ),
        AmendmentSummaryExample(
            expose_amdt="Amendement rédactionnel pour corriger une erreur",
            corps_amdt="À l'article 5, le mot 'les' est remplacé",
            summary="Corriger une erreur rédactionnelle à l'article 5 du code",
            metadata={"office": "office_B", "quality_score": 0.88},
        ),
        AmendmentSummaryExample(
            expose_amdt="Proposition de créer un nouveau dispositif d'aide",
            corps_amdt="Après l'article 12, il est inséré un article additionnel",
            summary="Créer une aide financière pour les étudiants en médecine",
            metadata={"office": "office_A", "quality_score": 0.92},
        ),
    ]


@pytest.fixture
def test_fixtures_dir() -> Path:
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "test_fixtures"


class TestAmendmentSummaryExample:
    """Tests for AmendmentSummaryExample dataclass."""

    def test_creation(self):
        """Test creating an example."""
        example = AmendmentSummaryExample(
            expose_amdt="Exposé test",
            corps_amdt="Corps test",
            summary="Résumé test",
            metadata={"key": "value"},
        )

        assert example.expose_amdt == "Exposé test"
        assert example.corps_amdt == "Corps test"
        assert example.summary == "Résumé test"
        assert example.metadata == {"key": "value"}

    def test_creation_without_metadata(self):
        """Test creating an example without metadata."""
        example = AmendmentSummaryExample(
            expose_amdt="Exposé test",
            corps_amdt="Corps test",
            summary="Résumé test",
        )

        assert example.metadata is None

    def test_to_dict(self):
        """Test converting example to dictionary."""
        example = AmendmentSummaryExample(
            expose_amdt="Exposé test",
            corps_amdt="Corps test",
            summary="Résumé test",
            metadata={"key": "value"},
        )

        result = example.to_dict()

        assert result["expose_amdt"] == "Exposé test"
        assert result["corps_amdt"] == "Corps test"
        assert result["summary"] == "Résumé test"
        assert result["metadata"] == {"key": "value"}

    def test_from_dict(self):
        """Test creating example from dictionary."""
        data = {
            "expose_amdt": "Exposé test",
            "corps_amdt": "Corps test",
            "summary": "Résumé test",
            "metadata": {"key": "value"},
        }

        example = AmendmentSummaryExample.from_dict(data)

        assert example.expose_amdt == "Exposé test"
        assert example.corps_amdt == "Corps test"
        assert example.summary == "Résumé test"
        assert example.metadata == {"key": "value"}

    def test_from_dict_without_metadata(self):
        """Test creating example from dictionary without metadata."""
        data = {
            "expose_amdt": "Exposé test",
            "corps_amdt": "Corps test",
            "summary": "Résumé test",
        }

        example = AmendmentSummaryExample.from_dict(data)

        assert example.metadata is None


class TestLoadDataset:
    """Tests for load_dataset function."""

    def test_load_from_json(self, test_fixtures_dir: Path):
        """Test loading dataset from JSON file."""
        json_file = test_fixtures_dir / "sample_training.json"
        examples = load_dataset(str(json_file))

        assert len(examples) == 5
        assert isinstance(examples[0], AmendmentSummaryExample)
        assert examples[0].expose_amdt.startswith("Cet amendement vise")
        assert examples[0].metadata is not None
        assert examples[0].metadata["office"] == "office_A"

    def test_load_from_csv(self, test_fixtures_dir: Path):
        """Test loading dataset from CSV file."""
        csv_file = test_fixtures_dir / "sample_training.csv"
        examples = load_dataset(str(csv_file))

        assert len(examples) == 3
        assert isinstance(examples[0], AmendmentSummaryExample)
        assert examples[0].metadata is not None

    def test_load_with_explicit_format(self, test_fixtures_dir: Path):
        """Test loading dataset with explicit format specification."""
        json_file = test_fixtures_dir / "sample_training.json"
        examples = load_dataset(str(json_file), file_format="json")

        assert len(examples) == 5

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_dataset("nonexistent_file.json")

    def test_load_unsupported_format(self, tmp_path: Path):
        """Test loading unsupported format raises error."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("some content")

        with pytest.raises(ValueError, match="Cannot auto-detect format"):
            load_dataset(str(test_file))

    def test_load_invalid_json(self, tmp_path: Path):
        """Test loading invalid JSON raises error."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text('{"not": "a list"}')

        with pytest.raises(ValueError, match="must contain a list"):
            load_dataset(str(test_file))


class TestDataFrameConversion:
    """Tests for DataFrame conversion functions."""

    def test_to_dataframe(self, sample_examples: list[AmendmentSummaryExample]):
        """Test converting examples to DataFrame."""
        df = to_dataframe(sample_examples)

        assert len(df) == 3
        assert "expose_amdt" in df.columns
        assert "corps_amdt" in df.columns
        assert "summary" in df.columns
        assert "office" in df.columns
        assert "quality_score" in df.columns

        assert df.iloc[0]["office"] == "office_A"
        assert df.iloc[0]["quality_score"] == 0.95

    def test_to_dataframe_empty(self):
        """Test converting empty list to DataFrame."""
        df = to_dataframe([])

        assert len(df) == 0
        assert "expose_amdt" in df.columns

    def test_from_dataframe(self):
        """Test converting DataFrame to examples."""
        df = pd.DataFrame(
            {
                "expose_amdt": ["Exposé 1", "Exposé 2"],
                "corps_amdt": ["Corps 1", "Corps 2"],
                "summary": ["Résumé 1", "Résumé 2"],
                "office": ["office_A", "office_B"],
            }
        )

        examples = from_dataframe(df)

        assert len(examples) == 2
        assert examples[0].expose_amdt == "Exposé 1"
        assert examples[0].metadata is not None
        assert examples[0].metadata["office"] == "office_A"
        assert examples[1].metadata is not None
        assert examples[1].metadata["office"] == "office_B"

    def test_from_dataframe_missing_columns(self):
        """Test converting DataFrame with missing required columns raises error."""
        df = pd.DataFrame(
            {
                "expose_amdt": ["Exposé 1"],
                "summary": ["Résumé 1"],
                # Missing corps_amdt
            }
        )

        with pytest.raises(ValueError, match="missing required columns"):
            from_dataframe(df)

    def test_from_dataframe_with_nan(self):
        """Test converting DataFrame with NaN values in metadata."""
        df = pd.DataFrame(
            {
                "expose_amdt": ["Exposé 1", "Exposé 2"],
                "corps_amdt": ["Corps 1", "Corps 2"],
                "summary": ["Résumé 1", "Résumé 2"],
                "office": ["office_A", None],
            }
        )

        examples = from_dataframe(df)

        assert len(examples) == 2
        assert examples[0].metadata is not None
        assert examples[0].metadata["office"] == "office_A"
        assert examples[1].metadata is not None
        assert examples[1].metadata["office"] is None


class TestSplitDataset:
    """Tests for split_dataset function."""

    def test_split_default_ratio(self, sample_examples: list[AmendmentSummaryExample]):
        """Test splitting with default 80/20 ratio."""
        train, val = split_dataset(sample_examples, random_seed=42)

        assert len(train) == 2
        assert len(val) == 1
        assert len(train) + len(val) == len(sample_examples)

    def test_split_custom_ratio(self, sample_examples: list[AmendmentSummaryExample]):
        """Test splitting with custom ratio."""
        train, val = split_dataset(sample_examples, train_ratio=0.6, random_seed=42)

        # With 3 examples and 0.6 ratio: 1 train, 2 val
        assert len(train) == 1
        assert len(val) == 2

    def test_split_deterministic(self, sample_examples: list[AmendmentSummaryExample]):
        """Test that split is deterministic with same seed."""
        train1, val1 = split_dataset(sample_examples, random_seed=42)
        train2, val2 = split_dataset(sample_examples, random_seed=42)

        # Same seed should give same split
        assert len(train1) == len(train2)
        assert len(val1) == len(val2)

    def test_split_without_shuffle(
        self, sample_examples: list[AmendmentSummaryExample]
    ):
        """Test splitting without shuffling."""
        train, val = split_dataset(sample_examples, shuffle=False)

        # First 80% should be training
        assert train[0].expose_amdt == sample_examples[0].expose_amdt
        assert train[1].expose_amdt == sample_examples[1].expose_amdt
        assert val[0].expose_amdt == sample_examples[2].expose_amdt

    def test_split_empty_dataset(self):
        """Test splitting empty dataset raises error."""
        with pytest.raises(ValueError, match="Cannot split empty dataset"):
            split_dataset([])

    def test_split_invalid_ratio(self, sample_examples: list[AmendmentSummaryExample]):
        """Test splitting with invalid ratio raises error."""
        with pytest.raises(ValueError, match="train_ratio must be between"):
            split_dataset(sample_examples, train_ratio=1.5)

        with pytest.raises(ValueError, match="train_ratio must be between"):
            split_dataset(sample_examples, train_ratio=0.0)


class TestValidateDataset:
    """Tests for validate_dataset function."""

    def test_validate_valid_dataset(
        self, sample_examples: list[AmendmentSummaryExample]
    ):
        """Test validating a valid dataset returns no issues."""
        issues = validate_dataset(sample_examples)

        assert len(issues) == 0

    def test_validate_empty_dataset(self):
        """Test validating empty dataset returns issue."""
        issues = validate_dataset([])

        assert len(issues) == 1
        assert "empty" in issues[0].lower()

    def test_validate_empty_fields(self):
        """Test validating examples with empty required fields."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="",  # Empty
                corps_amdt="Corps test",
                summary="Résumé test",
            ),
            AmendmentSummaryExample(
                expose_amdt="Exposé test",
                corps_amdt="",  # Empty
                summary="Résumé test",
            ),
            AmendmentSummaryExample(
                expose_amdt="Exposé test",
                corps_amdt="Corps test",
                summary="",  # Empty
            ),
        ]

        issues = validate_dataset(examples)

        assert len(issues) >= 3
        assert any("expose_amdt is empty" in issue for issue in issues)
        assert any("corps_amdt is empty" in issue for issue in issues)
        assert any("summary is empty" in issue for issue in issues)

    def test_validate_summary_length(self):
        """Test validating summary length constraints."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="Exposé test long enough for validation",
                corps_amdt="Corps test long enough for validation",
                summary="Trop court",  # Too short (2 words, need 8)
            ),
            AmendmentSummaryExample(
                expose_amdt="Exposé test long enough for validation",
                corps_amdt="Corps test long enough for validation",
                summary="Un résumé bien trop long qui dépasse largement la limite maximale de vingt mots imposée par les règles strictes et formelles",  # Too long (21 words > 20)
            ),
        ]

        issues = validate_dataset(examples)

        assert any("too short" in issue for issue in issues)
        assert any("too long" in issue for issue in issues)

    def test_validate_short_texts(self):
        """Test validating suspiciously short input texts."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="Court",  # Too short
                corps_amdt="Corps test long enough for validation",
                summary="Modifier le code de la santé publique",
            ),
            AmendmentSummaryExample(
                expose_amdt="Exposé test long enough for validation",
                corps_amdt="Court",  # Too short
                summary="Modifier le code de la santé publique",
            ),
        ]

        issues = validate_dataset(examples)

        assert any("suspiciously short" in issue for issue in issues)

    def test_validate_duplicates(self):
        """Test validating duplicate detection."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="Exposé identique",
                corps_amdt="Corps unique 1",
                summary="Résumé test avec au moins huit mots pour validation",
            ),
            AmendmentSummaryExample(
                expose_amdt="Exposé identique",  # Duplicate
                corps_amdt="Corps unique 2",
                summary="Résumé test avec au moins huit mots pour validation",
            ),
        ]

        issues = validate_dataset(examples)

        assert any("duplicate expose_amdt" in issue for issue in issues)


class TestCleanDataset:
    """Tests for clean_dataset function."""

    def test_clean_normalize_whitespace(self):
        """Test whitespace normalization."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="Exposé   avec    espaces\n\nmultiples",
                corps_amdt="Corps\tavec\ttabulations",
                summary="Résumé  avec   espaces",
            ),
        ]

        cleaned = clean_dataset(examples, normalize_whitespace=True)

        assert cleaned[0].expose_amdt == "Exposé avec espaces multiples"
        assert cleaned[0].corps_amdt == "Corps avec tabulations"
        assert cleaned[0].summary == "Résumé avec espaces"

    def test_clean_remove_empty(self):
        """Test removing examples with empty fields."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="Exposé valide",
                corps_amdt="Corps valide",
                summary="Résumé valide",
            ),
            AmendmentSummaryExample(
                expose_amdt="",  # Empty
                corps_amdt="Corps valide",
                summary="Résumé valide",
            ),
            AmendmentSummaryExample(
                expose_amdt="Exposé valide",
                corps_amdt="Corps valide",
                summary="",  # Empty
            ),
        ]

        cleaned = clean_dataset(examples, remove_empty=True)

        assert len(cleaned) == 1
        assert cleaned[0].expose_amdt == "Exposé valide"

    def test_clean_keep_empty(self):
        """Test keeping examples with empty fields when remove_empty=False."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="",
                corps_amdt="Corps valide",
                summary="Résumé valide",
            ),
        ]

        cleaned = clean_dataset(examples, remove_empty=False)

        assert len(cleaned) == 1

    def test_clean_truncate_long_texts(self):
        """Test truncating overly long texts."""
        long_text = "A" * 15000

        examples = [
            AmendmentSummaryExample(
                expose_amdt=long_text,
                corps_amdt=long_text,
                summary="Résumé valide",
            ),
        ]

        cleaned = clean_dataset(examples, max_expose_length=1000, max_corps_length=2000)

        assert len(cleaned[0].expose_amdt) == 1000
        assert len(cleaned[0].corps_amdt) == 2000
        assert cleaned[0].summary == "Résumé valide"

    def test_clean_preserves_metadata(self):
        """Test that cleaning preserves metadata."""
        examples = [
            AmendmentSummaryExample(
                expose_amdt="  Exposé  ",
                corps_amdt="  Corps  ",
                summary="  Résumé  ",
                metadata={"key": "value"},
            ),
        ]

        cleaned = clean_dataset(examples)

        assert cleaned[0].metadata == {"key": "value"}


class TestGetDatasetStatistics:
    """Tests for get_dataset_statistics function."""

    def test_statistics_basic(self, sample_examples: list[AmendmentSummaryExample]):
        """Test computing basic dataset statistics."""
        stats = get_dataset_statistics(sample_examples)

        assert stats["total_examples"] == 3
        assert "summary_length" in stats
        assert "expose_length" in stats
        assert "corps_length" in stats
        assert stats["has_metadata"] == 3
        assert "office" in stats["metadata_fields"]
        assert "quality_score" in stats["metadata_fields"]

    def test_statistics_summary_length(
        self, sample_examples: list[AmendmentSummaryExample]
    ):
        """Test summary length statistics."""
        stats = get_dataset_statistics(sample_examples)

        summary_stats = stats["summary_length"]
        assert "min" in summary_stats
        assert "max" in summary_stats
        assert "mean" in summary_stats
        assert "median" in summary_stats
        assert "std" in summary_stats

    def test_statistics_empty_dataset(self):
        """Test computing statistics for empty dataset."""
        stats = get_dataset_statistics([])

        assert stats["total_examples"] == 0
        assert stats["summary_length"] == {}
        assert stats["has_metadata"] == 0
        assert stats["metadata_fields"] == []
        assert isinstance(stats["metadata_fields"], list)


class TestS3Operations:
    """Tests for S3 save/load operations."""

    @pytest.mark.asyncio
    async def test_save_to_s3(self, sample_examples: list[AmendmentSummaryExample]):
        """Test saving dataset to S3."""
        mock_s3_service = MagicMock()
        mock_s3_service.upload_database_parquet = AsyncMock()

        with patch(
            "graal.summary.dspy_modules.dataset.get_s3_service",
            return_value=mock_s3_service,
        ):
            result = await save_dataset_to_s3(sample_examples, "dspy_datasets/test/v1")

            assert result == "dspy_datasets/test/v1.parquet"
            mock_s3_service.upload_database_parquet.assert_called_once()

            # Check that DataFrame was passed
            call_args = mock_s3_service.upload_database_parquet.call_args
            df_arg = call_args[0][0]
            assert isinstance(df_arg, pd.DataFrame)
            assert len(df_arg) == 3

    @pytest.mark.asyncio
    async def test_save_empty_dataset_raises_error(self):
        """Test that saving empty dataset raises error."""
        with pytest.raises(ValueError, match="Cannot save empty dataset"):
            await save_dataset_to_s3([], "dspy_datasets/test/v1")

    @pytest.mark.asyncio
    async def test_save_adds_parquet_extension(
        self, sample_examples: list[AmendmentSummaryExample]
    ):
        """Test that .parquet extension is added if not present."""
        mock_s3_service = MagicMock()
        mock_s3_service.upload_database_parquet = AsyncMock()

        with patch(
            "graal.summary.dspy_modules.dataset.get_s3_service",
            return_value=mock_s3_service,
        ):
            result = await save_dataset_to_s3(sample_examples, "dspy_datasets/test")

            assert result == "dspy_datasets/test.parquet"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
