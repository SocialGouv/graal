import pytest

from amendements_intelligents.utils.text_utils import (
    digitize_small_french_numbers,
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


@pytest.mark.parametrize(
    "input_phrase, expected_output",
    [
        ("zero", "0"),
        ("un", "1"),
        ("deux", "2"),
        ("trois", "3"),
        ("trois ans", "3 ans"),
        ("un deux trois", "1 2 3"),
        ("quatre cinq six", "4 5 6"),
        ("Un DEUX Trois", "1 2 3"),
        ("QUATRE cinq Six", "4 5 6"),
        ("Bonjour le monde", "Bonjour le monde"),
        ("12345", "12345"),
        ("dix sept", "17"),
        ("soixante seize", "76"),
        ("soixante dix sept", "77"),
        ("soixante dix huit", "78"),
        ("soixante dix neuf", "79"),
        ("quatre vingt", "80"),
        ("quatre vingt seize", "96"),
        ("quatre vingt dix sept", "97"),
        ("quatre vingt dix huit", "98"),
        ("quatre vingt dix neuf", "99"),
        (
            "Il y a dix sept oiseaux et quatre vingts poissons.",
            "Il y a 17 oiseaux et 80 poissons.",
        ),
        ("", ""),
        ("un.", "1."),
        ("Il y a un.", "Il y a 1."),
    ],
)
def test_replace_french_numbers(input_phrase, expected_output):
    assert digitize_small_french_numbers(input_phrase) == expected_output
