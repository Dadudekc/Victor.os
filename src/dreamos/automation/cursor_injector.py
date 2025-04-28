# src/dreamos/automation/cursor_injector.py
import pyautogui
import time
import os
import logging
import json
import random
from pathlib import Path
from typing import Dict, Optional, Tuple

# Attempt to import pyperclip for pasting, but make it optional
try:
    import pyperclip
    PYPERCLIPBOARD_AVAILABLE = True
except ImportError:
    PYPERCLIPBOARD_AVAILABLE = False
    logging.warning("pyperclip not found. Pasting disabled, will use typing (slower).")

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_COORDS_PATH = Path("config/cursor_agent_coords.json")
DEFAULT_QUEUE_PATH = Path("runtime/cursor_queue")
DEFAULT_PROCESSED_PATH = Path("runtime/cursor_processed")
MIN_PAUSE = 0.10  # Minimum pause between pyautogui actions
MAX_PAUSE = 0.25  # Maximum pause

# --- Configuration Loading ---

def load_agent_coordinates(config_path: Path = DEFAULT_COORDS_PATH) -> Optional[Dict[str, Tuple[int, int]]]:
    """Loads agent ID to screen coordinate mapping from a JSON file."""
    if not config_path.exists():
        logger.error(f"Agent coordinates file not found: {config_path}")
        return None
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Convert loaded dict values {"x": N, "y": M} to tuples (N, M)
        coordinates = {agent_id: (coords['x'], coords['y'])
                       for agent_id, coords in data.items()
                       if isinstance(coords, dict) and 'x' in coords and 'y' in coords}
        if len(coordinates) != len(data):
            logger.warning(f"Some entries in {config_path} were malformed.")
        logger.info(f"Loaded coordinates for {len(coordinates)} agents from {config_path}")
        return coordinates
    except json.JSONDecodeError:
        logger.error(f"Error decoding JSON from {config_path}")
        return None
    except Exception as e:
        logger.error(f"Error loading agent coordinates from {config_path}: {e}", exc_info=True)
        return None

# --- Queue Management ---

def get_next_prompt(agent_id: str, queue_base: Path = DEFAULT_QUEUE_PATH) -> Optional[Tuple[str, Path]]:
    """Gets the text and path of the next prompt file for an agent."""
    agent_queue_dir = queue_base / agent_id
    if not agent_queue_dir.is_dir():
        # logger.debug(f"Queue directory not found for {agent_id}: {agent_queue_dir}")
        return None

    try:
        # Get the oldest file based on name (e.g., timestamp prefix)
        prompt_files = sorted([f for f in agent_queue_dir.iterdir() if f.is_file()])
        if not prompt_files:
            return None

        next_prompt_file = prompt_files[0]
        prompt_text = next_prompt_file.read_text(encoding='utf-8')
        return prompt_text, next_prompt_file
    except Exception as e:
        logger.error(f"Error reading prompt queue for {agent_id}: {e}", exc_info=True)
        return None

def mark_prompt_processed(prompt_file_path: Path, processed_base: Path = DEFAULT_PROCESSED_PATH):
    """Moves a processed prompt file to the processed directory."""
    try:
        agent_id = prompt_file_path.parent.name
        processed_dir = processed_base / agent_id
        processed_dir.mkdir(parents=True, exist_ok=True)
        target_path = processed_dir / prompt_file_path.name
        prompt_file_path.rename(target_path)
        logger.debug(f"Moved {prompt_file_path.name} to {target_path}")
    except Exception as e:
        logger.error(f"Error moving processed prompt {prompt_file_path}: {e}", exc_info=True)

# --- Core Injection Logic ---

