"""
Unit tests for ConfigPreprocessor.
"""

import os
import tempfile
import unittest
from unittest.mock import patch

from graal.utils.config.config_preprocessor import ConfigPreprocessor


class TestConfigPreprocessor(unittest.TestCase):
    """Test cases for ConfigPreprocessor."""

    def setUp(self):
        """Set up test fixtures."""
        self.preprocessor = ConfigPreprocessor(validate_paths=False)

    def test_simple_environment_variable_substitution(self):
        """Test basic environment variable substitution."""
        config = {
            "paths": {
                "data_folder": "${DATA_FOLDER}/input",
                "output_folder": "${DATA_FOLDER}/output",
            }
        }

        with patch.dict(os.environ, {"DATA_FOLDER": "/tmp/test_data"}):  # noqa: S108
            result = self.preprocessor.preprocess_config(config)

        expected = {
            "paths": {
                "data_folder": "/tmp/test_data/input",  # noqa: S108
                "output_folder": "/tmp/test_data/output",  # noqa: S108
            }
        }

        self.assertEqual(result, expected)

    def test_nested_config_substitution(self):
        """Test environment variable substitution in nested configurations."""
        config = {
            "similarity_search": {
                "enabled": True,
                "similarity_db_file": "${DATA_FOLDER}/preprocessed/db.pkl",
                "thresholds": {"expose": 0.4, "corps": 0.9},
            },
            "output": {"file_prefix_template": "${DATA_FOLDER}/results_%Y-%m-%d"},
        }

        with patch.dict(os.environ, {"DATA_FOLDER": "/home/user/graal_data"}):
            result = self.preprocessor.preprocess_config(config)

        expected = {
            "similarity_search": {
                "enabled": True,
                "similarity_db_file": "/home/user/graal_data/preprocessed/db.pkl",
                "thresholds": {"expose": 0.4, "corps": 0.9},
            },
            "output": {
                "file_prefix_template": "/home/user/graal_data/results_%Y-%m-%d"
            },
        }

        self.assertEqual(result, expected)

    def test_list_substitution(self):
        """Test environment variable substitution in lists."""
        config = {
            "input_files": [
                {"path": "${DATA_FOLDER}/input1.json", "project": "PLF"},
                {"path": "${DATA_FOLDER}/input2.json", "project": "PLFSS"},
            ]
        }

        with patch.dict(os.environ, {"DATA_FOLDER": "/data"}):
            result = self.preprocessor.preprocess_config(config)

        expected = {
            "input_files": [
                {"path": "/data/input1.json", "project": "PLF"},
                {"path": "/data/input2.json", "project": "PLFSS"},
            ]
        }

        self.assertEqual(result, expected)

    def test_missing_environment_variable(self):
        """Test that missing environment variables raise ValueError."""
        config = {"paths": {"data_folder": "${MISSING_VAR}/input"}}

        # Ensure the environment variable doesn't exist
        if "MISSING_VAR" in os.environ:
            del os.environ["MISSING_VAR"]

        with self.assertRaises(ValueError) as context:
            self.preprocessor.preprocess_config(config)

        self.assertIn("MISSING_VAR", str(context.exception))
        self.assertIn("is required but not set", str(context.exception))

    def test_multiple_variables_in_single_string(self):
        """Test substitution of multiple variables in a single string."""
        config = {"path": "${BASE_DIR}/${PROJECT_NAME}/data"}

        with patch.dict(
            os.environ, {"BASE_DIR": "/home/user", "PROJECT_NAME": "graal"}
        ):
            result = self.preprocessor.preprocess_config(config)

        expected = {"path": "/home/user/graal/data"}

        self.assertEqual(result, expected)

    def test_no_substitution_needed(self):
        """Test that configs without variables are unchanged."""
        config = {
            "similarity_search": {
                "enabled": True,
                "thresholds": {"expose": 0.4, "corps": 0.9},
                "should_overwrite": True,
            },
            "processing_options": {"placeholder_amdt_body": False},
        }

        result = self.preprocessor.preprocess_config(config)
        self.assertEqual(result, config)

    def test_deep_copy_behavior(self):
        """Test that the original config is not modified."""
        original_config = {"paths": {"data_folder": "${DATA_FOLDER}/input"}}

        with patch.dict(os.environ, {"DATA_FOLDER": "/tmp/test"}):  # noqa: S108
            result = self.preprocessor.preprocess_config(original_config)

        # Original should be unchanged
        self.assertEqual(
            original_config["paths"]["data_folder"], "${DATA_FOLDER}/input"
        )
        # Result should be processed
        self.assertEqual(result["paths"]["data_folder"], "/tmp/test/input")  # noqa: S108

    def test_path_validation_disabled(self):
        """Test that path validation can be disabled."""
        config = {"paths": {"nonexistent_file": "${DATA_FOLDER}/nonexistent.txt"}}

        preprocessor = ConfigPreprocessor(validate_paths=False)

        with patch.dict(os.environ, {"DATA_FOLDER": "/tmp"}):  # noqa: S108
            # Should not raise an exception even if path doesn't exist
            result = preprocessor.preprocess_config(config)

        self.assertEqual(result["paths"]["nonexistent_file"], "/tmp/nonexistent.txt")  # noqa: S108

    def test_path_validation_with_existing_file(self):
        """Test path validation with an existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            config = {"paths": {"existing_file": temp_path}}

            preprocessor = ConfigPreprocessor(validate_paths=True)
            result = preprocessor.preprocess_config(config)

            self.assertEqual(result["paths"]["existing_file"], temp_path)
        finally:
            os.unlink(temp_path)

    def test_template_path_skipped_validation(self):
        """Test that template paths (with %) are skipped during validation."""
        config = {"output": {"file_prefix_template": "${DATA_FOLDER}/results_%Y-%m-%d"}}

        preprocessor = ConfigPreprocessor(validate_paths=True)

        with patch.dict(os.environ, {"DATA_FOLDER": "/tmp"}):  # noqa: S108
            # Should not raise an exception for template paths
            result = preprocessor.preprocess_config(config)

        self.assertEqual(
            result["output"]["file_prefix_template"],
            "/tmp/results_%Y-%m-%d",  # noqa: S108
        )

    def test_is_file_path_detection(self):
        """Test the file path detection heuristic."""
        preprocessor = ConfigPreprocessor()

        # Should be detected as paths
        self.assertTrue(preprocessor._is_file_path("/home/user/file.txt"))
        self.assertTrue(preprocessor._is_file_path("./relative/path.json"))
        self.assertTrue(preprocessor._is_file_path("../parent/file.pkl"))
        self.assertTrue(preprocessor._is_file_path("data/file.xlsx"))

        # Should not be detected as paths
        self.assertFalse(preprocessor._is_file_path("simple_string"))
        self.assertFalse(preprocessor._is_file_path("enabled"))
        self.assertFalse(preprocessor._is_file_path("0.4"))
        self.assertFalse(preprocessor._is_file_path(""))


if __name__ == "__main__":
    unittest.main()
