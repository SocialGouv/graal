#!/usr/bin/env python3
"""
CLI tool for optimizing DSPy summary prompts using MIPROv2.

This script trains model-specific prompts for amendment summary generation
and saves them to S3 for production use.

Usage:
    python scripts/optimize_summary_prompts.py \
        --office office_A \
        --model albert \
        --train-data data/dspy_training/train.json \
        --val-data data/dspy_training/validation.json \
        --save-to-s3

Examples:
    # Basic optimization with S3 save
    python scripts/optimize_summary_prompts.py \
        --office office_A \
        --model albert \
        --train-data data/train.json \
        --val-data data/val.json \
        --save-to-s3

    # Dry run with custom hyperparameters
    python scripts/optimize_summary_prompts.py \
        --office office_A \
        --model scaleway \
        --train-data data/train.json \
        --val-data data/val.json \
        --num-candidates 15 \
        --num-iterations 30 \
        --dry-run

    # Load data from S3
    python scripts/optimize_summary_prompts.py \
        --office office_B \
        --model vllm \
        --train-data s3://dspy_datasets/office_B/train \
        --val-data s3://dspy_datasets/office_B/val \
        --save-to-s3
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Callable

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from graal.summary.dspy_modules.adapters import create_dspy_adapter
from graal.summary.dspy_modules.dataset import (
    get_dataset_statistics,
    load_dataset,
    load_dataset_from_s3,
)
from graal.summary.dspy_modules.optimizers import create_optimizer
from graal.summary.dspy_modules.storage import get_dspy_prompt_storage
from graal.summary.llm_clients import LLMAPIClient
from graal.summary.llm_factory import (
    create_albert_client,
    create_ollama_client,
    create_scaleway_client,
    create_vllm_client,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def print_header(text: str, width: int = 80) -> None:
    """Print a formatted header."""
    print(f"\n{'=' * width}")
    print(f"{text:^{width}}")
    print(f"{'=' * width}")


def print_section(text: str, width: int = 80) -> None:
    """Print a formatted section header."""
    print(f"\n{'-' * width}")
    print(f"{text}")
    print(f"{'-' * width}")


def print_statistics(stats: dict[str, Any], prefix: str = "Dataset") -> None:
    """Print dataset statistics in a readable format."""
    print(f"\n{prefix} Statistics:")
    print(f"  Total examples: {stats['total_examples']}")

    print("\n  Summary length (words):")
    for key, value in stats["summary_length"].items():
        if isinstance(value, float):
            print(f"    {key}: {value:.2f}")
        else:
            print(f"    {key}: {value}")

    print("\n  Exposé length (chars):")
    for key in ["min", "max", "mean", "median"]:
        value = stats["expose_length"][key]
        print(f"    {key}: {value:.0f}")

    print("\n  Corps length (chars):")
    for key in ["min", "max", "mean", "median"]:
        value = stats["corps_length"][key]
        print(f"    {key}: {value:.0f}")


def generate_optimization_report(
    office: str,
    model: str,
    train_stats: dict[str, Any],
    val_stats: dict[str, Any],
    result: Any,
    version: str | None = None,
) -> dict[str, Any]:
    """Generate comprehensive optimization report.

    Args:
        office: Office name
        model: Model name
        train_stats: Training dataset statistics
        val_stats: Validation dataset statistics
        result: OptimizationResult from optimizer
        version: S3 version string (if saved)

    Returns:
        Report dictionary
    """
    report = {
        "optimization_info": {
            "office": office,
            "model": model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "dataset_info": {
            "train_size": train_stats["total_examples"],
            "val_size": val_stats["total_examples"],
            "train_summary_length": train_stats["summary_length"],
            "val_summary_length": val_stats["summary_length"],
        },
        "optimization_results": {
            "best_score": result.best_score,
            "train_score": result.train_score,
            "num_iterations": result.num_iterations,
            "total_time_seconds": result.total_time,
            "early_stopped": result.early_stopped,
        },
        "s3_info": {
            "saved": version is not None,
            "version": version,
        },
    }

    # Add history summary
    if result.history:
        report["optimization_history"] = {
            "iterations": len(result.history),
            "initial_val_score": result.history[0]["val_score"]
            if result.history
            else None,
            "final_val_score": result.history[-1]["val_score"]
            if result.history
            else None,
        }

    return report


def print_optimization_report(report: dict[str, Any]) -> None:
    """Print optimization report in a readable format."""
    print_header("OPTIMIZATION REPORT")

    print("\nOptimization Info:")
    print(f"  Office: {report['optimization_info']['office']}")
    print(f"  Model: {report['optimization_info']['model']}")
    print(f"  Timestamp: {report['optimization_info']['timestamp']}")

    print("\nDataset Info:")
    print(f"  Training examples: {report['dataset_info']['train_size']}")
    print(f"  Validation examples: {report['dataset_info']['val_size']}")

    print("\nOptimization Results:")
    print(
        f"  Best validation score: {report['optimization_results']['best_score']:.4f}"
    )
    print(
        f"  Final training score: {report['optimization_results']['train_score']:.4f}"
    )
    print(f"  Iterations completed: {report['optimization_results']['num_iterations']}")
    print(f"  Total time: {report['optimization_results']['total_time_seconds']:.1f}s")
    print(f"  Early stopped: {report['optimization_results']['early_stopped']}")

    if "optimization_history" in report:
        print("\nProgress:")
        print(
            f"  Initial val score: {report['optimization_history']['initial_val_score']:.4f}"
        )
        print(
            f"  Final val score: {report['optimization_history']['final_val_score']:.4f}"
        )
        improvement = (
            report["optimization_history"]["final_val_score"]
            - report["optimization_history"]["initial_val_score"]
        )
        print(f"  Improvement: {improvement:+.4f}")

    if report["s3_info"]["saved"]:
        print("\nS3 Storage:")
        print("  ✓ Saved to S3")
        print(f"  Version: {report['s3_info']['version']}")
    else:
        print("\nS3 Storage:")
        print("  ✗ Not saved (use --save-to-s3 to save)")


def save_report_to_file(report: dict[str, Any], output_path: Path) -> None:
    """Save optimization report to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved optimization report to {output_path}")


