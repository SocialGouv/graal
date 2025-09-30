#!/usr/bin/env python3
"""
S3 Upload Script

This script uploads files or directories to an S3 bucket.
It supports uploading individual files, multiple files, or entire directories.

Usage:
    poetry run python s3_upload.py <path1> [path2 ...] --destination <bucket_folder>
    poetry run python s3_upload.py /path/to/directory --destination folder/in/bucket
    poetry run python s3_upload.py file1.txt file2.txt --destination documents/

    Add --dry-run to see what would be uploaded without actually uploading.

Environment variables required:
    S3_BUCKET_ACCESS_KEY: S3 access key
    S3_BUCKET_SECRET_KEY: S3 secret key
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

# S3 Configuration
S3_BUCKET_ENDPOINT = "https://s3.gra.io.cloud.ovh.net"
S3_BUCKET_NAME = "graal-dev-app"  # TODO: make this configurable for prod uploads
S3_BUCKET_REGION = "gra"


class S3Uploader:
    def __init__(self):
        """Initialize S3 client with credentials from environment variables."""
        self.access_key = os.getenv("S3_BUCKET_ACCESS_KEY")
        self.secret_key = os.getenv("S3_BUCKET_SECRET_KEY")

        if not self.access_key or not self.secret_key:
            raise ValueError(
                "Missing S3 credentials. Please set S3_BUCKET_ACCESS_KEY and S3_BUCKET_SECRET_KEY "
                "environment variables."
            )

        # Configure S3 client for OVH endpoint
        config = Config(region_name=S3_BUCKET_REGION, retries={"max_attempts": 3})

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=S3_BUCKET_ENDPOINT,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            config=config,
        )

        print(f"Initialized S3 client for bucket: {S3_BUCKET_NAME}")

    def upload_file(self, local_path: Path, s3_key: str) -> bool:
        """
        Upload a single file to S3.

        Args:
            local_path: Path to the local file
            s3_key: Key (path) for the file in S3

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"Uploading {local_path} -> s3://{S3_BUCKET_NAME}/{s3_key}")

            self.s3_client.upload_file(str(local_path), S3_BUCKET_NAME, s3_key)

            print(f"✓ Successfully uploaded {local_path.name}")
            return True

        except ClientError as e:
            print(f"✗ Failed to upload {local_path}: {e}")
            return False
        except FileNotFoundError:
            print(f"✗ File not found: {local_path}")
            return False

    def upload_directory(
        self, directory_path: Path, destination_prefix: str
    ) -> List[bool]:
        """
        Upload an entire directory to S3, preserving directory structure.

        Args:
            directory_path: Path to the local directory
            destination_prefix: S3 prefix (folder) for the uploaded files

        Returns:
            List[bool]: List of upload results for each file
        """
        if not directory_path.is_dir():
            print(f"✗ Not a directory: {directory_path}")
            return [False]

        results = []

        # Walk through all files in the directory
        for file_path in directory_path.rglob("*"):
            if file_path.is_file():
                # Calculate relative path to preserve directory structure
                relative_path = file_path.relative_to(directory_path)
                s3_key = f"{destination_prefix.rstrip('/')}/{relative_path}".replace(
                    "\\", "/"
                )

                result = self.upload_file(file_path, s3_key)
                results.append(result)

        return results

    def upload_paths(self, paths: List[str], destination: str) -> None:
        """
        Upload multiple paths (files or directories) to S3.

        Args:
            paths: List of file/directory paths to upload
            destination: S3 destination prefix
        """
        all_results = []

        # Ensure destination ends with / if it's meant to be a folder
        if destination and not destination.endswith("/"):
            destination += "/"

        for path_str in paths:
            path = Path(path_str).resolve()

            if not path.exists():
                print(f"✗ Path does not exist: {path}")
                all_results.append(False)
                continue

            if path.is_file():
                # Upload single file
                s3_key = f"{destination}{path.name}"
                result = self.upload_file(path, s3_key)
                all_results.append(result)

            elif path.is_dir():
                # Upload directory
                print(f"Uploading directory: {path}")
                results = self.upload_directory(path, f"{destination}{path.name}")
                all_results.extend(results)

            else:
                print(f"✗ Unknown path type: {path}")
                all_results.append(False)

        # Print summary
        successful = sum(all_results)
        total = len(all_results)
        print(f"\nUpload Summary: {successful}/{total} files uploaded successfully")

        if successful < total:
            sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Upload files or directories to S3 bucket",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "paths", nargs="+", help="Path(s) to files or directories to upload"
    )

    parser.add_argument(
        "--destination",
        "-d",
        required=True,
        help='Destination folder in S3 bucket (e.g., "documents/" or "uploads/2023/")',
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be uploaded without actually uploading",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN MODE - No files will actually be uploaded")
        print(f"Would upload to: s3://{S3_BUCKET_NAME}/{args.destination}")
        for path in args.paths:
            print(f"  - {path}")
        return

    try:
        uploader = S3Uploader()
        uploader.upload_paths(args.paths, args.destination)

    except ValueError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)
    except NoCredentialsError:
        print("✗ AWS credentials not found. Please check your environment variables.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
