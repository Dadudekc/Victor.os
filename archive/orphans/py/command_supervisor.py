import argparse


def main():
    """Entry point for the command supervisor CLI tool."""
    parser = argparse.ArgumentParser(
        description="Dream.OS Command Supervisor — Monitor and manage system commands."
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to supervisor configuration file",
        default="supervisor_config.yaml",
    )

    args = parser.parse_args()

    # TODO: Implement command supervisor logic
    print(f"Command Supervisor: Starting with log level {args.log_level}")


if __name__ == "__main__":
    main()