def inject_prompt(
    agent_id: str,
    prompt_text: str,
    coordinates: Dict[str, Tuple[int, int]],
    use_paste: bool = True,
    random_offset: int = 3 # Max pixels to offset click randomly
) -> bool:
    """Injects a single prompt into the target agent's Cursor window."""
    target_coords = coordinates.get(agent_id)
    if not target_coords:
        logger.error(f"No coordinates found for agent {agent_id}. Skipping prompt injection.")
        return False

    target_x, target_y = target_coords
    # Apply optional random offset
    if random_offset > 0:
        offset_x = random.randint(-random_offset, random_offset)
        offset_y = random.randint(-random_offset, random_offset)
        target_x += offset_x
        target_y += offset_y

    logger.info(f"Injecting prompt for {agent_id} at ({target_x}, {target_y})..." )

    try:
        # 1. Move mouse to target
        pyautogui.moveTo(target_x, target_y, duration=random.uniform(0.1, 0.3))
        time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))

        # 2. Click to focus
        pyautogui.click(x=target_x, y=target_y)
        time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE)) # Pause after click for focus

        # 3. Clear field (optional but recommended) - Simulate Ctrl+A, Delete
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(random.uniform(MIN_PAUSE/2, MAX_PAUSE/2))
        pyautogui.press('delete')
        time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))

        # 4. Insert prompt (Paste or Type)
        if use_paste and PYPERCLIPBOARD_AVAILABLE:
            try:
                pyperclip.copy(prompt_text)
                time.sleep(random.uniform(MIN_PAUSE/2, MAX_PAUSE/2)) # Small pause for clipboard
                pyautogui.hotkey('ctrl', 'v')
                logger.debug(f"Pasted prompt for {agent_id}.")
            except Exception as paste_err:
                logger.warning(f"Pasting failed for {agent_id}, falling back to typing: {paste_err}")
                pyautogui.write(prompt_text, interval=random.uniform(0.01, 0.03)) # Type slowly
        else:
            logger.debug(f"Typing prompt for {agent_id}...")
            pyautogui.write(prompt_text, interval=random.uniform(0.01, 0.03)) # Type slowly

        time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE))

        # 5. Press Enter
        pyautogui.press('enter')
        logger.info(f"Prompt submitted for {agent_id}.")
        time.sleep(random.uniform(MIN_PAUSE, MAX_PAUSE)) # Small pause after enter

        return True

    except Exception as e:
        logger.error(f"PyAutoGUI error during injection for {agent_id}: {e}", exc_info=True)
        # Consider adding pyautogui.FailSafeException handling if needed
        return False

# --- Main Loop ---

def run_injection_loop(
    agent_ids: Optional[list[str]] = None,
    coords_path: Path = DEFAULT_COORDS_PATH,
    queue_path: Path = DEFAULT_QUEUE_PATH,
    processed_path: Path = DEFAULT_PROCESSED_PATH,
    cycle_pause: float = 1.0 # Seconds to pause between checking all agents
    ):
    """Continuously checks agent queues and injects prompts."""
    coordinates = load_agent_coordinates(coords_path)
    if not coordinates:
        logger.critical("Failed to load agent coordinates. Exiting injection loop.")
        return

    if agent_ids is None:
        # Use all agents found in the coordinates file if none specified
        agent_ids = list(coordinates.keys())
        logger.info(f"Monitoring agents: {', '.join(agent_ids)}")

    logger.info("Starting Cursor prompt injection loop...")
    while True: # Loop indefinitely
        prompts_processed_this_cycle = 0
        for agent_id in agent_ids:
            prompt_info = get_next_prompt(agent_id, queue_path)
            if prompt_info:
                prompt_text, prompt_file = prompt_info
                logger.info(f"Found prompt for {agent_id}: {prompt_file.name}")
                success = inject_prompt(agent_id, prompt_text, coordinates)
                if success:
                    mark_prompt_processed(prompt_file, processed_path)
                    prompts_processed_this_cycle += 1
                else:
                    logger.error(f"Failed to inject prompt for {agent_id}. File remains in queue: {prompt_file.name}")
                    # Optional: Add retry logic or move to an error queue here
            # else: No prompt found for this agent

        if prompts_processed_this_cycle == 0:
            logger.debug(f"No prompts found in queues this cycle. Pausing for {cycle_pause}s.")
            time.sleep(cycle_pause)
        else:
            logger.info(f"Processed {prompts_processed_this_cycle} prompts this cycle.")
            # Optional: Shorter pause if prompts were just processed
            time.sleep(max(0.1, cycle_pause / 5))


if __name__ == '__main__':
    # Example of running the loop directly
    # Configure logging
    log_format = "%(asctime)s - %(levelname)-8s - %(name)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_format)

    # Ensure queue/processed directories exist for testing
    test_agents = ['agent_01', 'agent_02']
    for aid in test_agents:
        (DEFAULT_QUEUE_PATH / aid).mkdir(parents=True, exist_ok=True)
        # Create dummy prompt file for agent_01
        if aid == 'agent_01':
             (DEFAULT_QUEUE_PATH / aid / "001_test_prompt.txt").write_text("This is a test prompt for agent_01 from main.", encoding='utf-8')

    print("Starting example injection loop (runs indefinitely)... Press Ctrl+C to stop.")
    # Assumes config/cursor_agent_coords.json exists with coords for agent_01, agent_02
    try:
        run_injection_loop(agent_ids=test_agents)
    except KeyboardInterrupt:
        print("\nInjection loop stopped by user.") 