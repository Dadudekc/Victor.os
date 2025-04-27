"""
Minimal isolated test of the context planner and execution agent.
No file I/O. Just symbolic plan validation.
"""

import json
import logging # Added for potential debugging

# Ensure core modules are importable (best effort)
import sys
import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Setup logging minimally for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger("_InternalTestLoop")

try:
    from dreamos.tools.registry import get_registry
    from dreamos.agents.tool_executor_agent import ToolExecutionAgent
    logger.info("Core components imported successfully.")
except ImportError as e:
    logger.error(f"Failed to import core components: {e}", exc_info=True)
    # Attempt to add parent directory to path if core isn't found
    try:
        parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '.'))
        if parent_dir not in sys.path:
            logger.info(f"Adding {parent_dir} to sys.path")
            sys.path.insert(0, parent_dir)
        from dreamos.tools.registry import get_registry
        from dreamos.agents.tool_executor_agent import ToolExecutionAgent
        logger.info("Core components imported successfully after path adjustment.")
    except ImportError as e2:
        logger.error(f"Still failed to import core components after path adjustment: {e2}", exc_info=True)
        sys.exit(1) # Exit if core components cannot be loaded

print("\n🔍 Starting minimal toolchain test...")

# -- Step 1: Define symbolic test task
task_description = "Analyze the `PromptCycleManager` class in `core/engine/prompt_cycle.py`."

# -- Step 2: Plan using ContextPlannerTool
logger.info("Getting context_planner tool...")
planner = get_registry().get_tool("context_planner")
if not planner:
    logger.error("ContextPlannerTool not found.")
    sys.exit(1)

logger.info(f"Generating plan for task: {task_description}")
plan_result = planner.execute({"task_description": task_description})
plan = plan_result.get("plan", [])

print("\n📐 Generated Plan:")
print(json.dumps(plan, indent=2))

# -- Step 3: Patch plan to avoid real file I/O
logger.info("Filtering plan to remove file-dependent steps...")
filtered_plan = [step for step in plan if step["action"] != "read_file"]

for step in filtered_plan:
    if step["action"] == "grep_search":
        # Redirect to a safe dummy dir (current dir for this test)
        step["params"]["target_directory"] = "."
        logger.info(f"Adjusted grep_search target directory for step: {step.get('description')}")

print("\n🛠️ Adjusted Plan for safe microexecution:")
print(json.dumps(filtered_plan, indent=2))

# -- Step 4: Execute plan using ToolExecutionAgent
logger.info("Executing adjusted plan...")
executor = ToolExecutionAgent()
execution_result = executor.execute_plan(filtered_plan)

print("\n🚀 Execution Result:")
print(json.dumps(execution_result, indent=2))

logger.info("Minimal toolchain test finished.") 
