"""
Dataset management utilities for DSPy training.

This module provides tools for loading, validating, and managing
training datasets for amendment summary generation.
"""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from graal.utils.s3_service import get_s3_service


@dataclass
class AmendmentSummaryExample:
    """Single training example for amendment summary generation.

    Attributes:
        expose_amdt: Exposé de l'amendement (explanatory statement)
        corps_amdt: Corps de l'amendement (body of the amendment)
        summary: Reference summary (ground truth)
        metadata: Optional metadata (office, quality_score, human_validated, etc.)
    """

    expose_amdt: str
    corps_amdt: str
    summary: str
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert example to dictionary format."""
        result = {
            "expose_amdt": self.expose_amdt,
            "corps_amdt": self.corps_amdt,
            "summary": self.summary,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AmendmentSummaryExample":
        """Create example from dictionary format."""
        return cls(
            expose_amdt=data["expose_amdt"],
            corps_amdt=data["corps_amdt"],
            summary=data["summary"],
            metadata=data.get("metadata"),
        )


def load_dataset(
    path: str, file_format: str | None = None
) -> list[AmendmentSummaryExample]:
    """Load training dataset from various formats.

    Supports JSON, CSV, Excel, Parquet formats. Auto-detects format from file
    extension if format parameter is not provided.

    Args:
        path: Path to the dataset file
        format: Optional format specification ("json", "csv", "excel", "parquet")
                If None, auto-detected from file extension

    Returns:
        List of AmendmentSummaryExample instances

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If format is unsupported or file is invalid

    Examples:
        >>> examples = load_dataset("data/training.json")
        >>> examples = load_dataset("data/training.csv", format="csv")
    """
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {path}")

    # Auto-detect format from extension
    if file_format is None:
        extension = file_path.suffix.lower()
        format_mapping = {
            ".json": "json",
            ".csv": "csv",
            ".xlsx": "excel",
            ".xls": "excel",
            ".parquet": "parquet",
        }
        file_format = format_mapping.get(extension)

        if file_format is None:
            raise ValueError(
                f"Cannot auto-detect format for extension: {extension}. "
                "Supported formats: json, csv, excel, parquet"
            )

    file_format = file_format.lower()

    logging.info(f"Loading dataset from {path} (format: {file_format})")

    if file_format == "json":
        return _load_from_json(file_path)
    elif file_format == "csv":
        return _load_from_csv(file_path)
    elif file_format == "excel":
        return _load_from_excel(file_path)
    elif file_format == "parquet":
        return _load_from_parquet(file_path)
    else:
        raise ValueError(
            f"Unsupported format: {file_format}. "
            "Supported formats: json, csv, excel, parquet"
        )


def _load_from_json(path: Path) -> list[AmendmentSummaryExample]:
    """Load dataset from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON file must contain a list of examples")

    examples = []
    for idx, item in enumerate(data):
        try:
            examples.append(AmendmentSummaryExample.from_dict(item))
        except (KeyError, TypeError) as e:
            logging.warning(f"Skipping invalid item at index {idx}: {e}")

    logging.info(f"Loaded {len(examples)} examples from JSON")
    return examples


def _load_from_csv(path: Path) -> list[AmendmentSummaryExample]:
    """Load dataset from CSV file."""
    df = pd.read_csv(path)
    return _dataframe_to_examples(df)


def _load_from_excel(path: Path) -> list[AmendmentSummaryExample]:
    """Load dataset from Excel file."""
    df = pd.read_excel(path)
    return _dataframe_to_examples(df)


def _load_from_parquet(path: Path) -> list[AmendmentSummaryExample]:
    """Load dataset from Parquet file."""
    df = pd.read_parquet(path)
    return _dataframe_to_examples(df)


