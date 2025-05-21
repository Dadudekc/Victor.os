import os
import json
import gzip
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HistoryCompressor:
    def __init__(self, history_dir: str, retention_days: int = 30):
        self.history_dir = history_dir
        self.retention_days = retention_days
        self.current_file = os.path.join(history_dir, 'history.jsonl')
        self.compression_thread = None
        self.running = False

    def start(self):
        """Start the compression service in the background."""
        self.running = True
        self.compression_thread = threading.Thread(target=self._compression_loop)
        self.compression_thread.daemon = True
        self.compression_thread.start()
        logger.info("History compression service started.")

    def stop(self):
        """Stop the compression service."""
        self.running = False
        if self.compression_thread:
            self.compression_thread.join()
        logger.info("History compression service stopped.")

    def _compression_loop(self):
        """Background loop for scheduled compression operations."""
        while self.running:
            now = datetime.now()
            next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            time_to_sleep = (next_midnight - now).total_seconds()
            time.sleep(time_to_sleep)
            self.rotate_and_compress()

    def rotate_and_compress(self):
        """Rotate the current history file and compress it."""
        if not os.path.exists(self.current_file):
            logger.warning(f"No history file found at {self.current_file}")
            return

        date_str = datetime.now().strftime('%Y%m%d')
        archive_file = os.path.join(self.history_dir, f'history-{date_str}.jsonl.gz')

        try:
            with open(self.current_file, 'rb') as f_in:
                with gzip.open(archive_file, 'wb') as f_out:
                    f_out.writelines(f_in)
            os.remove(self.current_file)
            logger.info(f"History rotated and compressed to {archive_file}")
        except Exception as e:
            logger.error(f"Failed to rotate and compress history: {e}")

        self._cleanup_old_archives()

    def _cleanup_old_archives(self):
        """Remove archives older than the retention period."""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        for filename in os.listdir(self.history_dir):
            if filename.startswith('history-') and filename.endswith('.jsonl.gz'):
                try:
                    date_str = filename[8:16]  # Extract YYYYMMDD
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    if file_date < cutoff_date:
                        os.remove(os.path.join(self.history_dir, filename))
                        logger.info(f"Removed old archive: {filename}")
                except Exception as e:
                    logger.error(f"Failed to process archive {filename}: {e}")

class ResponseHistory:
    def __init__(self, history_dir: str, retention_days: int = 30):
        self.history_dir = history_dir
        self.current_file = os.path.join(history_dir, 'history.jsonl')
        self.compressor = HistoryCompressor(history_dir, retention_days)
        self.compressor.start()

    def __del__(self):
        """Clean shutdown of the compression service."""
        self.compressor.stop()

    def add_response(self, agent_id: str, response: Dict[str, Any]):
        """Add a response to the history."""
        os.makedirs(self.history_dir, exist_ok=True)
        with open(self.current_file, 'a') as f:
            json.dump({'agent_id': agent_id, 'timestamp': datetime.now().isoformat(), 'response': response}, f)
            f.write('\n')

    def get_responses(self, agent_id: Optional[str] = None, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get responses from the history, optionally filtered by agent and time."""
        responses = []
        if not os.path.exists(self.current_file):
            return responses

        with open(self.current_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if agent_id and entry['agent_id'] != agent_id:
                        continue
                    if since and entry['timestamp'] < since:
                        continue
                    responses.append(entry)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse history entry: {e}")

        return responses

if __name__ == "__main__":
    # Example usage
    history = ResponseHistory('runtime/history')
    history.add_response('Agent-1', {'status': 'ACTIVE', 'message': 'Hello, world!'})
    responses = history.get_responses(agent_id='Agent-1')
    print(responses) 