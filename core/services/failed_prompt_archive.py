import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

def load_json_safe(file_path: str, default: Any = None) -> Any:
    """Load JSON from path, return default if file doesn't exist or fails."""
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                return default
            return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to load JSON from {file_path}: {e}", exc_info=True)
        return default


def write_json_safe(file_path: str, data: Any) -> None:
    """Write JSON data to path, ensuring directory exists and using atomic replace."""
    try:
        dirpath = os.path.dirname(file_path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        temp_path = f"{file_path}.tmp"
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, file_path)
    except Exception as e:
        logger.error(f"Failed to write JSON to {file_path}: {e}", exc_info=True)


class FailedPromptArchiveService:
    """Service to archive failed prompts with full metadata."""
    def __init__(self, archive_path: str = "memory/failed_prompt_archive.json"):
        self.archive_path = archive_path
        # Ensure archive directory exists
        dirpath = os.path.dirname(self.archive_path)
        if dirpath and not os.path.exists(dirpath):
            os.makedirs(dirpath, exist_ok=True)
        # Load existing archive or start with empty list
        loaded = load_json_safe(self.archive_path, default=[])
        self.archive: List[Dict[str, Any]] = loaded if isinstance(loaded, list) else []

    def log_failure(self, prompt_id: str, prompt_data: Dict[str, Any], reason: str, retry_count: int = 0) -> None:
        """Log a failed prompt attempt to the archive."""
        entry: Dict[str, Any] = {
            "prompt_id": prompt_id,
            "timestamp": datetime.utcnow().isoformat(),
            "reason": reason,
            "retry_count": retry_count,
            "prompt": prompt_data,
        }
        logger.warning(f"📦 Archiving failed prompt: {prompt_id} | reason: {reason} | retry_count: {retry_count}")
        self.archive.append(entry)
        write_json_safe(self.archive_path, self.archive)

    def get_failures(self, filter_by_reason: Optional[str] = None, max_retry: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve archived failures, optionally filtered by reason and retry count."""
        results = self.archive
        if filter_by_reason is not None:
            results = [r for r in results if r.get("reason") == filter_by_reason]
        if max_retry is not None:
            results = [r for r in results if r.get("retry_count", 0) <= max_retry]
        return results

    def get_by_prompt_id(self, prompt_id: str) -> List[Dict[str, Any]]:
        """Retrieve all archived entries for a specific prompt ID."""
        return [r for r in self.archive if r.get("prompt_id") == prompt_id] 