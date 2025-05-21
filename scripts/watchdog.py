"""
Watchdog script to ensure the cleanup directive broadcaster stays running.
"""

import subprocess
import time
import logging
import sys
import os
import signal
from pathlib import Path
import psutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scripts/watchdog.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Global state
running = True
current_process = None

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global running, current_process
    logger.info(f"Watchdog received signal {signum}. Initiating graceful shutdown...")
    running = False
    if current_process:
        try:
            current_process.terminate()
            current_process.wait(timeout=5)
        except:
            current_process.kill()

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def is_process_running(pid):
    """Check if a process is running."""
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False

def start_broadcaster():
    """Start the cleanup directive broadcaster."""
    global current_process
    try:
        script_dir = Path(__file__).parent
        broadcaster_script = script_dir / "cleanup_directive_broadcaster.py"
        
        # Kill any existing broadcaster processes
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'cleanup_directive_broadcaster.py' in ' '.join(proc.info['cmdline'] or []):
                    proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Start new process
        process = subprocess.Popen(
            [sys.executable, str(broadcaster_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True  # Run in new process group
        )
        
        current_process = process
        logger.info(f"Started cleanup directive broadcaster (PID: {process.pid})")
        return process
    except Exception as e:
        logger.error(f"Error starting broadcaster: {e}", exc_info=True)
        return None

def monitor_process(process):
    """Monitor a process and handle its output."""
    try:
        while running and process.poll() is None:
            # Check stdout
            stdout_line = process.stdout.readline()
            if stdout_line:
                logger.info(f"Broadcaster: {stdout_line.strip()}")
            
            # Check stderr
            stderr_line = process.stderr.readline()
            if stderr_line:
                logger.error(f"Broadcaster error: {stderr_line.strip()}")
            
            time.sleep(0.1)  # Prevent CPU spinning
            
        # Process ended
        stdout, stderr = process.communicate()
        if stdout:
            logger.info(f"Broadcaster final output: {stdout}")
        if stderr:
            logger.error(f"Broadcaster final error: {stderr}")
        
        return process.returncode
    except Exception as e:
        logger.error(f"Error monitoring process: {e}", exc_info=True)
        return -1

def main():
    """Main watchdog loop."""
    logger.info("Starting watchdog for cleanup directive broadcaster")
    consecutive_failures = 0
    max_failures = 5
    backoff_time = 60  # Start with 60 seconds
    
    while running:
        try:
            # Start the broadcaster
            process = start_broadcaster()
            if not process:
                consecutive_failures += 1
                backoff_time = min(backoff_time * 2, 3600)  # Max 1 hour
                logger.error(f"Failed to start broadcaster. Retrying in {backoff_time} seconds... (Failure {consecutive_failures}/{max_failures})")
                time.sleep(backoff_time)
                continue
            
            # Reset failure counter on successful start
            consecutive_failures = 0
            backoff_time = 60
            
            # Monitor the process
            return_code = monitor_process(process)
            
            if return_code != 0:
                logger.warning(f"Broadcaster process ended with code {return_code}. Restarting...")
            else:
                logger.info("Broadcaster process ended normally. Restarting...")
            
            # Small delay before restart
            time.sleep(5)
            
        except KeyboardInterrupt:
            logger.info("Watchdog received keyboard interrupt. Shutting down...")
            break
        except Exception as e:
            logger.error(f"Watchdog error: {e}", exc_info=True)
            consecutive_failures += 1
            if consecutive_failures >= max_failures:
                logger.critical(f"Too many consecutive failures ({consecutive_failures}). Shutting down watchdog.")
                break
            time.sleep(backoff_time)
    
    logger.info("Watchdog shutting down...")
    if current_process:
        try:
            current_process.terminate()
            current_process.wait(timeout=5)
        except:
            current_process.kill()

if __name__ == "__main__":
    main() 