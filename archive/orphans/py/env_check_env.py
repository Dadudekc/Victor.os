# Moved to src/dreamos/tools/env/check_env.py for package compliance (2024-05-12)
"""Environment check script for Dream.OS development."""

import argparse
import importlib
import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional, Tuple

import pkg_resources
from rich.console import Console
from rich.table import Table

console = Console()


def get_system_info() -> Dict[str, Any]:
    """Get system-level information."""
    info = {
        "os": {
            "name": os.name,
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
        },
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
        },
        "hardware": {
            "processor": platform.processor(),
            "machine": platform.machine(),
        },
    }

    # Check disk space
    try:
        total, used, free = shutil.disk_usage("/")
        info["disk"] = {
            "total_gb": total // (2**30),
            "used_gb": used // (2**30),
            "free_gb": free // (2**30),
            "free_percent": (free * 100) // total,
        }
    except Exception:
        info["disk"] = {"error": "Could not get disk usage"}

    # Check Git version
    try:
        git_version = subprocess.check_output(["git", "--version"]).decode().strip()
        info["git"] = {"version": git_version}
    except Exception:
        info["git"] = {"error": "Git not found"}

    # Check NVIDIA GPU if available
    try:
        nvidia_smi = subprocess.check_output(["nvidia-smi"]).decode()
        info["gpu"] = {"available": True, "info": nvidia_smi.split("\n")[0]}
    except Exception:
        info["gpu"] = {"available": False}

    return info


def check_package(package_name: str) -> Tuple[bool, Optional[str]]:
    """Check if a package is installed and return its version."""
    try:
        version = pkg_resources.get_distribution(package_name).version
        return True, version
    except pkg_resources.DistributionNotFound:
        return False, None


def check_import(module_name: str) -> Tuple[bool, Optional[str]]:
    """Check if a module can be imported."""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "unknown")
        return True, version
    except ImportError:
        return False, None


def get_env_status() -> Tuple[bool, str, str, list, Dict[str, Any]]:
    """Return (all_passed, python_version, pythonpath_status, results_list, system_info)"""
    required_packages = {
        "Core": [
            "python-dotenv",
            "pydantic",
            "asyncio",
        ],
        "GUI and Image": [
            "imagehash",
            "pillow",
            "pyautogui",
            "mss",
        ],
        "Testing": [
            "pytest",
            "pytest-asyncio",
            "pytest-cov",
        ],
        "Logging": [
            "loguru",
            "tqdm",
        ],
        "Audio": [
            "sounddevice",
            "soundfile",
        ],
        "Scientific": [
            "numpy",
            "scipy",
        ],
    }
    all_passed = True
    results = []
    for category, packages in required_packages.items():
        for package in packages:
            installed, version = check_package(package)
            status = "✅" if installed else "❌"
            version_str = version if version else "Not installed"
            if not installed:
                all_passed = False
            results.append((category, package, status, version_str))

    python_version = sys.version.split()[0]
    pythonpath = os.environ.get("PYTHONPATH", "")
    pythonpath_status = "src" in pythonpath

    # Get system info
    system_info = get_system_info()

    return all_passed, python_version, pythonpath_status, results, system_info


