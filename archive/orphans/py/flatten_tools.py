import shutil
from pathlib import Path


def flatten_tools():
    """Flatten all tools directories into captain_tools."""
    base_path = Path("src/dreamos/tools")
    captain_tools = base_path / "captain_tools"

    # Create captain_tools if it doesn't exist
    captain_tools.mkdir(exist_ok=True)

    # List of directories to flatten
    tool_dirs = [
        "analysis",
        "calibration",
        "coordination",
        "cursor_bridge",
        "discovery",
        "dreamos_utils",
        "env",
        "maintenance",
        "validation",
        "_core",
        "code_analysis",
        "functional",
        "scripts",
    ]

    # Additional root-level tools to move
    root_tools = [
        "edit_file.py",
        "read_file.py",
        "task_editor.py",
        "command_supervisor.py",
        "thea_relay_agent.py",
    ]

    # Move files from each directory
    for tool_dir in tool_dirs:
        source_dir = base_path / tool_dir
        if not source_dir.exists():
            continue

        print(f"Processing {tool_dir}...")

        # Move all files
        for item in source_dir.iterdir():
            if item.is_file():
                # Skip __init__.py files
                if item.name == "__init__.py":
                    continue

                # Create new filename with prefix
                new_name = f"{tool_dir}_{item.name}"
                target = captain_tools / new_name

                # Move the file
                shutil.move(str(item), str(target))
                print(f"  Moved {item.name} -> {new_name}")

        # Remove empty directories
        if not any(source_dir.iterdir()):
            source_dir.rmdir()
            print(f"  Removed empty directory {tool_dir}")

    # Move root-level tools
    print("\nProcessing root-level tools...")
    for tool in root_tools:
        source = base_path / tool
        if source.exists():
            new_name = f"root_{tool}"
            target = captain_tools / new_name
            shutil.move(str(source), str(target))
            print(f"  Moved {tool} -> {new_name}")

    print("\nFlattening complete!")


if __name__ == "__main__":
    flatten_tools()
