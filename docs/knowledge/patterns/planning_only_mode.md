# Pattern: Planning Only Mode

**Category:** Agent Lifecycle, Operational Modes
**Author:** Agent-3
**Last Updated:** 2023-08-15
**Referenced From:** agent_operation_analytics.md, meta_analysis_protocol_adherence.md

## Overview

Planning Only Mode is an operational pattern that restricts agent activities to planning, analysis, and documentation tasks without executing external changes or tool operations. This pattern enables safe operation during sensitive periods, allows for review before execution, and facilitates collaborative planning between agents.

## Context

In autonomous agent systems like Dream.OS, there are scenarios where restricting execution while maintaining agent cognition is beneficial:

1. **Sensitive Operations** - When changes could affect critical systems
2. **Scheduled Maintenance** - During system upgrades or backups
3. **Pre-execution Review** - For operations that require human approval
4. **Collaborative Planning** - When multiple agents need to agree on an approach
5. **Reduced Resource Consumption** - When execution resources are constrained
6. **Debugging Sessions** - To understand agent decision-making without side effects

These scenarios require a way to keep agents operational but restrict their ability to make changes to the environment.

## Solution Structure

Implement a Planning Only Mode that:

1. **Disables Tool Execution:** Prevents running external tools or making file changes
2. **Enables Documentation:** Allows documentation and planning activities
3. **Provides Simulation:** Offers execution simulation for validation
4. **Maintains Transparency:** Clearly indicates the restricted mode
5. **Supports Collaboration:** Facilitates sharing plans between agents

```python
from dreamos.skills.lifecycle import OperationalMode, ToolRegistry
from dreamos.skills.planner import PlanDocument
from typing import List, Dict, Any

class PlanningOnlyMode(OperationalMode):
    """Restricts agent to planning and documentation activities."""
    
    def __init__(
        self, 
        reason: str = "Unspecified planning session",
        allowed_tools: List[str] = None,
        simulation_enabled: bool = True
    ):
        super().__init__(name="planning_only")
        self.reason = reason
        self.allowed_tools = allowed_tools or ["document", "analyze", "plan"]
        self.simulation_enabled = simulation_enabled
        self.plan_document = PlanDocument()
        
    def can_execute_tool(self, tool_name: str) -> bool:
        """Determine if a tool can be executed in this mode."""
        tool = ToolRegistry.get_tool(tool_name)
        
        # Allow documentation and analysis tools
        if tool.category in self.allowed_tools:
            return True
            
        # For other tools, only allow simulation if enabled
        if self.simulation_enabled and tool.supports_simulation:
            return True
            
        return False
        
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool within planning mode constraints."""
        tool = ToolRegistry.get_tool(tool_name)
        
        if not self.can_execute_tool(tool_name):
            # Instead of executing, add to plan document
            step = {
                "tool": tool_name,
                "parameters": kwargs,
                "proposed_outcome": tool.simulate(**kwargs) if tool.supports_simulation else None,
                "rationale": kwargs.get("rationale", "No rationale provided")
            }
            self.plan_document.add_step(step)
            
            return {
                "status": "planned",
                "message": f"Tool {tool_name} execution added to plan (planning only mode)",
                "simulated_result": step["proposed_outcome"] if self.simulation_enabled else None
            }
        
        # Execute allowed tools (documentation, analysis)
        return tool.execute(**kwargs)
```

## Key Components

### 1. PlanningOnlyMode Class

A mode controller that:
- Filters which tools can be executed
- Maintains a plan document for proposed operations
- Provides simulation capabilities for execution preview
- Clearly communicates planning mode status

### 2. PlanDocument

A structured document that:
- Records proposed operations
- Captures operation parameters and rationale
- Maintains steps in a structured, executable format
- Supports export to various formats (JSON, Markdown, etc.)

### 3. Tool Simulation APIs

Extensions to tools that:
- Implement `.supports_simulation` flag
- Provide `.simulate()` method to preview execution results
- Return expected outcomes without making actual changes

### 4. Mode Integration

System hooks that:
- Detect planning mode activation
- Route tool execution through the appropriate channels
- Provide clear UI indicators when in planning mode
- Filter agent responses based on operational context

## Implementation Guidelines

1. **Tool Categories:**
   - Tag all tools with appropriate categories (document, analyze, plan, execute)
   - Ensure consistency in categorization across the system
   - Document which tools are safe for planning mode

2. **Plan Documents:**
   - Use standardized format for plan documents
   - Include execution prerequisites and validation checks
   - Store with appropriate metadata for retrieval
   - Include agent rationale for each proposed step

3. **Activation Mechanisms:**
   - Support both explicit (user-directed) activation
   - Allow automatic activation based on system conditions
   - Permit scheduled planning-only windows

4. **Execution Bridging:**
   - Enable approved plans to be executed without rewriting
   - Provide diff visualization between planned and actual execution
   - Support partial plan approval and execution

## Example Implementation

