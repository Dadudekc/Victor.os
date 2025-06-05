#!/bin/bash
set -e

echo "🧹 Starting Dedup / Redundancy Sweep..."

# 1. Tag & Cut
git tag archive-legacy
git rm -r archive/archived_scripts/
git rm -r scripts/maintenance/

# 2. Lift & Shift: calibration + validation
mv src/dreamos/tools/calibration/calibration/* src/dreamos/tools/calibration/
mv src/dreamos/tools/validation/validation/* src/dreamos/tools/validation/
rm -r src/dreamos/tools/calibration/calibration/
rm -r src/dreamos/tools/validation/validation/
find src/dreamos/tools/ -name '__init__.py' -empty -delete

# 3. Merge scraper module
mkdir -p src/dreamos/modules/
git mv runtime/modules/chatgpt_scraper src/dreamos/modules/scraper
touch src/dreamos/modules/__init__.py
echo "from .scraper import *" > src/dreamos/modules/__init__.py

# 4. Vendor sweep
mkdir -p vendor
git mv runtime/tree-sitter-grammars vendor/

# 5. CLI Consolidation
mkdir -p src/dreamos/cli/
git mv src/dreamos/tools/task_editor.py src/dreamos/cli/task_editor.py
git mv src/dreamos/tools/command_supervisor.py src/dreamos/cli/command_supervisor.py
# Optional: add other utility scripts here...

# Create unified entrypoint
cat > src/dreamos/cli/__main__.py <<EOF
import sys
from .task_editor import main as task_editor_main
from .command_supervisor import main as command_supervisor_main

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "edit-task":
        task_editor_main()
    elif cmd == "supervise":
        command_supervisor_main()
    else:
        print("Usage: python -m dreamos.cli [edit-task|supervise]")
EOF

# 6. CI gate — dupe detector (placeholder hook)
echo -e "Running duplicate file hash check..."
python src/dreamos/tools/maintenance/find_duplicate_tasks.py --fail-on-dupes

echo "✅ Refactor Complete: Redundancy slashed, structure optimized."
