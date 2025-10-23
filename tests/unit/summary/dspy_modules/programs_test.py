"""
Unit tests for DSPy program implementations.
"""

from graal.summary.dspy_modules.programs import (
    AmendmentSummarizer,
    AmendmentSummarizerPredict,
)


def test_amendment_summarizer_exists():
    """Test that AmendmentSummarizer class is defined."""
    assert AmendmentSummarizer is not None


def test_amendment_summarizer_initialization():
    """Test that AmendmentSummarizer can be initialized."""
    summarizer = AmendmentSummarizer()
    assert summarizer is not None
    assert hasattr(summarizer, "generate_summary")


def test_amendment_summarizer_predict_exists():
    """Test that AmendmentSummarizerPredict class is defined."""
    assert AmendmentSummarizerPredict is not None


def test_amendment_summarizer_predict_initialization():
    """Test that AmendmentSummarizerPredict can be initialized."""
    summarizer = AmendmentSummarizerPredict()
    assert summarizer is not None
    assert hasattr(summarizer, "generate_summary")


def test_amendment_summarizer_has_forward_method():
    """Test that AmendmentSummarizer has forward method."""
    summarizer = AmendmentSummarizer()
    assert hasattr(summarizer, "forward")
    assert callable(summarizer.forward)


def test_amendment_summarizer_predict_has_forward_method():
    """Test that AmendmentSummarizerPredict has forward method."""
    summarizer = AmendmentSummarizerPredict()
    assert hasattr(summarizer, "forward")
    assert callable(summarizer.forward)
