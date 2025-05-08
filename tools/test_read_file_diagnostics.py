import time
import traceback
from pathlib import Path

from dreamos.tools.read_file import read_file  # Adjust if import differs

# List of suspect files (update as needed)
TARGET_FILES = [
    "runtime/governance/onboarding/onboarding_autonomous_operation.md",
    "docs/specs/PF-BRIDGE-INT-001_PyAutoGUIControlModule_API.md",
    "runtime/tasks/task_backlog.json",
    "runtime/tasks/VALIDATE-BRIDGE-CYCLE-004.json",
    "specs/PROJECT_PLAN.md",
]


def test_read_file(path: Path):
    print(f"\n🔍 Testing: {path}")
    try:
        start = time.perf_counter()
        # Assuming the user-provided read_file function takes a Path object
        # and returns the content or raises an exception.
        # This might need to be adapted based on the actual signature of
        # dreamos.tools.read_file.read_file

        # Placeholder for the actual call if the API is different
        # For example, if it's an async function or takes different params.
        # content = read_file(str(path)) # Or however it's meant to be called

        # Using a generic call pattern, assuming it takes path and returns content string
        # The user's BLOCK-002 description implies this 'read_file' is a specific tool/function
        # that agents use.

        # Direct call as per user's scaffold
        raw_content_or_response = read_file(path)  # This is the function to diagnose

        # Process response: The 'read_file' being diagnosed might return a simple string,
        # a dict with 'content' and 'error', or throw an exception directly.
        # This script aims to capture that behavior.
        content = None
        if isinstance(raw_content_or_response, str):
            content = raw_content_or_response
        elif (
            isinstance(raw_content_or_response, dict)
            and "content" in raw_content_or_response
        ):
            content = raw_content_or_response["content"]
        elif (
            raw_content_or_response is None
        ):  # Handles if read_file returns None on error
            pass  # Handled by "if not content" below

        duration = time.perf_counter() - start
        if not content and not (
            isinstance(raw_content_or_response, dict)
            and raw_content_or_response.get("error")
        ):
            print(f"⚠️ EMPTY or None content returned [took {duration:.2f}s]")
        elif isinstance(raw_content_or_response, dict) and raw_content_or_response.get(
            "error"
        ):
            print(
                f"❌ Failed (returned error structure): {raw_content_or_response.get('error')} [took {duration:.2f}s]"
            )
        else:
            # Truncate content for display if too long
            display_content = (
                content[:200] + "..." if content and len(content) > 200 else content
            )
            print(
                f"✅ Success [took {duration:.2f}s] – {len(content) if content else 0} chars. Preview: {display_content}"
            )

    except Exception as e:
        duration = time.perf_counter() - start
        print(f"❌ Failed (Exception) [took {duration:.2f}s]: {e}")
        traceback.print_exc()


def main():
    print("== READ FILE DIAGNOSTIC ==")
    # Ensure the script is run from the workspace root or adjust paths accordingly.
    # Assuming TARGET_FILES are relative to the workspace root.
    workspace_root = Path.cwd()  # Or a more robust way to get project root

    print(f"Workspace root assumed to be: {workspace_root}")
    print(
        "Please ensure this script is run from the project's root directory, or adjust TARGET_FILES paths."
    )

    for relative_path_str in TARGET_FILES:
        # Ensure paths are treated as relative to the workspace root.
        # Path.resolve() on a relative path makes it relative to CWD.
        # If CWD is not workspace root, this could be an issue.
        # For simplicity, assuming script is run from workspace root for now.
        # More robust: pass workspace_root to Path()

        # full_path = Path(relative_path_str) # If script is in root
        full_path = workspace_root / relative_path_str

        if not full_path.exists():
            print(f"❓ Skipped (missing): {full_path} (was {relative_path_str})")
            continue
        test_read_file(full_path)


if __name__ == "__main__":
    main()
