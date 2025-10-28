"""
MIPROv2 optimization logic for prompt optimization.

This module contains the optimizer implementation for training model-specific
prompts using DSPy's MIPROv2 optimizer with progress tracking, checkpointing,
rate limiting, and early stopping support.
"""

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

import dspy
from dspy.teleprompt import MIPROv2

from graal.summary.dspy_modules.dataset import AmendmentSummaryExample
from graal.summary.dspy_modules.metrics import french_summary_metric
from graal.summary.dspy_modules.programs import (
    AmendmentSummarizer,
)
from graal.summary.dspy_modules.storage import DSPyPromptStorage
from graal.utils.rate_limiter import TokenBucketRateLimiter


@dataclass
class OptimizationConfig:
    """Configuration for DSPy optimization.

    Attributes:
        num_candidates: Number of candidate prompts to generate per iteration
        num_iterations: Maximum number of optimization iterations
        batch_size: Batch size for processing examples during optimization
        init_temperature: Initial temperature for prompt generation
        track_stats: Whether to track detailed statistics during optimization
        checkpoint_dir: Directory to save optimization checkpoints (optional)
        checkpoint_frequency: Save checkpoint every N iterations
        early_stopping_patience: Stop if no improvement for N iterations (0=disabled)
        early_stopping_threshold: Minimum improvement to reset patience counter
        rate_limit_per_minute: Maximum LLM API calls per minute (0=disabled)
        semantic_weight: Weight for semantic similarity in metric
        length_weight: Weight for length constraint in metric
        verb_weight: Weight for infinitive verb form in metric
        embedding_model: Sentence-transformers model for semantic similarity
    """

    num_candidates: int = 10
    num_iterations: int = 50
    batch_size: int = 25
    init_temperature: float = 1.0
    track_stats: bool = True
    checkpoint_dir: Optional[Path] = None
    checkpoint_frequency: int = 10
    early_stopping_patience: int = 0
    early_stopping_threshold: float = 0.001
    rate_limit_per_minute: int = 0
    semantic_weight: float = 0.7
    length_weight: float = 0.3
    verb_weight: float = 0.0
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass
class OptimizationResult:
    """Result of optimization process.

    Attributes:
        optimized_program: The optimized DSPy program
        best_score: Best validation score achieved
        train_score: Final training score
        num_iterations: Number of iterations completed
        total_time: Total optimization time in seconds
        history: Optimization history with scores per iteration
        early_stopped: Whether optimization stopped early
        checkpoint_path: Path to saved checkpoint (if any)
    """

    optimized_program: dspy.Module
    best_score: float
    train_score: float
    num_iterations: int
    total_time: float
    history: list[dict[str, Any]]
    early_stopped: bool
    checkpoint_path: Optional[Path]


class OptimizationProgressTracker:
    """Tracks optimization progress with logging and statistics."""

    def __init__(self, config: OptimizationConfig):
        """Initialize progress tracker.

        Args:
            config: Optimization configuration
        """
        self.config = config
        self.history: list[dict[str, Any]] = []
        self.start_time = time.time()
        self.best_score = 0.0
        self.best_iteration = 0
        self.iterations_without_improvement = 0

    def log_iteration(
        self, iteration: int, train_score: float, val_score: float
    ) -> None:
        """Log metrics for an iteration.

        Args:
            iteration: Current iteration number
            train_score: Training set score
            val_score: Validation set score
        """
        elapsed = time.time() - self.start_time
        improvement = val_score - self.best_score

        # Update best score
        if val_score > self.best_score:
            self.best_score = val_score
            self.best_iteration = iteration
            self.iterations_without_improvement = 0
        else:
            self.iterations_without_improvement += 1

        # Log to history
        self.history.append(
            {
                "iteration": iteration,
                "train_score": train_score,
                "val_score": val_score,
                "best_score": self.best_score,
                "improvement": improvement,
                "elapsed_seconds": elapsed,
            }
        )

        # Log to console
        logging.info(
            f"Iteration {iteration}/{self.config.num_iterations}: "
            f"train={train_score:.4f}, val={val_score:.4f}, "
            f"best={self.best_score:.4f} (iter {self.best_iteration}), "
            f"improvement={improvement:+.4f}, "
            f"elapsed={elapsed:.1f}s"
        )

    def should_stop_early(self) -> bool:
        """Check if optimization should stop early.

        Returns:
            True if early stopping criteria are met
        """
        if self.config.early_stopping_patience == 0:
            return False

        if self.iterations_without_improvement >= self.config.early_stopping_patience:
            logging.info(
                f"Early stopping: No improvement for {self.iterations_without_improvement} iterations"
            )
            return True

        return False

    def get_summary(self) -> dict[str, Any]:
        """Get optimization summary statistics.

        Returns:
            Dictionary with summary statistics
        """
        elapsed = time.time() - self.start_time
        return {
            "total_iterations": len(self.history),
            "best_score": self.best_score,
            "best_iteration": self.best_iteration,
            "total_time_seconds": elapsed,
            "early_stopped": self.should_stop_early(),
        }


