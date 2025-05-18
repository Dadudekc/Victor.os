# Dream.OS Planning + Context Management Protocol

This document outlines the official protocol for planning discipline and context management in the Dream.OS platform. The protocol ensures consistent planning practices across all episodes and tasks, while also preventing context window exhaustion in LLM-based workflows.

## 1. Planning Discipline Framework

All Dream.OS agent episodes and tasks must follow a standardized 4-phase real-world planning model:

### Phase 1: Strategic Planning (60-70% of effort)

- Identify the **tech stack**
- Define **integration points** with the existing codebase
- List **known unknowns** and assess architectural feasibility
- Write **success criteria** for each feature

### Phase 2: Feature Documentation

- Define **API endpoints**, request/response formats
- Outline **component logic**, flow, expected data behavior
- Define **database schema**
- Capture **end-to-end user stories**
- Map out **state persistence and transitions**

### Phase 3: Design

- Visualize or narrate the **modular architecture**
- Define **file structure**, module responsibilities, and system boundaries
- Identify reusable elements vs new scaffolding

### Phase 4: Task Planning

- Break down the work into **atomic, independently executable tasks**
- Attach each task to its **originating planning step**
- Embed task metadata for agent assignment, retry logic, and validation

## 2. Context Window Safeguards

To prevent context window exhaustion in LLM-based workflows, the protocol enforces the following context boundary practices:

1. **Create a new chat window (Ctrl+N)** whenever a major planning or architectural stage shifts
2. **Immediately commit work** before initiating the new chat:
   - File updates
   - Devlog summaries
   - Task board status changes
3. Treat each new chat as a **contextually bounded build unit**

### Context Boundary Points

Context boundaries should be created at the following key points:

- After Strategic Planning completion
- After Feature Documentation completion  
- After Design completion
- After reaching a major implementation milestone
- When transitioning from planning to execution

## 3. Implementation

The planning and context management protocol is implemented through the following components:

### Episode YAML Files

Episode YAML files now include:

- A `planning_stage` field to track the overall planning progress
- `planning_step` tags (1-4) for each task
- `planning_documentation` section with details for each planning phase
- `context_boundary_points` section listing recommended boundary points

Example:
```yaml
planning_stage: "complete"  # or a specific number 1-4

agent_assignments:
  Agent-1:
    task_id: "EP08-TASK-001"
    # other task details...
    planning_step: 4  # indicates Task Planning phase
    
planning_documentation:
  strategic_planning:
    tech_stack:
      - "Python 3.10+ for core systems"
      # other tech stack items...
```

### Context Management Utility

A command-line utility for managing context boundaries:

```
python manage_context.py new-phase --agent Agent-1 --episode 08 --phase task_execution --reason "Transition from planning to execution phase"
```

### Core Components Updates

- `agent_bootstrap_runner.py` - Includes context boundary awareness and planning step tracking
- `CursorInjector` - Adds context markers to prompts
- Validation tools - Enforces planning step requirements

## 4. Usage Guide

### For Episode Planning

1. Start with Strategic Planning (Phase 1)
2. Create a context boundary when moving to Feature Documentation (Phase 2)
3. Create another boundary when moving to Design (Phase 3)
4. Create a final boundary when moving to Task Planning (Phase 4)
5. Create a task execution boundary when starting implementation

### Commands

**Create a new context boundary:**
```
python manage_context.py new-phase --agent <agent-id> --episode <episode-id> --phase <phase> --reason "<reason>"
```

**List all boundaries:**
```
python manage_context.py list
```

**Check episode status:**
```
python manage_context.py status --episode <episode-id>
```

**Get boundary suggestions:**
```
python manage_context.py suggest --episode <episode-id>
```

## 5. Benefits

- **Preserves context integrity** across prompt history
- **Ensures clean state** for task execution vs planning
- **Prevents drift, hallucination, and token overflow**
- **Enforces planning discipline** across all episodes
- **Provides clear lineage** for how each task was developed
- **Enhances team coordination** by making planning phases explicit 