import html
import re

import nltk
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from unidecode import unidecode

FRENCH_IRREGULAR_PLURALS = {
    "travaux": "travail",
    "vitraux": "vitrail",
    "yeux": "œil",
    "chacals": "chacal",
}

# Define the decorator
def ensure_stopwords_downloaded(func):
    def wrapper(*args, **kwargs):
        try:
            stopwords.words("french")
        except LookupError:
            print("Downloading stopwords...")
            nltk.download("stopwords")
        return func(*args, **kwargs)

    return wrapper


@ensure_stopwords_downloaded
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
    if word.endswith("x") and word not in FRENCH_IRREGULAR_PLURALS:
        return word[:-1]
    return word


def normalize_text(text: str) -> str:
    """
    Normalize the given text by removing accents, apostrophes, dashes, backticks,
    special characters, and extra whitespaces.
    """
    text = unidecode(text)
    text = text.strip().lower()
    # Remove accents
    text = text.encode("ascii", "ignore").decode("utf-8")
    # Replace apostrophes, backticks and list dashes with spaces
    text = re.sub(r"['`’_]", " ", text)
    # text = re.sub(r"- ", "", text)
    # Remove special characters except for dashes and dots because they are important for articles
    text = re.sub(r"[^a-zA-Z0-9\s\-]", "", text)
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
