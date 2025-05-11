import asyncio
import json
import logging
import os
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


async def rewrite_file_safely_atomic(
    file_path: Path, data: List[Dict[str, Any]], is_compressed: bool
) -> bool:
    """Atomically writes data to a file using a temporary file and os.replace.

    Handles JSON serialization, including datetime objects, and optional
    zlib compression based on the `is_compressed` flag.

    Args:
        file_path: The target Path object for the final file.
        data: The list of dictionary entries to serialize and write.
        is_compressed: If True, applies zlib compression to the UTF-8 encoded JSON data.

    Returns:
        True if the write and atomic replacement were successful, False otherwise.
        Errors during write or replace are logged.
    """
    temp_path = file_path.with_suffix(file_path.suffix + f".{os.getpid()}.tmp")

    def _sync_rewrite():
        def dt_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(
                f"Object of type {type(obj).__name__} is not JSON serializable"
            )

        json_data = json.dumps(data, indent=2, default=dt_serializer)

        if is_compressed:
            encoded_data = json_data.encode("utf-8")
            compressed_data = zlib.compress(encoded_data)
            with open(temp_path, "wb") as f:
                f.write(compressed_data)
        else:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(json_data)

        os.replace(temp_path, file_path)

    try:
        await asyncio.to_thread(_sync_rewrite)
        logger.debug(f"Safely rewrote file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to rewrite file {file_path}: {e}", exc_info=True)
        if await asyncio.to_thread(temp_path.exists):
            try:
                await asyncio.to_thread(os.remove, temp_path)
            except OSError as rm_err:
                logger.error(
                    f"Failed to remove temporary save file {temp_path}: {rm_err}"
                )
        return False
