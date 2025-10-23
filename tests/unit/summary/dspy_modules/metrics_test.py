"""
Unit tests for DSPy evaluation metrics.

Tests the french_summary_metric function and its components:
- Semantic similarity calculation
- Length constraint validation
- Infinitive verb detection
- Combined score calculation
"""

from unittest.mock import MagicMock, patch

import dspy
import numpy as np
import pytest

from graal.summary.dspy_modules.metrics import (
    _check_infinitive_verb,
    _compute_length_score,
    _compute_semantic_similarity,
    french_summary_metric,
)


class TestComputeSemanticSimilarity:
    """Test semantic similarity computation using sentence-transformers."""

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_identical_summaries(self, mock_get_model):
        """Test that identical summaries have similarity score of 1.0."""
        # Mock the embedding model
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
        mock_get_model.return_value = mock_model

        predicted = "Modifier le code de la santé"
        reference = "Modifier le code de la santé"

        score = _compute_semantic_similarity(predicted, reference)

        assert score == 1.0
        mock_model.encode.assert_called_once()

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_similar_summaries(self, mock_get_model):
        """Test that semantically similar summaries have high score."""
        # Mock embeddings with high cosine similarity
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array(
            [
                [1.0, 0.1, 0.0],  # Predicted
                [0.9, 0.2, 0.1],  # Reference
            ]
        )
        mock_get_model.return_value = mock_model

        predicted = "Modifier le code de santé"
        reference = "Modifier le code de la santé publique"

        score = _compute_semantic_similarity(predicted, reference)

        assert 0.8 < score <= 1.0

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_different_summaries(self, mock_get_model):
        """Test that semantically different summaries have low score."""
        # Mock embeddings with low cosine similarity
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array(
            [
                [1.0, 0.0, 0.0],  # Predicted
                [0.0, 1.0, 0.0],  # Reference
            ]
        )
        mock_get_model.return_value = mock_model

        predicted = "Modifier le code fiscal"
        reference = "Supprimer la taxe d'habitation"

        score = _compute_semantic_similarity(predicted, reference)

        assert 0.0 <= score < 0.5

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_custom_embedding_model(self, mock_get_model):
        """Test that custom embedding model can be specified."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [1.0, 0.0]])
        mock_get_model.return_value = mock_model

        custom_model = "custom-model-name"
        _compute_semantic_similarity("test", "test", model_name=custom_model)

        mock_get_model.assert_called_once_with(custom_model)


class TestComputeLengthScore:
    """Test length constraint scoring for French summaries."""

    def test_perfect_length_8_words(self):
        """Test that 8 words (minimum) gets perfect score."""
        summary = "Modifier le code de la santé publique française"
        score = _compute_length_score(summary)
        assert score == 1.0

    def test_perfect_length_20_words(self):
        """Test that 20 words (maximum) gets perfect score."""
        summary = "Modifier le code de la santé publique française pour améliorer la prise en charge des patients dans les hôpitaux publics"
        assert len(summary.split()) == 20
        score = _compute_length_score(summary)
        assert score == 1.0

    def test_perfect_length_middle_range(self):
        """Test that 14 words (middle of range) gets perfect score."""
        summary = "Modifier le code de la santé publique pour améliorer la prise en charge hospitalière"
        assert len(summary.split()) == 14
        score = _compute_length_score(summary)
        assert score == 1.0

    def test_too_short_7_words(self):
        """Test that 7 words gets proportional penalty."""
        summary = "Modifier le code de la santé publique"
        assert len(summary.split()) == 7
        score = _compute_length_score(summary)
        assert score == pytest.approx(7.0 / 8.0, rel=0.01)

    def test_too_short_4_words(self):
        """Test that 4 words gets larger penalty."""
        summary = "Modifier le code fiscal"
        assert len(summary.split()) == 4
        score = _compute_length_score(summary)
        assert score == pytest.approx(4.0 / 8.0, rel=0.01)

    def test_too_short_1_word(self):
        """Test that 1 word gets very low score."""
        summary = "Modifier"
        score = _compute_length_score(summary)
        assert score == pytest.approx(1.0 / 8.0, rel=0.01)

    def test_too_long_25_words(self):
        """Test that 25 words gets proportional penalty."""
        summary = " ".join(["mot"] * 25)
        score = _compute_length_score(summary)
        assert score == pytest.approx(1.0 - (25 - 20) / 20.0, rel=0.01)

    def test_too_long_40_words(self):
        """Test that 40 words gets zero score."""
        summary = " ".join(["mot"] * 40)
        score = _compute_length_score(summary)
        assert score == 0.0

    def test_too_long_60_words(self):
        """Test that 60+ words stays at zero score."""
        summary = " ".join(["mot"] * 60)
        score = _compute_length_score(summary)
        assert score == 0.0

    def test_handles_extra_whitespace(self):
        """Test that extra whitespace is handled correctly."""
        summary = "  Modifier   le  code   de   la   santé   publique  "
        score = _compute_length_score(summary)
        # 7 words after splitting, slightly below minimum of 8
        assert score == pytest.approx(7.0 / 8.0, rel=0.01)

    def test_french_apostrophes(self):
        """Test that French apostrophes are counted correctly."""
        summary = "Modifier l'article du code de la santé publique"
        # Apostrophes don't split words, so l'article is one word
        assert len(summary.split()) == 8
        score = _compute_length_score(summary)
        assert score == 1.0


class TestCheckInfinitiveVerb:
    """Test French infinitive verb detection."""

    def test_common_er_verb(self):
        """Test common -er infinitive verbs."""
        assert _check_infinitive_verb("Modifier le code")
        assert _check_infinitive_verb("Supprimer la taxe")
        assert _check_infinitive_verb("Ajouter un article")
        assert _check_infinitive_verb("Créer une commission")

    def test_common_ir_verb(self):
        """Test common -ir infinitive verbs."""
        assert _check_infinitive_verb("Définir les modalités")
        assert _check_infinitive_verb("Établir un rapport")
        assert _check_infinitive_verb("Réunir les parties")

    def test_common_re_verb(self):
        """Test common -re infinitive verbs."""
        assert _check_infinitive_verb("Remettre un rapport")
        assert _check_infinitive_verb("Prendre en compte")
        assert _check_infinitive_verb("Étendre le dispositif")

    def test_common_oir_verb(self):
        """Test common -oir infinitive verbs."""
        assert _check_infinitive_verb("Recevoir les documents")
        assert _check_infinitive_verb("Prévoir une disposition")

    def test_not_infinitive(self):
        """Test that non-infinitive forms are rejected."""
        assert not _check_infinitive_verb("Le code de santé")
        assert not _check_infinitive_verb("Une modification importante")
        assert not _check_infinitive_verb("Modification du code")

    def test_past_participle(self):
        """Test that past participles (-é) are rejected."""
        assert not _check_infinitive_verb("Modifié le code")
        assert not _check_infinitive_verb("Supprimé la taxe")

    def test_conjugated_verb(self):
        """Test that conjugated verbs are rejected."""
        assert not _check_infinitive_verb("Modifie le code")
        assert not _check_infinitive_verb("Supprime la taxe")

    def test_case_insensitive(self):
        """Test that detection is case-insensitive."""
        assert _check_infinitive_verb("modifier le code")
        assert _check_infinitive_verb("MODIFIER le code")
        assert _check_infinitive_verb("Modifier le code")

    def test_with_punctuation(self):
        """Test that punctuation is handled correctly."""
        assert _check_infinitive_verb("Modifier.")
        assert _check_infinitive_verb("Supprimer,")
        assert _check_infinitive_verb("Ajouter:")

    def test_empty_summary(self):
        """Test that empty summary returns False."""
        assert not _check_infinitive_verb("")
        assert not _check_infinitive_verb("   ")

    def test_french_accents(self):
        """Test that French accents are handled correctly."""
        assert _check_infinitive_verb("Étendre le dispositif")
        assert _check_infinitive_verb("Créer une commission")
        assert _check_infinitive_verb("Établir un rapport")


class TestFrenchSummaryMetric:
    """Test the combined French summary metric."""

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_perfect_summary(self, mock_get_model):
        """Test that a perfect summary gets score close to 1.0."""
        # Mock perfect semantic similarity
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [1.0, 0.0]])
        mock_get_model.return_value = mock_model

        # Use 8-word summary (within valid range)
        example = dspy.Example(
            summary="Modifier le code de la santé publique française"
        ).with_inputs()
        prediction = dspy.Prediction(
            summary="Modifier le code de la santé publique française"
        )

        score = french_summary_metric(example, prediction)

        # Should be 1.0: 1.0 * 0.7 + 1.0 * 0.3 + 1.0 * 0.0 = 1.0
        assert score == pytest.approx(1.0, rel=0.01)

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_good_semantic_wrong_length(self, mock_get_model):
        """Test high semantic score but poor length score."""
        # Mock good semantic similarity
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.9, 0.1], [1.0, 0.0]])
        mock_get_model.return_value = mock_model

        example = dspy.Example(
            summary="Modifier le code de la santé publique"
        ).with_inputs()
        prediction = dspy.Prediction(summary="Modifier")  # Too short

        score = french_summary_metric(example, prediction)

        # Semantic (0.9) weighted by 0.7 = 0.63, length (1/8=0.125) weighted by 0.3 = 0.0375
        # Total ≈ 0.67
        assert 0.6 < score < 0.75

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_poor_semantic_good_length(self, mock_get_model):
        """Test low semantic score but good length score."""
        # Mock poor semantic similarity
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [0.0, 1.0]])
        mock_get_model.return_value = mock_model

        example = dspy.Example(
            summary="Modifier le code de la santé publique"
        ).with_inputs()
        prediction = dspy.Prediction(
            summary="Supprimer la taxe d'habitation pour tous les citoyens"
        )

        score = french_summary_metric(example, prediction)

        # Semantic (0.0) weighted by 0.7 = 0.0, length (1.0) weighted by 0.3 = 0.3
        # Total = 0.3
        assert 0.25 < score < 0.35

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_with_verb_bonus(self, mock_get_model):
        """Test that verb bonus increases score."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [1.0, 0.0]])
        mock_get_model.return_value = mock_model

        example = dspy.Example(
            summary="Modifier le code de la santé publique"
        ).with_inputs()
        prediction = dspy.Prediction(summary="Modifier le code de la santé publique")

        # With verb bonus weight
        score_with_bonus = french_summary_metric(example, prediction, verb_weight=0.1)

        # Without verb bonus
        score_without_bonus = french_summary_metric(
            example, prediction, verb_weight=0.0
        )

        assert score_with_bonus > score_without_bonus

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_custom_weights(self, mock_get_model):
        """Test that custom weights affect scoring."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.8, 0.2], [1.0, 0.0]])
        mock_get_model.return_value = mock_model

        example = dspy.Example(
            summary="Modifier le code de la santé publique"
        ).with_inputs()
        prediction = dspy.Prediction(summary="Modifier")  # Too short

        # Emphasize semantic
        score_semantic = french_summary_metric(
            example, prediction, semantic_weight=0.9, length_weight=0.1
        )

        # Emphasize length
        score_length = french_summary_metric(
            example, prediction, semantic_weight=0.1, length_weight=0.9
        )

        # Semantic score should be higher (good semantic, poor length)
        assert score_semantic > score_length

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_no_reference_summary(self, mock_get_model):
        """Test metric behavior when no reference summary available."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        example = dspy.Example().with_inputs()  # No reference
        prediction = dspy.Prediction(summary="Modifier le code de la santé publique")

        score = french_summary_metric(example, prediction)

        # Should only use length and verb, no semantic
        # Length = 1.0, verb = 1.0, combined with adjusted weights
        assert score > 0.0

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_custom_embedding_model(self, mock_get_model):
        """Test that custom embedding model can be specified."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [1.0, 0.0]])
        mock_get_model.return_value = mock_model

        example = dspy.Example(summary="test").with_inputs()
        prediction = dspy.Prediction(summary="test")

        custom_model = "custom-sentence-transformer"
        french_summary_metric(example, prediction, embedding_model=custom_model)

        mock_get_model.assert_called_with(custom_model)

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_score_bounds(self, mock_get_model):
        """Test that score is always between 0 and 1."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[1.0, 0.0], [0.0, 1.0]])
        mock_get_model.return_value = mock_model

        example = dspy.Example(summary="test").with_inputs()

        # Test various predictions
        predictions = [
            "Modifier",
            "Modifier le code de la santé publique",
            " ".join(["mot"] * 50),  # Very long
            "test non-infinitive",
        ]

        for pred_text in predictions:
            prediction = dspy.Prediction(summary=pred_text)
            score = french_summary_metric(example, prediction)
            assert 0.0 <= score <= 1.0, f"Score {score} out of bounds for: {pred_text}"

    @patch("graal.summary.dspy_modules.metrics._get_embedding_model")
    def test_real_french_examples(self, mock_get_model):
        """Test with realistic French legislative summaries."""

        # Mock embeddings based on similarity
        def mock_encode(texts):
            # Simulate realistic embeddings for similar summaries
            if "modifier" in texts[0].lower() and "modifier" in texts[1].lower():
                return np.array([[1.0, 0.1, 0.0], [0.9, 0.2, 0.1]])
            elif "remettre" in texts[0].lower() and "remettre" in texts[1].lower():
                return np.array([[1.0, 0.1, 0.0], [0.9, 0.2, 0.1]])
            else:
                return np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

        mock_model = MagicMock()
        mock_model.encode.side_effect = mock_encode
        mock_get_model.return_value = mock_model

        # Example 1: Good match
        example1 = dspy.Example(
            summary="Modifier le code de la sécurité sociale pour tous"
        ).with_inputs()
        prediction1 = dspy.Prediction(
            summary="Modifier le code de la sécurité sociale française"
        )
        score1 = french_summary_metric(example1, prediction1)
        assert score1 > 0.7

        # Example 2: Report type
        example2 = dspy.Example(
            summary="Remettre un rapport sur la mise en œuvre"
        ).with_inputs()
        prediction2 = dspy.Prediction(
            summary="Remettre un rapport sur la mise en œuvre de la loi"
        )
        score2 = french_summary_metric(example2, prediction2)
        assert score2 > 0.7
