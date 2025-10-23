"""
Unit tests for DSPy signature definitions.
"""

from graal.summary.dspy_modules.signatures import AmendmentSummary


def test_amendment_summary_signature_exists():
    """Test that AmendmentSummary signature is defined."""
    assert AmendmentSummary is not None


def test_amendment_summary_has_input_fields():
    """Test that signature has required input fields."""
    # Check that signature has the expected input fields
    # DSPy signatures store fields in __annotations__
    assert "expose_amdt" in AmendmentSummary.__annotations__
    assert "corps_amdt" in AmendmentSummary.__annotations__


def test_amendment_summary_has_output_field():
    """Test that signature has required output field."""
    # Check that signature has the expected output field
    # DSPy signatures store fields in __annotations__
    assert "summary" in AmendmentSummary.__annotations__


def test_amendment_summary_docstring():
    """Test that signature has comprehensive documentation."""
    assert AmendmentSummary.__doc__ is not None
    assert "8-20 words" in AmendmentSummary.__doc__
    assert "infinitive verb" in AmendmentSummary.__doc__
