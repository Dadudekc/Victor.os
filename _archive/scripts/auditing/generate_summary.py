import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Input Files
MANIFEST_FILE = Path("manifest.json")
IMPORT_GRAPH_FILE = Path("import-graph.json")
ORPHANED_FILE = Path("orphaned-files.json")
UNREFERENCED_ASSETS_FILE = Path("unreferenced-assets.json")
DOMAINS_FILE = Path("domains.json")

# Output File
OUTPUT_FILE = Path("summary.md")


def read_json_file(file_path: Path, description: str) -> dict | list | None:
    """Helper function to read and parse JSON audit files."""
    logging.info(f"Reading {description} from {file_path}...")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        logging.error(f"{description.capitalize()} file not found: {file_path}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {file_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error reading {description} file {file_path}: {e}")
        return None


def main():
    summary_lines = [
        f"# Project Audit Summary",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "This report summarizes the findings of the automated project structure audit.",
        "",
    ]

    # 1. Manifest Summary
    manifest_data = read_json_file(MANIFEST_FILE, "file manifest")
    total_files = len(manifest_data) if isinstance(manifest_data, list) else 0
    summary_lines.append("## 1. File Manifest")
    if manifest_data is not None:
        summary_lines.append(f"- Total files scanned in `src/`: {total_files}")
        # Could add more stats like total size, file type breakdown if needed later
    else:
        summary_lines.append(
            "- *Manifest file (`manifest.json`) not found or could not be read.*"
        )
    summary_lines.append("")

    # 2. Import Graph & Orphaned Files
    import_graph_data = read_json_file(IMPORT_GRAPH_FILE, "import graph")
    orphaned_data = read_json_file(ORPHANED_FILE, "orphaned files report")
    total_modules_in_graph = (
        len(import_graph_data) if isinstance(import_graph_data, dict) else 0
    )
    summary_lines.append("## 2. Module Imports & Orphaned Files")
    if import_graph_data is not None:
        summary_lines.append(
            f"- Total Python modules analyzed: {total_modules_in_graph}"
        )
    else:
        summary_lines.append(
            "- *Import graph file (`import-graph.json`) not found or could not be read.*"
        )

    if orphaned_data is not None and isinstance(orphaned_data, dict):
        count = orphaned_data.get("orphaned_files_count", 0)
        files = orphaned_data.get("orphaned_files", [])
        summary_lines.append(f"- Potentially orphaned Python modules found: {count}")
        if count > 0:
            summary_lines.append(
                "  - **Note:** Analysis based on AST parsing; requires manual verification."
            )
            summary_lines.append("  - **Files (first 10):**")
            for i, f in enumerate(files[:10]):
                summary_lines.append(f"    - `{f}`")
            if count > 10:
                summary_lines.append(
                    "    - ... (see `orphaned-files.json` for full list)"
                )
    else:
        summary_lines.append(
            "- *Orphaned files report (`orphaned-files.json`) not found or could not be read.*"
        )
    summary_lines.append("")

    # 3. Domain Classification
    domains_data = read_json_file(DOMAINS_FILE, "domain classification")
    summary_lines.append("## 3. Domain Classification")
    if (
        domains_data is not None
        and isinstance(domains_data, dict)
        and "domains" in domains_data
    ):
        domain_counts = {
            domain: len(files) for domain, files in domains_data["domains"].items()
        }
        summary_lines.append("- Files classified by domain based on path:")
        for domain, count in sorted(domain_counts.items()):
            summary_lines.append(f"  - `{domain}`: {count} files")
        summary_lines.append(f"  - (See `domains.json` for details)")
    else:
        summary_lines.append(
            "- *Domain classification file (`domains.json`) not found or could not be read.*"
        )
    summary_lines.append("")

    # 4. Asset Usage
    unreferenced_assets_data = read_json_file(
        UNREFERENCED_ASSETS_FILE, "unreferenced assets report"
    )
    summary_lines.append("## 4. Asset Usage")
    if unreferenced_assets_data is not None and isinstance(
        unreferenced_assets_data, dict
    ):
        count = unreferenced_assets_data.get("unreferenced_assets_count", 0)
        files = unreferenced_assets_data.get("unreferenced_assets", [])
        summary_lines.append(
            f"- Potentially unreferenced assets found (count=0 in usage scan): {count}"
        )
        if count > 0:
            summary_lines.append(
                "  - **Note:** Analysis based on simple filename presence in code; requires manual verification."
            )
            summary_lines.append("  - **Files:**")
            for f in files:
                summary_lines.append(f"    - `{f}`")
        else:
            summary_lines.append(
                "  - All identified assets had at least one potential reference found in the code scan."
            )
    else:
        summary_lines.append(
            "- *Unreferenced assets report (`unreferenced-assets.json`) not found or could not be read.*"
        )
    summary_lines.append("")

    # Write Summary
    logging.info(f"Writing audit summary to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(summary_lines))
        logging.info("Audit summary generation complete.")
    except Exception as e:
        logging.error(f"Failed to write output file {OUTPUT_FILE}: {e}")


if __name__ == "__main__":
    main()
