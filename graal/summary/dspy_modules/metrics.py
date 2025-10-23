"""
Evaluation metrics for summary quality.

This module implements metrics for evaluating amendment summaries:
- Semantic similarity to reference summaries using sentence-transformers
- Length constraints (8-20 words)
- French infinitive verb form detection (bonus)
"""

import re
from functools import lru_cache
from typing import Any

import dspy
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


@lru_cache(maxsize=1)
def _get_embedding_model(model_name: str) -> SentenceTransformer:
    """
    Load and cache the sentence transformer model.

    Args:
        model_name: Name of the sentence-transformers model to use

    Returns:
        Loaded SentenceTransformer model
    """
    return SentenceTransformer(model_name)


def _compute_semantic_similarity(
    predicted_summary: str,
    reference_summary: str,
    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> float:
    """
    Compute semantic similarity between predicted and reference summaries.

    Uses sentence-transformers to embed both summaries and computes cosine similarity.
    The default model is optimized for multilingual support including French.

    Args:
        predicted_summary: Generated summary text
        reference_summary: Reference summary text
        model_name: Name of the sentence-transformers model to use

    Returns:
        Cosine similarity score between 0 and 1
    """
    model = _get_embedding_model(model_name)

    # Generate embeddings for both summaries
    embeddings = model.encode([predicted_summary, reference_summary])

    # Compute cosine similarity
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]

    # Ensure score is in valid range [0, 1]
    return max(0.0, min(1.0, float(similarity)))


def _compute_length_score(summary: str) -> float:
    """
    Compute length constraint score for French summary.

    Summary must be 8-20 words long. This function uses proper French word
    tokenization, handling apostrophes and hyphens correctly.

    Args:
        summary: Summary text to evaluate

    Returns:
        Length score between 0 and 1:
        - 1.0 if word count is in range [8, 20]
        - Proportional penalty if too short (< 8 words)
        - Proportional penalty if too long (> 20 words)
    """
    # French word tokenization: split on whitespace and count tokens
    # This handles French apostrophes (l', d', qu') and hyphens correctly
    words = summary.strip().split()
    word_count = len(words)

    if 8 <= word_count <= 20:
        # Perfect length
        return 1.0
    elif word_count < 8:
        # Too short: proportional penalty
        return max(0.0, word_count / 8.0)
    else:
        # Too long: decreasing penalty up to 40 words, then 0
        return max(0.0, 1.0 - (word_count - 20) / 20.0)


def _check_infinitive_verb(summary: str) -> bool:
    """
    Check if summary starts with French infinitive verb.

    French infinitive verbs end in -er, -ir, -re, or -oir. This function
    checks if the first word matches this pattern.

    Common patterns in amendment summaries:
    - Modifier, Supprimer, Ajouter (most common)
    - Créer, Établir, Définir
    - Remettre (for reports)
    - Expérimenter (for experiments)

    Args:
        summary: Summary text to check

    Returns:
        True if summary starts with French infinitive verb, False otherwise
    """
    # Extract first word (may contain apostrophes or hyphens)
    words = summary.strip().split()
    if not words:
        return False

    first_word = words[0].lower().strip(".,;:!?")

    # Check for common French infinitive endings
    # -er, -ir, -re, -oir (standard French infinitive suffixes)
    infinitive_pattern = r"^[a-zàâäçéèêëïîôùûüÿæœ]+(er|ir|re|oir)$"

    return bool(re.match(infinitive_pattern, first_word))


def french_summary_metric(
    example: dspy.Example,
    prediction: Any,
    trace: Any = None,
    semantic_weight: float = 0.7,
    length_weight: float = 0.3,
    verb_weight: float = 0.0,
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
) -> float:
    """
    Evaluate French amendment summary quality using multiple metrics.

    This metric combines three components:
    1. Semantic similarity (70% by default): Measures how similar the generated
       summary is to the reference summary in meaning, using multilingual
       sentence embeddings optimized for French.
    2. Length constraint (30% by default): Enforces the 8-20 word requirement
       with proportional penalties for violations.
    3. Infinitive verb form (bonus only): Optional bonus for starting with a
       French infinitive verb as per style guidelines.

    The metric is designed for DSPy optimization and will be called many times,
    so embedding models are cached for efficiency.

    Args:
        example: DSPy example containing reference summary in 'summary' field
        prediction: DSPy prediction object with generated 'summary' attribute
        trace: DSPy trace object (optional, not used but required by DSPy signature)
        semantic_weight: Weight for semantic similarity component (0-1)
        length_weight: Weight for length constraint component (0-1)
        verb_weight: Weight for infinitive verb bonus (typically 0, just bonus)
        embedding_model: Name of sentence-transformers model for embeddings

    Returns:
        Combined quality score between 0 and 1, where:
        - 1.0 = perfect summary (semantically identical, correct length, proper verb)
        - 0.0 = completely poor summary

    Examples:
        >>> example = dspy.Example(summary="Modifier le code de la santé publique")
        >>> prediction = dspy.Prediction(summary="Modifier le code de santé")
        >>> score = french_summary_metric(example, prediction)
        >>> 0.8 < score < 1.0  # High score for good semantic match and length
        True

    Notes:
        - Optimized for French legislative summaries
        - Semantic similarity uses multilingual model supporting French
        - Length scoring uses proper French word tokenization
        - Verb detection uses French infinitive patterns
    """
    # Extract summaries
    predicted_summary = (
        prediction.summary if hasattr(prediction, "summary") else str(prediction)
    )
    reference_summary = example.summary if hasattr(example, "summary") else ""

    if not reference_summary:
        # If no reference summary available, only use length and verb constraints
        length_score = _compute_length_score(predicted_summary)
        verb_bonus = 1.0 if _check_infinitive_verb(predicted_summary) else 0.0

        # Adjust weights when no reference available
        adjusted_length_weight = semantic_weight + length_weight
        return (length_score * adjusted_length_weight) + (verb_bonus * verb_weight)

    # Compute individual metric components
    semantic_score = _compute_semantic_similarity(
        predicted_summary, reference_summary, model_name=embedding_model
    )
    length_score = _compute_length_score(predicted_summary)
    verb_bonus = 1.0 if _check_infinitive_verb(predicted_summary) else 0.0

    # Combine scores with weights
    combined_score = (
        (semantic_score * semantic_weight)
        + (length_score * length_weight)
        + (verb_bonus * verb_weight)
    )

    # Ensure final score is in valid range [0, 1]
    return max(0.0, min(1.0, combined_score))
