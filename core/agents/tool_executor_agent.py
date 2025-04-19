"""Agent responsible for executing a plan consisting of tool calls."""
import logging
from typing import List, Dict, Any

# Import the registry getter
from core.tools.registry import get_registry

logger = logging.getLogger(__name__)

class ToolExecutionAgent:
    """Executes a plan (list of tool call steps) sequentially."""

    def __init__(self):
        self.registry = get_registry()
        logger.info("ToolExecutionAgent initialized.")

    def execute_plan(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Executes a list of tool call steps.

        Args:
            plan (List[Dict[str, Any]]): A list where each dict represents a step,
                                         e.g., {'tool': 'tool_name', 'args': {...}}

        Returns:
            Dict[str, Any]: A dictionary containing the execution status,
                            final context (results of steps), and error info if any.
                            e.g., {
                                'status': 'success' | 'failure',
                                'final_context': { 'step_0_result': ..., 'step_1_result': ... },
                                'error_step': Optional[int],
                                'error_message': Optional[str]
                            }
        """
        if not isinstance(plan, list):
            logger.error(f"Invalid plan format: Expected list, got {type(plan)}.")
            return {"status": "failure", "error_message": "Plan must be a list.", "final_context": {}}

        logger.info(f"Executing plan with {len(plan)} steps...")
        execution_context: Dict[str, Any] = {} # Stores results from each step
        
        for i, step in enumerate(plan):
            step_num = i + 1
            logger.info(f"--- Executing Step {step_num}/{len(plan)} --- ")
            
            if not isinstance(step, dict) or "tool" not in step or "args" not in step:
                logger.error(f"Invalid step format at index {i}: {step}. Must have 'tool' and 'args'.")
                return {
                    "status": "failure", 
                    "error_step": step_num,
                    "error_message": f"Invalid step format: {step}",
                    "final_context": execution_context
                }

            tool_name = step["tool"]
            tool_args = step["args"]
            
            logger.info(f"Step {step_num}: Calling tool '{tool_name}' with args: {tool_args}")

            tool = self.registry.get_tool(tool_name)
            if not tool:
                logger.error(f"Tool '{tool_name}' not found in registry.")
                return {
                    "status": "failure", 
                    "error_step": step_num,
                    "error_message": f"Tool '{tool_name}' not found.",
                    "final_context": execution_context
                }
            
            try:
                # Pass the current execution context to the tool
                step_result = tool.execute(args=tool_args, context=execution_context)
                
                # Store result in context, maybe prefixing with step number or tool name
                # Using step index for simplicity now
                context_key = f"step_{i}_result"
                execution_context[context_key] = step_result
                logger.info(f"Step {step_num} completed. Result stored in context as '{context_key}'.")

            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}' in step {step_num}: {e}", exc_info=True)
                return {
                    "status": "failure", 
                    "error_step": step_num,
                    "error_message": f"Tool '{tool_name}' execution failed: {e}",
                    "final_context": execution_context
                }

        logger.info("Plan execution completed successfully.")
        return {"status": "success", "final_context": execution_context}

# Example Usage:
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # Assumes registry and tools are available via get_registry()
    executor = ToolExecutionAgent()

    # Example Plan (Requires files 'test1.txt', 'test2.txt' to exist for read steps)
    # Create dummy files for testing
    with open("test1.txt", "w") as f: f.write("Content of test1")
    with open("test2.txt", "w") as f: f.write("Content of test2")
        
    plan1 = [
        {"tool": "read_file", "args": {"filepath": "test1.txt"}}, 
        {"tool": "read_file", "args": {"filepath": "test2.txt"}},
        {"tool": "write_file", "args": {"filepath": "output.txt", "content": "Combined results."}}
    ]
    
    print("\n--- Executing Plan 1 (Success Expected) ---")
    result1 = executor.execute_plan(plan1)
    print("Result 1:")
    import json
    print(json.dumps(result1, indent=2))

    plan2 = [
        {"tool": "read_file", "args": {"filepath": "nonexistent.txt"}}, # This step will fail
        {"tool": "write_file", "args": {"filepath": "output2.txt", "content": "Should not run."}}
    ]
    
    print("\n--- Executing Plan 2 (Failure Expected) ---")
    result2 = executor.execute_plan(plan2)
    print("Result 2:")
    print(json.dumps(result2, indent=2))
    
    plan3 = [
        {"tool": "unknown_tool", "args": {}}, # Tool not found
    ]
    
    print("\n--- Executing Plan 3 (Tool Not Found Expected) ---")
    result3 = executor.execute_plan(plan3)
    print("Result 3:")
    print(json.dumps(result3, indent=2))
    
    # Clean up dummy files
    import os
    try: os.remove("test1.txt") 
    except OSError: pass
    try: os.remove("test2.txt") 
    except OSError: pass
    try: os.remove("output.txt") 
    except OSError: pass
    try: os.remove("output2.txt") 
    except OSError: pass 