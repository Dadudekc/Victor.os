# File processing logic (hashing, caching, exclusion)

import hashlib
import logging
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Set

# Avoid circular import for type hinting LanguageAnalyzer
if TYPE_CHECKING:
    from .analyzer import LanguageAnalyzer

logger = logging.getLogger(__name__)


class FileProcessor:
    """Handles file hashing, ignoring, caching checks, etc."""

    def __init__(
        self,
        project_root: Path,
        cache: Dict,
        cache_lock: threading.Lock,
        additional_ignore_dirs: Set[str],
    ):
        self.project_root = project_root
        self.cache = cache
        self.cache_lock = cache_lock
        # Ensure additional_ignore_dirs contains strings
        self.additional_ignore_dirs = set(map(str, additional_ignore_dirs))

    def hash_file(self, file_path: Path) -> str:
        """Calculates the MD5 hash of a file."""
        try:
            hasher = hashlib.md5()
            with file_path.open("rb") as f:
                while chunk := f.read(8192):  # Read in chunks
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            logger.warning(f"File not found during hashing: {file_path}")
            return ""
        except PermissionError:
            logger.warning(f"Permission error hashing file: {file_path}")
            return ""
        except Exception as e:
            logger.error(f"Error hashing file {file_path}: {e}", exc_info=True)
            return ""

    def should_exclude(self, file_path: Path) -> bool:
        """Exclude logic for venvs, node_modules, .git, specific names, etc."""
        # Common virtual environment patterns and default excludes
        venv_patterns = {
            "venv",
            "env",
            ".env",
            ".venv",
            "virtualenv",
            "ENV",
            "VENV",
            ".ENV",
            ".VENV",
            "python-env",
            "python-venv",
            "py-env",
            "py-venv",
            "envs",
            "conda-env",
            ".conda-env",
            ".poetry",  # Check for .poetry directory itself
        }
        default_exclude_dirs = {
            "__pycache__",
            "node_modules",
            "migrations",
            "build",
            "dist",
            "target",
            ".git",
            ".svn",
            ".hg",
            "coverage",
            "chrome_profile",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".idea",
            ".vscode",
            "site-packages",
            "lib",
            "Lib",  # Common site-package/lib dirs
        } | venv_patterns

        try:
            file_abs = file_path.resolve()
            file_parts = set(
                p.lower() for p in file_abs.parts
            )  # Use lowercase for comparison
        except (OSError, ValueError) as e:  # Handle potential resolution errors
            logger.warning(f"Could not resolve path or get parts for {file_path}: {e}")
            return True  # Exclude if path is problematic

        # 1. Check if the file is the scanner itself (if running as script)
        try:
            # Get the absolute path of the currently executing script file
            current_script_path = Path(__file__).resolve()
            # Check if the file path matches the script path or is within the script's directory  # noqa: E501
            if (
                file_abs == current_script_path
                or current_script_path in file_abs.parents
            ):
                # Allow if it's __init__.py in the same directory
                if file_abs.name != "__init__.py":
                    return True
        except NameError:
            pass  # __file__ not defined (e.g., interactive session)
        except (OSError, ValueError) as e:
            logger.warning(f"Error comparing file path to script path: {e}")
            # Don't exclude based on this error

        # 2. Check additional explicit ignore directories
        for ignore_str in self.additional_ignore_dirs:
            try:
                ignore_path = Path(ignore_str)
                if not ignore_path.is_absolute():
                    ignore_path = (self.project_root / ignore_path).resolve()
                # Check if the file is within the ignored directory
                if ignore_path in file_abs.parents or file_abs == ignore_path:
                    # logger.debug(f"Excluding {file_path} due to ignore rule: {ignore_str}")  # noqa: E501
                    return True
            except (OSError, ValueError) as e:
                logger.warning(
                    f"Could not resolve or compare ignore path '{ignore_str}': {e}"
                )
                continue  # Skip problematic ignore rule

        # 3. Check for default excluded directory names in the path parts
        # Using intersection for efficiency
        if file_parts.intersection(default_exclude_dirs):
            # logger.debug(f"Excluding {file_path} due to default exclude dir in path.")
            return True

        # 4. Check for common virtual environment indicator files/dirs
        # Combine checks to avoid repeated traversals
        try:
            for parent in file_abs.parents:
                parent_parts_lower = set(p.lower() for p in parent.parts)
                # Check parent directory name against patterns
                if (
                    parent.name.lower() in venv_patterns
                    or parent_parts_lower.intersection(venv_patterns)
                ):
                    # logger.debug(f"Excluding {file_path} due to venv pattern in parent: {parent.name}")  # noqa: E501
                    return True
                # Check for indicator files
                if (parent / "pyvenv.cfg").exists():
                    # logger.debug(f"Excluding {file_path} due to pyvenv.cfg in {parent}")  # noqa: E501
                    return True
                if (parent / "bin" / "activate").exists() or (
                    parent / "Scripts" / "activate.bat"
                ).exists():
                    # logger.debug(f"Excluding {file_path} due to activate script in {parent}")  # noqa: E501
                    return True
                # Stop early if we reach project root or system root
                if parent == self.project_root or parent == parent.parent:
                    break
        except (OSError, PermissionError) as e:
            logger.warning(
                f"Permission or OS error checking venv indicators for {file_path}: {e}"
            )
            # Don't exclude based on this error, might be legitimate code
            pass

        # If none of the above exclusion rules matched
        return False

    def process_file(
        self, file_path: Path, language_analyzer: "LanguageAnalyzer"
    ) -> Optional[tuple]:
        """Analyzes a file if not in cache or changed, else returns cached data if valid, or None if excluded/error."""  # noqa: E501
        try:
            relative_path = str(file_path.relative_to(self.project_root)).replace(
                "\\", "/"
            )  # Normalize slashes
        except ValueError:
            logger.warning(
                f"File {file_path} is not relative to project root {self.project_root}. Skipping."  # noqa: E501
            )
            return None

        if self.should_exclude(file_path):
            # logger.debug(f"Excluding file: {relative_path}")
            # Ensure excluded files are removed from cache if they exist there
            with self.cache_lock:
                if relative_path in self.cache:
                    # logger.debug(f"Removing excluded file {relative_path} from cache.")  # noqa: E501
                    del self.cache[relative_path]
            return None

        file_hash_val = self.hash_file(file_path)
        if not file_hash_val:  # Skip if hashing failed
            return None

        cached_data = None
        update_cache_needed = False

        with self.cache_lock:
            cached_data = self.cache.get(relative_path)

        # Check cache
        if cached_data and cached_data.get("hash") == file_hash_val:
            # logger.debug(f"Cache hit for {relative_path}")
            # Return the analysis part from cache if it exists
            if "analysis" in cached_data:
                return (relative_path, cached_data["analysis"])
            else:
                # Hash matches, but no analysis? Needs re-analysis.
                update_cache_needed = True
        else:
            # Cache miss or hash mismatch
            update_cache_needed = True

        # If we need to analyze (cache miss, hash mismatch, or missing analysis in cache)  # noqa: E501
        if update_cache_needed:
            # logger.debug(f"Analyzing file: {relative_path}")
            try:
                # Use try-except for reading to handle encoding/permission errors
                with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                    source_code = f.read()

                # Perform the analysis
                analysis_result = language_analyzer.analyze_file(file_path, source_code)

                # Update cache with new hash and analysis result
                with self.cache_lock:
                    self.cache[relative_path] = {
                        "hash": file_hash_val,
                        "analysis": analysis_result,
                    }

                return (relative_path, analysis_result)

            except FileNotFoundError:
                logger.warning(f"File not found during analysis: {file_path}")
                # Remove from cache if it was there
                with self.cache_lock:
                    if relative_path in self.cache:
                        del self.cache[relative_path]
                return None
            except PermissionError:
                logger.warning(f"Permission error analyzing file: {file_path}")
                with self.cache_lock:
                    if relative_path in self.cache:
                        del self.cache[relative_path]
                return None
            except UnicodeDecodeError as e:
                logger.warning(
                    f"Encoding error analyzing file {file_path}: {e}. Skipping."
                )
                with self.cache_lock:
                    if relative_path in self.cache:
                        del self.cache[relative_path]
                return None
            except Exception as e:
                logger.error(f"❌ Error analyzing {file_path}: {e}", exc_info=True)
                # Update cache with hash but mark analysis as failed?
                # For now, just remove from cache to force retry next time.
                with self.cache_lock:
                    if relative_path in self.cache:
                        del self.cache[relative_path]
                return None

        # Should not be reached if logic is correct, but return None as fallback
        return None
