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
    from core.tools.functional.context_planner_tool import ContextPlannerTool
    _toolchain_available = True
except ImportError as e:
    # Log import error but allow other modes to potentially run
    logging.warning(f"⚠️ Toolchain components not available (required for --run-task): {e}")
    get_registry = None
    ToolExecutionAgent = None
    ContextPlannerTool = None # Ensure planner is None if import fails
    _toolchain_available = False


# --- Logging (Simplified for GUI launch test) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Temporarily remove FileHandler
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
    if not _toolchain_available or not get_registry or not ToolExecutionAgent or not ContextPlannerTool:
         logger.error("❌ Cannot run task: Core toolchain components failed to import.")
         sys.exit(1)

    try:
        # Get the populated tool registry
        registry = get_registry()
        
        # Get the planner tool from the registry
        planner_tool_name = "context_planner"
        planner = registry.get_tool(planner_tool_name)
        if not planner:
             # This check might be redundant if ContextPlannerTool import succeeded, but good practice
             logger.error(f"❌ Planner tool '{planner_tool_name}' not found in registry.")
             sys.exit(1)
             
        # Instantiate the real ToolExecutionAgent (it gets registry internally)
        executor = ToolExecutionAgent() 

        logger.info("🛠 Generating execution plan...")
        plan_result = planner.execute(args={"task_description": task_description}, context={}) 
        
        # --- Display Narration & Log Versioned Plan --- 
        if not isinstance(plan_result, dict) or "plan" not in plan_result or "plan_narration" not in plan_result:
            logger.error(f"❌ Planner returned unexpected result format (missing plan/narration): {plan_result}")
            sys.exit(1)
            
        plan = plan_result.get("plan")
        plan_narration = plan_result.get("plan_narration", "(No narration provided)")
        plan_version = plan_result.get("plan_version", "N/A")

        # Log the full plan structure for traceability
        try:
             # Use default=str to handle non-serializable objects if any appear in future
             plan_json = json.dumps(plan_result, indent=2, default=str) 
             logger.info(f"📄 Plan Generated (v{plan_version}):\n{plan_json}")
        except Exception as json_e:
             logger.error(f"Failed to serialize plan result to JSON: {json_e}")
             logger.info(f"Raw Plan Result: {plan_result}") # Log raw on failure

        # Validate plan list format (as before)
        if not isinstance(plan, list):
            logger.error(f"❌ Planner failed to generate a valid list-based plan. Plan type: {type(plan)}.")
            sys.exit(1)
        
        # Print narration for the user
        print("\n" + "-"*10 + " Proposed Plan " + "-"*10)
        print(plan_narration)
        print("-"*35 + "\n")
        # --- End Narration/Logging Enhancements ---

        if not plan:
            logger.info("ℹ️ Planner generated an empty plan. No actions to execute.")
            # Exit gracefully for empty plan
            print("✅ Task requires no actions.")
            sys.exit(0)
        
        # --- Execute the plan using the real executor --- 
        # Optional: Add a small delay or prompt before execution?
        # time.sleep(2)
        logger.info("⚙️ Executing plan...")
        result = executor.execute_plan(plan=plan)
        # --- End execution --- 
        
        # Process results (existing logic seems compatible)
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