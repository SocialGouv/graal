import html
import logging
import logging.config
import re
from typing import Optional

from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from unidecode import unidecode

from graal.custom_types import TxtContent

logging.config.fileConfig("logging.conf")
FRENCH_IRREGULAR_PLURALS = {
    "travaux": "travail",
    "vitraux": "vitrail",
    "yeux": "œil",
    "chacals": "chacal",
    "messieurs": "monsieur",
    "mesdames": "madame",
    "mesdemoiselles": "mademoiselle",
}

# We want this to work after dashes and accents have been removed so we don't write them here.
# Also, we don't really care about numbers above 100 when working with amendments.
FRENCH_NUMBER_MAPPING = {
    "zero": "0",
    "un": "1",
    "une": "1",
    "deux": "2",
    "trois": "3",
    "quatre": "4",
    "cinq": "5",
    "six": "6",
    "sept": "7",
    "huit": "8",
    "neuf": "9",
    "dix": "10",
    "onze": "11",
    "douze": "12",
    "treize": "13",
    "quatorze": "14",
    "quinze": "15",
    "seize": "16",
    "dix sept": "17",
    "dix huit": "18",
    "dix neuf": "19",
    "vingt": "20",
    "vingts": "20",
    "trente": "30",
    "quarante": "40",
    "cinquante": "50",
    "soixante": "60",
    "soixante dix": "70",
    "soixante seize": "76",
    "soixante dix sept": "77",
    "soixante dix huit": "78",
    "soixante dix neuf": "79",
    "quatre vingt": "80",
    "quatre vingts": "80",
    "quatre vingt dix": "90",
    "quatre vingt seize": "96",
    "quatre vingt dix sept": "97",
    "quatre vingt dix huit": "98",
    "quatre vingt dix neuf": "99",
}


def digitize_small_french_numbers(text):
    """
    Replace French number words < 100 with their corresponding digits in the given text.
    """
    pattern = re.compile(
        r"\b("
        + "|".join(
            re.escape(key)
            for key in sorted(FRENCH_NUMBER_MAPPING.keys(), key=len, reverse=True)
        )
        + r")\b",
        re.IGNORECASE,
    )

    # Replace the number words with corresponding digits
    def replace_match(match):
        return FRENCH_NUMBER_MAPPING[match.group(0).lower()]

    return pattern.sub(replace_match, text)


def remove_stop_words(text, language="french"):
    stop_words = set(stopwords.words(language))
    words = word_tokenize(text)
    filtered_text = [word for word in words if word.lower() not in stop_words]
    return " ".join(filtered_text)


def remove_french_plurals(word):
    """
    Dummy removal of the plural form of the given French word.
    This function will wrongfully remove x and s sometimes (like "nous allons" -> "nous allon")
    but it is not a problem for our use case.
    """
    if word in FRENCH_IRREGULAR_PLURALS:
        return FRENCH_IRREGULAR_PLURALS[word]
    if word.endswith("s") and not word.endswith(("is", "us", "os", "as")):
        return word[:-1]
    if word.endswith("aux") and not word.endswith("eaux"):
        return word[:-3] + "al"
    if word.endswith("x"):
        return word[:-1]
    return word


def remove_small_roman_numerals(text: str) -> str:
    text = re.sub(r"\b[IVX]{1,5}\b", "", text)
    return text


def remove_sentences_starting_with(
    text: str, start_patterns: list[str], delimiter_pattern: str = r"[\.\!\?\n\t–\-]+"
) -> str:
    """
    Remove sentences starting with any of the given patterns from the given text.

    Parameters:
    text (str): The input text from which sentences will be removed.
    patterns (list[str]): A list of patterns. Sentences starting with any of these patterns will be removed.
    delimiter_pattern (str): A regex pattern used to split the text into sentences. Default is r"(?:[\\.\\!\\?\\s]+)".

    Returns:
    str: The text with the specified sentences removed.
    """
    sentences = [s for s in re.split(f"({delimiter_pattern})", text) if s]
    filtered_sentences = []
    skip_next = False

    for i in range(len(sentences)):
        if skip_next:
            skip_next = False
            continue

        sentence = sentences[i]
        if any(
            sentence.strip().lower().startswith(pattern.strip().lower())
            for pattern in start_patterns
        ):
            skip_next = True  # Skip the delimiter
        else:
            filtered_sentences.append(sentence)

    return "".join(filtered_sentences)


def normalize_text(text: Optional[str]) -> str:
    """
    Normalize the given text by removing accents, apostrophes, dashes, backticks,
    special characters, and extra whitespaces.
    """
    if text is None:
        return ""
    text = remove_small_roman_numerals(text)

    # Remove accents
    text = unidecode(text)
    text = text.strip().lower()
    # Replace apostrophes, backticks, underscores with spaces
    text = re.sub(r"['`’_]", " ", text)
    # Replace dashes with a space unless they are surrounded by numbers
    text = re.sub(r"(?<!\d)-(?!\d)", " ", text)
    # Remove most special characters
    text = re.sub(r"[^a-zA-Z0-9\s\-%]", "", text)

    text = remove_stop_words(text)
    text = digitize_small_french_numbers(text)
    text = " ".join(remove_french_plurals(word) for word in text.split())

    # Remove extra whitespaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_plain_text_from_html(encoded_html: str) -> None:
    # Decode HTML entities
    decoded_html = html.unescape(encoded_html)

    # Parse HTML and extract text
    soup = BeautifulSoup(decoded_html, "html.parser")
    plain_text = soup.get_text()
    return plain_text


def remove_gage_sentences(text: str) -> str:
    return remove_sentences_starting_with(
        text,
        start_patterns=[
            unidecode("la perte de recettes"),
            unidecode("la charge pour l'état"),
        ],
    )


class AttributionTextNormalizer:
    @staticmethod
    def normalize_text(text: TxtContent) -> TxtContent:
        """Normalize text by stripping, converting to lowercase, and removing specific spaces."""
        text = remove_small_roman_numerals(text)
        text = unidecode(text.strip().lower())
        # Replace dashes with a space unless they are surrounded by numbers
        text = re.sub(r"(?<!\d)-(?!\d)", " ", text)
        # Replace various Unicode space characters with a regular space
        text = re.sub(
            r"[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000]",
            " ",
            text,
        )
        # Remove extra whitespaces
        text = re.sub(r"\s+", " ", text)

        return text


class SummaryTextNormalizer:
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        Pre-process the user text to safely integrate into an LLM prompt.
        """

        cleaned_text = unidecode(text)
        cleaned_text = re.sub(r"[’]", "'", cleaned_text)

        cleaned_text = cleaned_text.replace("\n", " ").replace("\r", "").lower()
        cleaned_text = re.sub(
            r"[\u00A0\u1680\u180E\u2000-\u200B\u202F\u205F\u3000]",
            " ",
            cleaned_text,
        )

        cleaned_text = re.sub(r"[^a-z0-9À-ÿ'.,!? \-«»\"]+", "", cleaned_text)

        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()

        return cleaned_text
