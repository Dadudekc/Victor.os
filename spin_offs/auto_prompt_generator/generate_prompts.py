import sys
from pathlib import Path
import yaml

PROMPT_TEMPLATE = """You are {role} ({agent_id}).\nYour task: {task}\n"""


def generate_prompts(spec_path: Path, out_dir: Path) -> None:
    data = yaml.safe_load(spec_path.read_text())
    agents = data.get("agents", [])
    out_dir.mkdir(parents=True, exist_ok=True)
    for agent in agents:
        agent_id = agent["id"]
        role = agent.get("role", "agent")
        task = agent.get("task", "")
        prompt = PROMPT_TEMPLATE.format(role=role, agent_id=agent_id, task=task)
        (out_dir / f"{agent_id}.txt").write_text(prompt)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_prompts.py <spec.yaml> <output_dir>")
        sys.exit(1)
    spec_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    generate_prompts(spec_path, out_dir)
