"""
Utility functions for robust JSON handling with different UTF-8 encodings.
"""

import asyncio
import json
import logging
import logging.config
from typing import Any, Union

logging.config.fileConfig("logging.conf")


def load_json(content: Union[bytes, str], filename: str = "unknown") -> Any:
    """
    Robustly load JSON content handling different UTF-8 encodings.

    This function handles:
    - UTF-8 with BOM (Byte Order Mark)
    - Regular UTF-8 encoding
    - French characters and other Unicode content

    Args:
        content: Raw bytes or string content to parse as JSON
        filename: Filename for logging purposes

    Returns:
        Parsed JSON data

    Raises:
        ValueError: If content cannot be decoded or parsed as JSON
    """
    logging.debug(f"[JSON_UTILS] Loading JSON content for file: {filename}")

    # If content is already a string, try to parse directly
    if isinstance(content, str):
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logging.error(f"[JSON_UTILS] JSON parsing failed for {filename}: {str(e)}")
            raise ValueError(f"Invalid JSON content: {str(e)}") from e

    # Handle bytes content with different encoding strategies
    if isinstance(content, bytes):
        # Strategy 1: Try utf-8-sig first (handles BOM and regular UTF-8)
        # This is optimal for French content which often uses UTF-8 with BOM
        try:
            decoded_content = content.decode("utf-8-sig")
            logging.debug(
                f"[JSON_UTILS] Successfully decoded {filename} using utf-8-sig"
            )

            # Remove any remaining BOM characters that might have been left after decoding
            # This can happen if the content was double-encoded or manually prefixed with BOM
            if decoded_content.startswith("\ufeff"):
                decoded_content = decoded_content[1:]
                logging.debug(
                    f"[JSON_UTILS] Removed remaining BOM character from {filename}"
                )

            return json.loads(decoded_content)
        except UnicodeDecodeError:
            logging.debug(
                f"[JSON_UTILS] utf-8-sig decoding failed for {filename}, trying utf-8"
            )
        except json.JSONDecodeError as e:
            logging.error(
                f"[JSON_UTILS] JSON parsing failed for {filename} (utf-8-sig): {str(e)}"
            )
            raise ValueError(f"Invalid JSON content: {str(e)}") from e

        # Strategy 2: Fallback to regular utf-8
        try:
            decoded_content = content.decode("utf-8")
            logging.debug(f"[JSON_UTILS] Successfully decoded {filename} using utf-8")

            # Remove BOM if present (in case it wasn't handled by utf-8-sig)
            if decoded_content.startswith("\ufeff"):
                decoded_content = decoded_content[1:]
                logging.debug(f"[JSON_UTILS] Removed BOM character from {filename}")

            return json.loads(decoded_content)
        except UnicodeDecodeError as e:
            logging.error(
                f"[JSON_UTILS] UTF-8 decoding failed for {filename}: {str(e)}"
            )
            raise ValueError(f"Unable to decode file content as UTF-8: {str(e)}") from e
        except json.JSONDecodeError as e:
            logging.error(
                f"[JSON_UTILS] JSON parsing failed for {filename} (utf-8): {str(e)}"
            )
            raise ValueError(f"Invalid JSON content: {str(e)}") from e

    # Should not reach here with proper typing, but handle gracefully
    raise ValueError(f"Unsupported content type: {type(content)}")


async def load_json_from_file(file_path: str) -> Any:
    """
    Load JSON from a file path with robust encoding handling (async).

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON data

    Raises:
        ValueError: If file cannot be read or parsed as JSON
        FileNotFoundError: If file does not exist
    """

    def _load_sync() -> Any:
        logging.debug(f"[JSON_UTILS] Loading JSON from file: {file_path}")

        try:
            # Try utf-8-sig first (optimal for French content with potential BOM)
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
                logging.debug(
                    f"[JSON_UTILS] Successfully read {file_path} using utf-8-sig"
                )
                return json.loads(content)
        except UnicodeDecodeError:
            logging.debug(
                f"[JSON_UTILS] utf-8-sig reading failed for {file_path}, trying utf-8"
            )
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    logging.debug(
                        f"[JSON_UTILS] Successfully read {file_path} using utf-8"
                    )
                    return json.loads(content)
            except UnicodeDecodeError as e:
                logging.error(
                    f"[JSON_UTILS] UTF-8 reading failed for {file_path}: {str(e)}"
                )
                raise ValueError(f"Unable to read file as UTF-8: {str(e)}") from e
        except json.JSONDecodeError as e:
            logging.error(f"[JSON_UTILS] JSON parsing failed for {file_path}: {str(e)}")
            raise ValueError(f"Invalid JSON file: {str(e)}") from e
        except FileNotFoundError:
            logging.error(f"[JSON_UTILS] File not found: {file_path}")
            raise

    return await asyncio.to_thread(_load_sync)
