#!/usr/bin/env python3
"""
Script to find and merge duplicate directories in the codebase.
This script will:
1. Find directories with similar names (e.g., coordination vs _coordination)
2. Identify directories with similar content/purpose
3. Propose merges with clear paths for consolidation
4. Execute merges after confirmation
"""

import json
import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("merge_duplicate_dirs")


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate directories."""

    primary_dir: Path
    duplicate_dirs: List[Path]
    similarity_scores: Dict[Path, float]
    content_matches: Dict[Path, List[str]]


class DuplicateDirectoryFinder:
    """Finds and manages duplicate directories in the codebase."""

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.ignore_patterns = [
            r"^\.git$",
            r"^\.venv$",
            r"^node_modules$",
            r"^__pycache__$",
            r".*\.egg-info$",
            r"^\.pytest_cache$",
            r"^\.mypy_cache$",
            r"^\.ruff_cache$",
            r"^htmlcov$",
            r"^build$",
            r"^dist$",
        ]
        self.duplicate_groups: List[DuplicateGroup] = []

    def should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        return any(
            re.match(pattern, path.split("/")[-1]) for pattern in self.ignore_patterns
        )

    def find_similar_names(self) -> List[Tuple[str, List[Path]]]:
        """Find directories with similar names."""
        dir_groups: Dict[str, List[Path]] = {}

        for root, dirs, _ in os.walk(self.root_dir):
            for dir_name in dirs:
                if self.should_ignore(dir_name):
                    continue

                # Normalize directory name for comparison
                normalized_name = re.sub(r"[_-]", "", dir_name.lower())
                full_path = Path(root) / dir_name

                if normalized_name not in dir_groups:
                    dir_groups[normalized_name] = []
                dir_groups[normalized_name].append(full_path)

        # Filter out non-duplicates
        return [(name, paths) for name, paths in dir_groups.items() if len(paths) > 1]

    def get_directory_signature(self, dir_path: Path) -> Set[str]:
        """Get a signature of directory contents (file types, key files, etc.)."""
        signature = set()
        try:
            for root, _, files in os.walk(dir_path):
                rel_root = Path(root).relative_to(dir_path)
                for file in files:
                    # Add file extensions
                    signature.add(f"ext:{Path(file).suffix}")
                    # Add key filenames
                    if file in [
                        "__init__.py",
                        "README.md",
                        "setup.py",
                        "pyproject.toml",
                    ]:
                        signature.add(f"key:{file}")
                    # Add relative paths for structure comparison
                    signature.add(f"path:{rel_root / file}")
        except Exception as e:
            logger.warning(f"Error getting signature for {dir_path}: {e}")
        return signature

    def calculate_similarity(self, dir1: Path, dir2: Path) -> Tuple[float, List[str]]:
        """Calculate similarity between two directories."""
        sig1 = self.get_directory_signature(dir1)
        sig2 = self.get_directory_signature(dir2)

        if not sig1 or not sig2:
            return 0.0, []

        # Calculate Jaccard similarity
        intersection = sig1.intersection(sig2)
        union = sig1.union(sig2)
        similarity = len(intersection) / len(union) if union else 0

        # Get matching elements
        matches = sorted(intersection)

        return similarity, matches

    def find_duplicates(self, min_similarity: float = 0.3) -> List[DuplicateGroup]:
        """Find duplicate directories based on name and content similarity."""
        similar_names = self.find_similar_names()

        for _, dir_group in similar_names:
            # Use the shortest path as primary (usually the most centralized/canonical location)
            primary_dir = min(dir_group, key=lambda p: len(str(p)))
            duplicates = [d for d in dir_group if d != primary_dir]

            similarity_scores = {}
            content_matches = {}

            for dup_dir in duplicates:
                score, matches = self.calculate_similarity(primary_dir, dup_dir)
                if score >= min_similarity:
                    similarity_scores[dup_dir] = score
                    content_matches[dup_dir] = matches

            if similarity_scores:
                self.duplicate_groups.append(
                    DuplicateGroup(
                        primary_dir=primary_dir,
                        duplicate_dirs=[
                            d for d in duplicates if d in similarity_scores
                        ],
                        similarity_scores=similarity_scores,
                        content_matches=content_matches,
                    )
                )

        return self.duplicate_groups

    def generate_merge_plan(self) -> Dict:
        """Generate a merge plan for the duplicate directories."""
        merge_plan = {
            "timestamp": "",  # Will be filled by the calling code
            "merge_groups": [],
        }

        for group in self.duplicate_groups:
            group_plan = {
                "primary_dir": str(group.primary_dir),
                "duplicates": [
                    {
                        "path": str(dup_dir),
                        "similarity": group.similarity_scores[dup_dir],
                        "matching_elements": group.content_matches[dup_dir],
                    }
                    for dup_dir in group.duplicate_dirs
                ],
            }
            merge_plan["merge_groups"].append(group_plan)

        return merge_plan

    def execute_merge(self, group: DuplicateGroup, backup: bool = True) -> bool:
        """Execute the merge for a duplicate group."""
        try:
            # Create backup if requested
            if backup:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = self.root_dir / f"backup_{timestamp}"
                backup_dir.mkdir(exist_ok=True)

                for dup_dir in group.duplicate_dirs:
                    backup_path = backup_dir / dup_dir.relative_to(self.root_dir)
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(dup_dir, backup_path)

            # Merge each duplicate into the primary directory
            for dup_dir in group.duplicate_dirs:
                self._merge_directory(dup_dir, group.primary_dir)

                # Remove the duplicate directory if it's empty
                if not any(dup_dir.iterdir()):
                    shutil.rmtree(dup_dir)
                    logger.info(f"Removed empty directory: {dup_dir}")

            return True

        except Exception as e:
            logger.error(f"Error during merge: {e}")
            return False

    def _merge_directory(self, source: Path, target: Path) -> None:
        """Merge source directory into target directory."""
        target.mkdir(parents=True, exist_ok=True)

        for item in source.iterdir():
            target_item = target / item.name

            if item.is_dir():
                if not target_item.exists():
                    shutil.copytree(item, target_item)
                else:
                    self._merge_directory(item, target_item)
            else:
                if not target_item.exists():
                    shutil.copy2(item, target_item)
                else:
                    # Handle file conflicts
                    self._handle_file_conflict(item, target_item)

    def _handle_file_conflict(self, source: Path, target: Path) -> None:
        """Handle conflicting files during merge."""
        # If files are identical, skip
        if self._files_are_identical(source, target):
            return

        # Create a new name for the conflicting file
        base, ext = os.path.splitext(target.name)
        counter = 1
        while True:
            new_name = f"{base}_merged_{counter}{ext}"
            new_path = target.parent / new_name
            if not new_path.exists():
                shutil.copy2(source, new_path)
                break
            counter += 1

    def _files_are_identical(self, file1: Path, file2: Path) -> bool:
        """Check if two files are identical."""
        try:
            return file1.read_bytes() == file2.read_bytes()
        except Exception:
            return False


def main():
    """Main function to find and merge duplicate directories."""
    root_dir = Path.cwd()
    finder = DuplicateDirectoryFinder(root_dir)

    logger.info("Finding duplicate directories...")
    duplicate_groups = finder.find_duplicates()

    if not duplicate_groups:
        logger.info("No duplicate directories found.")
        return

    logger.info(f"Found {len(duplicate_groups)} groups of duplicate directories:")

    # Generate and save merge plan
    merge_plan = finder.generate_merge_plan()
    merge_plan["timestamp"] = datetime.now().isoformat()

    with open("merge_plan.json", "w") as f:
        json.dump(merge_plan, f, indent=2)

    logger.info("Merge plan saved to merge_plan.json")

    # Print findings
    for i, group in enumerate(duplicate_groups, 1):
        logger.info(f"\nGroup {i}:")
        logger.info(f"Primary: {group.primary_dir}")
        logger.info("Duplicates:")
        for dup in group.duplicate_dirs:
            logger.info(f"  - {dup} (similarity: {group.similarity_scores[dup]:.2f})")

    logger.info(
        "\nReview merge_plan.json and run with --execute flag to perform merges."
    )


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Find and merge duplicate directories")
    parser.add_argument("--execute", action="store_true", help="Execute the merges")
    parser.add_argument(
        "--no-backup", action="store_true", help="Skip creating backups"
    )
    args = parser.parse_args()

    main()
