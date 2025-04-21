#!/usr/bin/env python3
"""
One-shot Lore Compiler
Reads a dream_translation.yaml and tasks JSON, and emits mythic lore into a markdown file.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime

import yaml
from jinja2 import Template

# Default paths (can be overridden via CLI)
DEFAULT_TRANSLATION = Path("dream_logs/config/dream_translation.yaml")
DEFAULT_TASK_LIST = Path("runtime/task_list.json")
DEFAULT_OUTPUT_DIR = Path("dream_logs/lore")

# Simple Jinja2 template for lore
LORE_TEMPLATE = """
# Episode: {{ event_name }}

{%- for t in tasks %}
- On {{ t.get('timestamp_created', 'unknown time') }}, the {{ translation.get('agent', 'Agent') }} performed '{{ t.get('task_type', 'action') }}', described as "{{ translation.get(t.get('task_type'), t.get('task_type')) }}".
{%- endfor %}
"""

def load_translation(path: Path) -> dict:
    """Load YAML translation mapping."""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_tasks(path: Path) -> list:
    """Load JSON list of task events."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def compile_lore(translation: dict, tasks: list, output_path: Path, template_text: str, verbose: bool):
    """Render lore and write to output_path."""
    event_name = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    template = Template(template_text)
    content = template.render(
        event_name=event_name,
        tasks=tasks,
        translation=translation.get('components', {}),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding='utf-8')
    if verbose:
        print(f"Compiled lore written to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Compile Dreamscape lore from tasks.")
    parser.add_argument("--translation", type=Path, default=DEFAULT_TRANSLATION,
                        help="Path to dream_translation.yaml")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASK_LIST,
                        help="Path to JSON task list")
    parser.add_argument("--template", type=Path, default=None,
                        help="Path to Jinja2 template file (overrides default)")
    parser.add_argument("--output", type=Path,
                        default=DEFAULT_OUTPUT_DIR / f"{datetime.utcnow():%Y-%m-%d_%H-%M-%S}_lore.md",
                        help="Destination markdown file for lore")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Load translation
    translation = load_translation(args.translation)
    # Load tasks
    tasks = load_tasks(args.tasks)

    # Load template
    if args.template:
        if args.verbose:
            print(f"Loading template from {args.template}")
        template_text = args.template.read_text(encoding='utf-8')
    else:
        template_text = LORE_TEMPLATE
        if args.verbose:
            print("Using default lore template")
    # Compile lore
    compile_lore(translation, tasks, args.output, template_text, args.verbose)

if __name__ == "__main__":
    main() 