class AmendmentSummaryOptimizer:
    """Optimizer for amendment summary generation using MIPROv2.

    This class orchestrates the optimization process for DSPy-based summary
    generation, including:
    - MIPROv2 optimization with custom metrics
    - Progress tracking and logging
    - Checkpoint saving for long-running optimizations
    - Early stopping to prevent overfitting
    - Rate limiting to avoid overwhelming LLM APIs
    - Optimization history and statistics
    """

    def __init__(
        self,
        lm: dspy.LM,
        trainset: list[AmendmentSummaryExample],
        valset: list[AmendmentSummaryExample],
        config: Optional[OptimizationConfig] = None,
    ):
        """Initialize the optimizer.

        Args:
            lm: DSPy language model (wrapped GRAAL LLM client)
            trainset: Training dataset examples
            valset: Validation dataset examples
            config: Optimization configuration (uses defaults if not provided)

        Raises:
            ValueError: If datasets are empty or invalid
        """
        if not trainset:
            raise ValueError("Training dataset cannot be empty")
        if not valset:
            raise ValueError("Validation dataset cannot be empty")

        self.lm = lm
        self.trainset = self._convert_to_dspy_examples(trainset)
        self.valset = self._convert_to_dspy_examples(valset)
        self.config = config or OptimizationConfig()

        # Initialize components
        self.tracker = OptimizationProgressTracker(self.config)

        # Initialize rate limiter if enabled
        self.rate_limiter: Optional[TokenBucketRateLimiter] = None
        if self.config.rate_limit_per_minute > 0:
            self.rate_limiter = TokenBucketRateLimiter(
                rate_per_minute=self.config.rate_limit_per_minute
            )
            logging.info(
                f"Rate limiter enabled: {self.config.rate_limit_per_minute} calls/min"
            )

        # Create checkpoint directory if needed
        if self.config.checkpoint_dir:
            self.config.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        logging.info(
            f"Initialized optimizer: train_size={len(self.trainset)}, "
            f"val_size={len(self.valset)}, "
            f"num_candidates={self.config.num_candidates}, "
            f"num_iterations={self.config.num_iterations}"
        )

    def _convert_to_dspy_examples(
        self, examples: list[AmendmentSummaryExample]
    ) -> list[dspy.Example]:
        """Convert AmendmentSummaryExample to DSPy Example format.

        Args:
            examples: List of AmendmentSummaryExample objects

        Returns:
            List of DSPy Example objects
        """
        dspy_examples = []
        for ex in examples:
            dspy_ex = dspy.Example(
                expose_amdt=ex.expose_amdt,
                corps_amdt=ex.corps_amdt,
                summary=ex.summary,
            ).with_inputs("expose_amdt", "corps_amdt")
            dspy_examples.append(dspy_ex)
        return dspy_examples

    def _create_metric(self) -> Callable:
        """Create evaluation metric with configured weights.

        Returns:
            Metric function for DSPy optimization
        """

        def metric(example: dspy.Example, prediction: Any, trace: Any = None) -> float:
            return french_summary_metric(
                example=example,
                prediction=prediction,
                trace=trace,
                semantic_weight=self.config.semantic_weight,
                length_weight=self.config.length_weight,
                verb_weight=self.config.verb_weight,
                embedding_model=self.config.embedding_model,
            )

        return metric

    def _save_checkpoint(self, program: dspy.Module, iteration: int) -> Optional[Path]:
        """Save optimization checkpoint.

        Args:
            program: Current optimized program
            iteration: Current iteration number

        Returns:
            Path to saved checkpoint, or None if not saved
        """
        if not self.config.checkpoint_dir:
            return None

        checkpoint_path = (
            self.config.checkpoint_dir / f"checkpoint_iter_{iteration}.json"
        )

        try:
            # Save program state
            program.save(str(checkpoint_path))

            # Save optimization metadata
            metadata_path = checkpoint_path.with_suffix(".meta.json")
            metadata = {
                "iteration": iteration,
                "best_score": self.tracker.best_score,
                "history": self.tracker.history,
                "config": {
                    "num_candidates": self.config.num_candidates,
                    "num_iterations": self.config.num_iterations,
                    "batch_size": self.config.batch_size,
                    "init_temperature": self.config.init_temperature,
                },
            }

            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logging.info(f"Saved checkpoint: {checkpoint_path}")
            return checkpoint_path

        except Exception as e:
            logging.error(f"Failed to save checkpoint: {e}")
            return None

    def optimize(
        self, program_class: type[dspy.Module] = AmendmentSummarizer
    ) -> OptimizationResult:
        """Run MIPROv2 optimization.

        Args:
            program_class: DSPy program class to optimize (default: AmendmentSummarizer)

        Returns:
            OptimizationResult with optimized program and statistics

        Raises:
            RuntimeError: If optimization fails
        """
        logging.info("Starting MIPROv2 optimization...")
        start_time = time.time()

        try:
            # Set language model
            dspy.configure(lm=self.lm)

            # Create metric
            metric = self._create_metric()

            # Initialize program
            program = program_class()
            logging.info(f"Initialized program: {program_class.__name__}")

            # Create optimizer
            optimizer = MIPROv2(
                metric=metric,
                num_candidates=self.config.num_candidates,
                init_temperature=self.config.init_temperature,
                verbose=True,
            )

            # Track optimization progress
            checkpoint_path = None

            # Run optimization
            logging.info("Running MIPROv2 optimization...")
            optimized_program = optimizer.compile(
                program,
                trainset=self.trainset,
                num_trials=self.config.num_iterations,
                max_bootstrapped_demos=3,
                max_labeled_demos=5,
                eval_kwargs={"num_threads": 1},
            )

            # Evaluate final program
            train_score = self._evaluate_program(optimized_program, self.trainset)
            val_score = self._evaluate_program(optimized_program, self.valset)

            # Log final iteration
            self.tracker.log_iteration(
                self.config.num_iterations, train_score, val_score
            )

            # Save final checkpoint
            if self.config.checkpoint_dir:
                checkpoint_path = self._save_checkpoint(
                    optimized_program, self.config.num_iterations
                )

            # Create result
            elapsed = time.time() - start_time
            result = OptimizationResult(
                optimized_program=optimized_program,
                best_score=self.tracker.best_score,
                train_score=train_score,
                num_iterations=len(self.tracker.history),
                total_time=elapsed,
                history=self.tracker.history,
                early_stopped=self.tracker.should_stop_early(),
                checkpoint_path=checkpoint_path,
            )

            logging.info(
                f"Optimization complete: best_score={result.best_score:.4f}, "
                f"time={elapsed:.1f}s, iterations={result.num_iterations}"
            )

            return result

        except Exception as e:
            logging.error(f"Optimization failed: {e}")
            raise RuntimeError(f"MIPROv2 optimization failed: {e}") from e

    def _evaluate_program(
        self, program: dspy.Module, dataset: list[dspy.Example]
    ) -> float:
        """Evaluate program on a dataset.

        Args:
            program: DSPy program to evaluate
            dataset: Dataset to evaluate on

        Returns:
            Average metric score across dataset
        """
        metric = self._create_metric()
        scores = []

        for example in dataset:
            try:
                prediction = program(
                    expose_amdt=example.expose_amdt, corps_amdt=example.corps_amdt
                )
                score = metric(example, prediction)
                scores.append(score)
            except Exception as e:
                logging.warning(f"Evaluation error for example: {e}")
                scores.append(0.0)

        return sum(scores) / len(scores) if scores else 0.0

    async def optimize_with_storage(
        self,
        office: str,
        model: str,
        storage: DSPyPromptStorage,
        program_class: type[dspy.Module] = AmendmentSummarizer,
    ) -> tuple[OptimizationResult, str]:
        """Run optimization and save result to S3 storage.

        Args:
            office: Office/team name
            model: Model name
            storage: DSPy prompt storage instance
            program_class: DSPy program class to optimize

        Returns:
            Tuple of (OptimizationResult, version_string)

        Raises:
            RuntimeError: If optimization or storage fails
        """
        # Run optimization
        result = self.optimize(program_class=program_class)

        # Prepare prompt data for storage
        prompt_data = {
            "version": "1.0",
            "metadata": {
                "office": office,
                "model": model,
                "created_at": None,  # Will be set by storage
                "optimization": {
                    "best_score": result.best_score,
                    "train_score": result.train_score,
                    "num_iterations": result.num_iterations,
                    "total_time": result.total_time,
                    "early_stopped": result.early_stopped,
                    "config": {
                        "num_candidates": self.config.num_candidates,
                        "num_iterations": self.config.num_iterations,
                        "batch_size": self.config.batch_size,
                        "init_temperature": self.config.init_temperature,
                        "semantic_weight": self.config.semantic_weight,
                        "length_weight": self.config.length_weight,
                        "verb_weight": self.config.verb_weight,
                    },
                },
            },
            "prompt": result.optimized_program.dump_state(),
        }

        # Save to S3
        logging.info(f"Saving optimized prompt to S3: office={office}, model={model}")
        version = await storage.save_optimized_prompt(office, model, prompt_data)
        logging.info(f"Saved optimized prompt: version={version}")

        return result, version


