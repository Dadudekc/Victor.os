import argparse
from tsla_trader import core
from pathlib import Path

parser = argparse.ArgumentParser(
    description="TSLA Trade Machine CLI - Manage and summarize TSLA option trades.",
    epilog="Example: python basicbot/main_trader.py --summary"
)
parser.add_argument(
    "--add", 
    help="Add trade(s) from a YAML file. Provide the path to the YAML file.", 
    type=str, 
    metavar="FILE_PATH"
)
parser.add_argument(
    "--summary", 
    help="Display the trade summary for today and the weekly P/L.", 
    action="store_true"
)

args = parser.parse_args()

if args.add:
    yaml_file_path = Path(args.add)
    if not yaml_file_path.is_file():
        print(f"Error: YAML file not found at {yaml_file_path}")
        script_dir = Path(__file__).resolve().parent
        yaml_file_path_rel_script = script_dir / args.add
        if yaml_file_path_rel_script.is_file():
            yaml_file_path = yaml_file_path_rel_script
            print(f"Found YAML file relative to script: {yaml_file_path}")
        else:
            parser.print_help()
            exit(1)
    core.import_from_yaml(yaml_file_path)
elif args.summary:
    core.summarize_trades()
else:
    parser.print_help() 