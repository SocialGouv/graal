#!/usr/bin/env python3
"""
CLI tool for preparing DSPy training datasets.

This script provides utilities for loading, validating, cleaning, and splitting
training datasets for amendment summary generation.

Usage:
    python scripts/prepare_dspy_training_data.py \
        --input data/training.json \
        --output-dir data/dspy_training/ \
        --format json \
        --train-ratio 0.8 \
        --validate \
        --save-to-s3 dspy_datasets/office_A/

Examples:
    # Basic usage with validation
    python scripts/prepare_dspy_training_data.py \
        --input data/training.json \
        --output-dir data/dspy_training/

    # With S3 upload
    python scripts/prepare_dspy_training_data.py \
        --input data/training.csv \
        --format csv \
        --save-to-s3 dspy_datasets/office_A/v1

    # Dry run mode
    python scripts/prepare_dspy_training_data.py \
        --input data/training.json \
        --dry-run \
        --verbose
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graal.summary.dspy_modules.dataset import (
    AmendmentSummaryExample,
    clean_dataset,
    get_dataset_statistics,
    load_dataset,
    save_dataset_to_s3,
    split_dataset,
    to_dataframe,
    validate_dataset,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def print_statistics(stats: dict, prefix: str = "Dataset") -> None:
    """Print dataset statistics in a readable format."""
    print(f"\n{prefix} Statistics:")
    print(f"  Total examples: {stats['total_examples']}")

    print("\n  Summary length (words):")
    for key, value in stats["summary_length"].items():
        print(
            f"    {key}: {value:.2f}"
            if isinstance(value, float)
            else f"    {key}: {value}"
        )

    print("\n  Exposé length (chars):")
    for key in ["min", "max", "mean", "median"]:
        value = stats["expose_length"][key]
        print(f"    {key}: {value:.0f}")

    print("\n  Corps length (chars):")
    for key in ["min", "max", "mean", "median"]:
        value = stats["corps_length"][key]
        print(f"    {key}: {value:.0f}")

    if stats["metadata_fields"]:
        print("\n  Metadata:")
        print(f"    Examples with metadata: {stats['has_metadata']}")
        print(f"    Metadata fields: {', '.join(stats['metadata_fields'])}")


def save_examples_to_file(
    examples: list[AmendmentSummaryExample],
    output_path: Path,
    format: str = "json",
) -> None:
    """Save examples to local file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [ex.to_dict() for ex in examples], f, indent=2, ensure_ascii=False
            )
    elif format in ["csv", "parquet"]:
        df = to_dataframe(examples)
        if format == "csv":
            df.to_csv(output_path, index=False)
        else:  # parquet
            df.to_parquet(output_path, index=False)
    else:
        raise ValueError(f"Unsupported output format: {format}")

    logging.info(f"Saved {len(examples)} examples to {output_path}")


