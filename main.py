#!/usr/bin/env python3
"""Dream.OS Main Entry Point — Unified Gateway to GUI, Simulation, and Autonomous Execution."""

import sys
import os
import logging
import json
from pathlib import Path
from datetime import datetime
from enum import Enum, auto

# --- Core Imports (Placeholders - Ensure these paths are correct) ---
# Assuming imports might fail initially if core components aren't fully implemented yet
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import QTimer
    _qt_available = True
except ImportError:
    QApplication = None # Define dummy for type hinting if needed
    QTimer = None # Define dummy
    _qt_available = False

try:
    from ui.main_window import DreamOSMainWindow
    _main_window_available = True
except ImportError:
    DreamOSMainWindow = None # Define dummy
    _main_window_available = False

try:
    # These are needed for RUN_TASK mode
    from core.tools.registry import get_registry
    from core.agents.tool_executor_agent import ToolExecutionAgent
    _toolchain_available = True
except ImportError as e:
    # Log import error but allow other modes to potentially run
    logging.warning(f"⚠️ Toolchain components not available (required for --run-task): {e}")
    get_registry = None
    ToolExecutionAgent = None
    _toolchain_available = False


# --- Logging ---
# Ensure logs directory exists (handled by setup_environment, but good practice here too)
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / f"dream_os_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Configure logging to both console and file
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout) # Use stdout instead of default stderr
    ]
)
logger = logging.getLogger("DreamOS")

# --- Execution Modes ---
class StartupMode(Enum):
    GUI = auto()
    TEST = auto()
    RUN_TASK = auto()
    ERROR = auto() # Added error state

# --- Setup Directories ---
def setup_environment() -> bool:
    """Ensure required directories exist before launching Dream.OS."""
    try:
        root = Path(__file__).parent
        # Ensure core directories needed by different modes exist
        # Keep original list from test mode + runtime
        for sub in ["logs", "config", "memory", "runtime", "agent_directory", "templates", "prompts"]:
            (root / sub).mkdir(parents=True, exist_ok=True)
        logger.info("✅ Runtime environment initialized.")
        return True
    except Exception as e:
        logger.critical(f"❌ Failed to initialize runtime environment: {e}", exc_info=True)
        return False

# --- CLI Tool Chain Loop (Planner + Executor) ---
def run_tool_chain_loop(task_description: str):
    logger.info("🧠 Autonomous Execution Mode Enabled")
    logger.info(f"📌 Task: {task_description}")

    # Check if core components loaded
    if not _toolchain_available:
         logger.error("❌ Cannot run task: Core toolchain components (registry, executor agent) failed to import.")
         sys.exit(1)

    try:
        registry = get_registry()
        # Ensure planner tool exists in the registry
        planner_tool_name = "context_planner" # Or read from config?
        planner = registry.get_tool(planner_tool_name)
        if not planner:
             logger.error(f"❌ Planner tool '{planner_tool_name}' not found in registry.")
             sys.exit(1)
             
        executor = ToolExecutionAgent() # Assuming this can be instantiated directly

        logger.info("🛠 Generating execution plan...")
        # Ensure planner arguments match expectation
        plan_result = planner.execute(args={"task_description": task_description}) 
        
        # Validate plan result structure (adjust based on actual planner output)
        if not isinstance(plan_result, dict) or "plan" not in plan_result:
            logger.error(f"❌ Planner returned unexpected result format: {plan_result}")
            sys.exit(1)
            
        plan = plan_result.get("plan")
        if not plan: # Handles None or empty plan
            logger.error("❌ Planner failed to generate a valid plan.")
            sys.exit(1)
        
        logger.info(f"📊 Plan Generated: {plan}") # Log the plan itself for debugging

        logger.info("⚙️ Executing plan...")
        # Ensure executor arguments match expectation
        result = executor.execute_plan(plan=plan) 
        
        # Validate execution result structure (adjust based on actual executor output)
        if not isinstance(result, dict):
            logger.error(f"❌ Executor returned unexpected result format: {result}")
            sys.exit(1)

        status = result.get("status")
        if status == "success":
            print("\n" + "="*20 + " RESULT " + "="*20)
            print("✅ Task executed successfully.")
            final_context = result.get("final_context", {})
            if final_context:
                print("🧠 Final Context:")
                print(json.dumps(final_context, indent=2))
            else:
                 print("🧠 No final context provided by executor.")
            print("="*48)
        else:
            print("\n" + "="*20 + " FAILURE " + "="*19)
            print(f"❌ Execution failed at step {result.get('error_step', 'N/A')}: {result.get('error_message', 'No error message provided.')}")
            print("="*48)
            sys.exit(1)

    except Exception as e:
        logger.critical(f"❌ Error during tool chain execution: {e}", exc_info=True)
        sys.exit(1)