def print_env_status(strict: bool = False, verbose: bool = False) -> int:
    all_passed, python_version, pythonpath_status, results, system_info = (
        get_env_status()
    )

    # Print package status
    table = Table(title="Dream.OS Environment Check")
    table.add_column("Category", style="cyan")
    table.add_column("Package", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Version", style="blue")
    for row in results:
        table.add_row(*row)
    console.print(table)

    # Print system info
    console.print("\n[bold cyan]System Information:[/bold cyan]")
    console.print(f"OS: {system_info['os']['system']} {system_info['os']['release']}")
    console.print(
        f"Python: {system_info['python']['version']} ({system_info['python']['implementation']})"
    )
    console.print(f"Processor: {system_info['hardware']['processor']}")

    if "disk" in system_info and "error" not in system_info["disk"]:
        disk = system_info["disk"]
        console.print(
            f"Disk Space: {disk['free_gb']}GB free of {disk['total_gb']}GB ({disk['free_percent']}%)"
        )

    if "git" in system_info and "error" not in system_info["git"]:
        console.print(f"Git: {system_info['git']['version']}")

    if system_info["gpu"]["available"]:
        console.print(f"GPU: {system_info['gpu']['info']}")

    # Print summary
    if all_passed:
        console.print("\n[green]✅ All required packages are installed![/green]")
    else:
        console.print(
            "\n[red]❌ Some packages are missing. Please install them using:[/red]"
        )
        console.print("pip install -r requirements.dev.txt")

    console.print(f"\n[blue]Python version: {python_version}[/blue]")
    if pythonpath_status:
        console.print("[green]✅ PYTHONPATH includes 'src' directory[/green]")
    else:
        console.print("[yellow]⚠️ PYTHONPATH does not include 'src' directory[/yellow]")
        console.print("Please set it using:")
        console.print("$env:PYTHONPATH = 'src'  # PowerShell")
        console.print("export PYTHONPATH=src    # Bash")

    # Verbose output: print all details again, or add more info if needed
    if verbose:
        console.print("\n[bold magenta]Verbose details:[/bold magenta]")
        console.print(f"System info raw: {system_info}")
        console.print(f"All package results: {results}")

    if strict and (not all_passed or not pythonpath_status):
        sys.exit(1)
    return 0 if all_passed and pythonpath_status else 1


def generate_md_report() -> str:
    all_passed, python_version, pythonpath_status, results, system_info = (
        get_env_status()
    )
    md = ["# Dream.OS Environment Status\n"]

    # System Information
    md.append("## System Information")
    md.append(f"- **OS:** {system_info['os']['system']} {system_info['os']['release']}")
    md.append(
        f"- **Python:** {system_info['python']['version']} ({system_info['python']['implementation']})"
    )
    md.append(f"- **Processor:** {system_info['hardware']['processor']}")

    if "disk" in system_info and "error" not in system_info["disk"]:
        disk = system_info["disk"]
        md.append(
            f"- **Disk Space:** {disk['free_gb']}GB free of {disk['total_gb']}GB ({disk['free_percent']}%)"
        )

    if "git" in system_info and "error" not in system_info["git"]:
        md.append(f"- **Git:** {system_info['git']['version']}")

    if system_info["gpu"]["available"]:
        md.append(f"- **GPU:** {system_info['gpu']['info']}")

    # Environment Status
    md.append("\n## Environment Status")
    md.append(f"- **Python version:** `{python_version}`")
    md.append(
        f"- **PYTHONPATH includes 'src':** {'✅' if pythonpath_status else '❌'}\n"
    )

    md.append("### Required Packages")
    md.append("| Category | Package | Status | Version |")
    md.append("|----------|---------|--------|---------|")
    for row in results:
        md.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")

    # Status Summary
    status = (
        "GREEN"
        if all_passed and pythonpath_status
        else ("WARNING" if all_passed else "FAIL")
    )
    md.append(f"\n**Overall Status:** {status}")

    if not all_passed:
        md.append("\nMissing packages: Run `pip install -r requirements.dev.txt`")
    if not pythonpath_status:
        md.append(
            "\nPYTHONPATH missing 'src'. Set with `$env:PYTHONPATH = 'src'` (PowerShell) or `export PYTHONPATH=src` (Bash)"
        )

    return "\n".join(md)


def verify_runtime_env(strict: bool = False):
    """Importable function for agent boot check."""
    return print_env_status(strict)


def main():
    """Main entry point for environment check."""
    parser = argparse.ArgumentParser(description="Check Dream.OS environment")
    parser.add_argument(
        "--report-md", action="store_true", help="Generate markdown report"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--strict", action="store_true", help="Exit with error if any checks fail"
    )
    args = parser.parse_args()

    # Print results (print_env_status now handles get_env_status internally)
    print_env_status(strict=args.strict, verbose=args.verbose)

    # Generate markdown report if requested
    if args.report_md:
        print(generate_md_report())


if __name__ == "__main__":
    main()
