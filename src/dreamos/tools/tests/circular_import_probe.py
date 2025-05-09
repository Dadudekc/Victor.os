# Minimal reproduction harness to test AppConfig / Orchestrator imports
from dreamos.utils.import_debugger import try_import

AppConfig = try_import(
    lambda: __import__("dreamos.core.config", fromlist=["AppConfig"]).AppConfig,
    label="test_orchestrator -> AppConfig"
)

CursorOrchestrator = try_import(
    lambda: __import__("dreamos.automation.cursor_orchestrator", fromlist=["CursorOrchestrator"]).CursorOrchestrator,
    label="test_orchestrator -> CursorOrchestrator"
)

if __name__ == "__main__":
    print("Attempting to instantiate CursorOrchestrator...")
    # TODO: AppConfig might need arguments or a load method if it doesn't have a default __init__
    # For now, assuming a default constructor or that a potential error here is part of the debugging.
    config = AppConfig() 
    orchestrator = CursorOrchestrator(config=config)
    print("Success.") 