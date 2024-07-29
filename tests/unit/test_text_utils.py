import pytest

from amendements_intelligents.utils.text_utils import (
    normalize_text,
    remove_french_plurals,
    remove_stop_words,
)


def test_normalize_text():
    assert (
        normalize_text("  Àpostrophe's-are `removed`  ") == "apostrophe s-are removed"
    )
    assert normalize_text("non-breaking space") == "non-breaking space"
    assert normalize_text("Éxámplè") == "example"
    assert normalize_text("!@#$%^&*()_+<>?") == ""
    assert (
        normalize_text(
            ": « Les sociétés ont reçu la certification du référentiel Hébergeur de données de santé et des règles attachées à la norme ISO 27001. » »"
        )
        == "les societes ont recu la certification du referentiel hebergeur de donnees de sante et des regles attachees a la norme iso 27001"
    )

    assert normalize_text(
        """Le 3° de l’article L. 4081‑2 du code de la santé publique est complété par une phrase ainsi rédigée : « Les sociétés ont reçu la certification du référentiel Hébergeur de données de santé et des règles attachées à la norme ISO 27001. » »"""
    ) == normalize_text(
        """Le 3° de l’article L. 4081‑2 du code de la santé publique est complété par une phrase ainsi rédigée : « Les sociétés ont reçu la certification du référentiel hébergeur de données de santé et des règles attachées à la norme ISO 27001. »"""
    )


def test_remove_stop_words():
    assert (
        remove_stop_words("Ce texte contient des mots vides de sens.")
        == "texte contient mots vides sens ."
    )
    assert (
        remove_stop_words("Les mots vides de sens sont supprimés.")
        == "mots vides sens supprimés ."
    )
    assert (
        remove_stop_words("Il y a beaucoup de mots inutiles dans ce texte.")
        == "a beaucoup mots inutiles texte ."
    )
    assert (
        remove_stop_words("Les mots sans signification sont éliminés.")
        == "mots sans signification éliminés ."
    )
    assert remove_stop_words("une grande tour") == "grande tour"


@pytest.mark.parametrize(
    "input_word, expected_output",
    [
        # Regular plurals
        ("chats", "chat"),
        ("chiens", "chien"),
        # Singular words that should remain unchanged
        ("chat", "chat"),
        ("chien", "chien"),
        # Plurals ending in 'x'
        ("bijoux", "bijou"),
        # Plurals ending in 'aux'
        ("chevaux", "cheval"),
        ("journaux", "journal"),
        ("travaux", "travail"),
        ("vitraux", "vitrail"),
        # Special cases
        ("yeux", "œil"),
        # Plurals ending in 'eaux'
        ("eaux", "eau"),
        ("niveaux", "niveau"),
        # Words ending in 'is' should remain unchanged
        ("anis", "anis"),
        ("bis", "bis"),
        # Words ending in 'us' should remain unchanged
        ("virus", "virus"),
        ("bus", "bus"),
        # Words ending in 'os' should remain unchanged
        ("tacos", "tacos"),
        ("gros", "gros"),
        # Words ending in 'as' should remain unchanged
        ("bras", "bras"),
        ("cas", "cas"),
    ],
)
def test_remove_plurals(input_word, expected_output):
    assert remove_french_plurals(input_word) == expected_output
