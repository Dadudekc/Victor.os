# scripts/scan_for_rogue_files.py

import os

base_dir = "src"
rogue_files = []

for root, dirs, files in os.walk(base_dir):
    for f in files:
        if "dreamos" in f and "." in f.replace(".py", ""):
            full_path = os.path.join(root, f)
            rogue_files.append(full_path)

if rogue_files:
    print("⚠️ Rogue files detected (dots in names):")
    for path in rogue_files:
        print(" -", path)
else:
    print("✅ No rogue files detected.")