async def main() -> int:  # noqa: C901
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Prepare DSPy training datasets for amendment summary generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Load, validate, and split dataset
  python scripts/prepare_dspy_training_data.py \\
      --input data/training.json \\
      --output-dir data/dspy_training/ \\
      --validate

  # Load CSV with custom train ratio
  python scripts/prepare_dspy_training_data.py \\
      --input data/training.csv \\
      --format csv \\
      --train-ratio 0.9 \\
      --output-dir data/dspy_training/

  # Save to S3
  python scripts/prepare_dspy_training_data.py \\
      --input data/training.json \\
      --save-to-s3 dspy_datasets/office_A/v1

  # Dry run (validate only, no output)
  python scripts/prepare_dspy_training_data.py \\
      --input data/training.json \\
      --dry-run \\
      --verbose
        """,
    )

    # Input arguments
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to input dataset file",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "csv", "excel", "parquet", "auto"],
        default="auto",
        help="Input file format (default: auto-detect from extension)",
    )

    # Output arguments
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for output files (default: no local output)",
    )
    parser.add_argument(
        "--output-format",
        type=str,
        choices=["json", "csv", "parquet"],
        default="json",
        help="Output file format (default: json)",
    )

    # Processing arguments
    parser.add_argument(
        "--train-ratio",
        type=float,
        default=0.8,
        help="Ratio of data for training (default: 0.8)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate dataset quality and report issues",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Skip data cleaning step",
    )
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Skip train/validation split (save full dataset)",
    )

    # S3 arguments
    parser.add_argument(
        "--save-to-s3",
        type=str,
        default=None,
        help="S3 path prefix for saving datasets (e.g., dspy_datasets/office_A/v1)",
    )

    # General arguments
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and show statistics without saving files",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--min-summary-words",
        type=int,
        default=8,
        help="Minimum summary length in words (default: 8)",
    )
    parser.add_argument(
        "--max-summary-words",
        type=int,
        default=20,
        help="Maximum summary length in words (default: 20)",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger("graal").setLevel(logging.DEBUG)
        logging.setLevel(logging.DEBUG)

    try:
        # Load dataset
        print(f"\n{'=' * 60}")
        print(f"Loading dataset from: {args.input}")
        print(f"{'=' * 60}")

        format_arg = None if args.format == "auto" else args.format
        examples = load_dataset(args.input, file_format=format_arg)

        print(f"Loaded {len(examples)} examples")

        # Compute initial statistics
        initial_stats = get_dataset_statistics(examples)
        print_statistics(initial_stats, "Initial Dataset")

        # Validate dataset
        if args.validate:
            print(f"\n{'=' * 60}")
            print("Validating dataset...")
            print(f"{'=' * 60}")

            issues = validate_dataset(
                examples,
                min_summary_words=args.min_summary_words,
                max_summary_words=args.max_summary_words,
            )

            if issues:
                print(f"\n⚠️  Found {len(issues)} validation issues:")
                for issue in issues[:20]:  # Show first 20 issues
                    print(f"  - {issue}")
                if len(issues) > 20:
                    print(f"  ... and {len(issues) - 20} more issues")
                print(
                    "\nConsider cleaning the dataset or fixing these issues manually."
                )
            else:
                print("✓ No validation issues found!")

        # Clean dataset
        if not args.no_clean:
            print(f"\n{'=' * 60}")
            print("Cleaning dataset...")
            print(f"{'=' * 60}")

            examples = clean_dataset(examples)
            cleaned_stats = get_dataset_statistics(examples)
            print_statistics(cleaned_stats, "Cleaned Dataset")

        # Stop here if dry run
        if args.dry_run:
            print(f"\n{'=' * 60}")
            print("Dry run complete - no files saved")
            print(f"{'=' * 60}")
            return 0

        # Split dataset
        if not args.no_split:
            print(f"\n{'=' * 60}")
            print(f"Splitting dataset (train ratio: {args.train_ratio})...")
            print(f"{'=' * 60}")

            train_examples, val_examples = split_dataset(
                examples,
                train_ratio=args.train_ratio,
                shuffle=True,
                random_seed=42,
            )

            train_stats = get_dataset_statistics(train_examples)
            val_stats = get_dataset_statistics(val_examples)

            print_statistics(train_stats, "Training Set")
            print_statistics(val_stats, "Validation Set")
        else:
            train_examples = examples
            val_examples = []
            print("\nSkipping split - using full dataset")

        # Save to local files
        if args.output_dir:
            print(f"\n{'=' * 60}")
            print(f"Saving to local directory: {args.output_dir}")
            print(f"{'=' * 60}")

            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Determine file extension
            ext = (
                "json"
                if args.output_format == "json"
                else ("csv" if args.output_format == "csv" else "parquet")
            )

            if not args.no_split:
                train_path = output_dir / f"train.{ext}"
                val_path = output_dir / f"validation.{ext}"

                save_examples_to_file(train_examples, train_path, args.output_format)
                save_examples_to_file(val_examples, val_path, args.output_format)

                print(f"✓ Saved training set: {train_path}")
                print(f"✓ Saved validation set: {val_path}")
            else:
                full_path = output_dir / f"full_dataset.{ext}"
                save_examples_to_file(train_examples, full_path, args.output_format)
                print(f"✓ Saved full dataset: {full_path}")

        # Save to S3
        if args.save_to_s3:
            print(f"\n{'=' * 60}")
            print(f"Uploading to S3: {args.save_to_s3}")
            print(f"{'=' * 60}")

            if not args.no_split:
                train_s3_path = f"{args.save_to_s3}_train"
                val_s3_path = f"{args.save_to_s3}_validation"

                train_path = await save_dataset_to_s3(train_examples, train_s3_path)
                val_path = await save_dataset_to_s3(val_examples, val_s3_path)

                print(f"✓ Uploaded training set: {train_path}")
                print(f"✓ Uploaded validation set: {val_path}")
            else:
                full_s3_path = await save_dataset_to_s3(train_examples, args.save_to_s3)
                print(f"✓ Uploaded full dataset: {full_s3_path}")

        print(f"\n{'=' * 60}")
        print("Dataset preparation complete!")
        print(f"{'=' * 60}\n")

        return 0

    except FileNotFoundError as e:
        logging.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logging.error(f"Invalid input: {e}")
        return 1
    except Exception as e:
        logging.error(f"Error: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