def create_optimizer(
    lm: dspy.LM,
    trainset: list[AmendmentSummaryExample],
    valset: list[AmendmentSummaryExample],
    num_candidates: int = 10,
    num_iterations: int = 50,
    batch_size: int = 25,
    checkpoint_dir: Optional[Path | str] = None,
    early_stopping_patience: int = 0,
    rate_limit_per_minute: int = 0,
    **metric_kwargs,
) -> AmendmentSummaryOptimizer:
    """Factory function to create optimizer with common configuration.

    Args:
        lm: DSPy language model
        trainset: Training dataset
        valset: Validation dataset
        num_candidates: Number of candidate prompts per iteration
        num_iterations: Maximum optimization iterations
        batch_size: Batch size for processing
        checkpoint_dir: Directory for checkpoints (optional)
        early_stopping_patience: Patience for early stopping (0=disabled)
        rate_limit_per_minute: Maximum API calls per minute (0=disabled)
        **metric_kwargs: Additional metric configuration (semantic_weight, etc.)

    Returns:
        Configured AmendmentSummaryOptimizer instance
    """
    config = OptimizationConfig(
        num_candidates=num_candidates,
        num_iterations=num_iterations,
        batch_size=batch_size,
        checkpoint_dir=Path(checkpoint_dir) if checkpoint_dir else None,
        early_stopping_patience=early_stopping_patience,
        rate_limit_per_minute=rate_limit_per_minute,
        semantic_weight=metric_kwargs.get("semantic_weight", 0.7),
        length_weight=metric_kwargs.get("length_weight", 0.3),
        verb_weight=metric_kwargs.get("verb_weight", 0.0),
        embedding_model=metric_kwargs.get(
            "embedding_model",
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        ),
    )

    return AmendmentSummaryOptimizer(lm, trainset, valset, config)
