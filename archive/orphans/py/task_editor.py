import argparse


def main():
    """Entry point for the task editor CLI tool."""
    parser = argparse.ArgumentParser(
        description="Dream.OS Task Editor — Create and manage system tasks."
    )
    parser.add_argument(
        "--task-file",
        type=str,
        help="Path to the task file to edit (YAML/JSON)",
        default="working_tasks.json",
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create a new task instead of editing existing",
    )

    args = parser.parse_args()

    # TODO: Implement task editor logic
    print(
        f"Task Editor: {'Creating new task' if args.create else 'Editing'} {args.task_file}"
    )


if __name__ == "__main__":
    main()
