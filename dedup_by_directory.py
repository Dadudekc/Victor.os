import argparse
from pathlib import Path
import deduplication_scanner as ds


def scan_directory(dir_path: Path):
    """Run deduplication scan for a single directory."""
    output_dir = Path("runtime/reports/by_directory") / dir_path.name
    ds.REPORTS_DIR = output_dir
    ds.DUPLICATE_REPORT_JSON_PATH = output_dir / "duplicate_report.json"
    ds.DUPLICATE_SUMMARY_TXT_PATH = output_dir / "duplicate_summary.txt"
    ds.FILE_HASH_LOG_JSON_PATH = output_dir / "file_hash_log.json"

    config = ds.SCAN_CONFIG.copy()
    config["base_path"] = str(dir_path)

    scan_result = ds.scan_project(config)
    return scan_result


def main(base_path: str):
    base = Path(base_path)
    for item in sorted(base.iterdir()):
        if item.is_dir() and not item.name.startswith('.'):
            print(f"Scanning directory: {item}")
            scan_directory(item)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run deduplication scans one directory at a time using deduplication_scanner."
    )
    parser.add_argument(
        "--base",
        default=".",
        help="Base directory containing subdirectories to scan",
    )
    args = parser.parse_args()
    main(args.base)
