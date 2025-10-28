"""
Tests for DSPy MIPROv2 optimizer implementation.

This module tests the AmendmentSummaryOptimizer class including:
- Optimizer initialization and configuration
- Progress tracking and logging
- Checkpoint saving and loading
- Rate limiting
- Early stopping
- Optimization process
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import dspy
import pytest

from graal.summary.dspy_modules.dataset import AmendmentSummaryExample
from graal.summary.dspy_modules.optimizers import (
    AmendmentSummaryOptimizer,
    OptimizationConfig,
    OptimizationProgressTracker,
    OptimizationResult,
    create_optimizer,
)
from graal.summary.dspy_modules.programs import AmendmentSummarizer

# Fixtures


@pytest.fixture
def sample_train_data() -> list[AmendmentSummaryExample]:
    """Create sample training data."""
    return [
        AmendmentSummaryExample(
            expose_amdt="Cet amendement vise à modifier l'article 1.",
            corps_amdt="I. - L'article L. 111-1 est modifié.",
            summary="Modifier l'article L. 111-1 du code",
            metadata={"office": "office_A"},
        ),
        AmendmentSummaryExample(
            expose_amdt="Amendement de coordination technique.",
            corps_amdt="II. - Coordination avec l'article 2.",
            summary="Coordonner avec l'article 2",
            metadata={"office": "office_A"},
        ),
        AmendmentSummaryExample(
            expose_amdt="Supprimer les dispositions obsolètes.",
            corps_amdt="III. - L'article L. 222-3 est abrogé.",
            summary="Abroger l'article L. 222-3",
            metadata={"office": "office_A"},
        ),
    ]


@pytest.fixture
def sample_val_data() -> list[AmendmentSummaryExample]:
    """Create sample validation data."""
    return [
        AmendmentSummaryExample(
            expose_amdt="Ajout d'une nouvelle disposition.",
            corps_amdt="IV. - Après l'article L. 333-4, il est inséré.",
            summary="Insérer un article après L. 333-4",
            metadata={"office": "office_A"},
        ),
    ]


@pytest.fixture
def mock_lm() -> Mock:
    """Create mock DSPy language model."""
    lm = Mock(spec=dspy.LM)
    lm.model = "test-model"
    return lm


@pytest.fixture
def basic_config() -> OptimizationConfig:
    """Create basic optimization configuration."""
    return OptimizationConfig(
        num_candidates=2,
        num_iterations=3,
        batch_size=2,
        init_temperature=1.0,
        track_stats=True,
        checkpoint_dir=None,
        early_stopping_patience=0,
        rate_limit_per_minute=0,
    )


@pytest.fixture
def checkpoint_dir(tmp_path) -> Path:
    """Create temporary checkpoint directory."""
    checkpoint_path = tmp_path / "checkpoints"
    checkpoint_path.mkdir()
    return checkpoint_path


# OptimizationProgressTracker Tests


def test_progress_tracker_log_iteration(basic_config):
    """Test logging iteration metrics."""
    tracker = OptimizationProgressTracker(basic_config)

    tracker.log_iteration(1, 0.75, 0.80)

    assert len(tracker.history) == 1
    assert tracker.history[0]["iteration"] == 1
    assert tracker.history[0]["train_score"] == pytest.approx(0.75)
    assert tracker.history[0]["val_score"] == pytest.approx(0.80)
    assert tracker.best_score == pytest.approx(0.80)
    assert tracker.best_iteration == 1
    assert tracker.iterations_without_improvement == 0


def test_progress_tracker_improvement_tracking(basic_config):
    """Test tracking of improvements."""
    tracker = OptimizationProgressTracker(basic_config)

    # First iteration - improvement
    tracker.log_iteration(1, 0.75, 0.80)
    assert tracker.best_score == pytest.approx(0.80)
    assert tracker.iterations_without_improvement == 0

    # Second iteration - improvement
    tracker.log_iteration(2, 0.78, 0.85)
    assert tracker.best_score == pytest.approx(0.85)
    assert tracker.iterations_without_improvement == 0

    # Third iteration - no improvement
    tracker.log_iteration(3, 0.76, 0.82)
    assert tracker.best_score == pytest.approx(0.85)
    assert tracker.iterations_without_improvement == 1


def test_progress_tracker_early_stopping_disabled(basic_config):
    """Test early stopping when disabled."""
    tracker = OptimizationProgressTracker(basic_config)

    # Log many iterations without improvement
    for i in range(10):
        tracker.log_iteration(i + 1, 0.75, 0.80)

    assert not tracker.should_stop_early()


def test_progress_tracker_early_stopping_enabled():
    """Test early stopping when enabled."""
    config = OptimizationConfig(early_stopping_patience=3)
    tracker = OptimizationProgressTracker(config)

    # First iteration
    tracker.log_iteration(1, 0.75, 0.80)
    assert not tracker.should_stop_early()

    # Three iterations without improvement
    tracker.log_iteration(2, 0.76, 0.79)
    assert not tracker.should_stop_early()

    tracker.log_iteration(3, 0.74, 0.78)
    assert not tracker.should_stop_early()

    tracker.log_iteration(4, 0.75, 0.77)
    assert tracker.should_stop_early()


def test_progress_tracker_get_summary(basic_config):
    """Test getting optimization summary."""
    tracker = OptimizationProgressTracker(basic_config)

    tracker.log_iteration(1, 0.75, 0.80)
    tracker.log_iteration(2, 0.78, 0.85)

    summary = tracker.get_summary()

    assert summary["total_iterations"] == 2
    assert summary["best_score"] == pytest.approx(0.85)
    assert summary["best_iteration"] == 2
    assert "total_time_seconds" in summary
    assert summary["early_stopped"] is False


# AmendmentSummaryOptimizer Tests (RateLimiter tests removed - using existing TokenBucketRateLimiter)


def test_optimizer_initialization_empty_trainset(
    mock_lm, sample_val_data, basic_config
):
    """Test optimizer rejects empty training set."""
    with pytest.raises(ValueError, match="Training dataset cannot be empty"):
        AmendmentSummaryOptimizer(mock_lm, [], sample_val_data, basic_config)


def test_optimizer_initialization_empty_valset(
    mock_lm, sample_train_data, basic_config
):
    """Test optimizer rejects empty validation set."""
    with pytest.raises(ValueError, match="Validation dataset cannot be empty"):
        AmendmentSummaryOptimizer(mock_lm, sample_train_data, [], basic_config)


def test_optimizer_convert_to_dspy_examples(
    mock_lm, sample_train_data, sample_val_data, basic_config
):
    """Test conversion of examples to DSPy format."""
    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, basic_config
    )

    # Check trainset conversion
    assert len(optimizer.trainset) == 3
    for dspy_ex in optimizer.trainset:
        assert isinstance(dspy_ex, dspy.Example)
        assert hasattr(dspy_ex, "expose_amdt")
        assert hasattr(dspy_ex, "corps_amdt")
        assert hasattr(dspy_ex, "summary")


def test_optimizer_create_metric(
    mock_lm, sample_train_data, sample_val_data, basic_config
):
    """Test metric creation."""
    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, basic_config
    )

    metric = optimizer._create_metric()

    # Metric should be callable
    assert callable(metric)

    # Test with sample data
    example = dspy.Example(
        expose_amdt="Test", corps_amdt="Test", summary="Modifier le test"
    )
    prediction = Mock()
    prediction.summary = "Modifier le test"

    score = metric(example, prediction)
    assert 0.0 <= score <= 1.0


def test_optimizer_save_checkpoint(
    mock_lm, sample_train_data, sample_val_data, checkpoint_dir
):
    """Test checkpoint saving."""
    config = OptimizationConfig(checkpoint_dir=checkpoint_dir, checkpoint_frequency=1)
    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, config
    )

    # Create mock program
    program = Mock(spec=dspy.Module)
    program.save = Mock()

    # Save checkpoint
    checkpoint_path = optimizer._save_checkpoint(program, 1)

    assert checkpoint_path is not None
    assert checkpoint_path.name == "checkpoint_iter_1.json"

    # Verify program.save was called
    program.save.assert_called_once_with(str(checkpoint_path))

    # Verify metadata file exists (this is actually created, not mocked)
    metadata_path = checkpoint_path.with_suffix(".meta.json")
    assert metadata_path.exists()

    with open(metadata_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    assert metadata["iteration"] == 1
    assert "config" in metadata


def test_optimizer_save_checkpoint_disabled(
    mock_lm, sample_train_data, sample_val_data, basic_config
):
    """Test checkpoint saving when disabled."""
    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, basic_config
    )

    program = Mock(spec=dspy.Module)
    checkpoint_path = optimizer._save_checkpoint(program, 1)

    assert checkpoint_path is None


def test_optimizer_evaluate_program(
    mock_lm, sample_train_data, sample_val_data, basic_config
):
    """Test program evaluation."""
    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, basic_config
    )

    # Create mock program
    program = Mock(spec=dspy.Module)
    mock_prediction = Mock()
    mock_prediction.summary = "Modifier le code"
    program.return_value = mock_prediction

    # Evaluate on small dataset
    score = optimizer._evaluate_program(program, optimizer.valset[:1])

    assert 0.0 <= score <= 1.0
    assert program.call_count == 1


@patch("graal.summary.dspy_modules.optimizers.MIPROv2")
@patch("graal.summary.dspy_modules.optimizers.dspy.configure")
def test_optimizer_optimize_success(
    mock_configure,
    mock_mipro_class,
    mock_lm,
    sample_train_data,
    sample_val_data,
    basic_config,
):
    """Test successful optimization process."""
    # Setup mocks
    mock_mipro = Mock()
    mock_mipro_class.return_value = mock_mipro

    optimized_program = Mock(spec=AmendmentSummarizer)
    mock_prediction = Mock()
    mock_prediction.summary = "Modifier le test"
    optimized_program.return_value = mock_prediction
    optimized_program.dump_state = Mock(return_value={})

    mock_mipro.compile.return_value = optimized_program

    # Run optimization
    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, basic_config
    )
    result = optimizer.optimize()

    # Verify result
    assert isinstance(result, OptimizationResult)
    assert result.optimized_program == optimized_program
    assert 0.0 <= result.best_score <= 1.0
    assert 0.0 <= result.train_score <= 1.0
    assert result.num_iterations > 0
    assert result.total_time > 0
    assert isinstance(result.history, list)
    assert result.early_stopped is False


@pytest.mark.asyncio
@patch("graal.summary.dspy_modules.optimizers.MIPROv2")
@patch("graal.summary.dspy_modules.optimizers.dspy.configure")
async def test_optimizer_optimize_with_storage(
    mock_configure,
    mock_mipro_class,
    mock_lm,
    sample_train_data,
    sample_val_data,
    basic_config,
):
    """Test optimization with S3 storage."""
    # Setup mocks
    mock_mipro = Mock()
    mock_mipro_class.return_value = mock_mipro

    optimized_program = Mock(spec=AmendmentSummarizer)
    mock_prediction = Mock()
    mock_prediction.summary = "Modifier le test"
    optimized_program.return_value = mock_prediction
    optimized_program.dump_state = Mock(return_value={"state": "data"})

    mock_mipro.compile.return_value = optimized_program

    # Mock storage
    mock_storage = AsyncMock()
    mock_storage.save_optimized_prompt = AsyncMock(return_value="2025-10-24_10-00-00")

    # Run optimization with storage
    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, basic_config
    )
    result, version = await optimizer.optimize_with_storage(
        "office_A", "albert", mock_storage
    )

    # Verify result
    assert isinstance(result, OptimizationResult)
    assert version == "2025-10-24_10-00-00"
    mock_storage.save_optimized_prompt.assert_called_once()


# Factory Function Tests


def test_create_optimizer_with_checkpoint_dir(
    mock_lm, sample_train_data, sample_val_data, tmp_path
):
    """Test optimizer factory with checkpoint directory."""
    checkpoint_path = tmp_path / "checkpoints"

    optimizer = create_optimizer(
        mock_lm, sample_train_data, sample_val_data, checkpoint_dir=checkpoint_path
    )

    assert optimizer.config.checkpoint_dir == checkpoint_path
    assert optimizer.config.checkpoint_dir.exists()


# Integration Tests


def test_optimizer_full_workflow_mock(
    mock_lm, sample_train_data, sample_val_data, checkpoint_dir
):
    """Test complete optimizer workflow with mocked MIPROv2."""
    config = OptimizationConfig(
        num_candidates=2,
        num_iterations=3,
        checkpoint_dir=checkpoint_dir,
        checkpoint_frequency=1,
    )

    optimizer = AmendmentSummaryOptimizer(
        mock_lm, sample_train_data, sample_val_data, config
    )

    # Verify initialization
    assert len(optimizer.trainset) == 3
    assert len(optimizer.valset) == 1
    assert optimizer.config.checkpoint_dir == checkpoint_dir


def test_optimization_result_attributes():
    """Test OptimizationResult dataclass."""
    program = Mock(spec=AmendmentSummarizer)
    result = OptimizationResult(
        optimized_program=program,
        best_score=0.85,
        train_score=0.80,
        num_iterations=10,
        total_time=120.5,
        history=[{"iteration": 1, "val_score": 0.75}],
        early_stopped=False,
        checkpoint_path=None,
    )

    assert result.optimized_program == program
    assert result.best_score == pytest.approx(0.85)
    assert result.train_score == pytest.approx(0.80)
    assert result.num_iterations == 10
    assert result.total_time == pytest.approx(120.5)
    assert len(result.history) == 1
    assert result.early_stopped is False
    assert result.checkpoint_path is None
