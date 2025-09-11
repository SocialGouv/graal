import pytest

from graal.utils.text_utils import (
    digitize_small_french_numbers,
    normalize_text,
    remove_french_plurals,
    remove_sentences_starting_with,
    remove_small_roman_numerals,
    remove_stop_words,
)


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        (
            "This is a test with no roman numerals.",
            "This is a test with no roman numerals.",
        ),
        ("This is a test with I and II.", "This is a test with  and ."),
        ("This is a test with III, IV, and V.", "This is a test with , , and ."),
        ("This is a test with VI, VII, and VIII.", "This is a test with , , and ."),
        ("This is a test with IX, X, and XI.", "This is a test with , , and ."),
        ("This is a test with XIV, XV, and XVI.", "This is a test with , , and ."),
    ],
)
def test_remove_small_roman_numerals(input_text, expected_output):
    assert remove_small_roman_numerals(input_text) == expected_output


@pytest.mark.parametrize(
    "input_text, pattern, expected_output",
    [
        (
            "First line. Second line. Third line.",
            ["Second"],
            "First line. Third line.",
        ),
        (
            "First line\n\n\tSecond line.\nThird line.",
            ["Second"],
            "First line\n\n\tThird line.",
        ),
        (
            """
IV. – La perte de recettes pour l’État est co
V. – La perte de recettes pour les organismes. »
VI. – La charge pour l'État et les collectivités territoriales est compensée pour les organismes. »
            """,
            ["La perte de recettes", "La charge pour l'état"],
            "IV. –V. – »\nVI. – »",
        ),
    ],
)
def test_remove_sentences_starting_with(input_text, pattern, expected_output):
    assert (
        remove_sentences_starting_with(input_text, pattern).strip() == expected_output
    )


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        (
            "Ce texte contient des mots vides de sens.",
            "texte contient mots vides sens .",
        ),
        ("Les mots vides de sens sont supprimés.", "mots vides sens supprimés ."),
        (
            "Il y a beaucoup de mots inutiles dans ce texte.",
            "a beaucoup mots inutiles texte .",
        ),
        (
            "Les mots sans signification sont éliminés.",
            "mots sans signification éliminés .",
        ),
        ("une grande tour", "grande tour"),
    ],
)
def test_remove_stop_words(input_text, expected_output):
    assert remove_stop_words(input_text) == expected_output


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


@pytest.mark.parametrize(
    "input_text,expected_output",
    [
        (
            "  Àpostrophe's and dashes-are `removed`  ",
            "apostrophe and dashe are removed",
        ),
        ("non-breaking space", "non breaking space"),
        ("Éxámplè", "example"),
        ("!@#$%^&*()_+<>?", "%"),
        (
            ": « Les sociétés ont reçu la certification du référentiel Hébergeur de données de santé et des règles attachées à la norme ISO 27001. » »",
            "societe recu certification referentiel hebergeur donnee sante regle attachee a norme iso 27001",
        ),
        (
            "J'ai QUatre-vingt-dix-sept chameaux et quatre-vingt dix-huit pingouins",
            "97 chameau 98 pingouin",
        ),
        (
            "AVEC MES soixante seize baleines, je peux aller sur cinq continents",
            "76 baleine peu aller 5 continent",
        ),
        (
            # On vérifie que les gages sont bien retirés
            """
            III. – Un rapport d’évaluation est
            """,
            "rapport evaluation",
        ),
    ],
)
def test_normalize_text(input_text, expected_output):
    assert normalize_text(input_text) == expected_output


def test_normalize_text_with_special_characters():
    assert normalize_text(
        """Le 3° de l’article L. 4081‑2 du code de la santé publique est complété par une phrase ainsi rédigée : « Les sociétés ont reçu la certification du référentiel Hébergeur de données de santé et des règles attachées à la norme ISO 27001. » »"""
    ) == normalize_text(
        """Le 3° de l’article L. 4081‑2 du code de la santé publique est complété par une phrase ainsi rédigée : « Les sociétés ont reçu la certification du référentiel hébergeur de données de santé et des règles attachées à la norme ISO 27001. »"""
    )
