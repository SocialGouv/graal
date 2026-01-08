"""
Tests for robust JSON loading utilities.
"""

import json
import tempfile
from pathlib import Path

import pytest

from graal.utils.json_utils import load_json, load_json_from_file


class TestJsonUtils:
    """Test cases for JSON utilities with different encodings."""

    def test_load_json_with_utf8_bom(self):
        """Test loading JSON content with UTF-8 BOM."""
        # Create JSON content with UTF-8 BOM
        json_data = {"amendements": [{"num": "1", "objet": "Test français éàç"}]}
        json_string = json.dumps(json_data, ensure_ascii=False)

        # Add UTF-8 BOM to the content
        bom_content = "\ufeff" + json_string
        byte_content = bom_content.encode("utf-8-sig")

        # Test loading with BOM
        result = load_json(byte_content, "test_bom.json")

        assert result == json_data
        assert result["amendements"][0]["objet"] == "Test français éàç"

    def test_load_json_with_regular_utf8(self):
        """Test loading JSON content with regular UTF-8 (no BOM)."""
        json_data = {"amendements": [{"num": "2", "objet": "Test français éàç"}]}
        json_string = json.dumps(json_data, ensure_ascii=False)
        byte_content = json_string.encode("utf-8")

        # Test loading without BOM
        result = load_json(byte_content, "test_no_bom.json")

        assert result == json_data
        assert result["amendements"][0]["objet"] == "Test français éàç"

    def test_load_json_with_string_input(self):
        """Test loading JSON content from string input."""
        json_data = {"amendements": [{"num": "3", "objet": "Test français éàç"}]}
        json_string = json.dumps(json_data, ensure_ascii=False)

        result = load_json(json_string, "test_string.json")

        assert result == json_data
        assert result["amendements"][0]["objet"] == "Test français éàç"

    def test_load_json_invalid_json(self):
        """Test error handling for invalid JSON."""
        invalid_content = b"{ invalid json content"

        with pytest.raises(ValueError, match="Invalid JSON content"):
            load_json(invalid_content, "invalid.json")

    def test_load_json_invalid_encoding(self):
        """Test error handling for invalid encoding."""
        # Create content that's not valid UTF-8
        invalid_content = b"\xff\xfe\x00\x00invalid"

        with pytest.raises(ValueError, match="Unable to decode file content as UTF-8"):
            load_json(invalid_content, "invalid_encoding.json")

    @pytest.mark.asyncio
    async def test_load_json_from_file_with_bom(self):
        """Test loading JSON from file with UTF-8 BOM."""
        json_data = {"amendements": [{"num": "4", "objet": "Test français éàç"}]}

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", suffix=".json", delete=False
        ) as f:
            json.dump(json_data, f, ensure_ascii=False)
            temp_path = f.name

        try:
            result = await load_json_from_file(temp_path)
            assert result == json_data
            assert result["amendements"][0]["objet"] == "Test français éàç"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_load_json_from_file_without_bom(self):
        """Test loading JSON from file without BOM."""
        json_data = {"amendements": [{"num": "5", "objet": "Test français éàç"}]}

        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        ) as f:
            json.dump(json_data, f, ensure_ascii=False)
            temp_path = f.name

        try:
            result = await load_json_from_file(temp_path)
            assert result == json_data
            assert result["amendements"][0]["objet"] == "Test français éàç"
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_load_json_from_file_not_found(self):
        """Test error handling for file not found."""
        with pytest.raises(FileNotFoundError):
            await load_json_from_file("nonexistent_file.json")

    @pytest.mark.asyncio
    async def test_load_json_from_file_invalid_json(self):
        """Test error handling for invalid JSON file."""
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".json", delete=False
        ) as f:
            f.write("{ invalid json content")
            temp_path = f.name

        try:
            with pytest.raises(ValueError, match="Invalid JSON file"):
                await load_json_from_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_french_characters_preservation(self):
        """Test that French characters are properly preserved through the encoding process."""
        french_text = "Amendement rédactionnel avec caractères spéciaux: éàçùî"
        json_data = {
            "amendements": [
                {
                    "num": "6",
                    "objet": french_text,
                    "expose": "Exposé avec accents: àéèêëïîôöùûüÿç",
                    "corps": "Corps d'amendement français",
                }
            ]
        }

        # Test with BOM
        json_string = json.dumps(json_data, ensure_ascii=False)
        bom_content = "\ufeff" + json_string
        byte_content = bom_content.encode("utf-8-sig")

        result = load_json(byte_content, "test_french.json")

        assert result["amendements"][0]["objet"] == french_text
        assert "àéèêëïîôöùûüÿç" in result["amendements"][0]["expose"]
        assert "français" in result["amendements"][0]["corps"]
