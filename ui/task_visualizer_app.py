import streamlit as st
import pandas as pd
import json
from pathlib import Path
import time
import logging
import sys
import os # Added os import

# Configure logging for the visualizer
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TaskVisualizerApp")

# --- Configuration ---
# Assume task_list.json is in the project root relative to this script
project_root = Path(__file__).parent.parent
TASK_LIST_PATH = project_root / "task_list.json"
REFRESH_INTERVAL_SECONDS = 5 # How often to refresh the data

def read_tasks_from_json(file_path: Path) -> list:
    """Reads tasks directly from a JSON file."""
    if not file_path.exists():
        logger.warning(f"Task file not found: {file_path}")
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip(): # Check if file is empty
                 logger.info(f"Task file is empty: {file_path}")
                 return []
            tasks = json.loads(content)
        # Ensure it's a list
        return tasks if isinstance(tasks, list) else []
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {e}")
        st.error(f"Error reading task file (invalid JSON): {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error reading task file {file_path}: {e}", exc_info=True)
        st.error(f"Error reading task file: {e}")
        return []

def load_task_data(file_path: Path) -> pd.DataFrame:
    """Loads task data from task_list.json into a Pandas DataFrame."""
    tasks = read_tasks_from_json(file_path) # Use direct JSON read
    
    # Define expected columns (adjust based on actual task structure)
    expected_cols = [
        'task_id', 'status', 'task_type', 'action', 'target_agent', 
        'timestamp_created', 'timestamp_updated', 'result_summary', 'error_message', 'params'
    ]
    display_cols = [
        'task_id', 'status', 'task_type', 'action', 'target_agent', 
        'timestamp_created', 'timestamp_updated', 'result_summary', 'error_message'
    ]

    if not tasks:
        # Return empty dataframe with expected columns if file is empty or read fails
        return pd.DataFrame(columns=display_cols)
        
    try:
        # Convert list of dicts to DataFrame
        df = pd.DataFrame(tasks)
        
        # Ensure all expected columns exist, fill missing with None or default
        for col in expected_cols:
            if col not in df.columns:
                df[col] = None
        
        # Select and order columns for display
        df_display = df[display_cols].copy() # Use copy to avoid SettingWithCopyWarning
        
        # Basic type conversion/handling for display
        for col in ['timestamp_created', 'timestamp_updated']:
             if col in df_display.columns:
                 # Attempt conversion, fill errors with NaT (Not a Time)
                 df_display[col] = pd.to_datetime(df_display[col], errors='coerce')
                 # Format valid datetimes, keep NaT as is (will become N/A later)
                 df_display[col] = df_display[col].dt.strftime('%Y-%m-%d %H:%M:%S')

        df_display = df_display.fillna('N/A') # Replace NaNs/NaTs for display
        
        # Sort by creation time if column exists and has valid data
        if 'timestamp_created' in df_display.columns and not pd.api.types.is_string_dtype(df_display['timestamp_created']):
             # Need to convert back to datetime for sorting if it was string formatted
             # Simplified: sort by index if timestamp fails
             try:
                  df_display['_sort_ts'] = pd.to_datetime(df[df['timestamp_created'].notna()]['timestamp_created'], errors='coerce')
                  df_display = df_display.sort_values(by='_sort_ts', ascending=False).drop(columns=['_sort_ts'])
             except Exception:
                 logger.warning("Could not sort by timestamp_created, using default order.")
        else:
             # Sort by index (implicitly newest if appended)
             pass # Keep default order

        return df_display
    except Exception as e:
        logger.error(f"Error processing task data into DataFrame: {e}", exc_info=True)
        st.error(f"Error processing task data: {e}")
        # Return empty dataframe on processing error
        return pd.DataFrame(columns=display_cols)

# --- Streamlit App Layout ---
st.set_page_config(page_title="Dream.OS Task Visualizer", layout="wide")

st.title("Dream.OS Task Visualizer")
st.caption(f"Monitoring task list: {TASK_LIST_PATH.relative_to(project_root)}")

# Placeholder for the data display
data_placeholder = st.empty()

# --- Main Loop for Refreshing Data (disabled during import) ---
while False:
    try:
        logger.debug("Loading task data...")
        df_tasks = load_task_data(TASK_LIST_PATH)
        
        # Update the placeholder with the new data
        with data_placeholder.container():
            st.subheader("Current Tasks")
            if df_tasks.empty:
                st.info("No tasks found or task file is empty/invalid.")
            else:
                st.dataframe(df_tasks, use_container_width=True)
            
            st.caption(f"Last refreshed: {time.strftime('%Y-%m-%d %H:%M:%S')}. Refreshes every {REFRESH_INTERVAL_SECONDS} seconds.")
            
    except Exception as e:
        logger.error(f"Error during data refresh loop: {e}", exc_info=True)
        with data_placeholder.container():
             st.error(f"An error occurred during refresh: {e}")

    # Wait for the next refresh cycle
    time.sleep(REFRESH_INTERVAL_SECONDS)
    # Loop disabled 