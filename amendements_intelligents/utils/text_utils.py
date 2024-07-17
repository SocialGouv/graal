import html
import re

from bs4 import BeautifulSoup
from unidecode import unidecode


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
