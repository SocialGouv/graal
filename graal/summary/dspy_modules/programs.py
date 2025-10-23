"""
DSPy program implementations for amendment summarization.

This module contains DSPy modules (ChainOfThought, Predict, etc.) that use
the defined signatures to generate summaries.
"""

import dspy

from graal.summary.dspy_modules.signatures import AmendmentSummary


class AmendmentSummarizer(dspy.Module):
    """DSPy module for generating amendment summaries using Chain of Thought."""

    def __init__(self):
        """Initialize the amendment summarizer with ChainOfThought reasoning."""
        super().__init__()
        self.generate_summary = dspy.ChainOfThought(AmendmentSummary)

    def forward(self, expose_amdt: str, corps_amdt: str) -> dspy.Prediction:
        """Generate a summary for the given amendment.

        Args:
            expose_amdt: Explanatory statement of the amendment
            corps_amdt: Body text of the amendment

        Returns:
            DSPy Prediction object containing the generated summary
        """
        result = self.generate_summary(expose_amdt=expose_amdt, corps_amdt=corps_amdt)
        return result


class AmendmentSummarizerPredict(dspy.Module):
    """DSPy module for generating amendment summaries using direct Predict.

    This is a simpler alternative to ChainOfThought that may be faster
    but potentially less accurate for complex amendments.
    """

    def __init__(self):
        """Initialize the amendment summarizer with direct Predict."""
        super().__init__()
        self.generate_summary = dspy.Predict(AmendmentSummary)

    def forward(self, expose_amdt: str, corps_amdt: str) -> dspy.Prediction:
        """Generate a summary for the given amendment.

        Args:
            expose_amdt: Explanatory statement of the amendment
            corps_amdt: Body text of the amendment

        Returns:
            DSPy Prediction object containing the generated summary
        """
        result = self.generate_summary(expose_amdt=expose_amdt, corps_amdt=corps_amdt)
        return result
