#!/usr/bin/env python3
"""
Pure-Markdown episode generator.
Reads Markdown content from stdin or a specified file and writes to a timestamped .md in reports/episodes.
"""
import os
import sys
from datetime import datetime


def main():
    # Read Markdown content
    if len(sys.argv) > 1:
        infile = sys.argv[1]
        with open(infile, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = sys.stdin.read()
    if not content.strip():
        print("No Markdown content provided.", file=sys.stderr)
        sys.exit(1)

    # Prepare output path
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("reports", "episodes")
    os.makedirs(out_dir, exist_ok=True)
    filename = f"episode_{ts}.md"
    path = os.path.join(out_dir, filename)

    # Write Markdown file
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Saved Markdown episode to {path}")


if __name__ == '__main__':
    main() 