# --- GUI Bootstrapping ---
def launch_gui(test_mode: bool = False):
    
    # Check if GUI components are available
    if not _qt_available:
        logger.error("❌ Cannot launch GUI: PyQt5 failed to import.")
        sys.exit(1)
    if not _main_window_available:
        logger.error("❌ Cannot launch GUI: ui.main_window.DreamOSMainWindow failed to import.")
        sys.exit(1)
        
    app = QApplication(sys.argv)
    app.setApplicationName("Dream.OS")
    app.setApplicationVersion("1.0.2") # Incremented version
    app.setStyle("Fusion")

    logger.info("🎨 Launching GUI...")
    window = DreamOSMainWindow()

    if test_mode:
        logger.info("🧪 Running Test Mode Simulation via GUI stubs...")
        
        print("\n" + "="*20 + " TEST MODE " + "="*18)
        print("🧪 Simulating Agent Interactions via GUI Stubs...")

        print("\n📋 [Sim Interface Check]")
        print(f"  Tabs Found: {window.get_tab_names()}")

        test_task = {
            "id": f"task_test_{datetime.now().strftime('%H%M%S')}", # Shorter ID for test
            "task_type": "SIMULATION",
            "action": "RunTest",
            "target_agent": "TestRunner",
            "timestamp_created": datetime.now().isoformat(),
            "timestamp_updated": datetime.now().isoformat(),
            "name": "Autonomous Test Task",
            "description": "Generated via test mode.",
            "priority": "High",
            "status": "Pending",
            "params": {"mode": "test"},
            "result_summary": None,
            "error_message": None,
        }

        try:
            print("\n📝 [Sim Task Creation]")
            # Call the dummy task manager on the window instance
            window.task_manager.add_task(test_task) 
            print(f"  Task '{test_task['name']}' added via DummyTaskManager.")
            # Simulate syncing to board via window stub
            window.sync_event_with_board("task_add", test_task) 
            print("  Simulated sync_event_with_board('task_add', ...)")

            print("\n📊 [Sim Event Logging]")
            window.log_event("test_event", {"source": "test_mode", "time": datetime.now().isoformat()})
            print("  Simulated log_event(...)")

            print("\n💾 [Sim State Save]")
            window.save_state()
            print("  Simulated save_state(...)")

        except AttributeError as ae:
             logger.error(f"Simulation step failed: Missing method/attribute on DreamOSMainWindow - {ae}", exc_info=True)
             print(f"❌ Simulation step failed: {ae} (Check ui/main_window.py stubs)")
        except Exception as e:
            logger.warning(f"Simulation step encountered an error: {e}", exc_info=True)
            print(f"⚠️ Simulation step failed: {e}")
            
        print("\n✨ Test Simulation Sequence Completed.")
        print("Check runtime/structured_events.jsonl and task_list.json for results.")
        print("="*49 + "\n")

        # Close automatically after test
        # Use QTimer to allow event loop to start briefly before closing
        if QTimer: # Check if import succeeded
             QTimer.singleShot(100, app.quit) 
        else:
             logger.warning("QTimer not available, cannot auto-quit test mode GUI.")
             # Consider immediate exit if timer isn't available, 
             # though app.exec_() might handle it okay.
             # sys.exit(0) 
             
        app.exec_() # Start and immediately quit event loop (or wait for timer)
        sys.exit(0)

    window.show()
    sys.exit(app.exec_())

# --- Main Entry ---
def main():
    # --- Mode Detection ---
    args = sys.argv[1:] # Exclude script name
    mode = StartupMode.GUI # Default
    task_description = None
    
    # Basic argument parsing
    if "--test" in args:
        mode = StartupMode.TEST
        logger.info("Test mode requested.")
    elif "--run-task" in args:
        mode = StartupMode.RUN_TASK
        logger.info("Run task mode requested.")
        try:
            task_index = args.index("--run-task")
            if task_index + 1 < len(args):
                task_description = args[task_index + 1]
                # Simple check if next arg looks like another flag
                if task_description.startswith("--"):
                     logger.error("⚠️ '--run-task' provided but the next argument looks like another flag. Please provide a task description.")
                     mode = StartupMode.ERROR
                     task_description = None
            else:
                 logger.error("⚠️ '--run-task' provided without a task description.")
                 mode = StartupMode.ERROR
        except ValueError:
             # Should not happen if '--run-task' is in args, but safety check
             logger.error("Error parsing arguments for --run-task.")
             mode = StartupMode.ERROR
             
    elif len(args) > 0 and not args[0].startswith("--"):
         # Allow running task by just providing description as first arg? (Optional feature)
         # Example: python main.py "My task description"
         # mode = StartupMode.RUN_TASK
         # task_description = args[0]
         # logger.info("Run task mode inferred from first argument.")
         pass # Disabled for now, require explicit --run-task flag

    # --- Banner ---
    print("=" * 60)
    print("🚀 Dream.OS Initialization")
    print(f"📂 Working Dir: {os.getcwd()}")
    print(f"🧠 Mode: {mode.name}")
    if mode == StartupMode.RUN_TASK and task_description:
         print(f"📝 Task: \"{task_description[:50]}{'...' if len(task_description) > 50 else ''}\"")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print("=" * 60)
    
    # --- Exit on Error Mode ---
    if mode == StartupMode.ERROR:
         print("Exiting due to argument parsing error.")
         sys.exit(1)

    # --- Boot ---
    if not setup_environment():
        # Logger already logged the critical error in the function
        print("Startup failed: environment not initialized.")
        sys.exit(1)

    # --- Execution Dispatch ---
    if mode == StartupMode.GUI:
        launch_gui(test_mode=False)
    elif mode == StartupMode.TEST:
        launch_gui(test_mode=True)
    elif mode == StartupMode.RUN_TASK:
        if task_description:
            run_tool_chain_loop(task_description)
        else:
             # This case should be caught by argument parsing, but safeguard
             logger.error("Attempted to run task mode without a task description.")
             sys.exit(1)

if __name__ == "__main__":
    main() 