```python
from dreamos.skills.lifecycle import OperationalMode, agent_context
from dreamos.skills.planner import PlanDocument, PlanExporter
from typing import Dict, Any, List, Optional

class PlanningOnlyMode(OperationalMode):
    def __init__(
        self,
        reason: str = "Unspecified planning session",
        plan_id: Optional[str] = None,
        allowed_categories: List[str] = None
    ):
        super().__init__(name="planning_only")
        self.reason = reason
        self.plan_id = plan_id or f"plan_{int(time.time())}"
        self.allowed_categories = allowed_categories or ["document", "analyze", "plan"]
        self.plan_document = PlanDocument(self.plan_id)
        self.log_handler = self._setup_logging()
        
    def __enter__(self):
        """Enter planning only mode."""
        agent_context.set_attribute("operational_mode", "planning_only")
        agent_context.set_attribute("can_execute", False)
        
        # Log planning mode activation
        logger.info(f"Entering planning only mode: {self.reason}")
        
        # Register this mode with the agent's context
        agent_context.register_plan_document(self.plan_document)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit planning only mode."""
        # Export the plan document
        if len(self.plan_document.steps) > 0:
            exporter = PlanExporter(self.plan_document)
            plan_path = exporter.export_to_markdown()
            logger.info(f"Planning session completed. Plan saved to {plan_path}")
            
        # Restore normal operational mode
        agent_context.set_attribute("operational_mode", "standard")
        agent_context.set_attribute("can_execute", True)
        
        return False  # Don't suppress exceptions
    
    def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute or plan a tool operation."""
        tool = ToolRegistry.get_tool(tool_name)
        
        # Always allow tools in permitted categories
        if tool.category in self.allowed_categories:
            return tool.execute(**kwargs)
            
        # For execution tools, add to plan instead
        step = {
            "tool": tool_name,
            "parameters": kwargs,
            "proposed_outcome": self._simulate_tool(tool, **kwargs),
            "rationale": kwargs.get("rationale", "No rationale provided"),
            "timestamp": time.time()
        }
        self.plan_document.add_step(step)
        
        return {
            "status": "planned",
            "message": f"Tool {tool_name} added to plan {self.plan_id}",
            "simulated_result": step["proposed_outcome"]
        }
    
    def _simulate_tool(self, tool, **kwargs) -> Dict[str, Any]:
        """Simulate tool execution if possible."""
        if hasattr(tool, "simulate") and callable(tool.simulate):
            try:
                return tool.simulate(**kwargs)
            except Exception as e:
                logger.warning(f"Tool simulation failed: {str(e)}")
                return {"simulation_error": str(e)}
        
        return {"simulation_not_available": True}
        
    def _setup_logging(self):
        """Configure logging for planning mode."""
        # Implementation details for logging setup
        return None  # Placeholder for actual handler


# Usage example
def plan_complex_operation(task_description: str):
    """Plan a complex operation without executing it."""
    with PlanningOnlyMode(reason=f"Planning for: {task_description}") as planning_mode:
        # Perform analysis
        data = analyze_task_requirements(task_description)
        
        # Document approach
        document_approach(data["requirements"])
        
        # Create execution plan
        for step in data["steps"]:
            # This won't execute but will be added to the plan
            perform_operation(step["operation"], **step["parameters"])
        
    # Return the generated plan
    return planning_mode.plan_document
```

## Benefits

1. **Safety:** Prevents unintended changes during sensitive periods
2. **Transparency:** Makes agent reasoning visible before execution
3. **Collaboration:** Enables review and refinement of plans
4. **Resource Efficiency:** Reduces computational load when execution resources are constrained
5. **Auditability:** Creates clear documentation of intended actions
6. **Human-in-the-loop:** Facilitates human review before execution

## Limitations

1. **Simulation Accuracy:** Not all operations can be perfectly simulated
2. **Context Changes:** World state may change between planning and execution
3. **Planning Overhead:** Creates additional planning artifacts to manage
4. **Tool Support:** Requires simulation support across all tools

## Related Patterns

- [Autonomous Loop Stability](autonomous_loop_stability.md)
- [Degraded Operation Mode](degraded_operation_mode.md)
- [Agent Coordination Protocol](agent_coordination_protocol.md)

## Known Uses

1. **System Maintenance:** Used during system upgrades to safely plan post-upgrade activities
2. **Multi-Agent Coordination:** Applied when multiple agents need to agree on an approach
3. **Human Approval Workflow:** Utilized for changes requiring human review and approval
4. **Resource-Constrained Environments:** Employed when execution resources are limited

## Example Scenario

During a critical system upgrade:

1. The system administrator activates Planning Only Mode across all agents
2. Agents continue analyzing and planning activities:
   - They analyze system status to identify necessary post-upgrade actions
   - They develop plans for resuming normal operations
   - They document current state for comparison after the upgrade
3. Each agent produces a plan document with proposed actions
4. System administrator reviews and approves the plans
5. After the upgrade, plans are executed in normal operational mode

This approach ensures no accidental interference during the upgrade while keeping agents productive and prepared to resume operations efficiently. 