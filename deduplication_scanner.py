import os
import hashlib
import json
import subprocess
import platform
from collections import defaultdict
from pathlib import Path
import difflib

# --- Configuration ---
SCAN_CONFIG = {
    "base_path": "./",
    "ignore_dirs": [
        ".git", ".venv", "__pycache__", "node_modules", "htmlcov",
        ".mypy_cache", ".pytest_cache", ".ruff_cache", ".dreamos_cache",
        "archive", "logs"
    ],
    "file_types": [".py", ".md", ".yaml", ".json"],
    "use_certutil_for_large_files": True,
    "large_file_threshold_kb": 500,
    "similarity_threshold": 0.85  # For near-duplicate names
}

# --- Output Paths ---
REPORTS_DIR = Path("runtime/reports")
DUPLICATE_REPORT_JSON_PATH = REPORTS_DIR / "duplicate_report.json"
DUPLICATE_SUMMARY_TXT_PATH = REPORTS_DIR / "duplicate_summary.txt"
FILE_HASH_LOG_JSON_PATH = REPORTS_DIR / "file_hash_log.json"

# --- Helper Functions ---

def get_file_hash_md5(filepath: Path, use_certutil: bool, threshold_kb: int) -> str | None:
    """Calculates MD5 hash for a file."""
    try:
        size_kb = filepath.stat().st_size / 1024
        if use_certutil and size_kb > threshold_kb and platform.system() == "Windows":
            try:
                # Ensure the path is absolute for certutil if it has spaces or special chars
                abs_path_str = str(filepath.resolve())
                result = subprocess.run(
                    ['certutil', '-hashfile', abs_path_str, 'MD5'],
                    capture_output=True, text=True, check=True, shell=False
                )
                # Output of certutil includes "MD5 hash of <file>:" and then the hash on the next line.
                lines = result.stdout.strip().split('\\n')
                for i, line in enumerate(lines):
                    if "md5 hash of" in line.lower() and i + 1 < len(lines):
                        return lines[i+1].strip()
                    if i == 1 and len(lines) > 1 : # Fallback for some certutil versions
                         return lines[i].strip()
                # If specific line not found, try to find a 32-char hex string
                for line in lines:
                    hash_candidate = line.strip()
                    if len(hash_candidate) == 32 and all(c in '0123456789abcdefABCDEF' for c in hash_candidate):
                        return hash_candidate
                print(f"Warning: Could not parse MD5 from certutil output for {filepath}. Output:\\n{result.stdout}")
                return None
            except subprocess.CalledProcessError as e:
                print(f"Error using certutil for {filepath}: {e.stderr}")
                # Fallback to hashlib
            except FileNotFoundError:
                print("Error: certutil command not found. Ensure it's in your PATH. Falling back to hashlib.")
                # Fallback to hashlib
        
        # Fallback or default hashing with hashlib
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        print(f"Error: File not found for hashing: {filepath}")
        return None
    except PermissionError:
        print(f"Error: Permission denied for hashing: {filepath}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while hashing {filepath}: {e}")
        return None

def get_string_similarity(s1: str, s2: str) -> float:
    """Calculates similarity ratio between two strings."""
    return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

# --- Main Scan Logic ---

