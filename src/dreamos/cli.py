#!/usr/bin/env python3
"""
Victor.os Command Line Interface
Comprehensive CLI for managing and interacting with Victor.os
"""

import os
import sys
import json
import click
import subprocess
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

console = Console()

@click.group()
@click.version_option(version="2.0.0", prog_name="Victor.os")
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--config', type=click.Path(exists=True), help='Path to config file')
def cli(debug: bool, config: Optional[str]):
    """Victor.os - AI-native operating system for agent swarms"""
    if debug:
        console.print("[yellow]Debug mode enabled[/yellow]")
    
    if config:
        console.print(f"[blue]Using config: {config}[/blue]")

@cli.command()
@click.option('--quick', is_flag=True, help='Quick installation (minimal dependencies)')
@click.option('--full', is_flag=True, help='Full installation (all dependencies)')
@click.option('--dev', is_flag=True, help='Development installation (includes dev tools)')
def install(quick: bool, full: bool, dev: bool):
    """Install Victor.os and dependencies"""
    console.print(Panel.fit("🚀 Victor.os Installation", style="bold blue"))
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Installing Victor.os...", total=None)
        
        try:
            # Run the installation script
            install_script = Path("scripts/install.py")
            if install_script.exists():
                cmd = [sys.executable, str(install_script)]
                if dev:
                    cmd.append("--dev")
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    progress.update(task, description="✅ Installation completed")
                    console.print("\n[green]Victor.os installed successfully![/green]")
                else:
                    progress.update(task, description="❌ Installation failed")
                    console.print(f"\n[red]Installation failed:[/red]\n{result.stderr}")
            else:
                progress.update(task, description="❌ Install script not found")
                console.print("[red]Installation script not found at scripts/install.py[/red]")
                
        except Exception as e:
            progress.update(task, description="❌ Installation error")
            console.print(f"[red]Installation error: {e}[/red]")

@cli.command()
@click.option('--all', is_flag=True, help='Run all tests')
@click.option('--unit', is_flag=True, help='Run unit tests only')
@click.option('--integration', is_flag=True, help='Run integration tests only')
@click.option('--coverage', is_flag=True, help='Generate coverage report')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def test(all: bool, unit: bool, integration: bool, coverage: bool, verbose: bool):
    """Run Victor.os test suite"""
    console.print(Panel.fit("🧪 Victor.os Test Suite", style="bold green"))
    
    cmd = [sys.executable, "-m", "pytest"]
    
    if all:
        cmd.extend(["tests/"])
    elif unit:
        cmd.extend(["tests/unit/"])
    elif integration:
        cmd.extend(["tests/integration/"])
    else:
        cmd.extend(["tests/"])
    
    if verbose:
        cmd.extend(["-v", "--tb=short"])
    
    if coverage:
        cmd.extend(["--cov=src", "--cov-report=html", "--cov-report=term"])
    
    console.print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd)
        if result.returncode == 0:
            console.print("[green]✅ All tests passed![/green]")
        else:
            console.print("[red]❌ Some tests failed[/red]")
    except Exception as e:
        console.print(f"[red]Test execution error: {e}[/red]")

@cli.command()
@click.option('--config', is_flag=True, help='Show configuration')
@click.option('--status', is_flag=True, help='Show system status')
@click.option('--agents', is_flag=True, help='Show agent status')
@click.option('--logs', is_flag=True, help='Show recent logs')
def status(config: bool, status_flag: bool, agents: bool, logs: bool):
    """Show Victor.os system status"""
    console.print(Panel.fit("📊 Victor.os Status", style="bold cyan"))
    
    if config:
        show_configuration()
    elif status_flag:
        show_system_status()
    elif agents:
        show_agent_status()
    elif logs:
        show_recent_logs()
    else:
        # Show all status information
        show_configuration()
        console.print()
        show_system_status()
        console.print()
        show_agent_status()
        console.print()
        show_recent_logs()

def show_configuration():
    """Show current configuration"""
    console.print("[bold]Configuration:[/bold]")
    
    config_files = [
        "runtime/config/system.json",
        "runtime/config/agents.json",
        "runtime/config/empathy.json",
        "runtime/config/ethos.json"
    ]
    
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                console.print(f"  [blue]{config_file}:[/blue] ✅ Loaded")
            except Exception as e:
                console.print(f"  [red]{config_file}:[/red] ❌ Error: {e}")
        else:
            console.print(f"  [yellow]{config_file}:[/yellow] ⚠️  Not found")

