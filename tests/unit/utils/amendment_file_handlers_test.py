"""
Unit tests for amendment file handlers.

Tests the extract_date_from_amendment_json function to verify date extraction
from amendment JSON files.
"""

from datetime import datetime

import pytest

from graal.utils.amendment_file_handlers import extract_date_from_amendment_json


class TestExtractDateFromAmendmentJson:
    """Test suite for extract_date_from_amendment_json function."""

    def test_extract_date_valid_json_with_microseconds_returns_timestamp(self) -> None:
        """Test that valid JSON with microseconds returns correct Unix timestamp."""
        # Arrange
        json_content = """
        {
            "amendements": [
                {
                    "num": 837,
                    "avis": "Défavorable",
                    "date_derniere_modif": "2025-01-30 14:55:20.366848",
                    "mission_titre_court": ""
                }
            ]
        }
        """
        expected_dt = datetime(2025, 1, 30, 14, 55, 20, 366848)
        expected_timestamp = int(expected_dt.timestamp())

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result == expected_timestamp
        assert isinstance(result, int)

    def test_extract_date_valid_json_without_microseconds_returns_timestamp(
        self,
    ) -> None:
        """Test that valid JSON without microseconds returns correct Unix timestamp."""
        # Arrange
        json_content = """
        {
            "amendements": [
                {
                    "num": 100,
                    "date_derniere_modif": "2025-01-15 10:30:45"
                }
            ]
        }
        """
        expected_dt = datetime(2025, 1, 15, 10, 30, 45)
        expected_timestamp = int(expected_dt.timestamp())

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result == expected_timestamp

    def test_extract_date_multiple_amendments_returns_first_non_empty(self) -> None:
        """Test that first non-empty date is returned when multiple amendments exist."""
        # Arrange
        json_content = """
        {
            "amendements": [
                {
                    "num": 1,
                    "date_derniere_modif": ""
                },
                {
                    "num": 2,
                    "date_derniere_modif": "2025-02-01 12:00:00"
                },
                {
                    "num": 3,
                    "date_derniere_modif": "2025-02-02 13:00:00"
                }
            ]
        }
        """
        expected_dt = datetime(2025, 2, 1, 12, 0, 0)
        expected_timestamp = int(expected_dt.timestamp())

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result == expected_timestamp

    @pytest.mark.parametrize(
        "json_content",
        [
            # All dates empty strings
            '{"amendements": [{"date_derniere_modif": ""}, {"date_derniere_modif": ""}]}',
            # All dates missing
            '{"amendements": [{"num": 1}, {"num": 2}]}',
            # All dates None
            '{"amendements": [{"date_derniere_modif": null}, {"date_derniere_modif": null}]}',
            # Empty amendements array
            '{"amendements": []}',
            # Mix of empty, null, and missing
            '{"amendements": [{"date_derniere_modif": ""}, {"num": 2}, {"date_derniere_modif": null}]}',
        ],
    )
    def test_extract_date_no_valid_dates_returns_none(self, json_content: str) -> None:
        """Test that None is returned when no valid dates are found."""
        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result is None

    @pytest.mark.parametrize(
        "json_content",
        [
            # Invalid JSON syntax
            '{"amendements": [}',
            # Not valid JSON at all
            "this is not json",
            # Empty string
            "",
            # Incomplete JSON
            '{"amendements":',
        ],
    )
    def test_extract_date_malformed_json_returns_none(self, json_content: str) -> None:
        """Test that None is returned for malformed JSON."""
        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result is None

    @pytest.mark.parametrize(
        "json_content",
        [
            # Missing amendements key
            '{"data": [{"date_derniere_modif": "2025-01-30 14:55:20"}]}',
            # amendements is not an array
            '{"amendements": "not an array"}',
            # amendements is null
            '{"amendements": null}',
            # amendements is an object instead of array
            '{"amendements": {"date_derniere_modif": "2025-01-30 14:55:20"}}',
            # Empty JSON object
            "{}",
        ],
    )
    def test_extract_date_missing_amendements_array_returns_none(
        self, json_content: str
    ) -> None:
        """Test that None is returned when amendements array is missing or invalid."""
        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result is None

    @pytest.mark.parametrize(
        "invalid_date",
        [
            # Wrong date format
            "30-01-2025 14:55:20",
            # Invalid date values
            "2025-13-30 14:55:20",
            # Incomplete date
            "2025-01-30",
            # Random string
            "not a date",
            # ISO format (not supported)
            "2025-01-30T14:55:20Z",
        ],
    )
    def test_extract_date_invalid_date_format_continues_to_next(
        self, invalid_date: str
    ) -> None:
        """Test that invalid date formats are skipped and next amendment is checked."""
        # Arrange - first amendment has invalid date, second has valid date
        json_content = f"""
        {{
            "amendements": [
                {{"date_derniere_modif": "{invalid_date}"}},
                {{"date_derniere_modif": "2025-02-01 10:00:00"}}
            ]
        }}
        """
        expected_dt = datetime(2025, 2, 1, 10, 0, 0)
        expected_timestamp = int(expected_dt.timestamp())

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result == expected_timestamp

    def test_extract_date_all_invalid_dates_returns_none(self) -> None:
        """Test that None is returned when all date formats are invalid."""
        # Arrange
        json_content = """
        {
            "amendements": [
                {"date_derniere_modif": "invalid-date-1"},
                {"date_derniere_modif": "invalid-date-2"},
                {"date_derniere_modif": "not a date at all"}
            ]
        }
        """

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result is None

    def test_extract_date_amendment_not_dict_is_skipped(self) -> None:
        """Test that non-dict amendment entries are skipped."""
        # Arrange
        json_content = """
        {
            "amendements": [
                "not a dict",
                123,
                {"date_derniere_modif": "2025-02-01 15:30:00"}
            ]
        }
        """
        expected_dt = datetime(2025, 2, 1, 15, 30, 0)
        expected_timestamp = int(expected_dt.timestamp())

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result == expected_timestamp

    def test_extract_date_date_field_not_string_is_skipped(self) -> None:
        """Test that non-string date values are skipped."""
        # Arrange
        json_content = """
        {
            "amendements": [
                {"date_derniere_modif": 1234567890},
                {"date_derniere_modif": true},
                {"date_derniere_modif": "2025-02-01 16:00:00"}
            ]
        }
        """
        expected_dt = datetime(2025, 2, 1, 16, 0, 0)
        expected_timestamp = int(expected_dt.timestamp())

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result == expected_timestamp

    def test_extract_date_with_additional_fields_returns_timestamp(self) -> None:
        """Test that function works correctly with additional JSON fields."""
        # Arrange
        json_content = """
        {
            "metadata": {"version": "1.0"},
            "amendements": [
                {
                    "num": 837,
                    "avis": "Défavorable",
                    "date_derniere_modif": "2025-01-30 14:55:20.366848",
                    "mission_titre_court": "",
                    "auteur": "Député X",
                    "extra_field": "extra_value"
                }
            ],
            "other_data": "should be ignored"
        }
        """
        expected_dt = datetime(2025, 1, 30, 14, 55, 20, 366848)
        expected_timestamp = int(expected_dt.timestamp())

        # Act
        result = extract_date_from_amendment_json(json_content)

        # Assert
        assert result == expected_timestamp
