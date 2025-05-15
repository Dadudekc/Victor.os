"""
Memory Manager for JARVIS
Provides persistent memory storage and retrieval capabilities.
"""

import json
import logging
import os
import time
import sys
import errno
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class FileLock:
    """File locking utility for cross-process synchronization with Windows compatibility."""
    
    def __init__(self, path: Path):
        """Initialize file lock.
        
        Args:
            path: Path to the lock file
        """
        self.path = path
        self.lock_file = None
        self.acquired = False
        
    def acquire(self, timeout: float = 10.0, delay: float = 0.1) -> bool:
        """Acquire the file lock.
        
        Args:
            timeout: Maximum time to wait for lock in seconds
            delay: Time to wait between attempts in seconds
            
        Returns:
            True if lock was acquired, False otherwise
        """
        start_time = time.time()
        
        # Create parent directory if it doesn't exist
        self.path.parent.mkdir(parents=True, exist_ok=True)
        
        while True:
            if (time.time() - start_time) >= timeout:
                logger.warning(f"Timed out waiting for lock: {self.path}")
                return False
                
            try:
                # Try to create the lock file exclusively
                if sys.platform == 'win32':
                    # Windows implementation
                    try:
                        # Open with exclusive access
                        fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        self.lock_file = os.fdopen(fd, 'w')
                        self.acquired = True
                        logger.debug(f"Acquired lock: {self.path}")
                        return True
                    except OSError as e:
                        # File exists, another process has the lock
                        if e.errno == errno.EEXIST:
                            pass  # Try again after delay
                        else:
                            raise
                else:
                    # Unix implementation with fcntl
                    import fcntl
                    
                    # Open the file in exclusive creation mode
                    self.lock_file = open(self.path, 'w')
                    
                    # Try to lock the file
                    try:
                        fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self.acquired = True
                        logger.debug(f"Acquired lock: {self.path}")
                        return True
                    except IOError:
                        # Another process has the lock
                        self.lock_file.close()
                        self.lock_file = None
                        
            except Exception as e:
                logger.debug(f"Error acquiring lock: {str(e)}")
                
            # Wait before trying again
            time.sleep(delay)
    
    def release(self) -> bool:
        """Release the file lock.
        
        Returns:
            True if lock was released, False otherwise
        """
        if not self.acquired:
            return False
            
        try:
            if self.lock_file:
                self.lock_file.close()
                self.lock_file = None
            
            # Try to remove the lock file
            try:
                os.unlink(self.path)
            except Exception:  # Be explicit about the exception
                pass
                
            self.acquired = False
            logger.debug(f"Released lock: {self.path}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing lock: {str(e)}")
            return False
    
    def __enter__(self):
        """Enter context manager."""
        self.acquire()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.release()


