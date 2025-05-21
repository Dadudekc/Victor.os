"""
Dream.OS Launcher CLI Commands

Core command implementations for the Dream.OS Launcher CLI.
"""

import os
import json
import logging
import sys
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from dreamos.launcher.scanner import ComponentScanner
from dreamos.launcher.registry import ComponentRegistry
from dreamos.launcher.process_manager import get_process_manager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.launcher.cli")


def scan_command(args: argparse.Namespace) -> None:
    """
    Execute the scan command to discover components.
    
    Args:
        args: Command-line arguments
    """
    logger.info(f"Starting component scan in {args.directory}")
    
    scanner = ComponentScanner()
    
    if args.resume:
        scanner._load_checkpoint(args.resume)
        
    components = scanner.scan_directory(
        Path(args.directory),
        max_depth=args.max_depth,
        file_patterns=args.file_patterns
    )
    
    # Print summary
    print(f"\nScan Summary:")
    print(f"  Found {len(components)} components")
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump({"components": components}, f, indent=2)
        print(f"  Results saved to {args.output}")
        
    # Print component types summary
    if components:
        types = {}
        for comp_id, comp in components.items():
            comp_type = comp.get("type", "unknown")
            types[comp_type] = types.get(comp_type, 0) + 1
            
        print("\nComponent Types:")
        for comp_type, count in types.items():
            print(f"  {comp_type}: {count}")

    # Add scanned components to registry if requested
    if args.register:
        registry = ComponentRegistry()
        added = 0
        updated = 0
        failed = 0
        
        print("\nRegistering components...")
        for comp_id, comp in components.items():
            # Check if component already exists
            existing = registry.get_component(comp_id)
            
            if existing:
                # Update existing component
                success, error = registry.update_component(comp_id, comp)
                if success:
                    updated += 1
                else:
                    failed += 1
                    print(f"  Failed to update {comp_id}: {error}")
            else:
                # Create new component
                success, error = registry.create_component(comp)
                if success:
                    added += 1
                else:
                    failed += 1
                    print(f"  Failed to add {comp_id}: {error}")
                    
        print(f"  Added: {added}, Updated: {updated}, Failed: {failed}")


def list_command(args: argparse.Namespace) -> None:
    """
    Execute the list command to show registered components.
    
    Args:
        args: Command-line arguments
    """
    registry = ComponentRegistry()
    
    # Apply filters
    filters = {}
    if args.type:
        filters["type"] = args.type
    if args.agent:
        filters["owner_agent"] = args.agent
        
    # Get components
    if filters:
        components = registry.search_components(filters=filters)
    else:
        components = registry.get_all_components()
        
    if not components:
        print("No components match the specified filters.")
        return
        
    # Sort by name
    sorted_components = sorted(
        components.items(),
        key=lambda x: x[1].get("name", "") if x[1] and "name" in x[1] else ""
    )
    
    # Print components
    print(f"\nFound {len(sorted_components)} components:")
    print("{:<30} {:<15} {:<20} {:<50}".format(
        "NAME", "TYPE", "OWNER", "ENTRY POINT"))
    print("-" * 115)
    
    for comp_id, comp in sorted_components:
        if comp is None:
            logger.warning(f"Found None component with ID: {comp_id}")
            continue
            
        print("{:<30} {:<15} {:<20} {:<50}".format(
            comp.get("name", "")[:30],
            comp.get("type", "")[:15],
            comp.get("owner_agent", "")[:20],
            comp.get("entry_point", "")[:50]
        ))
        
    # Print details if requested
    if args.verbose and len(sorted_components) == 1:
        comp_id, comp = sorted_components[0]
        if comp is not None:
            print("\nComponent Details:")
            print(json.dumps(comp, indent=2))