async def load_training_data(
    train_path: str, val_path: str
) -> tuple[list[Any], list[Any], dict[str, Any], dict[str, Any]]:
    """Load training and validation datasets.

    Args:
        train_path: Path to training data (local file or S3 path)
        val_path: Path to validation data (local file or S3 path)

    Returns:
        Tuple of (train_examples, val_examples, train_stats, val_stats)
    """
    print_section("Loading Training Data")

    # Load training data
    if train_path.startswith("s3://"):
        logger.info(f"Loading training data from S3: {train_path}")
        train_examples = await load_dataset_from_s3(train_path.replace("s3://", ""))
    else:
        logger.info(f"Loading training data from file: {train_path}")
        train_examples = load_dataset(train_path)

    print(f"✓ Loaded {len(train_examples)} training examples")

    # Load validation data
    if val_path.startswith("s3://"):
        logger.info(f"Loading validation data from S3: {val_path}")
        val_examples = await load_dataset_from_s3(val_path.replace("s3://", ""))
    else:
        logger.info(f"Loading validation data from file: {val_path}")
        val_examples = load_dataset(val_path)

    print(f"✓ Loaded {len(val_examples)} validation examples")

    # Print statistics
    train_stats = get_dataset_statistics(train_examples)
    val_stats = get_dataset_statistics(val_examples)

    print_statistics(train_stats, "Training Set")
    print_statistics(val_stats, "Validation Set")

    return train_examples, val_examples, train_stats, val_stats


def create_llm_client(model: str) -> LLMAPIClient:
    """Create LLM client for the specified model.

    Args:
        model: Model name (albert, scaleway, ollama, vllm)

    Returns:
        LLM client instance

    Raises:
        ValueError: If model is not supported
    """
    print_section(f"Creating LLM Client: {model}")

    client_factories: dict[str, Callable[[], LLMAPIClient]] = {
        "albert": create_albert_client,
        "scaleway": create_scaleway_client,
        "ollama": create_ollama_client,
        "vllm": create_vllm_client,
    }

    factory = client_factories.get(model.lower())
    if not factory:
        raise ValueError(
            f"Unsupported model: {model}. "
            f"Supported models: {list(client_factories.keys())}"
        )

    try:
        client = factory()
        logger.info(f"✓ Created {model} client: {client.name}")
        return client
    except KeyError as e:
        raise ValueError(
            f"Missing environment variables for {model} client. "
            f"Check that all required credentials are set: {e}"
        ) from e