def _dataframe_to_examples(df: pd.DataFrame) -> list[AmendmentSummaryExample]:
    """Convert DataFrame to list of examples."""
    required_columns = {"expose_amdt", "corps_amdt", "summary"}
    missing_columns = required_columns - set(df.columns)

    if missing_columns:
        raise ValueError(f"DataFrame missing required columns: {missing_columns}")

    # Get metadata columns (any column not in required set)
    metadata_columns = [col for col in df.columns if col not in required_columns]

    examples = []
    for _idx, row in df.iterrows():
        metadata = (
            {col: row[col] for col in metadata_columns} if metadata_columns else None
        )
        # Convert NaN to None for metadata
        if metadata:
            metadata = {k: (None if pd.isna(v) else v) for k, v in metadata.items()}

        examples.append(
            AmendmentSummaryExample(
                expose_amdt=str(row["expose_amdt"]),
                corps_amdt=str(row["corps_amdt"]),
                summary=str(row["summary"]),
                metadata=metadata if metadata else None,
            )
        )

    logging.info(f"Loaded {len(examples)} examples from DataFrame")
    return examples


def from_dataframe(df: pd.DataFrame) -> list[AmendmentSummaryExample]:
    """Convert pandas DataFrame to list of examples.

    Args:
        df: DataFrame with columns: expose_amdt, corps_amdt, summary, and optional metadata

    Returns:
        List of AmendmentSummaryExample instances

    Raises:
        ValueError: If DataFrame is missing required columns
    """
    return _dataframe_to_examples(df)


def to_dataframe(examples: list[AmendmentSummaryExample]) -> pd.DataFrame:
    """Convert list of examples to pandas DataFrame.

    Args:
        examples: List of AmendmentSummaryExample instances

    Returns:
        DataFrame with all examples and their metadata
    """
    if not examples:
        return pd.DataFrame(columns=["expose_amdt", "corps_amdt", "summary"])

    # Convert examples to dictionaries
    records = []
    for example in examples:
        record = {
            "expose_amdt": example.expose_amdt,
            "corps_amdt": example.corps_amdt,
            "summary": example.summary,
        }
        # Add metadata fields as separate columns
        if example.metadata:
            record.update(example.metadata)
        records.append(record)

    return pd.DataFrame(records)


def split_dataset(
    examples: list[AmendmentSummaryExample],
    train_ratio: float = 0.8,
    shuffle: bool = True,
    random_seed: int = 42,
) -> tuple[list[AmendmentSummaryExample], list[AmendmentSummaryExample]]:
    """Split dataset into training and validation sets.

    Args:
        examples: List of examples to split
        train_ratio: Proportion of data for training (0.0 to 1.0)
        shuffle: Whether to shuffle before splitting
        random_seed: Random seed for reproducibility

    Returns:
        Tuple of (train_examples, validation_examples)

    Raises:
        ValueError: If train_ratio is not in valid range or examples is empty
    """
    if not examples:
        raise ValueError("Cannot split empty dataset")

    if not 0.0 < train_ratio < 1.0:
        raise ValueError(f"train_ratio must be between 0 and 1, got {train_ratio}")

    # Shuffle if requested
    if shuffle:
        import random

        examples_copy = examples.copy()
        random.seed(random_seed)
        random.shuffle(examples_copy)
    else:
        examples_copy = examples

    # Calculate split point
    split_idx = int(len(examples_copy) * train_ratio)

    train_examples = examples_copy[:split_idx]
    val_examples = examples_copy[split_idx:]

    logging.info(
        f"Split dataset: {len(train_examples)} training, {len(val_examples)} validation"
    )

    return train_examples, val_examples