def run_command(args: argparse.Namespace) -> None:
    """
    Execute the run command to start a component.
    
    Args:
        args: Command-line arguments
    """
    # Get component from registry
    registry = ComponentRegistry()
    component = registry.get_component(args.component_id)
    
    if not component:
        print(f"Component not found: {args.component_id}")
        return
        
    # Get process manager
    process_manager = get_process_manager()
    
    # Prepare component info
    component_id = component.get("component_id")
    component_type = component.get("type", "unknown")
    component_name = component.get("name", component_id)
    entry_point = component.get("entry_point")
    
    if not entry_point:
        print(f"Error: Component {component_id} does not have an entry point")
        return
        
    # Parse command line arguments if provided
    cmd_args = []
    if args.args:
        cmd_args = args.args.split()
        
    # Set up environment variables
    env = {}
    required_env_vars = component.get("required_env_vars", [])
    if required_env_vars:
        print(f"Required environment variables: {', '.join(required_env_vars)}")
        
        # Check if any required variables are missing
        missing_vars = [var for var in required_env_vars if var not in os.environ]
        if missing_vars and not args.ignore_missing_env:
            print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
            print("Use --ignore-missing-env to run anyway")
            return
            
    # Set up resource limits
    resource_limits = {}
    if args.cpu_limit:
        resource_limits["cpu_percent"] = float(args.cpu_limit)
    if args.memory_limit:
        resource_limits["memory_mb"] = float(args.memory_limit)
        
    # Check dependencies
    dependencies = component.get("dependencies", [])
    if dependencies:
        print(f"Component dependencies: {', '.join(dependencies)}")
        
        # Check if dependencies are registered
        missing_deps = []
        for dep_id in dependencies:
            if not registry.get_component(dep_id):
                missing_deps.append(dep_id)
                
        if missing_deps and not args.ignore_dependencies:
            print(f"Error: Missing dependencies: {', '.join(missing_deps)}")
            print("Use --ignore-dependencies to run anyway")
            return
            
    # Start the process
    print(f"Starting component: {component_name}")
    print(f"Entry point: {entry_point}")
    if cmd_args:
        print(f"Arguments: {' '.join(cmd_args)}")
        
    success, process_data = process_manager.start_process(
        component_id=component_id,
        component_type=component_type,
        entry_point=entry_point,
        args=cmd_args,
        env=env,
        resource_limits=resource_limits,
        restart_policy=args.restart_policy,
        checkpoint_enabled=args.checkpoint_enabled,
        checkpoint_interval=args.checkpoint_interval
    )
    
    if success:
        process_id = process_data.get("process_id")
        pid = process_data.get("pid")
        log_file = process_data.get("log_file")
        
        print(f"Successfully started component {component_name}")
        print(f"Process ID: {process_id}")
        print(f"System PID: {pid}")
        print(f"Log file: {log_file}")
    else:
        print(f"Failed to start component {component_name}")


def processes_command(args: argparse.Namespace) -> None:
    """
    Execute the processes command to list running processes.
    
    Args:
        args: Command-line arguments
    """
    process_manager = get_process_manager()
    
    # Get all processes
    all_processes = process_manager.get_all_processes()
    
    # Filter by component if specified
    if args.component_id:
        all_processes = {
            proc_id: proc_data for proc_id, proc_data in all_processes.items()
            if proc_data.get("component_id") == args.component_id
        }
        
    # Filter by status if specified
    if args.status:
        all_processes = {
            proc_id: proc_data for proc_id, proc_data in all_processes.items()
            if proc_data.get("status") == args.status
        }
        
    if not all_processes:
        print("No matching processes found")
        return
        
    # Sort by start time (newest first)
    sorted_processes = sorted(
        all_processes.items(),
        key=lambda x: x[1].get("start_time", ""),
        reverse=True
    )
    
    # Print processes
    print(f"\nFound {len(sorted_processes)} processes:")
    print("{:<20} {:<30} {:<10} {:<15} {:<15}".format(
        "PROCESS ID", "COMPONENT", "PID", "STATUS", "STARTED"))
    print("-" * 95)
    
    for proc_id, proc_data in sorted_processes:
        # Get short process ID (truncate for display)
        short_proc_id = proc_id[-17:] if len(proc_id) > 20 else proc_id
        
        # Format start time
        start_time = proc_data.get("start_time", "")
        if start_time:
            try:
                # Extract just the time part for display
                start_time = start_time.split("T")[1].split(".")[0]
            except:
                pass
                
        print("{:<20} {:<30} {:<10} {:<15} {:<15}".format(
            short_proc_id,
            proc_data.get("component_id", "")[:30],
            proc_data.get("pid", ""),
            proc_data.get("status", ""),
            start_time
        ))
        
    # Print details if requested
    if args.verbose and len(sorted_processes) == 1:
        proc_id, proc_data = sorted_processes[0]
        print("\nProcess Details:")
        print(json.dumps(proc_data, indent=2))
        
        # Print recent logs if available
        if args.logs:
            print("\nRecent Logs:")
            logs = process_manager.get_process_logs(proc_id, args.logs)
            if logs:
                for line in logs:
                    print(line.rstrip())
            else:
                print("No logs available")


