import os, hashlib, json
from pathlib import Path

SCAN_DIR = "D:/Dream.os"
EXTENSIONS = [".py", ".ts", ".tsx", ".json", ".html", ".css", ".js"]
IGNORE_DIRS = {'.git', '.venv', '__pycache__', '.mypy_cache', 'node_modules', '.dreamos_cache', 'archive', 'vendor', 'htmlcov'}

hashes = {}
file_hash_log = {}

def compute_sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

# Ensure reports directory exists before starting the walk
output_reports_dir = os.path.join(SCAN_DIR, "runtime", "reports")
os.makedirs(output_reports_dir, exist_ok=True)

for root, dirs, files in os.walk(SCAN_DIR):
    # More robust directory filtering at the source of os.walk
    # Filter out any subdirectories that are in IGNORE_DIRS or start with '.'
    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]

    # Skip processing files in the current root if the root itself is an ignored directory name
    # This is a secondary check; dirs[:] above should prevent descent into these.
    if Path(root).name in IGNORE_DIRS:
        continue
        
    for fname in files:
        if any(fname.endswith(ext) for ext in EXTENSIONS):
            full_path = os.path.join(root, fname)
            # Construct Path object once for efficiency
            p_full_path = Path(full_path)

            # Skip if any part of the path is in IGNORE_DIRS
            # This is a more thorough check for nested ignored directories not caught by dirs[:]
            # (e.g. if SCAN_DIR itself was an ignored type, or complex nesting)
            # However, with SCAN_DIR being absolute, and dirs[:] filtering, this might be redundant
            # but kept for safety. Simpler: check if p_full_path.parent.name is in IGNORE_DIRS
            # For now, let's simplify the skip logic based on dirs[:] being the primary filter.
            # If root itself was filtered out by the continue above, these files won't be processed.

            try:
                # print(f"Processing: {full_path}") # Optional: for verbose logging
                hashval = compute_sha256(full_path)
                file_hash_log[full_path] = hashval
                hashes.setdefault(hashval, []).append(full_path)
            except FileNotFoundError:
                print(f"Error (FileNotFound): Skipping {full_path}")
            except PermissionError:
                print(f"Error (PermissionError): Skipping {full_path}")
            except Exception as e:
                print(f"Error hashing {full_path}: {e}")

# Filter exact duplicates
duplicate_report = {h: paths for h, paths in hashes.items() if len(paths) > 1}

with open(os.path.join(output_reports_dir, "sha256_file_index.json"), "w") as f:
    json.dump(file_hash_log, f, indent=2)

with open(os.path.join(output_reports_dir, "duplicate_report.json"), "w") as f:
    json.dump(duplicate_report, f, indent=2)

summary_lines = []
if not duplicate_report:
    summary_lines.append("No exact duplicate files found matching the criteria.")
else:
    summary_lines.append(f"Found {len(duplicate_report)} group(s) of exact duplicate files:")
    for h, paths in duplicate_report.items():
        summary_lines.append(f"\nHash: {h} ({len(paths)} files)")
        for p in paths:
            # Make paths relative to SCAN_DIR for cleaner output if desired, or keep absolute
            # relative_p = os.path.relpath(p, SCAN_DIR)
            summary_lines.append(f"  {p}")

with open(os.path.join(output_reports_dir, "duplicate_summary.txt"), "w") as f:
    f.write("\n".join(summary_lines))

print(f"✅ Exact deduplication scan complete. Reports saved to {output_reports_dir}") 