def validate_dataset(  # noqa: C901
    examples: list[AmendmentSummaryExample],
    min_summary_words: int = 8,
    max_summary_words: int = 20,
) -> list[str]:
    """Validate dataset and return list of issues found.

    Checks for:
    - Empty expose_amdt or corps_amdt
    - Empty summaries
    - Summaries outside word count range
    - Very short input texts (potential data quality issues)
    - Near-duplicate examples

    Args:
        examples: List of examples to validate
        min_summary_words: Minimum acceptable summary length
        max_summary_words: Maximum acceptable summary length

    Returns:
        List of issue descriptions (empty if dataset is valid)
    """
    issues = []

    if not examples:
        issues.append("Dataset is empty")
        return issues

    # Track for duplicate detection
    expose_hashes: dict[int, int] = {}
    corps_hashes: dict[int, int] = {}

    for idx, example in enumerate(examples):
        # Check for empty inputs
        if not example.expose_amdt or not example.expose_amdt.strip():
            issues.append(f"Example {idx}: expose_amdt is empty")

        if not example.corps_amdt or not example.corps_amdt.strip():
            issues.append(f"Example {idx}: corps_amdt is empty")

        if not example.summary or not example.summary.strip():
            issues.append(f"Example {idx}: summary is empty")
            continue

        # Check summary length
        summary_words = len(example.summary.strip().split())
        if summary_words < min_summary_words:
            issues.append(
                f"Example {idx}: summary too short ({summary_words} words, "
                f"minimum {min_summary_words})"
            )
        elif summary_words > max_summary_words:
            issues.append(
                f"Example {idx}: summary too long ({summary_words} words, "
                f"maximum {max_summary_words})"
            )

        # Check for very short texts
        if len(example.expose_amdt.strip()) < 20:
            issues.append(
                f"Example {idx}: expose_amdt suspiciously short "
                f"({len(example.expose_amdt)} chars)"
            )

        if len(example.corps_amdt.strip()) < 20:
            issues.append(
                f"Example {idx}: corps_amdt suspiciously short "
                f"({len(example.corps_amdt)} chars)"
            )

        # Track duplicates
        expose_hash = hash(example.expose_amdt.strip().lower())
        corps_hash = hash(example.corps_amdt.strip().lower())

        if expose_hash in expose_hashes:
            issues.append(
                f"Example {idx}: duplicate expose_amdt (same as example "
                f"{expose_hashes[expose_hash]})"
            )
        else:
            expose_hashes[expose_hash] = idx

        if corps_hash in corps_hashes:
            issues.append(
                f"Example {idx}: duplicate corps_amdt (same as example "
                f"{corps_hashes[corps_hash]})"
            )
        else:
            corps_hashes[corps_hash] = idx

    logging.info(f"Validation found {len(issues)} issues")
    return issues


def clean_dataset(
    examples: list[AmendmentSummaryExample],
    remove_empty: bool = True,
    normalize_whitespace: bool = True,
    max_expose_length: int = 10000,
    max_corps_length: int = 50000,
) -> list[AmendmentSummaryExample]:
    """Clean and normalize dataset.

    Operations:
    - Remove entries with missing required fields (if remove_empty=True)
    - Normalize whitespace (remove extra spaces, newlines)
    - Truncate overly long texts with warning

    Args:
        examples: List of examples to clean
        remove_empty: Whether to remove examples with empty required fields
        normalize_whitespace: Whether to normalize whitespace
        max_expose_length: Maximum length for expose_amdt (truncate if longer)
        max_corps_length: Maximum length for corps_amdt (truncate if longer)

    Returns:
        List of cleaned examples
    """
    cleaned_examples = []
    removed_count = 0
    truncated_count = 0

    for idx, example in enumerate(examples):
        # Check for empty required fields
        if remove_empty:
            if (
                not example.expose_amdt
                or not example.expose_amdt.strip()
                or not example.corps_amdt
                or not example.corps_amdt.strip()
                or not example.summary
                or not example.summary.strip()
            ):
                logging.debug(f"Removing example {idx}: empty required field")
                removed_count += 1
                continue

        # Create cleaned copy
        cleaned_expose = example.expose_amdt
        cleaned_corps = example.corps_amdt
        cleaned_summary = example.summary

        if normalize_whitespace:
            # Normalize whitespace: collapse multiple spaces, remove leading/trailing
            cleaned_expose = re.sub(r"\s+", " ", cleaned_expose).strip()
            cleaned_corps = re.sub(r"\s+", " ", cleaned_corps).strip()
            cleaned_summary = re.sub(r"\s+", " ", cleaned_summary).strip()

        # Truncate overly long texts
        if len(cleaned_expose) > max_expose_length:
            logging.warning(
                f"Example {idx}: truncating expose_amdt from "
                f"{len(cleaned_expose)} to {max_expose_length} chars"
            )
            cleaned_expose = cleaned_expose[:max_expose_length]
            truncated_count += 1

        if len(cleaned_corps) > max_corps_length:
            logging.warning(
                f"Example {idx}: truncating corps_amdt from "
                f"{len(cleaned_corps)} to {max_corps_length} chars"
            )
            cleaned_corps = cleaned_corps[:max_corps_length]
            truncated_count += 1

        cleaned_examples.append(
            AmendmentSummaryExample(
                expose_amdt=cleaned_expose,
                corps_amdt=cleaned_corps,
                summary=cleaned_summary,
                metadata=example.metadata,
            )
        )

    logging.info(
        f"Cleaned dataset: {len(cleaned_examples)} examples kept, "
        f"{removed_count} removed, {truncated_count} truncated"
    )

    return cleaned_examples


