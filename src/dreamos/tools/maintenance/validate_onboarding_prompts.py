# validate_onboarding_prompts.py
import os
import sys

from dreamos.rendering.template_engine import TemplateEngine


def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(
        project_root, "_agent_coordination", "onboarding", "_start_prompt_template.md"
    )
    if not os.path.isfile(template_path):
        print(f"Template not found: {template_path}")
        sys.exit(1)
    with open(template_path, "r", encoding="utf-8") as f:
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
