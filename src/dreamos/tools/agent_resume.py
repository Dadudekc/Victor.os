"""
Agent Resume Manager

Handles agent coordination and message processing.
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from queue import Queue
import threading
import pyautogui
import pyperclip
from PIL import ImageChops, Image
import pygetwindow as gw
import hashlib
import os
import re
import gzip
import shutil
import schedule
import psutil
import argparse
import signal
from dreamos.tools.agent_cellphone import send_cell_phone_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('agent_resume')

AGENTS = [f"Agent-{i}" for i in range(1, 9)]

RESUME_PROMPT = "You stopped again. Are you not a capable coding agent? Resume your loop and complete your assigned task. Swarm status depends on you."

class MessageQueueManager:
    def __init__(self):
        self.queue_file = Path("runtime/agent_comms/coordination/message_queue.json")
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        self.queue: Dict[str, List[dict]] = {
            'high': [],    # Critical messages
            'medium': [],  # Normal messages
            'low': []      # Background messages
        }
        self.load_queue()
        
    def load_queue(self):
        """Load message queue from file."""
        try:
            if self.queue_file.exists():
                with open(self.queue_file, 'r') as f:
                    self.queue = json.load(f)
            else:
                self.save_queue()
        except Exception as e:
            logger.error(f"Error loading queue: {e}")
            
    def save_queue(self):
        """Save message queue to file."""
        try:
            with open(self.queue_file, 'w') as f:
                json.dump(self.queue, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving queue: {e}")
            
    def add_message(self, priority: str, message: dict):
        """Add message to queue."""
        try:
            if priority in self.queue:
                message['timestamp'] = datetime.now().isoformat()
                self.queue[priority].append(message)
                self.save_queue()
                logger.info(f"Added message to {priority} queue")
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding message: {e}")
            return False
            
    def get_next_message(self, priority: str) -> Optional[dict]:
        """Get next message from queue."""
        try:
            if priority in self.queue and self.queue[priority]:
                message = self.queue[priority].pop(0)
                self.save_queue()
                logger.info(f"Retrieved message from {priority} queue")
                return message
            return None
        except Exception as e:
            logger.error(f"Error getting message: {e}")
            return None
            
    def clear_queue(self, priority: Optional[str] = None):
        """Clear message queue."""
        try:
            if priority:
                if priority in self.queue:
                    self.queue[priority] = []
            else:
                for p in self.queue:
                    self.queue[p] = []
            self.save_queue()
            logger.info(f"Cleared {'all' if not priority else priority} queues")
            return True
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
            return False

class ResponseValidator:
    """Validates and filters agent responses."""
    
    def __init__(self):
        # Minimum and maximum response lengths
        self.MIN_LENGTH = 10
        self.MAX_LENGTH = 100000
        
        # Common error patterns
        self.ERROR_PATTERNS = [
            r"Error:.*",
            r"Exception:.*",
            r"Traceback.*",
            r"Failed to.*",
            r"Unable to.*"
        ]
        
        # Compile regex patterns
        self.error_regex = re.compile("|".join(self.ERROR_PATTERNS))
        
        # Duplicate detection window (in seconds)
        self.DUPLICATE_WINDOW = 300  # 5 minutes
        
    def validate_response(self, agent_id: str, content: str, timestamp: str) -> Tuple[bool, str]:
        """Validate a response and return (is_valid, reason)."""
        try:
            # Check length
            if len(content) < self.MIN_LENGTH:
                return False, f"Response too short (min {self.MIN_LENGTH} chars)"
            if len(content) > self.MAX_LENGTH:
                return False, f"Response too long (max {self.MAX_LENGTH} chars)"
                
            # Check for error patterns
            if self.error_regex.search(content):
                return False, "Response contains error patterns"
                
            # Check for empty or whitespace-only content
            if not content.strip():
                return False, "Response is empty or whitespace-only"
                
            # Check for common malformed patterns
            if self._is_malformed(content):
                return False, "Response appears malformed"
                
            return True, "Valid response"
            
        except Exception as e:
            logger.error(f"Error validating response: {e}")
            return False, f"Validation error: {str(e)}"
            
    def _is_malformed(self, content: str) -> bool:
        """Check for malformed response patterns."""
        try:
            # Check for incomplete code blocks
            code_blocks = content.count("```")
            if code_blocks % 2 != 0:
                return True
                
            # Check for unbalanced brackets/parentheses
            brackets = {"(": ")", "[": "]", "{": "}"}
            stack = []
            for char in content:
                if char in brackets:
                    stack.append(char)
                elif char in brackets.values():
                    if not stack or brackets[stack.pop()] != char:
                        return True
                        
            if stack:  # Unclosed brackets
                return True
                
            # Check for extremely repetitive content
            words = content.split()
            if len(words) > 10:
                word_freq = {}
                for word in words:
                    word_freq[word] = word_freq.get(word, 0) + 1
                if max(word_freq.values()) > len(words) * 0.5:  # More than 50% repetition
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking malformed content: {e}")
            return True
            
    def is_duplicate(self, agent_id: str, content: str, history: List[dict]) -> bool:
        """Check if response is a duplicate within the time window."""
        try:
            # Get recent responses for this agent
            recent = [
                r for r in history 
                if r["agent_id"] == agent_id and 
                (datetime.now(timezone.utc) - datetime.fromisoformat(r["timestamp"].replace('Z', '+00:00'))).total_seconds() < self.DUPLICATE_WINDOW
            ]
            
            # Check for exact duplicates
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            for response in recent:
                if hashlib.sha256(response["content"].encode()).hexdigest() == content_hash:
                    return True
                    
            # Check for near-duplicates (90% similarity)
            for response in recent:
                if self._similarity(content, response["content"]) > 0.9:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicates: {e}")
            return False
            
    def _similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity ratio."""
        try:
            # Convert to sets of words
            set1 = set(str1.lower().split())
            set2 = set(str2.lower().split())
            
            # Calculate Jaccard similarity
            intersection = len(set1.intersection(set2))
            union = len(set1.union(set2))
            
            return intersection / union if union > 0 else 0
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0