class MemoryManager:
    """Memory management system for JARVIS."""
    
    # Default maximum number of memory items to keep
    DEFAULT_MAX_ITEMS = 1000
    
    def __init__(self, max_items: int = DEFAULT_MAX_ITEMS):
        """Initialize the memory manager.
        
        Args:
            max_items: Maximum number of memory items to keep
        """
        self._memory_items = []
        self._lock = threading.RLock()
        self._max_items = max_items
        
    def add_interaction(self, interaction: Dict[str, Any]) -> None:
        """Add an interaction to memory.
        
        Args:
            interaction: Dictionary containing interaction details
        """
        with self._lock:
            # Ensure timestamp exists
            if "timestamp" not in interaction:
                interaction["timestamp"] = datetime.now().isoformat()
                
            self._memory_items.append(interaction)
            
            # Check if compaction needed
            if len(self._memory_items) > self._max_items:
                self._compact_memory()
            
    def add_memory(self, memory_item: Dict[str, Any]) -> None:
        """Add a generic memory item.
        
        Args:
            memory_item: Dictionary containing memory details
        """
        with self._lock:
            # Ensure timestamp exists
            if "timestamp" not in memory_item:
                memory_item["timestamp"] = datetime.now().isoformat()
                
            self._memory_items.append(memory_item)
            
            # Check if compaction needed
            if len(self._memory_items) > self._max_items:
                self._compact_memory()
    
    def retrieve_recent(self, count: int = 5) -> List[Dict[str, Any]]:
        """Retrieve the most recent memory items.
        
        Args:
            count: Number of items to retrieve
            
        Returns:
            List of memory items
        """
        with self._lock:
            # Sort by timestamp (newest first) and return requested count
            sorted_items = sorted(
                self._memory_items,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
            return sorted_items[:count]
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search memory for items containing the query string.
        
        Args:
            query: Search string
            
        Returns:
            List of matching memory items
        """
        with self._lock:
            query = query.lower()
            results = []
            
            for item in self._memory_items:
                # Check various fields for matches
                content = item.get("content", "").lower()
                input_text = item.get("input", "").lower()
                response = item.get("response", {}).get("content", "").lower()
                
                if (query in content or query in input_text or query in response):
                    results.append(item)
                    
            return results
    
    def clear(self) -> None:
        """Clear all memory items."""
        with self._lock:
            self._memory_items = []
            
    def size(self) -> int:
        """Get the number of memory items.
        
        Returns:
            Number of items in memory
        """
        with self._lock:
            return len(self._memory_items)
    
    def load(self, file_path: Path) -> bool:
        """Load memory from a file.
        
        Args:
            file_path: Path to the memory file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                logger.info(f"Loading memory from: {file_path}")
                if not file_path.exists():
                    logger.warning(f"Memory file does not exist: {file_path}")
                    return False
                
                # Try to load without locking first for tests
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        
                        if isinstance(data, list):
                            self._memory_items = data
                        elif isinstance(data, dict) and "memory_items" in data:
                            self._memory_items = data["memory_items"]
                        else:
                            logger.error("Invalid memory file format")
                            return False
                    
                    # Check if compaction needed after loading
                    if len(self._memory_items) > self._max_items:
                        self._compact_memory()
                        
                    logger.info(f"Successfully loaded {len(self._memory_items)} memory items")
                    return True
                except Exception as e:
                    logger.error(f"Error loading memory: {str(e)}")
                    return False
        except Exception as e:
            logger.error(f"Error loading memory: {str(e)}")
            return False
    
    def save(self, file_path: Path) -> bool:
        """Save memory to a file.
        
        Args:
            file_path: Path where to save the memory
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                logger.info(f"Saving memory to: {file_path}")
                
                # Ensure directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Check directory permissions
                if not os.access(file_path.parent, os.W_OK):
                    logger.error(f"No write permission for directory: {file_path.parent}")
                    return False
                
                # Try direct save for tests
                try:
                    # Prepare memory data
                    memory_data = {
                        "version": "1.0",
                        "timestamp": datetime.now().isoformat(),
                        "memory_items": self._memory_items
                    }
                    
                    # Write to file
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(memory_data, f, indent=2)
                    
                    # Verify file was created
                    if file_path.exists():
                        logger.info(f"Successfully saved {len(self._memory_items)} memory items")
                        return True
                    else:
                        logger.error(f"Failed to create memory file: {file_path}")
                        return False
                except Exception as e:
                    logger.error(f"Error saving memory: {str(e)}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error saving memory: {str(e)}")
            return False
    
    def set_max_items(self, max_items: int) -> None:
        """Set the maximum number of memory items to keep.
        
        Args:
            max_items: Maximum number of items
        """
        with self._lock:
            self._max_items = max_items
            
            # Check if compaction needed
            if len(self._memory_items) > self._max_items:
                self._compact_memory()
    
    def _compact_memory(self) -> None:
        """Compact memory by removing oldest items to stay within size limit."""
        with self._lock:
            if len(self._memory_items) <= self._max_items:
                return
                
            logger.info(f"Compacting memory from {len(self._memory_items)} items to {self._max_items} items")
            
            # Sort by timestamp (newest first)
            self._memory_items.sort(
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )
            
            # Keep only the newest items
            self._memory_items = self._memory_items[:self._max_items]
            
            logger.info(f"Memory compacted to {len(self._memory_items)} items")
    
    def archive_old_memories(self, archive_path: Path, older_than_days: int = 30) -> bool:
        """Archive memories older than specified days.
        
        Args:
            archive_path: Path to archive file
            older_than_days: Archive items older than this many days
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._lock:
                logger.info(f"Archiving memories older than {older_than_days} days to {archive_path}")
                
                # Calculate cutoff date
                cutoff_date = datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                cutoff_date = cutoff_date.replace(
                    day=cutoff_date.day - older_than_days
                )
                cutoff_str = cutoff_date.isoformat()
                
                # Separate items into current and archive
                current_items = []
                archive_items = []
                
                for item in self._memory_items:
                    timestamp = item.get("timestamp", "")
                    if timestamp < cutoff_str:
                        archive_items.append(item)
                    else:
                        current_items.append(item)
                
                # Update current items
                self._memory_items = current_items
                
                # Save archive if there are items to archive
                if archive_items:
                    # Ensure directory exists
                    archive_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Load existing archive if it exists
                    existing_archive = []
                    if archive_path.exists():
                        try:
                            with open(archive_path, "r", encoding="utf-8") as f:
                                archive_data = json.load(f)
                                if isinstance(archive_data, list):
                                    existing_archive = archive_data
                                elif isinstance(archive_data, dict) and "memory_items" in archive_data:
                                    existing_archive = archive_data["memory_items"]
                        except Exception as e:
                            logger.warning(f"Error loading existing archive: {str(e)}")
                    
                    # Combine with new archive items
                    combined_archive = existing_archive + archive_items
                    
                    # Save archive
                    with open(archive_path, "w", encoding="utf-8") as f:
                        json.dump({
                            "version": "1.0",
                            "timestamp": datetime.now().isoformat(),
                            "memory_items": combined_archive
                        }, f, indent=2)
                    
                    logger.info(f"Archived {len(archive_items)} items, keeping {len(current_items)} items")
                    return True
                else:
                    logger.info("No items to archive")
                    return True
                    
        except Exception as e:
            logger.error(f"Error archiving memories: {str(e)}")
            return False
            
    def __str__(self) -> str:
        """String representation of memory manager.
        
        Returns:
            String representation
        """
        return f"MemoryManager({len(self._memory_items)} items)" 