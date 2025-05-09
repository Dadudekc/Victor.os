# src/dreamos/core/state/snapshot_manager.py
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import filelock

from dreamos.utils import file_io

logger = logging.getLogger(__name__)


class SnapshotError(Exception):
    """Custom exception for snapshot errors."""

    pass


class SnapshotManager:
    """Handles creation of system state snapshots (DB file copy)."""

    def __init__(self, db_path: Path, snapshot_dir: Path):
        self.db_path = db_path
        self.snapshot_dir = snapshot_dir
        self.db_lock_path = self.db_path.parent / f"{self.db_path.name}.lock"

        if not self.db_path.is_file():
            # Log critical error but allow init, create call will fail
            logger.critical(
                f"Database file not found at specified path: {self.db_path}"
            )
            # raise SnapshotError(f"Database file not found: {self.db_path}")

        # Ensure snapshot directory exists
        if not file_io.ensure_directory(self.snapshot_dir):
            # file_io.ensure_directory already logs the error
            logger.critical(
                f"Failed to create or ensure snapshot directory {self.snapshot_dir}. SnapshotManager may not function."
            )
            # Depending on desired behavior, we might raise an error immediately
            raise SnapshotError(f"Failed to create snapshot directory: {self.snapshot_dir}")
        else:
            logger.info(f"Snapshot directory ensured: {self.snapshot_dir}")

    def create_snapshot(self, reason: str = "manual") -> Path:
        """Creates a snapshot by copying the database file, using a file lock.

        Args:
            reason: Optional reason for creating the snapshot (for metadata).

        Returns:
            Path to the created snapshot file.

        Raises:
            SnapshotError: If the snapshot creation fails.
        """
        if not self.db_path.is_file():
            raise SnapshotError(
                f"Cannot create snapshot, DB file not found: {self.db_path}"
            )

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        snapshot_filename = f"snapshot_{timestamp_str}.sqlite"
        snapshot_filepath = self.snapshot_dir / snapshot_filename

        # TODO: Implement locking/pause mechanism before copy if needed for atomicity
        # For now, assumes brief file operations are atomic enough or system is paused.
        logger.info(f"Creating snapshot of {self.db_path} to {snapshot_filepath}...")
        logger.debug(f"Attempting to acquire lock: {self.db_lock_path}")

        try:
            lock = filelock.FileLock(self.db_lock_path, timeout=10)
            with lock:
                logger.debug(f"Lock acquired for {self.db_path}")
                # Use copy2 to preserve metadata like modification time if possible
                shutil.copy2(self.db_path, snapshot_filepath)
                logger.info(f"Snapshot created successfully: {snapshot_filepath}")
            logger.debug(f"Lock released for {self.db_path}")

            # Optional: Create metadata file
            meta_filename = f"snapshot_{timestamp_str}.meta.json"
            meta_filepath = self.snapshot_dir / meta_filename
            metadata = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "source_db": str(self.db_path),
                # Add app version, etc. later
            }
            try:
                with open(meta_filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2)
                logger.debug(f"Snapshot metadata created: {meta_filepath}")
            except Exception as meta_e:
                logger.warning(
                    f"Failed to create snapshot metadata file {meta_filepath}: {meta_e}"
                )

            return snapshot_filepath

        except filelock.Timeout:
            logger.error(f"Failed to acquire lock on {self.db_lock_path} within timeout.")
            raise SnapshotError("Failed to acquire DB lock for snapshot")
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}", exc_info=True)
            # Attempt cleanup of potentially partial snapshot file
            if snapshot_filepath.exists():
                try:
                    snapshot_filepath.unlink()
                except Exception as clean_e:
                    logger.error(
                        f"Failed to clean up partial snapshot file {snapshot_filepath}: {clean_e}"
                    )
            raise SnapshotError(f"Snapshot creation failed: {e}") from e

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """Lists available snapshots based on .sqlite files in the directory."""
        snapshots = []
        try:
            for item in self.snapshot_dir.glob("snapshot_*.sqlite"):
                if item.is_file():
                    mtime = item.stat().st_mtime
                    snapshots.append(
                        {
                            "filename": item.name,
                            "path": str(item),
                            "size_bytes": item.stat().st_size,
                            "created_at_local": datetime.fromtimestamp(
                                mtime
                            ).isoformat(),
                            # Could try reading metadata file too
                        }
                    )
            # Sort by presumed creation time (from filename or mtime)
            snapshots.sort(key=lambda x: x["filename"], reverse=True)
        except Exception as e:
            logger.error(
                f"Failed to list snapshots in {self.snapshot_dir}: {e}", exc_info=True
            )

        return snapshots


# Example usage (requires db_path and snapshot_dir)
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO)
#     db_file = Path('./runtime/db/dreamos_state.sqlite')
#     snap_dir = Path('./runtime/snapshots')
#     # Ensure dummy DB exists for testing
#     db_file.parent.mkdir(exist_ok=True)
#     if not db_file.exists(): db_file.touch()
#
#     manager = SnapshotManager(db_path=db_file, snapshot_dir=snap_dir)
#     try:
#         new_snap = manager.create_snapshot(reason="manual_test")
#         print(f"Created: {new_snap}")
#     except SnapshotError as e:
#         print(f"Error: {e}")
#
#     print("Available Snapshots:")
#     for snap in manager.list_snapshots():
#         print(f" - {snap['filename']} ({snap['size_bytes']} bytes, {snap['created_at_local']})")
