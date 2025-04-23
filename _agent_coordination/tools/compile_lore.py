#!/usr/bin/env python3
"""
One-shot Lore Compiler
Reads a dream_translation.yaml and tasks JSON, and emits mythic lore into a markdown file.
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
import subprocess

import yaml
from jinja2 import Template

# Default paths (can be overridden via CLI)
DEFAULT_TRANSLATION = Path("dream_logs/config/dream_translation.yaml")
DEFAULT_TASK_LIST = Path("runtime/task_list.json")
DEFAULT_OUTPUT_DIR = Path("dream_logs/lore")

# Default Jinja2 template for lore including channel and description
LORE_TEMPLATE = """
# Episode: {{ event_name }}
**Channel:** {{ translation.get('AzureBlobChannel', 'AzureBlobChannel') }}

{%- for t in tasks %}
- On {{ t.get('timestamp_created', 'unknown time') }}, the {{ translation.get('agent', 'Agent') }} performed '{{ t.get('task_type', 'task') }}', description: "{{ t.get('payload', {}).get('description', '') }}", narrative: "{{ translation.get(t.get('task_type', 'task'), translation.get('task', '')) }}".
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
    """Render lore with style template and write to output_path."""
    # Normalize task payloads: wrap non-dict payloads into {'description': payload}
    for task in tasks:
        pl = task.get('payload')
        if not isinstance(pl, dict):
            task['payload'] = {'description': pl}
        # Extract description into top-level key for templates expecting task.description
        desc = task['payload'].get('description')
        task.setdefault('description', desc)
        # Map agent identity
        agent_id = task.get('payload', {}).get('agent_id') or task.get('claimed_by')
        task.setdefault('agent', agent_id)
        # Expose status
        task.setdefault('status', task.get('status'))
    # Build rendering context
    event_name = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    # Inject timestamp_created, result_summary, commit_hash, target_files, and log_tail for each task
    # Determine current commit hash for traceability
    try:
        commit_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        commit_hash = ""
    for task in tasks:
        # Timestamp per task falls back to event time
        task.setdefault('timestamp_created', event_name)
        # Summary description if not provided
        status = task.get('status', 'unknown')
        task.setdefault('result_summary', f"Task processed with status: {status}")
        # Commit hash
        task.setdefault('commit_hash', commit_hash)
        # Target files list
        tf = task.get('payload', {}).get('modified_files')
        task.setdefault('target_files', tf if isinstance(tf, list) else [])
        # Log tail
        lt = task.get('payload', {}).get('log_tail')
        task.setdefault('log_tail', lt if isinstance(lt, str) else "")
    template = Template(template_text)
    content = template.render(
        event_name=event_name,
        date=date_str,
        tasks=tasks,
        translation=translation.get('components', {}),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding='utf-8')
    if verbose:
        print(f"Compiled lore written to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Compile Dreamscape lore from tasks.")
    parser.add_argument("--once", action="store_true", help="Alias for single-run execution (no-op)")
    parser.add_argument("--translation", type=Path, default=DEFAULT_TRANSLATION,
                        help="Path to dream_translation.yaml")
    parser.add_argument("--tasks", type=Path, default=DEFAULT_TASK_LIST,
                        help="Path to JSON task list")
    parser.add_argument("--template", type=Path, default=None,
                        help="Path to Jinja2 template file (overrides default)")
    parser.add_argument("--output", type=Path,
                        default=DEFAULT_OUTPUT_DIR / f"{datetime.utcnow():%Y-%m-%d_%H-%M-%S}_lore.md",
                        help="Destination markdown file for lore")
    parser.add_argument("--style", type=str, default="default", help="Lore style to use (default or devlog)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    # Allow legacy flags like --once to be ignored
    args, _ = parser.parse_known_args()

    # Load translation
    translation = load_translation(args.translation)
    # Load tasks
    tasks = load_tasks(args.tasks)

    # Load template (explicit template override > style > default)
    if args.template:
        if args.verbose:
            print(f"Loading custom template from {args.template}")
        template_text = args.template.read_text(encoding='utf-8')
    elif args.style and args.style != "default":
        style_path = Path("templates/lore") / f"{args.style}_lore.j2"
        if not style_path.exists():
            raise FileNotFoundError(f"Lore template for style '{args.style}' not found at {style_path}")
        if args.verbose:
            print(f"Loading style template from {style_path}")
        template_text = style_path.read_text(encoding='utf-8')
    else:
        if args.verbose:
            print("Using default lore template")
        template_text = LORE_TEMPLATE

    # Compile lore
    compile_lore(translation, tasks, args.output, template_text, args.verbose)

if __name__ == "__main__":
    main() 