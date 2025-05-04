# validate_onboarding_prompts.py
import argparse
import os
import sys
from pathlib import Path

from dreamos.rendering.template_engine import TemplateEngine


def find_project_root():
    # This function should be implemented to find the project root
    # For now, we'll use a hardcoded path
    return Path("/path/to/your/project")


def main():
    parser = argparse.ArgumentParser(
        description="Validate onboarding prompt templates."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=find_project_root(),
        help="Root directory of the Dream.OS project.",
    )
    args = parser.parse_args()

    # Construct path to the prompt template relative to the project root
    prompt_template_path = (
        args.project_root
        / "runtime"
        / "governance"
        / "onboarding"
        / "_start_prompt_template.md"
    )

    if not os.path.exists(prompt_template_path):
        print(f"Error: Prompt template not found at {prompt_template_path}")
        sys.exit(1)
    with open(prompt_template_path, "r", encoding="utf-8") as f:
        template_string = f.read()
    engine = TemplateEngine()
    for i in range(1, 9):
        agent_id = f"{i:03d}"
        try:
            rendered = engine.render(template_string, {"agent_id": agent_id})
        except Exception as e:
            print(f"Error rendering for agent {agent_id}: {e}")
            continue
        separator = "--- Agent {0} Start Prompt ---".format(agent_id)
        print(separator)
        print(rendered)
        print("\n")


if __name__ == "__main__":
    main()