def get_dataset_statistics(
    examples: list[AmendmentSummaryExample],
) -> dict[str, Any]:
    """Compute comprehensive dataset statistics.

    Args:
        examples: List of examples to analyze

    Returns:
        Dictionary with statistics including:
        - total_examples: Total number of examples
        - summary_length: Statistics about summary word counts
        - expose_length: Statistics about expose_amdt character counts
        - corps_length: Statistics about corps_amdt character counts
        - has_metadata: Count of examples with metadata
        - metadata_fields: Set of all metadata field names
    """
    if not examples:
        return {
            "total_examples": 0,
            "summary_length": {},
            "expose_length": {},
            "corps_length": {},
            "has_metadata": 0,
            "metadata_fields": [],
        }

    import numpy as np

    # Collect lengths
    summary_lengths = [len(ex.summary.split()) for ex in examples]
    expose_lengths = [len(ex.expose_amdt) for ex in examples]
    corps_lengths = [len(ex.corps_amdt) for ex in examples]

    # Collect metadata info
    metadata_count = sum(1 for ex in examples if ex.metadata)
    metadata_fields: set[str] = set()
    for ex in examples:
        if ex.metadata:
            metadata_fields.update(ex.metadata.keys())

    return {
        "total_examples": len(examples),
        "summary_length": {
            "min": int(np.min(summary_lengths)),
            "max": int(np.max(summary_lengths)),
            "mean": float(np.mean(summary_lengths)),
            "median": float(np.median(summary_lengths)),
            "std": float(np.std(summary_lengths)),
        },
        "expose_length": {
            "min": int(np.min(expose_lengths)),
            "max": int(np.max(expose_lengths)),
            "mean": float(np.mean(expose_lengths)),
            "median": float(np.median(expose_lengths)),
        },
        "corps_length": {
            "min": int(np.min(corps_lengths)),
            "max": int(np.max(corps_lengths)),
            "mean": float(np.mean(corps_lengths)),
            "median": float(np.median(corps_lengths)),
        },
        "has_metadata": metadata_count,
        "metadata_fields": sorted(metadata_fields),
    }


async def save_dataset_to_s3(
    examples: list[AmendmentSummaryExample], s3_path: str
) -> str:
    """Save dataset to S3 in Parquet format for reproducibility.

    Args:
        examples: List of examples to save
        s3_path: S3 path (e.g., "dspy_datasets/office_A/training_v1")
                 .parquet extension will be added automatically if not present

    Returns:
        Full S3 path where dataset was saved

    Raises:
        Exception: If S3 is not configured or upload fails
    """
    if not examples:
        raise ValueError("Cannot save empty dataset")

    # Ensure .parquet extension
    if not s3_path.endswith(".parquet"):
        s3_path = f"{s3_path}.parquet"

    # Convert to DataFrame
    df = to_dataframe(examples)

    # Upload to S3 using S3Service
    s3_service = get_s3_service()
    await s3_service.upload_database_parquet(df, s3_path)

    logging.info(f"Saved {len(examples)} examples to S3: {s3_path}")
    return s3_path


async def load_dataset_from_s3(s3_path: str) -> list[AmendmentSummaryExample]:
    """Load dataset from S3.

    Args:
        s3_path: S3 path to the dataset (e.g., "dspy_datasets/office_A/training_v1.parquet")

    Returns:
        List of AmendmentSummaryExample instances

    Raises:
        Exception: If S3 is not configured or file not found
    """
    # Load from S3 using S3Service
    s3_service = get_s3_service()
    df = await s3_service.load_database_parquet(s3_path)

    # Convert to examples
    examples = from_dataframe(df)

    logging.info(f"Loaded {len(examples)} examples from S3: {s3_path}")
    return examples
