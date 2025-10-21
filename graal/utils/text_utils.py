import html
import logging
import logging.config
import re
import unicodedata
from typing import Callable, Optional

import pandas as pd
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from unidecode import unidecode

logging.config.fileConfig("logging.conf")
FRENCH_IRREGULAR_PLURALS_OR_EXCEPTIONS = {
    "aux": "aux",
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


def digitize_small_french_numbers(text: Optional[str]) -> str:
    """
    Replace French number words < 100 with their corresponding digits in the given text.
    """
    if text is None:
        return ""

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


def remove_stop_words(text: Optional[str], language: str = "french") -> str:
    if text is None:
        return ""
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
    if word in FRENCH_IRREGULAR_PLURALS_OR_EXCEPTIONS:
        return FRENCH_IRREGULAR_PLURALS_OR_EXCEPTIONS[word]
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
    start_patterns = [unidecode(pattern) for pattern in start_patterns]
    sentences = [s for s in re.split(f"({delimiter_pattern})", text) if s]
    filtered_sentences = []
    skip_next = False

    for i in range(len(sentences)):
        if skip_next:
            skip_next = False
            continue

        sentence = sentences[i]
        sentence_unidecoded = unidecode(sentence)
        if any(
            sentence_unidecoded.strip().lower().startswith(pattern.strip().lower())
            for pattern in start_patterns
        ):
            skip_next = True  # Skip the delimiter
        else:
            filtered_sentences.append(sentence)

    return "".join(filtered_sentences)


def normalize_text(text: str) -> str:
    """
    Normalize the given text by removing accents, apostrophes, dashes, backticks,
    special characters, and extra whitespaces.
    """
    original_text = text
    logging.debug(f"[TEXT_NORMALIZATION] Original text: '{original_text}'")

    text = remove_small_roman_numerals(text)
    logging.debug(f"[TEXT_NORMALIZATION] After removing roman numerals: '{text}'")

    # Remove accents
    text = unidecode(text)
    text = text.strip().lower()
    logging.debug(f"[TEXT_NORMALIZATION] After unidecode and lowercase: '{text}'")

    # Replace apostrophes, backticks, underscores with spaces
    text = re.sub(r"['`'_]", " ", text)
    logging.debug(
        f"[TEXT_NORMALIZATION] After replacing apostrophes/backticks: '{text}'"
    )

    # Replace dashes with a space unless they are surrounded by numbers
    text = re.sub(r"(?<!\d)-(?!\d)", " ", text)
    logging.debug(f"[TEXT_NORMALIZATION] After replacing dashes: '{text}'")

    # Remove most special characters
    text = re.sub(r"[^a-zA-Z0-9\s\-%]", "", text)
    logging.debug(f"[TEXT_NORMALIZATION] After removing special characters: '{text}'")

    text = remove_stop_words(text)
    logging.debug(f"[TEXT_NORMALIZATION] After removing stop words: '{text}'")

    text = digitize_small_french_numbers(text)
    logging.debug(f"[TEXT_NORMALIZATION] After digitizing numbers: '{text}'")

    text = " ".join(remove_french_plurals(word) for word in text.split())
    logging.debug(f"[TEXT_NORMALIZATION] After removing plurals: '{text}'")

    # Remove extra whitespaces
    text = re.sub(r"\s+", " ", text)
    final_text = text.strip()
    logging.debug(f"[TEXT_NORMALIZATION] Final normalized text: '{final_text}'")

    if not final_text:
        logging.warning(
            f"[TEXT_NORMALIZATION] Text became empty after normalization! Original: '{original_text}'"
        )

    return final_text


def extract_plain_text_from_html(encoded_html: str) -> str:
    logging.debug(f"[HTML_EXTRACTION] Original HTML: '{encoded_html}'")

    # Decode HTML entities
    decoded_html = html.unescape(encoded_html)
    logging.debug(f"[HTML_EXTRACTION] After HTML unescape: '{decoded_html}'")

    # Parse HTML and extract text
    soup = BeautifulSoup(decoded_html, "html.parser")
    plain_text = soup.get_text()

    # Normalize Unicode to NFC form to ensure consistent representation
    # This handles cases where accented characters may be encoded as:
    # - Precomposed (NFC): single character like 'é' (U+00E9)
    # - Decomposed (NFD): base letter + combining mark like 'e' + U+0301
    plain_text = unicodedata.normalize("NFC", plain_text)
    logging.debug(f"[HTML_EXTRACTION] Final plain text: '{plain_text}'")

    return plain_text


def remove_gage_sentences(text: str) -> str:
    return remove_sentences_starting_with(
        text,
        start_patterns=[
            "la perte de recettes",
            "la charge pour l'état",
        ],
    )


def add_placeholders_to_empty_column(
    df: pd.DataFrame,
    column: str,
    placeholder_text: str | None = None,
    placeholder_generator: Callable[[int, pd.Series], str] | None = None,
) -> pd.DataFrame:
    """
    Add placeholder text to empty cells in a DataFrame column.

    Supports two modes:
    1. Static placeholder: Same text for all empty cells (use placeholder_text)
    2. Dynamic placeholder: Different text per row (use placeholder_generator)

    Args:
        df: DataFrame to process
        column: Column name to fill empty values in
        placeholder_text: Static text to use for all empty cells (mutually exclusive with placeholder_generator)
        placeholder_generator: Callable that takes (index, row) and returns placeholder text (mutually exclusive with placeholder_text)

    Returns:
        DataFrame with placeholders applied to empty cells in the specified column

    Raises:
        ValueError: If neither or both placeholder_text and placeholder_generator are provided
        ValueError: If column doesn't exist in DataFrame

    Examples:
        # Static placeholder
        df = add_placeholders_to_empty_column(df, "Corps amdt", placeholder_text="Corps d'amendement non renseigné")

        # Dynamic placeholder with index
        df = add_placeholders_to_empty_column(
            df,
            "Corps amdt",
            placeholder_generator=lambda idx, row: f"Placeholder for amendment {idx}"
        )
    """

    # Validate inputs
    if placeholder_text is None and placeholder_generator is None:
        raise ValueError(
            "Either placeholder_text or placeholder_generator must be provided"
        )
    if placeholder_text is not None and placeholder_generator is not None:
        raise ValueError(
            "Only one of placeholder_text or placeholder_generator can be provided"
        )
    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found in DataFrame")

    # Create mask for empty values (None, NaN, empty string, or whitespace-only)
    empty_mask = df[column].isna() | (df[column].astype(str).str.strip() == "")

    num_empty = empty_mask.sum()
    if num_empty == 0:
        return df

    logging.info(
        f"Applying placeholder text to {num_empty} empty cells in column '{column}'"
    )

    # Apply placeholders
    if placeholder_text is not None:
        # Static placeholder - use vectorized operation
        df.loc[empty_mask, column] = placeholder_text
    elif placeholder_generator is not None:
        # Dynamic placeholder - need to iterate over empty rows
        for index in df[empty_mask].index:
            row = df.loc[index]
            df.at[index, column] = placeholder_generator(index, row)

    return df
