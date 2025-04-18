#!/usr/bin/env python3
"""Dream.OS Main Entry Point."""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime # Keep for test mode task ID

from PyQt5.QtWidgets import QApplication
# Removed QIcon import as it wasn't used in the simplified setup

# Import the *new* main window
from ui.main_window import DreamOSMainWindow 

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_environment():
    """Ensure basic directories exist."""
    try:
        root_dir = Path(__file__).parent
        # Keep original list if needed by other parts, add runtime
        dirs = [
            root_dir / "agent_directory", # Keep if used elsewhere
            root_dir / "logs",
            root_dir / "config",
            root_dir / "memory", # Keep if used elsewhere
            root_dir / "runtime" 
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
        logger.info("Basic environment directories verified/created.")
        return True
    except Exception as e:
        print(f"Error setting up environment: {e}", file=sys.stderr)
        logger.error(f"Error setting up environment: {e}", exc_info=True)
        return False

def main(test_mode=False):
    """Main application entry point."""
    try:
        # Setup environment FIRST
        if not setup_environment():
             logger.critical("❌ Critical error during initial environment setup. Exiting.")
             sys.exit(1)

        # Enable debug logging if DEBUG environment variable is set
        if os.getenv("DEBUG"):
            logging.getLogger().setLevel(logging.DEBUG) # Set root logger level
            logger.info("🔍 Debug mode enabled - verbose logging active")

        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName("Dream.OS")
        app.setApplicationVersion("1.0.1") # Increment version slightly

        # Set application style (optional)
        app.setStyle("Fusion")

        # Create main window (using the new stub implementation)
        logger.info("Initializing DreamOSMainWindow...")
        window = DreamOSMainWindow() 
        logger.info("✓ DreamOSMainWindow initialized.")
        
        if test_mode:
            logger.info("🧪 Running in Test & Simulation Mode (--test)")
            # --- Execute the test sequence from the original main.py --- 
            # It will now call the stub methods in the new DreamOSMainWindow
            print("🧪 Running Autonomous Test Sequence & Agentic Coordination Kickoff...")
            
            # Test 1: Agent Interface - Tab System Check
            print("📋 [Agent Test] Verifying Core Interface (Tab System):")
            tab_names = window.get_tab_names()
            if tab_names:
                 for tab_name in tab_names:
                    print(f"  ✓ Found interface component: {tab_name}")
            else:
                print("  ⚠️ No tabs found in the main window.")
            
            # Test 2: Agent Action - Task Management & Logging
            print("📝 [Agent Test] Simulating Task Creation & Logging:")
            test_task = {
                "id": f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "name": "Autonomous Test Task",
                "description": "Task created during automated agentic simulation.",
                "priority": "High",
                "status": "Pending"
            }
            try:
                # Access the dummy task manager directly
                window.task_manager.add_task(test_task)
                print(f"  ✓ Task '{test_task['name']}' added via (Dummy) Task Manager.")
                # Simulate logging to a central task board via window stub
                print(f"  📡 Syncing Task {test_task['id']} with Central Agent Board...") 
                window.sync_event_with_board("task_add", test_task)
            except Exception as e:
                print(f"  ❌ Failed to add or log task: {e}")

            # Test 3: Agent Perception - Event Logging & Mailbox Update
            print("📊 [Agent Test] Simulating Event Perception & Mailbox Update:")
            event_name = "agent_simulation_event"
            event_data = {"timestamp": datetime.now().isoformat(), "source": "main.py test"}
            try:
                # Call the window stub method
                window.log_event(event_name, event_data)
                print(f"  ✓ Event '{event_name}' logged via window stub.")
            except Exception as e:
                print(f"  ❌ Failed to log event or notify mailbox: {e}")

            # Test 4: Agent State - Persistence & Board Sync
            print("💾 [Agent Test] Simulating State Persistence & Board Sync:")
            try:
                # Call the window stub method
                window.save_state()
                print("  ✓ Local agent state saved via window stub.")
            except Exception as e:
                print(f"  ❌ Failed to save state or sync with board: {e}")

            print("✨ Autonomous Test Sequence Completed!")
            
            # Cleanup
            print("🧹 Cleaning up resources...")
            window.close() # Calls the closeEvent -> cleanup_resources stub
            print("✓ Resources released (via stub)." )
            # Exit after test mode
            sys.exit(0)
            # --- End Test Sequence ---
            
        # Normal Mode: Show the GUI
        logger.info("🚀 Launching Dream.OS GUI...")
        window.show()
        
        # Start event loop
        exit_code = app.exec_()
        logger.info(f"Application exited with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        critical_error_msg = f"❌ CRITICAL ERROR in main execution: {e}"
        print(critical_error_msg, file=sys.stderr)
        # Use logger if available
        try: 
            logger.critical(critical_error_msg, exc_info=True)
        except NameError:
             pass # logger wasn't initialized if setup_environment failed early
        sys.exit(1)

if __name__ == "__main__":
    """
    Dream.OS: Main entry point
    --------------------------
    Launches the main application window or runs a test sequence.
    
    Running Modes:
    -------------
    1. Normal Mode (GUI):
       ```bash
       python main.py
       ```
       Launches the Dream.OS graphical user interface.
    
    2. Test & Simulation Mode:
       ```bash
       python main.py --test
       ```
       Executes an automated sequence simulating agent actions and coordination
       by calling stub methods on the main window.
    
    3. Debug Mode (Verbose Logging):
       ```bash
       # Windows: set DEBUG=1 && python main.py [--test]
       # Unix/Mac:  DEBUG=1 python main.py [--test]
       ```
       Enables detailed logging for deeper analysis.
    """
    
    # Parse command line arguments
    test_mode = "--test" in sys.argv
    
    # Display startup banner (basic logging should be configured now)
    print("=" * 60)
    print("🚀 Initializing Dream.OS Entry Point")
    print(f"📂 Working Directory: {os.getcwd()}")
    print(f"🔧 Python Version: {sys.version.split()[0]}")
    # Removed Qt version check to simplify startup
    print(f"🔬 Mode: {'Agentic Simulation (--test)' if test_mode else 'Normal GUI'}")
    print("=" * 60)
    
    # Launch application in the chosen mode
    main(test_mode=test_mode) 