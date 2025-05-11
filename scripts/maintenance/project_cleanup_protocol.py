"""
Project Cleanup Protocol
-----------------------
This protocol defines the systematic process for cleaning and organizing the project
based on analysis of project_analysis.json and chatgpt_project_context.json.

The protocol runs in cycles until the project meets cleanliness criteria.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple


class ProjectCleanupProtocol:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.analysis_file = self.project_root / "project_analysis.json"
        self.context_file = self.project_root / "chatgpt_project_context.json"
        self.archive_dir = self.project_root / "archive"
        self.orphans_dir = self.archive_dir / "orphans"
        self.cleanup_log = self.project_root / "cleanup_log.json"

        # Initialize directories
        self.archive_dir.mkdir(exist_ok=True)
        self.orphans_dir.mkdir(exist_ok=True)

        # Cleanup criteria thresholds
        self.max_complexity = 30  # Maximum acceptable complexity per file
        self.min_utility_score = 0.5  # Minimum utility score to keep a file
        self.max_duplicate_functions = 3  # Maximum allowed duplicate function names

    def load_analysis(self) -> Dict:
        """Load and parse the project analysis files."""
        with open(self.analysis_file) as f:
            analysis = json.load(f)
        with open(self.context_file) as f:
            context = json.load(f)
        return analysis, context

    def calculate_file_utility_score(self, file_data: Dict) -> float:
        """Calculate a utility score for a file based on various metrics."""
        score = 0.0

        # Complexity penalty
        complexity = file_data.get("complexity", 0)
        if complexity > self.max_complexity:
            score -= 0.3

        # Function count bonus
        functions = len(file_data.get("functions", []))
        score += min(functions * 0.1, 0.3)

        # Class count bonus
        classes = len(file_data.get("classes", {}))
        score += min(classes * 0.1, 0.3)

        # Route count bonus (for web applications)
        routes = len(file_data.get("routes", []))
        score += min(routes * 0.1, 0.2)

        # Docstring presence bonus
        has_docstrings = any(
            cls.get("docstring") for cls in file_data.get("classes", {}).values()
        )
        if has_docstrings:
            score += 0.2

        return max(0.0, min(1.0, score))

    def identify_duplicate_functions(self, analysis: Dict) -> Dict[str, List[str]]:
        """Identify functions that appear in multiple files."""
        function_locations = {}
        for file_path, file_data in analysis.items():
            for func in file_data.get("functions", []):
                if func not in function_locations:
                    function_locations[func] = []
                function_locations[func].append(file_path)
        return {
            func: locs
            for func, locs in function_locations.items()
            if len(locs) > self.max_duplicate_functions
        }

    def find_orphaned_files(self, analysis: Dict) -> Set[str]:
        """Identify files that are not imported or referenced by other files."""
        referenced_files = set()
        for file_data in analysis.values():
            # Add files referenced in imports
            for func in file_data.get("functions", []):
                if func.startswith("import_") or func.startswith("from_"):
                    referenced_files.add(func.split("_")[1])

        all_files = set(analysis.keys())
        return all_files - referenced_files

    def archive_file(self, file_path: str, reason: str) -> None:
        """Move a file to the archive directory with metadata."""
        src_path = self.project_root / file_path
        if not src_path.exists():
            return

        # Create archive subdirectory based on file type
        file_type = src_path.suffix[1:] or "no_extension"
        archive_subdir = self.orphans_dir / file_type
        archive_subdir.mkdir(exist_ok=True)

        # Move file
        dest_path = archive_subdir / src_path.name
        shutil.move(str(src_path), str(dest_path))

        # Log the archive action
        self.log_cleanup_action(file_path, "archive", reason)

    def log_cleanup_action(self, file_path: str, action: str, reason: str) -> None:
        """Log a cleanup action to the cleanup log."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "file_path": file_path,
            "action": action,
            "reason": reason,
        }

        if self.cleanup_log.exists():
            with open(self.cleanup_log) as f:
                log = json.load(f)
        else:
            log = []

        log.append(log_entry)

        with open(self.cleanup_log, "w") as f:
            json.dump(log, f, indent=2)

    def run_cleanup_cycle(self) -> Tuple[bool, List[str]]:
        """
        Run a single cleanup cycle.
        Returns (is_clean, list_of_actions_taken)
        """
        analysis, context = self.load_analysis()
        actions_taken = []

        # 1. Check for low utility files
        for file_path, file_data in analysis.items():
            utility_score = self.calculate_file_utility_score(file_data)
            if utility_score < self.min_utility_score:
                reason = f"Low utility score: {utility_score:.2f}"
                self.archive_file(file_path, reason)
                actions_taken.append(f"Archived {file_path}: {reason}")

        # 2. Handle duplicate functions
        duplicates = self.identify_duplicate_functions(analysis)
        for func, locations in duplicates.items():
            # Keep the most complex implementation, archive others
            implementations = [(loc, analysis[loc]["complexity"]) for loc in locations]
            implementations.sort(key=lambda x: x[1], reverse=True)

            for loc, _ in implementations[1:]:  # Skip the most complex one
                reason = (
                    f"Duplicate function '{func}' with better implementation elsewhere"
                )
                self.archive_file(loc, reason)
                actions_taken.append(f"Archived {loc}: {reason}")

        # 3. Handle orphaned files
        orphans = self.find_orphaned_files(analysis)
        for orphan in orphans:
            reason = "File is not referenced by any other file"
            self.archive_file(orphan, reason)
            actions_taken.append(f"Archived {orphan}: {reason}")

        # Check if project is clean
        is_clean = (
            len(actions_taken) == 0
            and all(
                self.calculate_file_utility_score(data) >= self.min_utility_score
                for data in analysis.values()
            )
            and len(self.identify_duplicate_functions(analysis)) == 0
        )

        return is_clean, actions_taken

    def run_until_clean(self, max_cycles: int = 10) -> List[str]:
        """
        Run cleanup cycles until the project is clean or max_cycles is reached.
        Returns list of all actions taken.
        """
        all_actions = []
        cycle = 0

        while cycle < max_cycles:
            is_clean, actions = self.run_cleanup_cycle()
            all_actions.extend(actions)

            if is_clean:
                break

            cycle += 1

        return all_actions


def main():
    """Main entry point for the cleanup protocol."""
    project_root = os.getcwd()
    protocol = ProjectCleanupProtocol(project_root)

    print("Starting project cleanup protocol...")
    actions = protocol.run_until_clean()

    if actions:
        print("\nCleanup actions taken:")
        for action in actions:
            print(f"- {action}")
    else:
        print("\nNo cleanup actions were necessary.")

    print("\nCleanup complete. Check cleanup_log.json for details.")


if __name__ == "__main__":
    main()
