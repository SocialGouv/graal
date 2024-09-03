import argparse
import json
import sys

import tabulate


def main():
    required_coverage_per_file = {
        # "my_file": 70,
    }
    parser = argparse.ArgumentParser(description="Check coverage of JSON files")
    parser.add_argument(
        "file_path", nargs="?", default="coverage.json", help="Path to the JSON file"
    )
    parser.add_argument(
        "required_coverage", type=int, nargs="?", default=80, help="Required coverage"
    )
    args = parser.parse_args()

    try:
        # Open the JSON file
        with open(args.file_path, encoding="UTF-8") as file:
            data = json.load(file)
            errors = []
            files = data["files"]
            for file_name in files:
                # Process each file in the dictionary
                # Add your code here to perform operations on each file
                # For example, you can print the file name
                percent_covered = files[file_name]["summary"]["percent_covered"]
                required_coverage = args.required_coverage
                if file_name in required_coverage_per_file:
                    required_coverage = required_coverage_per_file[file_name]
                if percent_covered < required_coverage:
                    errors.append(
                        {
                            "file_name": file_name,
                            "percent_covered": percent_covered,
                            "required_coverage": required_coverage,
                        }
                    )
        if errors:
            table = []
            for error in errors:
                file_name = error["file_name"]
                required_coverage = error["required_coverage"]
                percent_covered = int(error["percent_covered"])
                coverage = f"{percent_covered} / {required_coverage}"
                table.append([file_name, coverage])

            headers = ["File Name", "Coverage"]
            print(tabulate.tabulate(table, headers))
            print("\033[1;31mErrors with code coverage\033[0m")
            sys.exit(1)
        else:
            print("\033[1;32mAll files meet the required coverage\033[0m")

    except FileNotFoundError:
        print(f"File '{args.file_path}' not found.")
        sys.exit(1)

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
