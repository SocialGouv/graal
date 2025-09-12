"""
This module serves as the main entry point for processing amendments related to
the French legislative process

Key functionalities include:
- Loading and basic preprocessing of amendment data
- Running features without cross-dependencies
- Coordinating preprocessing steps (like allotment) separately from features
- Ensuring each feature uses its own text normalization
- Saving the processed results to Excel and CSV formats
"""

import argparse
import logging
import logging.config
import time
from pathlib import Path
from typing import Any

import yaml

from graal.core.processing_pipeline import ProcessingPipeline

logging.config.fileConfig("logging.conf")


def load_config(config_path: str) -> dict[str, Any]:
    """
    Load configuration from a YAML file.

    Args:
        config_path: Path to the configuration file (.yaml or .yml)

    Returns:
        Configuration as a dictionary

    Raises:
        ValueError: If the file extension is not supported
    """
    file_extension = Path(config_path).suffix.lower()

    with open(config_path, "r", encoding="UTF-8") as file:
        if file_extension in [".yaml", ".yml"]:
            config = yaml.safe_load(file)
        else:
            raise ValueError(
                f"Unsupported configuration file format: {file_extension}. Only YAML (.yaml, .yml) is supported."
            )

    return config


def parse_arguments() -> dict[str, Any]:
    parser = argparse.ArgumentParser(
        description="Process amendments related to the French legislative process using features."
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to the configuration file (.yaml or .yml).",
    )
    args = parser.parse_args()
    return load_config(args.config)


if __name__ == "__main__":
    start_time = time.time()
    args = parse_arguments()
    pipeline = ProcessingPipeline()
    pipeline.run(args)
    end_time = time.time()
    logging.info(f"Total execution time: {end_time - start_time} seconds")
