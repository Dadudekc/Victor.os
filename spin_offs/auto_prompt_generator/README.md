# Auto-Prompt Script Generator for Multi-Agent Systems

This utility creates standardized prompt files for Dream.OS or other multi-agent
workflows. It reads a YAML specification of agent roles and tasks, then generates
individual prompt text files to seed each agent's Cursor chat window.

## Usage
1. Prepare a YAML file with your agent definitions (see `example_agents.yaml`).
2. Run `python generate_prompts.py example_agents.yaml output_dir/`.
3. The script writes a `<agent_id>.txt` prompt for each agent in the output directory.

## Example YAML
```yaml
agents:
  - id: agent1
    role: documentation
    task: "Write API docs for the payment module"
  - id: agent2
    role: testing
    task: "Create integration tests for the new endpoints"
```

The resulting files can be dropped directly into Cursor to bootstrap your swarm.
