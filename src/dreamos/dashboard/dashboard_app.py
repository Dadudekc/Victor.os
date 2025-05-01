# src/dreamos/dashboard/dashboard_app.py
"""Minimal Flask web application to display Dream.OS agent statuses."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from flask import Flask, abort, render_template

# --- Configuration ---
# Determine project root relative to this file
# src/dreamos/dashboard/dashboard_app.py -> src/dreamos -> src -> ROOT
PROJECT_ROOT = Path(__file__).resolve().parents[3]
TASK_BOARD_PATH = PROJECT_ROOT / "runtime" / "task_board.json"

# Configure basic logging for the app
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("DashboardApp")

# --- Flask App Initialization ---
app = Flask(
    __name__,
    template_folder="templates",  # Explicitly set template folder relative to app
    # static_folder='static' # If needed later
)


# --- Helper Function ---
def read_task_board() -> dict:
    """Safely reads and parses the task_board.json file."""
    try:
        if not TASK_BOARD_PATH.exists():
            logger.error(f"Task board file not found at: {TASK_BOARD_PATH}")
            return {"error": "Task board file not found.", "agents": {}}

        # Read directly without locking for dashboard view
        with open(TASK_BOARD_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure basic structure
        if "agents" not in data:
            data["agents"] = {}
        return data
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from task board {TASK_BOARD_PATH}: {e}")
        return {"error": f"Task board JSON decode error: {e}", "agents": {}}
    except Exception as e:
        logger.error(f"Error reading task board {TASK_BOARD_PATH}: {e}", exc_info=True)
        return {"error": f"Failed to read task board: {e}", "agents": {}}


# --- Routes ---
@app.route("/")
def index():
    """Main route to display the agent status dashboard."""
    logger.info("Request received for dashboard.")
    board_data = read_task_board()
    agents = board_data.get("agents", {})
    last_updated = board_data.get("last_updated_utc", "N/A")
    read_error = board_data.get("error")

    # Prepare agents data for template (e.g., sort or add display logic)
    agent_list = []
    for agent_id, details in agents.items():
        details["agent_id"] = agent_id  # Ensure agent_id is in the dict
        agent_list.append(details)

    # Sort by agent ID for consistent display
    agent_list.sort(key=lambda x: x.get("agent_id", ""))

    current_time_utc = datetime.now(timezone.utc).isoformat(timespec="seconds") + "Z"

    return render_template(
        "dashboard.html",
        agents=agent_list,
        last_updated=last_updated,
        current_time=current_time_utc,
        read_error=read_error,
    )


# --- Main Execution (for development server) ---
if __name__ == "__main__":
    logger.info("Starting Flask development server for Dream.OS Dashboard.")
    # Note: host='0.0.0.0' makes it accessible on the network
    # Use debug=True only for development, disable for production
    app.run(host="127.0.0.1", port=8000, debug=True)