async def run_optimization(  # noqa: C901
    office: str,
    model: str,
    train_path: str,
    val_path: str,
    num_candidates: int,
    num_iterations: int,
    batch_size: int,
    checkpoint_dir: str | None,
    early_stopping_patience: int,
    rate_limit_per_minute: int,
    semantic_weight: float,
    length_weight: float,
    verb_weight: float,
    save_to_s3: bool,
    dry_run: bool,
    report_path: str | None,
) -> int:
    """Run the optimization process.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        print_header(f"DSPy Prompt Optimization: {office} / {model}")

        # Load training data
        train_examples, val_examples, train_stats, val_stats = await load_training_data(
            train_path, val_path
        )

        if dry_run:
            print_header("DRY RUN MODE - No optimization will be performed")
            print("\nConfiguration:")
            print(f"  Office: {office}")
            print(f"  Model: {model}")
            print(f"  Train examples: {len(train_examples)}")
            print(f"  Val examples: {len(val_examples)}")
            print(f"  Num candidates: {num_candidates}")
            print(f"  Num iterations: {num_iterations}")
            print(f"  Batch size: {batch_size}")
            print(f"  Early stopping: {early_stopping_patience}")
            print(f"  Rate limit: {rate_limit_per_minute}/min")
            print(f"  Semantic weight: {semantic_weight}")
            print(f"  Length weight: {length_weight}")
            print(f"  Verb weight: {verb_weight}")
            print(f"  Save to S3: {save_to_s3}")

            print("\n✓ Dry run complete - no optimization performed")
            return 0

        # Create LLM client
        llm_client = create_llm_client(model)

        # Create DSPy adapter
        print_section("Creating DSPy Adapter")
        dspy_adapter = create_dspy_adapter(llm_client)
        logger.info(f"✓ Created DSPy adapter for {model}")

        # Create optimizer
        print_section("Initializing Optimizer")
        optimizer = create_optimizer(
            lm=dspy_adapter,
            trainset=train_examples,
            valset=val_examples,
            num_candidates=num_candidates,
            num_iterations=num_iterations,
            batch_size=batch_size,
            checkpoint_dir=checkpoint_dir,
            early_stopping_patience=early_stopping_patience,
            rate_limit_per_minute=rate_limit_per_minute,
            semantic_weight=semantic_weight,
            length_weight=length_weight,
            verb_weight=verb_weight,
        )
        logger.info("✓ Optimizer initialized")

        # Run optimization
        print_header("Running MIPROv2 Optimization")
        print("\nThis may take a while depending on dataset size and iterations...")
        print("Progress will be logged as optimization proceeds.\n")

        if save_to_s3:
            # Optimize and save to S3
            storage = get_dspy_prompt_storage()
            result, version = await optimizer.optimize_with_storage(
                office=office,
                model=model,
                storage=storage,
            )
        else:
            # Optimize without S3 save
            result = optimizer.optimize()
            version = None

        # Generate and display report
        print_header("Optimization Complete")

        report = generate_optimization_report(
            office=office,
            model=model,
            train_stats=train_stats,
            val_stats=val_stats,
            result=result,
            version=version,
        )

        print_optimization_report(report)

        # Save report to file if requested
        if report_path:
            save_report_to_file(report, Path(report_path))
            print(f"\n✓ Report saved to: {report_path}")

        print("\n" + "=" * 80)
        print("SUCCESS".center(80))
        print("=" * 80 + "\n")

        return 0

    except Exception as e:
        logger.error(f"Optimization failed: {e}", exc_info=True)
        print(f"\n❌ ERROR: {e}\n")
        return 1


async def main() -> int:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Optimize DSPy summary prompts using MIPROv2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic optimization with S3 save
  python scripts/optimize_summary_prompts.py \\
      --office office_A \\
      --model albert \\
      --train-data data/train.json \\
      --val-data data/val.json \\
      --save-to-s3

  # Custom hyperparameters
  python scripts/optimize_summary_prompts.py \\
      --office office_B \\
      --model scaleway \\
      --train-data data/train.json \\
      --val-data data/val.json \\
      --num-candidates 15 \\
      --num-iterations 30 \\
      --early-stopping-patience 5

  # Dry run to test configuration
  python scripts/optimize_summary_prompts.py \\
      --office office_A \\
      --model vllm \\
      --train-data data/train.json \\
      --val-data data/val.json \\
      --dry-run

  # Load data from S3
  python scripts/optimize_summary_prompts.py \\
      --office office_A \\
      --model albert \\
      --train-data s3://dspy_datasets/office_A/train \\
      --val-data s3://dspy_datasets/office_A/val \\
      --save-to-s3
        """,
    )

    # Required arguments
    parser.add_argument(
        "--office",
        type=str,
        required=True,
        help="Office/team name (e.g., office_A, office_B)",
    )
    parser.add_argument(
        "--model",
        type=str,
        required=True,
        choices=["albert", "scaleway", "ollama", "vllm"],
        help="LLM model to optimize for",
    )
    parser.add_argument(
        "--train-data",
        type=str,
        required=True,
        help="Path to training dataset (local file or s3://path)",
    )
    parser.add_argument(
        "--val-data",
        type=str,
        required=True,
        help="Path to validation dataset (local file or s3://path)",
    )

    # Optimization hyperparameters
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=10,
        help="Number of candidate prompts per iteration (default: 10)",
    )
    parser.add_argument(
        "--num-iterations",
        type=int,
        default=50,
        help="Maximum number of optimization iterations (default: 50)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Batch size for processing examples (default: 25)",
    )

    # Advanced options
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default=None,
        help="Directory to save optimization checkpoints (optional)",
    )
    parser.add_argument(
        "--early-stopping-patience",
        type=int,
        default=0,
        help="Stop if no improvement for N iterations (0=disabled, default: 0)",
    )
    parser.add_argument(
        "--rate-limit-per-minute",
        type=int,
        default=0,
        help="Maximum LLM API calls per minute (0=disabled, default: 0)",
    )

    # Metric weights
    parser.add_argument(
        "--semantic-weight",
        type=float,
        default=0.7,
        help="Weight for semantic similarity in metric (default: 0.7)",
    )
    parser.add_argument(
        "--length-weight",
        type=float,
        default=0.3,
        help="Weight for length constraint in metric (default: 0.3)",
    )
    parser.add_argument(
        "--verb-weight",
        type=float,
        default=0.0,
        help="Weight for infinitive verb form in metric (default: 0.0)",
    )

    # Output options
    parser.add_argument(
        "--save-to-s3",
        action="store_true",
        help="Save optimized prompt to S3 storage",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default=None,
        help="Path to save optimization report JSON (optional)",
    )

    # General options
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and show statistics without running optimization",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose:
        logging.getLogger("graal").setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    # Validate arguments
    if args.num_candidates < 1:
        logger.error("num-candidates must be >= 1")
        return 1

    if args.num_iterations < 1:
        logger.error("num-iterations must be >= 1")
        return 1

    if args.batch_size < 1:
        logger.error("batch-size must be >= 1")
        return 1

    # Validate metric weights
    total_weight = args.semantic_weight + args.length_weight + args.verb_weight
    if total_weight <= 0:
        logger.error("Sum of metric weights must be > 0")
        return 1

    # Run optimization
    return await run_optimization(
        office=args.office,
        model=args.model,
        train_path=args.train_data,
        val_path=args.val_data,
        num_candidates=args.num_candidates,
        num_iterations=args.num_iterations,
        batch_size=args.batch_size,
        checkpoint_dir=args.checkpoint_dir,
        early_stopping_patience=args.early_stopping_patience,
        rate_limit_per_minute=args.rate_limit_per_minute,
        semantic_weight=args.semantic_weight,
        length_weight=args.length_weight,
        verb_weight=args.verb_weight,
        save_to_s3=args.save_to_s3,
        dry_run=args.dry_run,
        report_path=args.report_path,
    )


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
