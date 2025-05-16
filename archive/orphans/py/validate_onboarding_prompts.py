# validate_onboarding_prompts.py
import argparse
import os
import sys
from pathlib import Path

from dreamos.rendering.template_engine import TemplateEngine


def find_project_root():
    # This function should be implemented to find the project root
    # For now, we'll use a hardcoded path
    # return Path("/path/to/your/project") # Original placeholder
    # Attempt to find the project root by looking for a .git folder or pyproject.toml
    current_path = Path(__file__).resolve()
    while current_path != current_path.parent:
        if (current_path / ".git").exists() or (
            current_path / "pyproject.toml"
        ).exists():
            return current_path
        current_path = current_path.parent
    # Fallback if no marker found - this might indicate script is not within project
    # Or raise an error, or use AppConfig if available
    # For now, return current_path.parent as a last resort, though less reliable.
    # A better fallback would be to require --project-root if auto-detection fails.
    print(
        "Warning: Could not reliably auto-detect project root. Using script parent directory.",
        file=sys.stderr,
    )
    return (
        Path(__file__).resolve().parent
    )  # Fallback, consider making --project-root mandatory if this is hit


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