def stop_command(args: argparse.Namespace) -> None:
    """
    Execute the stop command to stop a running process.
    
    Args:
        args: Command-line arguments
    """
    process_manager = get_process_manager()
    
    # Get process info
    process_info = process_manager.get_process_info(args.process_id)
    if not process_info:
        print(f"Process not found: {args.process_id}")
        return
        
    # Confirm stop if not forced
    if not args.force:
        component_id = process_info.get("component_id", "unknown")
        confirm = input(f"Are you sure you want to stop process {args.process_id} ({component_id})? (y/n): ")
        if confirm.lower() != 'y':
            print("Stop cancelled")
            return
            
    # Stop the process
    success = process_manager.stop_process(args.process_id, force=args.force, timeout=args.timeout)
    
    if success:
        print(f"Successfully stopped process {args.process_id}")
    else:
        print(f"Failed to stop process {args.process_id}")


def restart_command(args: argparse.Namespace) -> None:
    """
    Execute the restart command to restart a running process.
    
    Args:
        args: Command-line arguments
    """
    process_manager = get_process_manager()
    
    # Get process info
    process_info = process_manager.get_process_info(args.process_id)
    if not process_info:
        print(f"Process not found: {args.process_id}")
        return
        
    # Restart the process
    success, new_process_id = process_manager.restart_process(args.process_id)
    
    if success:
        print(f"Successfully restarted process {args.process_id}")
        print(f"New process ID: {new_process_id}")
    else:
        print(f"Failed to restart process {args.process_id}")


def logs_command(args: argparse.Namespace) -> None:
    """
    Execute the logs command to show logs for a process.
    
    Args:
        args: Command-line arguments
    """
    process_manager = get_process_manager()
    
    # Get process info
    process_info = process_manager.get_process_info(args.process_id)
    if not process_info:
        print(f"Process not found: {args.process_id}")
        return
        
    # Get log file
    log_file = process_info.get("log_file")
    if not log_file:
        print(f"No log file found for process {args.process_id}")
        return
        
    # Get logs
    logs = process_manager.get_process_logs(args.process_id, args.lines)
    
    if not logs:
        print(f"No logs available for process {args.process_id}")
        return
        
    # Print logs
    print(f"Logs for process {args.process_id} (showing last {len(logs)} lines):")
    print("-" * 80)
    for line in logs:
        print(line.rstrip())


def register_command(args: argparse.Namespace) -> None:
    """
    Execute the register command to manually register a component.
    
    Args:
        args: Command-line arguments
    """
    if args.file:
        # Register from file
        try:
            with open(args.file, 'r') as f:
                component_data = json.load(f)
        except Exception as e:
            print(f"Error reading file: {e}")
            return
    else:
        # Create component from arguments
        if not args.id or not args.name or not args.entry_point or not args.type:
            print("Error: component_id, name, entry_point, and type are required")
            return
            
        component_data = {
            "component_id": args.id,
            "name": args.name,
            "entry_point": args.entry_point,
            "type": args.type,
        }
        
        # Add optional fields
        if args.description:
            component_data["description"] = args.description
        if args.owner:
            component_data["owner_agent"] = args.owner
        if args.dependencies:
            component_data["dependencies"] = args.dependencies.split(",")
        if args.env_vars:
            component_data["required_env_vars"] = args.env_vars.split(",")
        if args.tags:
            component_data["tags"] = args.tags.split(",")
            
    # Register component
    registry = ComponentRegistry()
    success, error = registry.create_component(component_data)
    
    if success:
        print(f"Successfully registered component: {component_data.get('name')}")
    else:
        print(f"Failed to register component: {error}")


def delete_command(args: argparse.Namespace) -> None:
    """
    Execute the delete command to remove a component from the registry.
    
    Args:
        args: Command-line arguments
    """
    registry = ComponentRegistry()
    component = registry.get_component(args.component_id)
    
    if not component:
        print(f"Component not found: {args.component_id}")
        return
        
    # Confirm deletion if not forced
    if not args.force:
        confirm = input(f"Are you sure you want to delete {component.get('name', args.component_id)}? (y/n): ")
        if confirm.lower() != 'y':
            print("Deletion cancelled.")
            return
            
    # Delete component
    success, error = registry.delete_component(args.component_id)
    
    if success:
        print(f"Successfully deleted component: {component.get('name', args.component_id)}")
    else:
        print(f"Failed to delete component: {error}")


