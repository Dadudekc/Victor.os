# dedup_report_generator.py

import os
import json
from collections import defaultdict
from pathlib import Path

INPUT_FILE = "_dedup_scan_output.txt"
JSON_OUT = "duplicate_report.json"
SUMMARY_OUT = "duplicate_summary.md"

def parse_line(line):
    # Format: Path;Length;Hash
    parts = line.strip().split(";")
    if len(parts) != 3:
        return None
    path, length, sha = parts
    return path, int(length), sha

def group_duplicates(file_records):
    hash_map = defaultdict(list)
    name_map = defaultdict(list)
    dir_map = defaultdict(list)

    for path, length, sha in file_records:
        hash_map[sha].append(path)
        filename = os.path.basename(path)
        name_map[filename].append((path, sha))
        parent = str(Path(path).parent)
        dir_map[parent].append(path)

    return hash_map, name_map, dir_map

def generate_report(file_records):
    hash_map, name_map, dir_map = group_duplicates(file_records)

    exact_dupes = {k: v for k, v in hash_map.items() if len(v) > 1}
    name_conflicts = {k: v for k, v in name_map.items() if len(v) > 1 and len(set(sha for _, sha in v)) > 1}
    dir_clusters = {k: v for k, v in dir_map.items() if len(v) > 5}  # Tune threshold if needed

    report = {
        "duplicate_hash_clusters": exact_dupes,
        "filename_collisions": name_conflicts,
        "directory_clusters": dir_clusters
    }

    with open(JSON_OUT, "w") as f:
        json.dump(report, f, indent=2)

    with open(SUMMARY_OUT, "w") as f:
        f.write("# 🔍 Deduplication Summary\n\n")
        f.write(f"**Exact Duplicate File Clusters:** {len(exact_dupes)}\n")
        f.write(f"**Filename Collisions (same name, different hash):** {len(name_conflicts)}\n")
        f.write(f"**Heavy Directory Clusters (5+ files):** {len(dir_clusters)}\n\n")

        f.write("## Top Duplicate Hashes\n")
        for sha, paths in sorted(exact_dupes.items(), key=lambda x: -len(x[1]))[:10]:
            f.write(f"\n- SHA: `{sha}` ({len(paths)} copies)\n")
            for p in paths:
                f.write(f"  - {p}\n")

    print(f"\n✅ Duplicate analysis complete. Reports saved to:\n- {JSON_OUT}\n- {SUMMARY_OUT}")

def main():
    # Ensure the input file exists before trying to open it
    if not os.path.exists(INPUT_FILE):
        print(f"Error: Input file '{INPUT_FILE}' not found. Please ensure it exists in the same directory as the script.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    file_records = []
    for line in lines:
        parsed = parse_line(line)
        if parsed:
            file_records.append(parsed)
    
    if not file_records:
        print(f"No valid records found in '{INPUT_FILE}'. The file might be empty or in an incorrect format.")
        return

    generate_report(file_records)

if __name__ == "__main__":
    main() 