import os
import re
from pathlib import Path

def update_imports():
    """Update import statements in tools to reflect the new flattened structure."""
    captain_tools = Path("src/dreamos/tools/captain_tools")
    
    # Map of old import paths to new ones
    import_map = {
        r"from\s+src\.dreamos\.tools\.([^.]+)\.([^.]+)\s+import": r"from src.dreamos.tools.captain_tools.\1_\2 import",
        r"from\s+src\.dreamos\.tools\.([^.]+)\s+import": r"from src.dreamos.tools.captain_tools.\1_ import",
        r"import\s+src\.dreamos\.tools\.([^.]+)\.([^.]+)": r"import src.dreamos.tools.captain_tools.\1_\2",
        r"import\s+src\.dreamos\.tools\.([^.]+)": r"import src.dreamos.tools.captain_tools.\1_"
    }
    
    # Process each Python file
    for py_file in captain_tools.glob("*.py"):
        print(f"Processing {py_file.name}...")
        
        # Read file content
        with open(py_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Update imports
        modified = False
        for old_pattern, new_pattern in import_map.items():
            new_content = re.sub(old_pattern, new_pattern, content)
            if new_content != content:
                modified = True
                content = new_content
        
        # Write back if modified
        if modified:
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Updated imports in {py_file.name}")
        else:
            print(f"  No import updates needed for {py_file.name}")

if __name__ == "__main__":
    update_imports() 