def show_system_status():
    """Show system status"""
    console.print("[bold]System Status:[/bold]")
    
    # Check if runtime directories exist
    runtime_dirs = [
        "runtime/config",
        "runtime/logs", 
        "runtime/data",
        "runtime/cache"
    ]
    
    for dir_path in runtime_dirs:
        if Path(dir_path).exists():
            console.print(f"  [green]{dir_path}:[/green] ✅ Ready")
        else:
            console.print(f"  [red]{dir_path}:[/red] ❌ Missing")

def show_agent_status():
    """Show agent status"""
    console.print("[bold]Agent Status:[/bold]")
    
    # Check agent mailboxes
    mailbox_dirs = [
        "agent_tools/mailbox",
        "prompts/agent_inboxes",
        "runtime/agent_comms/agent_mailboxes"
    ]
    
    for mailbox_dir in mailbox_dirs:
        if Path(mailbox_dir).exists():
            agent_count = len([d for d in Path(mailbox_dir).iterdir() if d.is_dir()])
            console.print(f"  [blue]{mailbox_dir}:[/blue] {agent_count} agents")
        else:
            console.print(f"  [yellow]{mailbox_dir}:[/yellow] ⚠️  Not found")

def show_recent_logs():
    """Show recent logs"""
    console.print("[bold]Recent Logs:[/bold]")
    
    log_dir = Path("runtime/logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            # Show most recent log file
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            try:
                with open(latest_log, 'r') as f:
                    lines = f.readlines()
                    console.print(f"  [blue]Latest log ({latest_log.name}):[/blue]")
                    for line in lines[-5:]:  # Last 5 lines
                        console.print(f"    {line.strip()}")
            except Exception as e:
                console.print(f"  [red]Error reading log: {e}[/red]")
        else:
            console.print("  [yellow]No log files found[/yellow]")
    else:
        console.print("  [red]Log directory not found[/red]")

@cli.command()
@click.option('--start', is_flag=True, help='Start Victor.os runtime')
@click.option('--stop', is_flag=True, help='Stop Victor.os runtime')
@click.option('--restart', is_flag=True, help='Restart Victor.os runtime')
@click.option('--daemon', is_flag=True, help='Run as daemon')
def runtime(start: bool, stop: bool, restart: bool, daemon: bool):
    """Manage Victor.os runtime"""
    console.print(Panel.fit("⚙️  Victor.os Runtime Management", style="bold magenta"))
    
    if start:
        start_runtime(daemon)
    elif stop:
        stop_runtime()
    elif restart:
        stop_runtime()
        console.print("Restarting...")
        start_runtime(daemon)
    else:
        # Show runtime status
        show_runtime_status()

def start_runtime(daemon: bool):
    """Start Victor.os runtime"""
    console.print("Starting Victor.os runtime...")
    
    try:
        from src.dreamos.runtime.runtime_manager import RuntimeManager
        runtime = RuntimeManager()
        
        if daemon:
            # TODO: Implement daemon mode
            console.print("[yellow]Daemon mode not yet implemented[/yellow]")
        else:
            runtime.start()
    except ImportError as e:
        console.print(f"[red]Failed to import runtime manager: {e}[/red]")
    except Exception as e:
        console.print(f"[red]Failed to start runtime: {e}[/red]")

def stop_runtime():
    """Stop Victor.os runtime"""
    console.print("Stopping Victor.os runtime...")
    # TODO: Implement graceful shutdown
    console.print("[yellow]Runtime stop not yet implemented[/yellow]")

def show_runtime_status():
    """Show runtime status"""
    console.print("[bold]Runtime Status:[/bold]")
    console.print("  [yellow]Runtime status check not yet implemented[/yellow]")

@cli.command()
@click.option('--create', help='Create new agent')
@click.option('--list', 'list_agents', is_flag=True, help='List all agents')
@click.option('--status', help='Show agent status')
@click.option('--logs', help='Show agent logs')
def agent(create: Optional[str], list_agents: bool, status: Optional[str], logs: Optional[str]):
    """Manage Victor.os agents"""
    console.print(Panel.fit("🤖 Victor.os Agent Management", style="bold yellow"))
    
    if create:
        create_agent(create)
    elif list_agents:
        list_all_agents()
    elif status:
        show_agent_status_detail(status)
    elif logs:
        show_agent_logs(logs)
    else:
        console.print("Use --help for agent management options")

def create_agent(agent_name: str):
    """Create a new agent"""
    console.print(f"Creating agent: {agent_name}")
    
    # Create agent directory structure
    agent_dirs = [
        f"agent_tools/mailbox/{agent_name}",
        f"prompts/agent_inboxes/{agent_name}",
        f"runtime/agent_comms/agent_mailboxes/{agent_name}"
    ]
    
    for agent_dir in agent_dirs:
        Path(agent_dir).mkdir(parents=True, exist_ok=True)
        
        # Create default mailbox files
        mailbox_files = ["inbox.json", "outbox.json", "status.json"]
        for mailbox_file in mailbox_files:
            mailbox_path = Path(agent_dir) / mailbox_file
            if not mailbox_path.exists():
                with open(mailbox_path, 'w') as f:
                    json.dump({}, f, indent=2)
    
    console.print(f"[green]✅ Agent '{agent_name}' created successfully[/green]")

def list_all_agents():
    """List all agents"""
    console.print("[bold]Available Agents:[/bold]")
    
    agent_dirs = [
        "agent_tools/mailbox",
        "prompts/agent_inboxes", 
        "runtime/agent_comms/agent_mailboxes"
    ]
    
    all_agents = set()
    for agent_dir in agent_dirs:
        if Path(agent_dir).exists():
            agents = [d.name for d in Path(agent_dir).iterdir() if d.is_dir()]
            all_agents.update(agents)
    
    if all_agents:
        for agent in sorted(all_agents):
            console.print(f"  • {agent}")
    else:
        console.print("  [yellow]No agents found[/yellow]")

def show_agent_status_detail(agent_name: str):
    """Show detailed agent status"""
    console.print(f"[bold]Agent Status: {agent_name}[/bold]")
    console.print("[yellow]Detailed agent status not yet implemented[/yellow]")

def show_agent_logs(agent_name: str):
    """Show agent logs"""
    console.print(f"[bold]Agent Logs: {agent_name}[/bold]")
    console.print("[yellow]Agent logs not yet implemented[/yellow]")

@cli.command()
@click.option('--clean', is_flag=True, help='Clean temporary files')
@click.option('--logs', is_flag=True, help='Clean old logs')
@click.option('--cache', is_flag=True, help='Clean cache')
@click.option('--all', is_flag=True, help='Clean everything')
def cleanup(clean: bool, logs: bool, cache: bool, all: bool):
    """Clean up Victor.os files"""
    console.print(Panel.fit("🧹 Victor.os Cleanup", style="bold red"))
    
    if all or clean:
        cleanup_temp_files()
    if all or logs:
        cleanup_old_logs()
    if all or cache:
        cleanup_cache()
    
    if not any([clean, logs, cache, all]):
        # Default cleanup
        cleanup_temp_files()

def cleanup_temp_files():
    """Clean temporary files"""
    console.print("Cleaning temporary files...")
    
    # Remove Python cache
    for root, dirs, files in os.walk("."):
        for dir in dirs:
            if dir == "__pycache__":
                cache_path = os.path.join(root, dir)
                try:
                    import shutil
                    shutil.rmtree(cache_path)
                    console.print(f"  ✅ Removed {cache_path}")
                except Exception as e:
                    console.print(f"  ❌ Failed to remove {cache_path}: {e}")
    
    # Clean temp directories
    temp_dirs = ["runtime/temp", "temp"]
    for temp_dir in temp_dirs:
        if Path(temp_dir).exists():
            try:
                import shutil
                shutil.rmtree(temp_dir)
                Path(temp_dir).mkdir(parents=True, exist_ok=True)
                console.print(f"  ✅ Cleaned {temp_dir}")
            except Exception as e:
                console.print(f"  ❌ Failed to clean {temp_dir}: {e}")

def cleanup_old_logs():
    """Clean old log files"""
    console.print("Cleaning old logs...")
    console.print("[yellow]Log cleanup not yet implemented[/yellow]")

def cleanup_cache():
    """Clean cache files"""
    console.print("Cleaning cache...")
    console.print("[yellow]Cache cleanup not yet implemented[/yellow]")

@cli.command()
@click.option('--docs', is_flag=True, help='Generate documentation')
@click.option('--api', is_flag=True, help='Generate API docs')
@click.option('--coverage', is_flag=True, help='Generate coverage report')
def generate(docs: bool, api: bool, coverage: bool):
    """Generate Victor.os documentation and reports"""
    console.print(Panel.fit("📚 Victor.os Documentation Generator", style="bold blue"))
    
    if docs:
        generate_documentation()
    if api:
        generate_api_docs()
    if coverage:
        generate_coverage_report()
    
    if not any([docs, api, coverage]):
        # Generate all
        generate_documentation()
        generate_api_docs()
        generate_coverage_report()

def generate_documentation():
    """Generate documentation"""
    console.print("Generating documentation...")
    console.print("[yellow]Documentation generation not yet implemented[/yellow]")

def generate_api_docs():
    """Generate API documentation"""
    console.print("Generating API documentation...")
    console.print("[yellow]API documentation generation not yet implemented[/yellow]")

def generate_coverage_report():
    """Generate coverage report"""
    console.print("Generating coverage report...")
    
    try:
        cmd = [sys.executable, "-m", "pytest", "--cov=src", "--cov-report=html", "--cov-report=term"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            console.print("[green]✅ Coverage report generated[/green]")
            console.print("  📊 HTML report: htmlcov/index.html")
        else:
            console.print("[red]❌ Coverage report generation failed[/red]")
    except Exception as e:
        console.print(f"[red]Coverage generation error: {e}[/red]")

@cli.command()
def dashboard():
    """Launch Victor.os dashboard"""
    console.print(Panel.fit("📊 Victor.os Dashboard", style="bold green"))
    
    try:
        from src.dreamos.agent_dashboard.dashboard import Dashboard
        dashboard = Dashboard()
        dashboard.run()
    except ImportError as e:
        console.print(f"[red]Failed to import dashboard: {e}[/red]")
        console.print("[yellow]Make sure PyQt5 is installed[/yellow]")
    except Exception as e:
        console.print(f"[red]Failed to launch dashboard: {e}[/red]")

@cli.command()
def doctor():
    """Diagnose Victor.os installation and configuration"""
    console.print(Panel.fit("🏥 Victor.os Doctor", style="bold cyan"))
    
    # Check Python version
    console.print("[bold]Python Environment:[/bold]")
    console.print(f"  Python version: {sys.version}")
    console.print(f"  Python path: {sys.executable}")
    
    # Check dependencies
    console.print("\n[bold]Dependencies:[/bold]")
    required_deps = [
        "pytest", "PyQt5", "requests", "aiohttp", "fastapi", 
        "pydantic", "pyautogui", "pandas", "numpy", "discord"
    ]
    
    for dep in required_deps:
        try:
            __import__(dep)
            console.print(f"  ✅ {dep}")
        except ImportError:
            console.print(f"  ❌ {dep}")
    
    # Check file structure
    console.print("\n[bold]File Structure:[/bold]")
    required_dirs = [
        "src/dreamos", "runtime/config", "runtime/logs", 
        "tests", "docs", "scripts"
    ]
    
    for dir_path in required_dirs:
        if Path(dir_path).exists():
            console.print(f"  ✅ {dir_path}")
        else:
            console.print(f"  ❌ {dir_path}")
    
    # Check configuration
    console.print("\n[bold]Configuration:[/bold]")
    config_files = [
        "runtime/config/system.json",
        "runtime/config/agents.json",
        "runtime/config/empathy.json",
        "runtime/config/ethos.json"
    ]
    
    for config_file in config_files:
        if Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    json.load(f)
                console.print(f"  ✅ {config_file}")
            except Exception as e:
                console.print(f"  ⚠️  {config_file} (invalid JSON: {e})")
        else:
            console.print(f"  ❌ {config_file}")

def main():
    """Main CLI entry point"""
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]CLI error: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main() 