def scan_project(config: dict):
    base_path = Path(config["base_path"]).resolve()
    ignore_dirs_set = {name.lower() for name in config["ignore_dirs"]}
    file_types_set = {ft.lower() for ft in config["file_types"]}
    
    print(f"Starting scan in: {base_path}")
    print(f"Ignoring directories: {ignore_dirs_set}")
    print(f"Targeting file types: {file_types_set}")

    all_files_data = {} # path_str -> {"hash": str, "size": int, "name": str}
    hashes_to_files = defaultdict(list) # hash -> [path_str, path_str, ...]
    all_dir_paths = set()
    all_filenames = [] # (filename, full_path_str)

    for root, dirs, files in os.walk(base_path, topdown=True):
        current_path_obj = Path(root)
        
        # Directory filtering
        dirs[:] = [d for d in dirs if d.lower() not in ignore_dirs_set and not d.startswith('.')]
        
        # Check if current path itself should be ignored
        if any(part.lower() in ignore_dirs_set for part in current_path_obj.parts[len(base_path.parts):]):
            continue
        
        all_dir_paths.add(str(current_path_obj))

        for filename in files:
            filepath = current_path_obj / filename
            filepath_str = str(filepath)

            # File type filtering
            if file_types_set and filepath.suffix.lower() not in file_types_set:
                continue

            # File specific ignore patterns (e.g. hidden files, though os.walk might handle some)
            if filename.startswith('.'):
                continue

            print(f"Processing: {filepath_str}")
            file_hash = get_file_hash_md5(
                filepath,
                config["use_certutil_for_large_files"],
                config["large_file_threshold_kb"]
            )
            
            if file_hash:
                try:
                    size = filepath.stat().st_size
                    all_files_data[filepath_str] = {"hash": file_hash, "size": size, "name": filename}
                    hashes_to_files[file_hash].append(filepath_str)
                    all_filenames.append((filename, filepath_str))
                except FileNotFoundError:
                     print(f"Warning: File {filepath_str} disappeared after listing and before stat.")
                except Exception as e:
                    print(f"Warning: Could not get stat for {filepath_str}: {e}")


    # 1. Exact Duplicates
    exact_duplicates = {
        hash_val: paths
        for hash_val, paths in hashes_to_files.items() if len(paths) > 1
    }

    # 2. Near-Duplicate Filenames
    near_duplicate_filenames = defaultdict(list)
    processed_indices = set()
    filenames_with_paths = sorted(list(set(all_filenames))) # unique filenames with their paths

    for i in range(len(filenames_with_paths)):
        if i in processed_indices:
            continue
        
        fname1, fpath1 = filenames_with_paths[i]
        current_group = [fpath1]
        processed_indices.add(i)
        
        for j in range(i + 1, len(filenames_with_paths)):
            if j in processed_indices:
                continue
            
            fname2, fpath2 = filenames_with_paths[j]
            # Avoid comparing a file with itself if it appears multiple times due to different paths (already handled by exact_duplicates)
            # Focus on filename similarity for different files or same filename in different locations (if not exact duplicate)
            if fname1 == fname2 and fpath1 != fpath2 : # Same name, different path (could be non-duplicate content)
                 # Check if they are already part of an exact duplicate group by content
                hash1 = all_files_data.get(fpath1, {}).get("hash")
                hash2 = all_files_data.get(fpath2, {}).get("hash")
                if hash1 and hash2 and hash1 == hash2: # Already caught by exact duplicates
                    continue
            
            similarity = get_string_similarity(fname1, fname2)
            if similarity >= config["similarity_threshold"]:
                current_group.append(fpath2)
                processed_indices.add(j)
        
        if len(current_group) > 1:
            # Use the first filename as a representative key for the group
            near_duplicate_filenames[f"Group for '{fname1}' (and similar)"].extend(current_group)
    
    # Filter out groups where all files are already exact duplicates of each other
    # (though the logic above tries to avoid it, double check)
    # This part might be complex; for now, just list them. Refinement might be needed.


    # 3. Similar Directory Names
    sorted_dir_paths = sorted(list(all_dir_paths))
    similar_dir_names = defaultdict(list)
    processed_dir_indices = set()

    for i in range(len(sorted_dir_paths)):
        if i in processed_dir_indices:
            continue
        
        dirpath1_str = sorted_dir_paths[i]
        dir1_name = Path(dirpath1_str).name
        current_dir_group = [dirpath1_str]
        processed_dir_indices.add(i)

        for j in range(i + 1, len(sorted_dir_paths)):
            if j in processed_dir_indices:
                continue
            
            dirpath2_str = sorted_dir_paths[j]
            dir2_name = Path(dirpath2_str).name
            
            # Avoid comparing a dir with itself or empty names
            if not dir1_name or not dir2_name or dir1_name == dir2_name : # identical names handled if paths are diff
                 if dir1_name == dir2_name and dirpath1_str != dirpath2_str: # same name, diff path
                    pass # let it be grouped
                 else: # identical paths or one name is empty
                    continue


            similarity = get_string_similarity(dir1_name, dir2_name)
            if similarity >= config["similarity_threshold"]:
                current_dir_group.append(dirpath2_str)
                processed_dir_indices.add(j)
        
        if len(current_dir_group) > 1:
            similar_dir_names[f"Group for directory '{dir1_name}' (and similar names)"].extend(current_dir_group)


    # --- Reporting ---
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_data = {
        "scan_config": config,
        "exact_duplicates": exact_duplicates,
        "near_duplicate_filenames": dict(near_duplicate_filenames), # convert defaultdict
        "similar_directory_names": dict(similar_dir_names), # convert defaultdict
        "notes": [
            "Exact duplicates are grouped by content hash.",
            "Near-duplicate filenames are grouped by filename string similarity.",
            "Similar directory names are grouped by directory name string similarity.",
            "Review 'similar_directory_names' carefully; sub-structure similarity is not deeply analyzed in this version."
        ]
    }

    with open(DUPLICATE_REPORT_JSON_PATH, 'w') as f:
        json.dump(report_data, f, indent=4)
    print(f"JSON report saved to: {DUPLICATE_REPORT_JSON_PATH}")

    # File hash log
    with open(FILE_HASH_LOG_JSON_PATH, 'w') as f:
        json.dump(all_files_data, f, indent=4)
    print(f"File hash log saved to: {FILE_HASH_LOG_JSON_PATH}")
    
    # Summary Txt
    summary_lines = [
        "DEDUPLICATION SCAN SUMMARY",
        "==========================",
        f"Scan Date: {Path(__file__).stat().st_mtime}", # A bit of a hack for timestamp
        f"Base Path Scanned: {config['base_path']}",
        f"Ignored Dirs: {config['ignore_dirs']}",
        f"File Types: {config['file_types']}",
        "---",
    ]

    summary_lines.append(f"Found {len(exact_duplicates)} groups of exact duplicate files:")
    for hash_val, paths in exact_duplicates.items():
        summary_lines.append(f"  Hash: {hash_val} ({len(paths)} files):")
        for p in paths:
            summary_lines.append(f"    - {p} (Size: {all_files_data.get(p, {}).get('size', 'N/A')} bytes)")
    
    summary_lines.append("---")
    summary_lines.append(f"Found {len(near_duplicate_filenames)} groups of near-duplicate filenames:")
    for group_name, paths in near_duplicate_filenames.items():
        summary_lines.append(f"  {group_name}:")
        for p in paths:
            summary_lines.append(f"    - {p}")

    summary_lines.append("---")
    summary_lines.append(f"Found {len(similar_dir_names)} groups of similar directory names:")
    for group_name, paths in similar_dir_names.items():
        summary_lines.append(f"  {group_name}:")
        for p in paths:
            summary_lines.append(f"    - {p}")
            
    summary_lines.append("---")
    summary_lines.append(f"Total files processed (matching type filters): {len(all_files_data)}")
    summary_lines.append(f"Total unique directories scanned: {len(all_dir_paths)}")
    summary_lines.append(f"Full JSON report at: {DUPLICATE_REPORT_JSON_PATH}")
    summary_lines.append(f"File hash log at: {FILE_HASH_LOG_JSON_PATH}")

    with open(DUPLICATE_SUMMARY_TXT_PATH, 'w') as f:
        f.write("\\n".join(summary_lines))
    print(f"Text summary saved to: {DUPLICATE_SUMMARY_TXT_PATH}")

    print("Scan complete.")

if __name__ == "__main__":
    scan_project(SCAN_CONFIG) 