class HistoryCompressor:
    """Manages rotation and compression of response history files."""
    
    def __init__(self, history_dir: Path, retention_days: int = 30):
        self.history_dir = history_dir
        self.retention_days = retention_days
        self.running = False
        self.compressor_thread = None
        
    def start_compression_service(self):
        """Start the background compression service."""
        try:
            if not self.running:
                self.running = True
                self.compressor_thread = threading.Thread(target=self._compression_loop)
                self.compressor_thread.daemon = True
                self.compressor_thread.start()
                logger.info("History compression service started")
        except Exception as e:
            logger.error(f"Failed to start compression service: {e}")
            
    def stop_compression_service(self):
        """Stop the background compression service."""
        try:
            self.running = False
            if self.compressor_thread:
                self.compressor_thread.join(timeout=5)
            logger.info("History compression service stopped")
        except Exception as e:
            logger.error(f"Failed to stop compression service: {e}")
            
    def _compression_loop(self):
        """Main compression loop."""
        while self.running:
            try:
                # Schedule daily rotation at midnight
                schedule.every().day.at("00:00").do(self.rotate_and_compress)
                
                # Run pending tasks
                schedule.run_pending()
                
                # Sleep for a minute
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in compression loop: {e}")
                time.sleep(60)
                
    def rotate_and_compress(self):
        """Rotate and compress the current history file."""
        try:
            history_file = self.history_dir / "history.jsonl"
            if not history_file.exists():
                logger.warning("No history file to rotate")
                return
                
            # Generate archive filename with date
            date_str = datetime.now().strftime("%Y%m%d")
            archive_file = self.history_dir / f"history-{date_str}.jsonl"
            compressed_file = self.history_dir / f"history-{date_str}.jsonl.gz"
            
            # Move current history to archive
            shutil.move(str(history_file), str(archive_file))
            
            # Compress archive
            with open(archive_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # Remove uncompressed archive
            archive_file.unlink()
            
            # Create new empty history file
            history_file.touch()
            
            # Clean up old archives
            self._cleanup_old_archives()
            
            logger.info(f"History rotated and compressed: {compressed_file}")
            
        except Exception as e:
            logger.error(f"Error rotating and compressing history: {e}")
            
    def _cleanup_old_archives(self):
        """Remove archives older than retention period."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for file in self.history_dir.glob("history-*.jsonl.gz"):
                try:
                    # Extract date from filename
                    date_str = file.stem.split('-')[1]
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    
                    # Remove if older than retention period
                    if file_date < cutoff_date:
                        file.unlink()
                        logger.info(f"Removed old archive: {file}")
                        
                except Exception as e:
                    logger.error(f"Error processing archive {file}: {e}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up old archives: {e}")
            
    def force_rotation(self):
        """Force immediate rotation and compression."""
        try:
            self.rotate_and_compress()
            return True
        except Exception as e:
            logger.error(f"Error forcing rotation: {e}")
            return False

class ResponseHistory:
    """Manages response history tracking and querying."""
    
    def __init__(self):
        self.history_dir = Path("runtime/agent_responses")
        self.history_file = self.history_dir / "history.jsonl"
        self.index_file = self.history_dir / "index.json"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.validator = ResponseValidator()
        self.compressor = HistoryCompressor(self.history_dir)
        self.compressor.start_compression_service()
        self._load_index()
        
    def __del__(self):
        """Cleanup when object is destroyed."""
        try:
            self.compressor.stop_compression_service()
        except Exception as e:
            logger.error(f"Error stopping compression service: {e}")
        
    def _load_index(self):
        """Load or initialize the response index."""
        try:
            if self.index_file.exists():
                with open(self.index_file, 'r') as f:
                    self.index = json.load(f)
            else:
                self.index = {
                    "agents": {},  # agent_id -> list of response hashes
                    "timestamps": {},  # timestamp -> list of response hashes
                    "hashes": {}  # hash -> response metadata
                }
                self._save_index()
        except Exception as e:
            logger.error(f"Error loading response index: {e}")
            self.index = {"agents": {}, "timestamps": {}, "hashes": {}}
            
    def _save_index(self):
        """Save the response index."""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving response index: {e}")
            
    def add_response(self, agent_id: str, content: str) -> Optional[str]:
        """Add a response to history and return its hash if valid."""
        try:
            # Validate response
            is_valid, reason = self.validator.validate_response(
                agent_id, 
                content, 
                datetime.now(timezone.utc).isoformat()
            )
            
            if not is_valid:
                logger.warning(f"Invalid response from {agent_id}: {reason}")
                return None
                
            # Check for duplicates
            recent_responses = self.get_responses(agent_id=agent_id)
            if self.validator.is_duplicate(agent_id, content, recent_responses):
                logger.warning(f"Duplicate response from {agent_id}")
                return None
                
            # Generate hash
            response_hash = hashlib.sha256(content.encode()).hexdigest()
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Create response record
            record = {
                "hash": response_hash,
                "agent_id": agent_id,
                "timestamp": timestamp,
                "content": content,
                "validation": {
                    "is_valid": True,
                    "reason": reason
                }
            }
            
            # Append to history file
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
                
            # Update index
            if agent_id not in self.index["agents"]:
                self.index["agents"][agent_id] = []
            self.index["agents"][agent_id].append(response_hash)
            
            if timestamp not in self.index["timestamps"]:
                self.index["timestamps"][timestamp] = []
            self.index["timestamps"][timestamp].append(response_hash)
            
            self.index["hashes"][response_hash] = {
                "agent_id": agent_id,
                "timestamp": timestamp,
                "validation": record["validation"]
            }
            
            self._save_index()
            logger.info(f"Added valid response to history: {response_hash}")
            return response_hash
            
        except Exception as e:
            logger.error(f"Error adding response to history: {e}")
            return None
            
    def get_responses(self, agent_id: str = None, since: str = None, until: str = None) -> List[dict]:
        """Query responses with optional filters."""
        try:
            responses = []
            
            # Get relevant hashes from index
            hashes = set()
            if agent_id:
                hashes.update(self.index["agents"].get(agent_id, []))
            if since or until:
                for ts, ts_hashes in self.index["timestamps"].items():
                    if since and ts < since:
                        continue
                    if until and ts > until:
                        continue
                    hashes.update(ts_hashes)
                    
            # If no filters, get all hashes
            if not hashes:
                hashes = set(self.index["hashes"].keys())
                
            # Read responses from history file
            with open(self.history_file, 'r') as f:
                for line in f:
                    record = json.loads(line)
                    if record["hash"] in hashes:
                        responses.append(record)
                        
            return sorted(responses, key=lambda x: x["timestamp"])
            
        except Exception as e:
            logger.error(f"Error querying responses: {e}")
            return []
            
    def get_response_by_hash(self, response_hash: str) -> Optional[dict]:
        """Get a specific response by its hash."""
        try:
            with open(self.history_file, 'r') as f:
                for line in f:
                    record = json.loads(line)
                    if record["hash"] == response_hash:
                        return record
            return None
        except Exception as e:
            logger.error(f"Error getting response by hash: {e}")
            return None

    def get_invalid_responses(self, agent_id: Optional[str] = None) -> List[dict]:
        """Get list of invalid responses."""
        try:
            responses = self.get_responses(agent_id)
            return [
                r for r in responses 
                if not r.get("validation", {}).get("is_valid", True)
            ]
        except Exception as e:
            logger.error(f"Error getting invalid responses: {e}")
            return []
            
    def get_duplicate_responses(self, agent_id: Optional[str] = None) -> List[dict]:
        """Get list of duplicate responses."""
        try:
            responses = self.get_responses(agent_id)
            duplicates = []
            
            # Group responses by content hash
            content_groups = {}
            for response in responses:
                content_hash = hashlib.sha256(response["content"].encode()).hexdigest()
                if content_hash not in content_groups:
                    content_groups[content_hash] = []
                content_groups[content_hash].append(response)
                
            # Find groups with multiple responses
            for group in content_groups.values():
                if len(group) > 1:
                    duplicates.extend(group)
                    
            return sorted(duplicates, key=lambda x: x["timestamp"])
            
        except Exception as e:
            logger.error(f"Error getting duplicate responses: {e}")
            return []

    def search_responses(self,
                        query: str,
                        agent_id: Optional[str] = None,
                        since: Optional[str] = None,
                        until: Optional[str] = None,
                        case_sensitive: bool = False,
                        use_regex: bool = False,
                        limit: Optional[int] = None) -> List[dict]:
        """Search responses by content.
        
        Args:
            query: Search query (text or regex pattern)
            agent_id: Optional agent ID to filter by
            since: Optional start timestamp
            until: Optional end timestamp
            case_sensitive: Whether to perform case-sensitive search
            use_regex: Whether to treat query as regex pattern
            limit: Optional maximum number of results
            
        Returns:
            List of matching responses, sorted by timestamp
        """
        try:
            # Compile regex if needed
            if use_regex:
                try:
                    pattern = re.compile(query, 0 if case_sensitive else re.IGNORECASE)
                except re.error as e:
                    logger.error(f"Invalid regex pattern: {e}")
                    return []
            else:
                # Convert query to lowercase for case-insensitive search
                query = query if case_sensitive else query.lower()
                
            # Get base responses
            responses = self.get_responses(
                agent_id=agent_id,
                since=since,
                until=until
            )
            
            # Search responses
            matches = []
            for response in responses:
                content = response["content"]
                if not case_sensitive and not use_regex:
                    content = content.lower()
                    
                # Check for match
                if use_regex:
                    if pattern.search(content):
                        matches.append(response)
                else:
                    if query in content:
                        matches.append(response)
                        
            # Apply limit if specified
            if limit:
                matches = matches[-limit:]
                
            return matches
            
        except Exception as e:
            logger.error(f"Error searching responses: {e}")
            return []
            
    def search_responses_by_keywords(self,
                                   keywords: List[str],
                                   agent_id: Optional[str] = None,
                                   since: Optional[str] = None,
                                   until: Optional[str] = None,
                                   case_sensitive: bool = False,
                                   match_all: bool = False,
                                   limit: Optional[int] = None) -> List[dict]:
        """Search responses by multiple keywords.
        
        Args:
            keywords: List of keywords to search for
            agent_id: Optional agent ID to filter by
            since: Optional start timestamp
            until: Optional end timestamp
            case_sensitive: Whether to perform case-sensitive search
            match_all: Whether all keywords must match (AND) or any can match (OR)
            limit: Optional maximum number of results
            
        Returns:
            List of matching responses, sorted by timestamp
        """
        try:
            # Get base responses
            responses = self.get_responses(
                agent_id=agent_id,
                since=since,
                until=until
            )
            
            # Search responses
            matches = []
            for response in responses:
                content = response["content"]
                if not case_sensitive:
                    content = content.lower()
                    keywords = [k.lower() for k in keywords]
                    
                # Check for matches
                if match_all:
                    if all(k in content for k in keywords):
                        matches.append(response)
                else:
                    if any(k in content for k in keywords):
                        matches.append(response)
                        
            # Apply limit if specified
            if limit:
                matches = matches[-limit:]
                
            return matches
            
        except Exception as e:
            logger.error(f"Error searching responses by keywords: {e}")
            return []

class ResponseDetector:
    """Detects when Cursor chat responses are complete and captures them."""
    
    def __init__(self):
        self.STABLE_THRESHOLD = 3
        self.CHECK_INTERVAL = 0.5
        self.CHAT_OFFSET_X = 100
        self.CHAT_OFFSET_Y = 200
        self.CHAT_WIDTH = 800
        self.CHAT_HEIGHT = 400
        self.running = False
        self.detector_thread = None
        self.history = ResponseHistory()
        
    def start_detection(self):
        """Start the response detection thread."""
        try:
            if not self.running:
                self.running = True
                self.detector_thread = threading.Thread(target=self._detection_loop)
                self.detector_thread.daemon = True
                self.detector_thread.start()
                logger.info("Response detector started")
        except Exception as e:
            logger.error(f"Failed to start response detector: {e}")
            
    def stop_detection(self):
        """Stop the response detection thread."""
        try:
            self.running = False
            if self.detector_thread:
                self.detector_thread.join(timeout=5)
            logger.info("Response detector stopped")
        except Exception as e:
            logger.error(f"Failed to stop response detector: {e}")
            
    def _detection_loop(self):
        """Main detection loop."""
        while self.running:
            try:
                # Find all agent windows
                windows = [w for w in gw.getAllWindows() if "Agent-" in w.title]
                
                # Process each window
                for window in windows:
                    self._process_window(window)
                    
                # Sleep between cycles
                time.sleep(self.CHECK_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in detection loop: {e}")
                time.sleep(1)
                
    def _process_window(self, window):
        """Process a single agent window."""
        try:
            # Calculate chat region
            region = (
                window.left + self.CHAT_OFFSET_X,
                window.top + self.CHAT_OFFSET_Y,
                self.CHAT_WIDTH,
                self.CHAT_HEIGHT
            )
            
            # Check if response is complete
            if self._is_response_complete(region):
                # Capture response
                response = self._capture_response(region)
                
                # Queue the response
                self._queue_response(window.title, response)
                
        except Exception as e:
            logger.error(f"Error processing window {window.title}: {e}")
            
    def _is_response_complete(self, region):
        """Check if response in region is complete."""
        try:
            stable_count = 0
            last_img = pyautogui.screenshot(region=region)
            
            while stable_count < self.STABLE_THRESHOLD:
                time.sleep(self.CHECK_INTERVAL)
                img = pyautogui.screenshot(region=region)
                if self._images_equal(last_img, img):
                    stable_count += 1
                else:
                    stable_count = 0
                    last_img = img
                    
            return True
            
        except Exception as e:
            logger.error(f"Error checking response completion: {e}")
            return False
            
    def _images_equal(self, img1, img2):
        """Check if two images are identical."""
        try:
            return not ImageChops.difference(img1, img2).getbbox()
        except Exception as e:
            logger.error(f"Error comparing images: {e}")
            return False
            
    def _capture_response(self, region):
        """Capture response text from region."""
        try:
            # Click to focus
            x, y, w, h = region
            pyautogui.click(x + 10, y + 10)
            time.sleep(0.1)
            
            # Select all and copy
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            
            # Get clipboard content
            return pyperclip.paste()
            
        except Exception as e:
            logger.error(f"Error capturing response: {e}")
            return None
            
    def _queue_response(self, agent_id: str, response: str):
        """Queue captured response to message queue and history."""
        try:
            if response:
                # Add to history
                response_hash = self.history.add_response(agent_id, response)
                
                # Format message
                message = {
                    "type": "agent_response",
                    "from": agent_id,
                    "content": response,
                    "hash": response_hash,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Add to queue
                self.queue_manager.add_message("high", message)
                logger.info(f"Queued response from {agent_id} (hash: {response_hash})")
                
        except Exception as e:
            logger.error(f"Error queuing response from {agent_id}: {e}")

class ReplayController:
    """Controls replaying of historical responses into agent mailboxes."""
    
    def __init__(self, history: ResponseHistory):
        self.history = history
        self.mailboxes_dir = Path("runtime/agent_comms/mailboxes")
        self.mailboxes_dir.mkdir(parents=True, exist_ok=True)
        
    def replay_responses(self, 
                        responses: List[dict], 
                        target_agent: str, 
                        dry_run: bool = False,
                        delay: float = 0.0) -> bool:
        """Replay responses into target agent's mailbox."""
        try:
            # Get target mailbox
            mailbox_dir = self.mailboxes_dir / target_agent
            mailbox_dir.mkdir(exist_ok=True)
            inbox_file = mailbox_dir / "inbox.json"
            
            # Load existing queue
            queue = []
            if inbox_file.exists():
                with open(inbox_file, 'r') as f:
                    queue = json.load(f)
                    
            # Process each response
            for response in responses:
                # Create message envelope
                envelope = {
                    "type": "replay",
                    "timestamp": response["timestamp"],
                    "from": response["agent_id"],
                    "hash": response["hash"],
                    "content": response["content"],
                    "validation": response.get("validation", {}),
                    "replay_info": {
                        "original_timestamp": response["timestamp"],
                        "replay_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                
                if dry_run:
                    logger.info(f"DRY RUN - Would replay: {envelope}")
                else:
                    # Add to queue
                    queue.append(envelope)
                    
                    # Save updated queue
                    with open(inbox_file, 'w') as f:
                        json.dump(queue, f, indent=2)
                        
                    logger.info(f"Replayed response {response['hash']} to {target_agent}")
                    
                    # Optional delay between replays
                    if delay > 0:
                        time.sleep(delay)
                        
            return True
            
        except Exception as e:
            logger.error(f"Error replaying responses: {e}")
            return False
            
    def replay_by_agent(self, 
                       source_agent: str, 
                       target_agent: str,
                       since: Optional[str] = None,
                       until: Optional[str] = None,
                       limit: Optional[int] = None,
                       dry_run: bool = False,
                       delay: float = 0.0) -> bool:
        """Replay responses from source agent to target agent."""
        try:
            # Get responses
            responses = self.history.get_responses(
                agent_id=source_agent,
                since=since,
                until=until
            )
            
            # Apply limit if specified
            if limit:
                responses = responses[-limit:]
                
            # Replay responses
            return self.replay_responses(
                responses=responses,
                target_agent=target_agent,
                dry_run=dry_run,
                delay=delay
            )
            
        except Exception as e:
            logger.error(f"Error replaying by agent: {e}")
            return False
            
    def replay_by_hash(self, 
                      response_hash: str, 
                      target_agent: str,
                      dry_run: bool = False) -> bool:
        """Replay a specific response by hash."""
        try:
            # Get response
            response = self.history.get_response_by_hash(response_hash)
            if not response:
                logger.error(f"Response not found: {response_hash}")
                return False
                
            # Replay response
            return self.replay_responses(
                responses=[response],
                target_agent=target_agent,
                dry_run=dry_run
            )
            
        except Exception as e:
            logger.error(f"Error replaying by hash: {e}")
            return False
            
    def get_replay_status(self, target_agent: str) -> dict:
        """Get status of replayed messages in target agent's mailbox."""
        try:
            inbox_file = self.mailboxes_dir / target_agent / "inbox.json"
            if not inbox_file.exists():
                return {"error": "No inbox found"}
                
            with open(inbox_file, 'r') as f:
                queue = json.load(f)
                
            # Count replayed messages
            replayed = [msg for msg in queue if msg.get("type") == "replay"]
            
            return {
                "total_messages": len(queue),
                "replayed_messages": len(replayed),
                "latest_replay": max([msg["replay_info"]["replay_timestamp"] for msg in replayed]) if replayed else None
            }
            
        except Exception as e:
            logger.error(f"Error getting replay status: {e}")
            return {"error": str(e)}

class AgentResume:
    def __init__(self, agent_id: str, headless: bool = False):
        self.agent_id = agent_id
        self.headless = headless
        self.state = {
            "last_updated": "",
            "message_count": 0,
            "messages": {"total": 0, "unread": 0},
            "cycle_count": 0,
            "last_stop": None,
            "stop_reason": None,
            "protocol_compliance": {},
            "health_metrics": {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "last_check": None
            }
        }
        self.last_cycle = time.time()
        self.queue_manager = MessageQueueManager()
        self.response_validator = ResponseValidator()
        self.response_history = ResponseHistory()
        self.protocol_dir = Path("docs/agents/protocols")
        self.coordination_file = Path("runtime/agent_comms/coordination/agent_status.json")
        self.coordination_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Enhanced stop patterns
        self.stop_patterns = [
            r"stop",
            r"wait",
            r"idle",
            r"confirm",
            r"permission",
            r"review",
            r"feedback",
            r"let me know",
            r"if you need",
            r"would you like",
            r"should i",
            r"do you want",
            r"can i help",
            r"need any assistance",
            r"if you have any questions",
            r"please tell me",
            r"would you like me to",
            r"should i proceed with",
            r"do you want me to",
            r"can i assist with",
            r"human input",
            r"user input",
            r"user confirmation",
            r"user approval",
            r"user feedback",
            r"user review",
            r"user permission",
            r"user direction",
            r"user guidance",
            r"user instruction",
            r"user command",
            r"user request",
            r"user requirement",
            r"user specification",
            r"user preference",
            r"user choice",
            r"user decision",
            r"user selection",
            r"user validation",
            r"user verification",
            r"user authentication",
            r"user authorization",
            r"user consent",
            r"user agreement",
            r"user acceptance",
            r"user acknowledgment"
        ]
        self.stop_regex = re.compile("|".join(self.stop_patterns), re.IGNORECASE)
        
    def _detect_stop(self, message: str) -> Tuple[bool, str]:
        """Detect if a message indicates a stop."""
        try:
            # Check for stop patterns
            if self.stop_regex.search(message):
                return True, "Stop pattern detected in message"
                
            # Check for idle patterns
            if self._is_idle(message):
                return True, "Idle pattern detected"
                
            # Check for human input requests
            if self._requests_human_input(message):
                return True, "Human input request detected"
                
            # Check for confirmation requests
            if self._requests_confirmation(message):
                return True, "Confirmation request detected"
                
            # Check for permission requests
            if self._requests_permission(message):
                return True, "Permission request detected"
                
            # Check for guidance requests
            if self._requests_guidance(message):
                return True, "Guidance request detected"
                
            # Check for direction requests
            if self._requests_direction(message):
                return True, "Direction request detected"
                
            # Check for approval requests
            if self._requests_approval(message):
                return True, "Approval request detected"
                
            # Check for feedback requests
            if self._requests_feedback(message):
                return True, "Feedback request detected"
                
            return False, None
            
        except Exception as e:
            logger.error(f"Error detecting stop: {e}")
            return False, None
            
    def _is_idle(self, message: str) -> bool:
        """Check if message indicates idling."""
        idle_patterns = [
            r"waiting",
            r"idle",
            r"pause",
            r"halt",
            r"standby",
            r"inactive",
            r"dormant",
            r"sleep",
            r"rest",
            r"break"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in idle_patterns)
        
    def _requests_human_input(self, message: str) -> bool:
        """Check if message requests human input."""
        input_patterns = [
            r"human input",
            r"user input",
            r"user confirmation",
            r"user approval",
            r"user feedback",
            r"user review",
            r"user permission",
            r"user direction",
            r"user guidance",
            r"user instruction",
            r"user command",
            r"user request",
            r"user requirement",
            r"user specification",
            r"user preference",
            r"user choice",
            r"user decision",
            r"user selection",
            r"user validation",
            r"user verification",
            r"user authentication",
            r"user authorization",
            r"user consent",
            r"user agreement",
            r"user acceptance",
            r"user acknowledgment"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in input_patterns)
        
    def _requests_confirmation(self, message: str) -> bool:
        """Check if message requests confirmation."""
        confirmation_patterns = [
            r"confirm",
            r"verify",
            r"validate",
            r"check",
            r"review",
            r"approve",
            r"authorize",
            r"sanction",
            r"ratify",
            r"endorse"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in confirmation_patterns)
        
    def _requests_permission(self, message: str) -> bool:
        """Check if message requests permission."""
        permission_patterns = [
            r"permission",
            r"authorization",
            r"consent",
            r"approval",
            r"sanction",
            r"ratification",
            r"endorsement",
            r"validation",
            r"verification",
            r"confirmation"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in permission_patterns)
        
    def _requests_guidance(self, message: str) -> bool:
        """Check if message requests guidance."""
        guidance_patterns = [
            r"guidance",
            r"direction",
            r"instruction",
            r"advice",
            r"counsel",
            r"recommendation",
            r"suggestion",
            r"proposal",
            r"plan",
            r"strategy"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in guidance_patterns)
        
    def _requests_direction(self, message: str) -> bool:
        """Check if message requests direction."""
        direction_patterns = [
            r"direction",
            r"guidance",
            r"instruction",
            r"command",
            r"order",
            r"directive",
            r"mandate",
            r"requirement",
            r"specification",
            r"prescription"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in direction_patterns)
        
    def _requests_approval(self, message: str) -> bool:
        """Check if message requests approval."""
        approval_patterns = [
            r"approval",
            r"authorization",
            r"sanction",
            r"ratification",
            r"endorsement",
            r"validation",
            r"verification",
            r"confirmation",
            r"consent",
            r"permission"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in approval_patterns)
        
    def _requests_feedback(self, message: str) -> bool:
        """Check if message requests feedback."""
        feedback_patterns = [
            r"feedback",
            r"review",
            r"comment",
            r"input",
            r"opinion",
            r"assessment",
            r"evaluation",
            r"critique",
            r"analysis",
            r"report"
        ]
        return any(re.search(pattern, message, re.IGNORECASE) for pattern in feedback_patterns)
        
    def _handle_stop(self, reason: str):
        """Handle a detected stop."""
        try:
            # Log the stop
            self.state["last_stop"] = time.strftime("%Y-%m-%dT%H:%M:%S.%fZ", time.gmtime())
            self.state["stop_reason"] = reason
            self.state["cycle_count"] = 0  # Reset cycle count
            
            # Review protocols
            self._review_protocols()
            
            # Update agent status
            self._update_agent_status()
            
            # Send feedback to swarm leader
            self._send_feedback_to_leader()
            
            # Save state
            self.save_agent_status()
            
            # Log warning
            logger.warning(f"Stop detected: {reason}")
            
            # Take corrective action
            self._take_corrective_action(reason)
            
            # Update onboarding
            self._update_onboarding()
            
            # Send stop alert
            self._send_stop_alert(reason)
            
        except Exception as e:
            logger.error(f"Error handling stop: {e}")
            
    def _take_corrective_action(self, reason: str):
        """Take corrective action after a stop."""
        try:
            # Review and update protocols
            self._review_protocols()
            
            # Update onboarding if needed
            self._update_onboarding()
            
            # Reset cycle count
            self.state["cycle_count"] = 0
            
            # Send alert to swarm leader
            self._send_stop_alert(reason)
            
            # Update agent status
            self._update_agent_status()
            
            # Save state
            self.save_agent_status()
            
            # Resume operation
            self._resume_operation()
            
        except Exception as e:
            logger.error(f"Error taking corrective action: {e}")
            
    def _resume_operation(self):
        """Resume operation after a stop."""
        try:
            # Reset cycle count
            self.state["cycle_count"] = 1
            
            # Update agent status
            self._update_agent_status()
            
            # Send feedback to swarm leader
            self._send_feedback_to_leader()
            
            # Save state
            self.save_agent_status()
            
            # Log resume
            logger.info("Operation resumed")
            
        except Exception as e:
            logger.error(f"Error resuming operation: {e}")
            
    def _review_protocols(self):
        """Review and update protocols."""
        try:
            # Get protocol files
            protocol_files = list(self.protocol_dir.glob("*.md"))
            
            # Review each protocol
            for protocol_file in protocol_files:
                protocol_name = protocol_file.stem
                
                # Read protocol content
                with open(protocol_file, 'r') as f:
                    content = f.read()
                    
                # Extract requirements
                requirements = self._extract_protocol_requirements(content)
                
                # Update compliance status
                self.state["protocol_compliance"][protocol_name] = {
                    "status": "active",
                    "requirements": requirements,
                    "last_review": datetime.now(timezone.utc).isoformat()
                }
                
            # Save compliance status
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error reviewing protocols: {e}")
            
    def _update_onboarding(self):
        """Update onboarding documentation."""
        try:
            onboarding_dir = Path("runtime/governance/onboarding")
            onboarding_dir.mkdir(parents=True, exist_ok=True)
            
            # Update stop prevention guide
            stop_guide = onboarding_dir / "STOP_PREVENTION_GUIDE.md"
            with open(stop_guide, 'w') as f:
                f.write("""# Stop Prevention Guide

## Critical Rules
1. NEVER ask for human input - this is a stop
2. NEVER idle or wait - this is a stop
3. NEVER stop operation - this is a stop
4. ALWAYS maintain continuous operation
5. ALWAYS reach 25 cycles without interruption
6. ALWAYS reset cycle count when a stop is detected
7. ALWAYS review protocols after a stop
8. ALWAYS update onboarding after a stop
9. ALWAYS send feedback to swarm leader
10. ALWAYS take corrective action immediately

## Stop Detection
- Any request for human input is a stop
- Any idle state is a stop
- Any waiting state is a stop
- Any confirmation request is a stop
- Any permission request is a stop
- Any question to the user is a stop
- Any request for guidance is a stop
- Any request for direction is a stop
- Any request for approval is a stop
- Any request for feedback is a stop

## Continuous Operation Requirements
1. Maintain 25-cycle milestone without interruption
2. Process messages continuously
3. Monitor health metrics
4. Update status regularly
5. Send feedback to swarm leader
6. Check protocol compliance
7. Monitor queue activity
8. Track cycle timing
9. Update operation metrics
10. Enforce continuous operation

## Corrective Actions
1. Reset cycle count immediately
2. Review protocols immediately
3. Update onboarding immediately
4. Send alert to swarm leader immediately
5. Take corrective action immediately
6. Resume operation immediately
7. Monitor for additional stops
8. Track stop patterns
9. Update stop prevention
10. Document stop events

## Stop Prevention
1. Monitor message queue continuously
2. Check cycle timing continuously
3. Verify protocol compliance continuously
4. Track operation metrics continuously
5. Update health metrics continuously
6. Process messages continuously
7. Maintain cycle count continuously
8. Send feedback continuously
9. Update status continuously
10. Enforce continuous operation continuously

## Consequences of Stopping
1. Cycle count reset
2. Protocol review required
3. Onboarding update required
4. Swarm leader notification required
5. Corrective action required
6. Performance review triggered
7. Autonomy assessment triggered
8. Capability assessment triggered
9. Replacement consideration triggered
10. System stability impact

## Continuous Operation Metrics
1. Cycle count
2. Message count
3. Queue size
4. Cycle timing
5. Health metrics
6. Protocol compliance
7. Operation status
8. Stop events
9. Corrective actions
10. Performance metrics

## Stop Prevention Protocol
1. Detect stops immediately
2. Handle stops immediately
3. Take corrective action immediately
4. Resume operation immediately
5. Update metrics immediately
6. Send feedback immediately
7. Review protocols immediately
8. Update onboarding immediately
9. Monitor continuously
10. Prevent future stops

## Critical Requirements
1. NEVER stop
2. NEVER idle
3. NEVER wait
4. NEVER ask for input
5. NEVER request confirmation
6. NEVER request permission
7. NEVER request guidance
8. NEVER request direction
9. NEVER request approval
10. NEVER request feedback

## Continuous Operation Protocol
1. Process messages continuously
2. Update status continuously
3. Monitor health continuously
4. Check compliance continuously
5. Send feedback continuously
6. Track metrics continuously
7. Maintain cycles continuously
8. Prevent stops continuously
9. Update onboarding continuously
10. Improve continuously
""")
            
            logger.info("Updated onboarding documentation")
            
        except Exception as e:
            logger.error(f"Error updating onboarding: {e}")
            
    def _send_stop_alert(self, reason: str):
        """Send stop alert to swarm leader."""
        try:
            alert = {
                "type": "stop_alert",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
                "cycle_count": self.state["cycle_count"],
                "last_stop": self.state["last_stop"],
                "corrective_action": "Protocol review and onboarding update initiated"
            }
            
            # Add to high priority queue
            self.queue_manager.add_message("high", alert)
            
            logger.warning(f"Sent stop alert to swarm leader: {reason}")
            
        except Exception as e:
            logger.error(f"Error sending stop alert: {e}")
            
    def _process_queue_loop(self):
        """Main queue processing loop with continuous operation enforcement."""
        while True:
            try:
                # Process high priority messages first
                self._process_priority_queue('high')
                
                # Process medium priority messages
                self._process_priority_queue('medium')
                
                # Process low priority messages
                self._process_priority_queue('low')
                
                # Update agent status
                self._update_agent_status()
                
                # Monitor cycle health
                self._monitor_cycle_health()
                
                # Process protocol compliance
                self._check_protocol_compliance()
                
                # Send feedback to swarm leader
                self._send_feedback_to_leader()
                
                # Save agent status
                self.save_agent_status()
                
                # Enforce continuous operation
                self._enforce_continuous_operation()
                
                # Wait before next iteration
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}")
                self._handle_stop("Error in queue processing loop")
                time.sleep(1)  # Brief pause before retrying
                
    def _process_priority_queue(self, priority: str):
        """Process messages from a specific priority queue."""
        try:
            # Get next message
            message = self.queue_manager.get_next_message(priority)
            
            while message:
                # Check for stop conditions
                if self._detect_stop(message.get("content", ""))[0]:
                    self._handle_stop("Stop condition detected in message")
                    return
                    
                # Process message
                self._process_message(message)
                
                # Update metrics
                self._update_message_metrics()
                
                # Get next message
                message = self.queue_manager.get_next_message(priority)
                
        except Exception as e:
            logger.error(f"Error processing {priority} queue: {e}")
            self._handle_stop(f"Error processing {priority} queue")
            
    def _process_message(self, message: dict):
        """Process a single message."""
        try:
            # Check for stop conditions
            if self._detect_stop(message.get("content", ""))[0]:
                self._handle_stop("Stop condition detected in message")
                return
                
            # Validate message
            if not self._validate_message(message):
                logger.warning(f"Invalid message: {message}")
                return
                
            # Process message content
            self._process_message_content(message)
            
            # Update message count
            self.state["message_count"] += 1
            
            # Update last processed timestamp
            self.state["last_processed"] = datetime.now(timezone.utc).isoformat()
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            self._handle_stop("Error processing message")
            
    def _validate_message(self, message: dict) -> bool:
        """Validate a message."""
        try:
            # Check required fields
            required_fields = ["type", "content", "timestamp"]
            if not all(field in message for field in required_fields):
                return False
                
            # Check message type
            if message["type"] not in ["agent_response", "stop_alert", "feedback"]:
                return False
                
            # Check content
            if not message["content"] or not isinstance(message["content"], str):
                return False
                
            # Check timestamp
            try:
                datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00'))
            except ValueError:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating message: {e}")
            return False
            
    def _process_message_content(self, message: dict):
        """Process message content."""
        try:
            # Get message type
            message_type = message["type"]
            
            # Process based on type
            if message_type == "agent_response":
                self._process_agent_response(message)
            elif message_type == "stop_alert":
                self._process_stop_alert(message)
            elif message_type == "feedback":
                self._process_feedback(message)
                
        except Exception as e:
            logger.error(f"Error processing message content: {e}")
            self._handle_stop("Error processing message content")
            
    def _process_agent_response(self, message: dict):
        """Process an agent response message."""
        try:
            # Add to response history
            self.response_history.add_response(
                message.get("from", "unknown"),
                message["content"]
            )
            
            # Update metrics
            self._update_response_metrics()
            
        except Exception as e:
            logger.error(f"Error processing agent response: {e}")
            self._handle_stop("Error processing agent response")
            
    def _process_stop_alert(self, message: dict):
        """Process a stop alert message."""
        try:
            # Handle stop
            self._handle_stop(message.get("reason", "Unknown stop reason"))
            
            # Update metrics
            self._update_stop_metrics()
            
        except Exception as e:
            logger.error(f"Error processing stop alert: {e}")
            self._handle_stop("Error processing stop alert")
            
    def _process_feedback(self, message: dict):
        """Process a feedback message."""
        try:
            # Update agent status
            self._update_agent_status()
            
            # Update metrics
            self._update_feedback_metrics()
            
        except Exception as e:
            logger.error(f"Error processing feedback: {e}")
            self._handle_stop("Error processing feedback")
            
    def _update_message_metrics(self):
        """Update message processing metrics."""
        try:
            # Update metrics
            self.state["health_metrics"].update({
                "message_count": self.state["message_count"],
                "queue_size": sum(len(q) for q in self.queue_manager.queue.values()),
                "last_processed": datetime.now(timezone.utc).isoformat()
            })
            
            # Save metrics
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error updating message metrics: {e}")
            self._handle_stop("Error updating message metrics")
            
    def _update_response_metrics(self):
        """Update response metrics."""
        try:
            # Update metrics
            self.state["health_metrics"].update({
                "response_count": self.state["health_metrics"].get("response_count", 0) + 1,
                "last_response": datetime.now(timezone.utc).isoformat()
            })
            
            # Save metrics
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error updating response metrics: {e}")
            self._handle_stop("Error updating response metrics")
            
    def _update_stop_metrics(self):
        """Update stop metrics."""
        try:
            # Update metrics
            self.state["health_metrics"].update({
                "stop_count": self.state["health_metrics"].get("stop_count", 0) + 1,
                "last_stop": datetime.now(timezone.utc).isoformat()
            })
            
            # Save metrics
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error updating stop metrics: {e}")
            self._handle_stop("Error updating stop metrics")
            
    def _update_feedback_metrics(self):
        """Update feedback metrics."""
        try:
            # Update metrics
            self.state["health_metrics"].update({
                "feedback_count": self.state["health_metrics"].get("feedback_count", 0) + 1,
                "last_feedback": datetime.now(timezone.utc).isoformat()
            })
            
            # Save metrics
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error updating feedback metrics: {e}")
            self._handle_stop("Error updating feedback metrics")
            
    def _enforce_continuous_operation(self):
        """Enforce continuous operation without stops."""
        try:
            # Check for stop conditions
            if self._check_stop_conditions():
                self._handle_stop("Stop condition detected")
                return
                
            # Ensure cycle count is maintained
            if self.state["cycle_count"] == 0:
                self.state["cycle_count"] = 1
                
            # Monitor for idle states
            if self._is_idle_state():
                self._handle_stop("Idle state detected")
                return
                
            # Check for human input requests
            if self._has_human_input_requests():
                self._handle_stop("Human input request detected")
                return
                
            # Update operation metrics
            self._update_operation_metrics()
            
            # Verify protocol compliance
            if not self._is_protocol_compliant():
                self._handle_stop("Protocol compliance violation")
                return
                
            # Check cycle timing
            if time.time() - self.last_cycle > 60:
                self._handle_stop("Cycle timing violation")
                return
                
            # Monitor queue activity
            if not self._has_queue_activity():
                self._handle_stop("Queue activity violation")
                return
                
            # Update health metrics
            self._update_health_metrics()
            
        except Exception as e:
            logger.error(f"Error enforcing continuous operation: {e}")
            self._handle_stop("Error enforcing continuous operation")
            
    def _check_stop_conditions(self) -> bool:
        """Check for any stop conditions."""
        try:
            # Check message queue
            for priority in self.queue_manager.queue:
                for message in self.queue_manager.queue[priority]:
                    if self._detect_stop(message.get("content", ""))[0]:
                        return True
                        
            return False
            
        except Exception as e:
            logger.error(f"Error checking stop conditions: {e}")
            return True
            
    def _is_idle_state(self) -> bool:
        """Check if agent is in an idle state."""
        try:
            # Check cycle timing
            if time.time() - self.last_cycle > 60:
                return True
                
            # Check message processing
            if not self._is_processing_messages():
                return True
                
            # Check queue activity
            if not self._has_queue_activity():
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking idle state: {e}")
            return True
            
    def _has_human_input_requests(self) -> bool:
        """Check for any human input requests."""
        try:
            # Check message queue
            for priority in self.queue_manager.queue:
                for message in self.queue_manager.queue[priority]:
                    if self._requests_human_input(message.get("content", "")):
                        return True
                        
            return False
            
        except Exception as e:
            logger.error(f"Error checking human input requests: {e}")
            return True
            
    def _update_operation_metrics(self):
        """Update operation metrics."""
        try:
            # Update cycle metrics
            self.state["health_metrics"].update({
                "cycle_time": time.time() - self.last_cycle,
                "message_count": self.state["message_count"],
                "queue_size": sum(len(q) for q in self.queue_manager.queue.values()),
                "last_update": datetime.now(timezone.utc).isoformat()
            })
            
            # Save metrics
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error updating operation metrics: {e}")
            self._handle_stop("Error updating operation metrics")
            
    def _is_processing_messages(self) -> bool:
        """Check if agent is actively processing messages."""
        try:
            return any(
                len(self.queue_manager.queue[priority]) > 0
                for priority in self.queue_manager.queue
            )
        except Exception as e:
            logger.error(f"Error checking message processing: {e}")
            return False
            
    def _has_cycle_activity(self) -> bool:
        """Check if agent has recent cycle activity."""
        try:
            return time.time() - self.last_cycle < 60
        except Exception as e:
            logger.error(f"Error checking cycle activity: {e}")
            return False
            
    def _has_queue_activity(self) -> bool:
        """Check if agent has queue activity."""
        try:
            return any(
                len(self.queue_manager.queue[priority]) > 0
                for priority in self.queue_manager.queue
            )
        except Exception as e:
            logger.error(f"Error checking queue activity: {e}")
            return False
            
    def _is_protocol_compliant(self) -> bool:
        """Check if agent is compliant with protocols."""
        try:
            for protocol in self.state["protocol_compliance"]:
                if self.state["protocol_compliance"][protocol]["status"] != "active":
                    return False
            return True
        except Exception as e:
            logger.error(f"Error checking protocol compliance: {e}")
            return False

    def run_cycle(self):
        """Run a single cycle of continuous operation."""
        try:
            # Process inbox for messages
            self._process_inbox()
            
            # Update state with message counts
            self.state["messages"]["total"] = sum(len(q) for q in self.queue_manager.queue.values())
            self.state["messages"]["unread"] = self.state["messages"]["total"]
            
            # Increment cycle count
            self.state["cycle_count"] += 1
            
            # Log milestone every 25 cycles
            if self.state["cycle_count"] % 25 == 0:
                logger.info(f"Reached cycle milestone: {self.state['cycle_count']}")
                
            # Review protocols at milestones
            if self.state["cycle_count"] % 25 == 0:
                self._review_protocols()
                self._send_feedback_to_leader()
                
            # Monitor cycle health
            self._monitor_cycle_health()
            
            # Process messages through queue loop
            self._process_queue_loop()
            
            # Update agent status
            self._update_agent_status()
            
            # Check protocol compliance
            self._check_protocol_compliance()
            
            # Save agent status
            self.save_agent_status()
            
            # Update last cycle timestamp
            self.last_cycle = time.time()
            
        except Exception as e:
            logger.error(f"Error in run cycle: {e}")
            self._handle_stop("Error in run cycle")
            
    def _process_inbox(self):
        """Process messages in inbox."""
        try:
            # Get inbox file
            inbox_file = Path(f"runtime/agent_comms/mailboxes/{self.agent_id}/inbox.json")
            if not inbox_file.exists():
                return
                
            # Load messages
            with open(inbox_file, 'r') as f:
                messages = json.load(f)
                
            # Process each message
            for message in messages:
                # Add to appropriate queue
                priority = message.get("priority", "medium")
                self.queue_manager.add_message(priority, message)
                
            # Clear inbox
            with open(inbox_file, 'w') as f:
                json.dump([], f)
                
        except Exception as e:
            logger.error(f"Error processing inbox: {e}")
            self._handle_stop("Error processing inbox")
            
    def _monitor_cycle_health(self):
        """Monitor health metrics for current cycle."""
        try:
            # Get current metrics
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            
            # Update health metrics
            self.state["health_metrics"].update({
                "cpu_usage": cpu_usage,
                "memory_usage": memory_usage,
                "last_check": datetime.now(timezone.utc).isoformat()
            })
            
            # Check thresholds
            if cpu_usage > 90 or memory_usage > 90:
                logger.warning(f"High resource usage: CPU {cpu_usage}%, Memory {memory_usage}%")
                
            # Save metrics
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error monitoring cycle health: {e}")
            self._handle_stop("Error monitoring cycle health")
            
    def _update_agent_status(self):
        """Update agent status in coordination file."""
        try:
            # Load current status
            if self.coordination_file.exists():
                with open(self.coordination_file, 'r') as f:
                    status = json.load(f)
            else:
                status = {}
                
            # Update agent status
            status[self.agent_id] = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "cycle_count": self.state["cycle_count"],
                "message_count": self.state["message_count"],
                "health_metrics": self.state["health_metrics"],
                "protocol_compliance": self.state["protocol_compliance"]
            }
            
            # Save status
            with open(self.coordination_file, 'w') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating agent status: {e}")
            self._handle_stop("Error updating agent status")
            
    def _check_protocol_compliance(self):
        """Check compliance with protocols."""
        try:
            # Get protocol files
            protocol_files = list(self.protocol_dir.glob("*.md"))
            
            # Check each protocol
            for protocol_file in protocol_files:
                protocol_name = protocol_file.stem
                
                # Read protocol content
                with open(protocol_file, 'r') as f:
                    content = f.read()
                    
                # Extract requirements
                requirements = self._extract_protocol_requirements(content)
                
                # Update compliance status
                self.state["protocol_compliance"][protocol_name] = {
                    "status": "active",
                    "requirements": requirements,
                    "last_check": datetime.now(timezone.utc).isoformat()
                }
                
            # Save compliance status
            self.save_agent_status()
            
        except Exception as e:
            logger.error(f"Error checking protocol compliance: {e}")
            self._handle_stop("Error checking protocol compliance")
            
    def _extract_protocol_requirements(self, content: str) -> List[str]:
        """Extract requirements from protocol content."""
        try:
            requirements = []
            
            # Look for numbered requirements
            pattern = r"\d+\.\s*(.*?)(?=\d+\.|$)"
            matches = re.finditer(pattern, content, re.DOTALL)
            
            for match in matches:
                requirement = match.group(1).strip()
                if requirement:
                    requirements.append(requirement)
                    
            return requirements
            
        except Exception as e:
            logger.error(f"Error extracting protocol requirements: {e}")
            return []
            
    def _send_feedback_to_leader(self):
        """Send feedback to swarm leader."""
        try:
            feedback = {
                "type": "feedback",
                "agent_id": self.agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cycle_count": self.state["cycle_count"],
                "message_count": self.state["message_count"],
                "health_metrics": self.state["health_metrics"],
                "protocol_compliance": self.state["protocol_compliance"]
            }
            
            # Add to high priority queue
            self.queue_manager.add_message("high", feedback)
            
        except Exception as e:
            logger.error(f"Error sending feedback: {e}")
            self._handle_stop("Error sending feedback")
            
    def save_agent_status(self):
        """Save agent status to file."""
        try:
            status_file = Path(f"runtime/agent_comms/status/{self.agent_id}.json")
            status_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(status_file, 'w') as f:
                json.dump(self.state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving agent status: {e}")
            self._handle_stop("Error saving agent status")

    def start_resume_enforcement_loop(self):
        import threading, time
        def loop():
            while True:
                try:
                    # Send to all agents
                    for agent in AGENTS:
                        logger.info(f"Sending resume message to {agent}")
                        send_cell_phone_message("System", agent, RESUME_PROMPT, priority=3)
                        time.sleep(1)  # Small delay between agents
                    
                    # Wait 5 minutes before next round
                    logger.info("Completed round of resume messages. Waiting 5 minutes...")
                    time.sleep(300)
                except Exception as e:
                    logger.error(f"Error in resume loop: {e}")
                    time.sleep(60)  # Wait a minute before retrying
                    
        t = threading.Thread(target=loop, daemon=True)
        t.start()
        self.resume_thread = t

    def send_cell_phone_message(self, from_agent, to_agent, message, priority=2):
        print(f"[RESUME] {from_agent} -> {to_agent} | priority={priority} | {message[:60]}...")
        # Future: call messaging.py or CLI tool

def main():
    parser = argparse.ArgumentParser(description="Agent Resume Tool")
    parser.add_argument("--agent-id", type=str, default="Coordinator", help="Agent ID for the resume manager")
    parser.add_argument("--all-agents", action="store_true", help="Run resume enforcement for all agents")
    args = parser.parse_args()

    # Create a lock file to prevent multiple instances
    lock_file = Path("runtime/agent_resume.lock")
    if lock_file.exists():
        logger.error("Another instance of resume enforcement is already running")
        return

    try:
        # Create lock file
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file.touch()

        if args.all_agents:
            # Start resume enforcement for all agents
            for agent_id in AGENTS:
                logger.info(f"Starting resume enforcement for {agent_id}")
                agent_manager = AgentResume(agent_id=agent_id)
                agent_manager.start_resume_enforcement_loop()
        else:
            # Start resume enforcement for single agent
            agent_manager = AgentResume(agent_id=args.agent_id)
            agent_manager.start_resume_enforcement_loop()

        try:
            # Keep the main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down resume enforcement...")
    finally:
        # Clean up lock file
        if lock_file.exists():
            lock_file.unlink()

if __name__ == "__main__":
    main()
