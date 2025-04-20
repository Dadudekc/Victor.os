import sys
import os
import logging

# Add project root to path to mimic running main.py
project_root = os.path.dirname(__file__)
sys.path.insert(0, project_root)

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ImportCheck")

logger.info("Attempting to import DreamOSMainWindow...")
try:
    from ui.main_window import DreamOSMainWindow
    logger.info("Import successful!")
except Exception as e:
    logger.error(f"Import failed: {type(e).__name__} - {e}", exc_info=True)
    print(f"\n--- DETAILED TRACEBACK ---\n")
    import traceback
    traceback.print_exc()
    print(f"\n--- END TRACEBACK ---") 