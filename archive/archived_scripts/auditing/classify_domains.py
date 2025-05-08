import json
import logging
from collections import defaultdict
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

MANIFEST_FILE = Path("manifest.json")
OUTPUT_FILE = Path("domains.json")

# Simple path-based classification rules
# Order matters, first match wins
DOMAIN_RULES = [
    (lambda p: p.startswith("src/features/"), "feature"),
    (lambda p: p.startswith("src/shared/"), "shared"),
    (
        lambda p: p.startswith("src/assets/")
        or p.split(".")[-1].lower()
        in [
            "png",
            "jpg",
            "jpeg",
            "gif",
            "svg",
            "css",
            "scss",
            "less",
            "woff",
            "woff2",
            "ttf",
            "eot",
        ],
        "asset",
    ),
    (lambda p: p.startswith("src/dreamos/"), "core_dreamos"),
    (lambda p: p.startswith("src/dreamscape/"), "app_dreamscape"),
    (lambda p: p.startswith("src/social/"), "app_social"),
    (lambda p: p.startswith("src/tools/"), "tooling"),
    (
        lambda p: p.startswith("src/tests/") or p.startswith("tests/"),
        "test",
    ),  # Added rule for tests
    (lambda p: p.startswith("src/"), "core_src_root"),  # Files directly in src
]
DEFAULT_DOMAIN = "unknown"


def classify_path(file_path_str: str) -> str:
    """Apply classification rules to a file path string."""
    # Normalize path separators
    normalized_path = file_path_str.replace("\\", "/").lower()

    # Strip potential D:\Dream.os prefix if present from manifest
    # Find 'src/' boundary
    src_index = normalized_path.find("src/")
    if src_index != -1:
        path_relative_to_project = normalized_path[src_index:]
    else:
        # Handle files potentially outside src if manifest includes them
        # Check common non-src paths
        if normalized_path.endswith(
            (".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".ini")
        ):
            return "docs_config"
        # Maybe check for test files outside src
        test_index = normalized_path.find("tests/")
        if test_index != -1:
            path_relative_to_project = normalized_path[test_index:]
            if path_relative_to_project.startswith("tests/"):
                return "test"

        path_relative_to_project = normalized_path  # Fallback if 'src/' not found

    for rule_func, domain in DOMAIN_RULES:
        if rule_func(path_relative_to_project):
            return domain
    return DEFAULT_DOMAIN


def main():
    logging.info(f"Reading file manifest: {MANIFEST_FILE}")
    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)
        if not isinstance(manifest_data, list):
            logging.error(
                f"Manifest file {MANIFEST_FILE} does not contain a JSON list."
            )
            return
    except FileNotFoundError:
        logging.error(f"Manifest file not found: {MANIFEST_FILE}")
        return
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {MANIFEST_FILE}: {e}")
        return
    except Exception as e:
        logging.error(f"Error reading manifest file {MANIFEST_FILE}: {e}")
        return

    logging.info(f"Classifying {len(manifest_data)} files by domain...")
    domain_mapping = defaultdict(list)
    classification_details = []

    for file_entry in manifest_data:
        if not isinstance(file_entry, dict) or "FullName" not in file_entry:
            logging.warning(f"Skipping invalid entry in manifest: {file_entry}")
            continue

        file_path = file_entry["FullName"]
        domain = classify_path(file_path)
        domain_mapping[domain].append(file_path)
        classification_details.append({"file": file_path, "domain": domain})

    # Prepare output structure matching Task 7 (grouping by domain)
    output_data = {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_source": str(MANIFEST_FILE),
        "classification_rules_description": "Path-based heuristics: features, shared, assets (ext/path), core_dreamos, app_dreamscape, app_social, tooling, core_src_root, test, docs_config, unknown",  # noqa: E501
        "domains": dict(domain_mapping),  # Convert defaultdict to dict for JSON
    }

    logging.info(f"Writing domain classification map to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2)
        logging.info("Domain classification complete.")
    except Exception as e:
        logging.error(f"Failed to write output file {OUTPUT_FILE}: {e}")


if __name__ == "__main__":
    from datetime import datetime, timezone  # Import locally for timestamp

    main()
