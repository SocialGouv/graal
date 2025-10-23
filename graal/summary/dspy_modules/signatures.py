"""
DSPy signature definitions for amendment summarization.

This module defines the input/output structure for DSPy-based summary generation.
"""

import dspy


class AmendmentSummary(dspy.Signature):
    """Generate concise French summary for legislative amendment.

    The summary must:
    - Be 8-20 words long
    - Start with an infinitive verb in French
    - Be politically neutral
    - Include essential information (actors, beneficiaries, locations, rates)
    - Use acronyms without explaining them
    - Avoid adjectives and justifications

    Special cases:
    - Reports: Start with "Remettre un rapport"
    - Experiments: Start with "Expérimenter"
    """

    expose_amdt: str = dspy.InputField(
        desc="Exposé de l'amendement (explanatory statement explaining the amendment's purpose)"
    )
    corps_amdt: str = dspy.InputField(
        desc="Corps de l'amendement (body of the amendment containing the actual legal text modifications)"
    )
    summary: str = dspy.OutputField(
        desc="Résumé en français (8-20 mots, commencer par un verbe à l'infinitif, neutre politiquement)"
    )
