#!/usr/bin/env python3
"""
Tool to apply generated code changes back into project files.

Usage:
  code_applicator.py --target <file> [--source <source_file>] [--backup]

Options:
  --target <file>     Path to the target file to update.
  --source <file>     Path to a file containing the new content. If omitted, reads from stdin.
  --backup            Create a backup of the original file with an added .bak suffix.
"""
import argparse
import shutil
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Apply generated code changes to a target file.")
    parser.add_argument("--target", required=True, help="Path to the target file to update.")
    parser.add_argument("--source", help="Path to a file with new content; if omitted, reads from stdin.")
    parser.add_argument("--backup", action="store_true", help="Create a backup of the original file before writing.")
    args = parser.parse_args()

    target_path = Path(args.target)
    if not target_path.exists():
        print(f"Error: target file {target_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    if args.backup:
        backup_path = target_path.with_suffix(target_path.suffix + '.bak')
        shutil.copy(str(target_path), str(backup_path))
        print(f"Backup created at {backup_path}")

    if args.source:
        source_path = Path(args.source)
        if not source_path.exists():
            print(f"Error: source file {source_path} does not exist.", file=sys.stderr)
            sys.exit(1)
        content = source_path.read_text(encoding='utf-8')
    else:
        content = sys.stdin.read()

    try:
        target_path.write_text(content, encoding='utf-8')
        print(f"Applied new content to {target_path}")
    except Exception as e:
        print(f"Error writing to {target_path}: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main() 