def create_parser() -> argparse.ArgumentParser:
    """
    Create the command-line argument parser.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Dream.OS Launcher CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for components")
    scan_parser.add_argument("--directory", "-d", default=os.getcwd(), 
                           help="Directory to scan")
    scan_parser.add_argument("--max-depth", "-m", type=int, default=10, 
                           help="Maximum directory depth")
    scan_parser.add_argument("--resume", "-r", 
                           help="Resume from checkpoint ID")
    scan_parser.add_argument("--file-patterns", "-p", nargs="+", 
                           default=["*.py", "*.js", "*.sh", "*.bat"],
                           help="File patterns to match")
    scan_parser.add_argument("--output", "-o", 
                           help="Output file for scan results")
    scan_parser.add_argument("--register", action="store_true",
                           help="Register discovered components in the registry")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List components")
    list_parser.add_argument("--type", "-t", 
                           choices=["agent", "service", "tool", "utility"],
                           help="Filter by component type")
    list_parser.add_argument("--agent", "-a", 
                           help="Filter by owner agent (e.g. 'agent-5')")
    list_parser.add_argument("--verbose", "-v", action="store_true",
                           help="Show detailed information")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a component")
    run_parser.add_argument("component_id", help="ID of the component to run")
    run_parser.add_argument("--args", "-a", 
                          help="Arguments to pass to the component")
    run_parser.add_argument("--ignore-missing-env", action="store_true",
                          help="Ignore missing environment variables")
    run_parser.add_argument("--ignore-dependencies", action="store_true",
                          help="Ignore missing dependencies")
    run_parser.add_argument("--cpu-limit", type=float,
                          help="CPU usage limit in percent")
    run_parser.add_argument("--memory-limit", type=float,
                          help="Memory usage limit in MB")
    run_parser.add_argument("--restart-policy", 
                          choices=["NEVER", "ON_FAILURE", "ALWAYS"],
                          default="NEVER",
                          help="Restart policy")
    run_parser.add_argument("--checkpoint-enabled", action="store_true",
                          help="Enable checkpointing")
    run_parser.add_argument("--checkpoint-interval", type=int, default=3600,
                          help="Checkpoint interval in seconds")
                          
    # Processes command
    processes_parser = subparsers.add_parser("processes", help="List running processes")
    processes_parser.add_argument("--component-id", "-c",
                                help="Filter by component ID")
    processes_parser.add_argument("--status", "-s",
                                choices=["running", "terminated", "crashed", "starting"],
                                help="Filter by process status")
    processes_parser.add_argument("--verbose", "-v", action="store_true",
                                help="Show detailed information")
    processes_parser.add_argument("--logs", "-l", type=int, default=20,
                                help="Show recent logs (number of lines)")
                                
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop a running process")
    stop_parser.add_argument("process_id", help="ID of the process to stop")
    stop_parser.add_argument("--force", "-f", action="store_true",
                           help="Force kill the process")
    stop_parser.add_argument("--timeout", "-t", type=int, default=30,
                           help="Timeout for graceful shutdown in seconds")
                           
    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart a running process")
    restart_parser.add_argument("process_id", help="ID of the process to restart")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show logs for a process")
    logs_parser.add_argument("process_id", help="ID of the process")
    logs_parser.add_argument("--lines", "-n", type=int, default=100,
                           help="Number of log lines to show")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a component")
    register_parser.add_argument("--file", "-f",
                               help="JSON file with component data")
    register_parser.add_argument("--id",
                               help="Component ID")
    register_parser.add_argument("--name", "-n",
                               help="Component name")
    register_parser.add_argument("--entry-point", "-e",
                               help="Entry point (path to script)")
    register_parser.add_argument("--type", "-t",
                               choices=["agent", "service", "tool", "utility"],
                               help="Component type")
    register_parser.add_argument("--description", "-d",
                               help="Component description")
    register_parser.add_argument("--owner", "-o",
                               help="Owner agent (e.g. 'agent-5')")
    register_parser.add_argument("--dependencies",
                               help="Comma-separated list of dependencies")
    register_parser.add_argument("--env-vars",
                               help="Comma-separated list of required environment variables")
    register_parser.add_argument("--tags",
                               help="Comma-separated list of tags")
                               
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a component")
    delete_parser.add_argument("component_id", help="ID of the component to delete")
    delete_parser.add_argument("--force", "-f", action="store_true",
                             help="Delete without confirmation")
    
    return parser


def main() -> int:
    """
    Main entry point for the launcher CLI.
    
    Returns:
        Exit code
    """
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
        
    try:
        if args.command == "scan":
            scan_command(args)
        elif args.command == "list":
            list_command(args)
        elif args.command == "run":
            run_command(args)
        elif args.command == "processes":
            processes_command(args)
        elif args.command == "stop":
            stop_command(args)
        elif args.command == "restart":
            restart_command(args)
        elif args.command == "logs":
            logs_command(args)
        elif args.command == "register":
            register_command(args)
        elif args.command == "delete":
            delete_command(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 