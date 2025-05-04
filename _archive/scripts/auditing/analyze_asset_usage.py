import json
import logging
import os
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

DOMAINS_FILE = Path("domains.json")
SRC_DIR = Path("../src")  # Relative path from audit/ to src/
OUTPUT_FILE = Path("assets-usage.json")
# Define file extensions considered as 'code' to scan FOR asset usage
# Might need refinement based on project specifics (JS/TS/CSS etc.)
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".scss",
    ".vue",
}
EXCLUDE_DIRS = {
    "__pycache__",
    "node_modules",
    ".git",
    ".vscode",
    ".idea",
}  # Exclude common large/binary dirs


def find_code_files(start_dir: Path) -> list[Path]:
    """Find all code files recursively based on extensions, excluding specified directories."""  # noqa: E501
    code_files = []
    for root, dirs, files in os.walk(start_dir):
        # Modify dirs in-place to exclude unwanted ones
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if Path(file).suffix.lower() in CODE_EXTENSIONS:
                code_files.append(Path(root) / file)
    return code_files


def get_asset_files(domains_path: Path) -> list[str]:
    """Extract asset file paths from the domains.json file."""
    try:
        with open(domains_path, "r", encoding="utf-8") as f:
            domains_data = json.load(f)
        if (
            isinstance(domains_data, dict)
            and "domains" in domains_data
            and "asset" in domains_data["domains"]
        ):
            # Return full paths as stored in the domains file
            return domains_data["domains"]["asset"]
        else:
            logging.warning(
                f"Could not find 'asset' domain or valid structure in {domains_path}"
            )
            return []
    except FileNotFoundError:
        logging.error(f"Domains file not found: {domains_path}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {domains_path}: {e}")
        return []
    except Exception as e:
        logging.error(f"Error reading domains file {domains_path}: {e}")
        return []


def main():
    logging.info(f"Reading asset list from {DOMAINS_FILE}...")
    asset_files = get_asset_files(DOMAINS_FILE)
    if not asset_files:
        logging.warning("No asset files found to analyze usage for. Exiting.")
        # Create empty output file for consistency?
        output_data = {
            "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "domains_source": str(DOMAINS_FILE),
            "code_scan_extensions": sorted(list(CODE_EXTENSIONS)),
            "asset_usage_count": 0,
            "asset_usage": {},
        }
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            logging.info(f"Wrote empty asset usage report to {OUTPUT_FILE}.")
        except Exception as e:
            logging.error(f"Failed to write empty output file {OUTPUT_FILE}: {e}")
        return

    logging.info(f"Found {len(asset_files)} asset files. Preparing for usage scan...")
    # Create a simple map from asset filename (or maybe filename + immediate parent dir) to full path  # noqa: E501
    # Use filename as the primary key for simple string search
    asset_filenames = {Path(p).name: p for p in asset_files}
    usage_counts = defaultdict(int)

    logging.info(f"Scanning code files in {SRC_DIR}...")
    code_files_to_scan = find_code_files(SRC_DIR)
    logging.info(f"Found {len(code_files_to_scan)} code files to scan.")

    scanned_count = 0
    log_interval = max(
        1, len(code_files_to_scan) // 10
    )  # Log progress roughly 10 times

    for code_file in code_files_to_scan:
        try:
            with open(code_file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Very basic heuristic: check if asset filename exists as a string
                # This will have false positives and negatives but is a starting point
                for asset_name, full_asset_path in asset_filenames.items():
                    # Use regex to find the asset name potentially surrounded by quotes or path chars  # noqa: E501
                    # Making this more robust is hard - e.g. variable assembly
                    # Let's just do a simple string search for the filename for now
                    if asset_name in content:
                        usage_counts[full_asset_path] += 1
                        # Maybe break after first match per file if only tracking *if* used?  # noqa: E501
                        # For now, count all occurrences.
        except Exception as e:
            logging.warning(f"Could not read or process code file {code_file}: {e}")

        scanned_count += 1
        if scanned_count % log_interval == 0:
            logging.info(
                f"Scanned {scanned_count}/{len(code_files_to_scan)} code files..."
            )

    logging.info("Code scan complete. Finalizing usage counts...")
    # Ensure all assets from the list are in the output, even if count is 0
    final_usage = {
        asset_path: usage_counts.get(asset_path, 0) for asset_path in asset_files
    }

    output_data = {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "domains_source": str(DOMAINS_FILE),
        "code_scan_extensions": sorted(list(CODE_EXTENSIONS)),
        "asset_usage_count": len(final_usage),
        "asset_usage": final_usage,  # Maps full asset path to usage count
    }

    logging.info(f"Writing asset usage report to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, sort_keys=True)
        logging.info("Asset usage analysis complete.")
    except Exception as e:
        logging.error(f"Failed to write output file {OUTPUT_FILE}: {e}")


if __name__ == "__main__":
    from datetime import datetime, timezone  # Import locally

    main()
