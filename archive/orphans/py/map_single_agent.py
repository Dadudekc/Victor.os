"""
Dream.OS Single Agent Coordinate Mapper

Maps coordinates for a single agent's input box and copy button.
"""

import json
import time
from pathlib import Path

import pyautogui
from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

console = Console()


def countdown(seconds: int, message: str):
    """Show a countdown timer."""
    with Live(console=console, refresh_per_second=1) as live:
        for i in range(seconds, 0, -1):
            live.update(Text(f"{message} in {i}...", style="bold yellow"))
            time.sleep(1)
        live.update(Text("Click now!", style="bold green"))


def get_coordinates(agent_id: str) -> dict:
    """Get coordinates for an agent's input box and copy button."""
    coords = {}

    # Get input box coordinates
    console.print(f"\n[cyan]Position your mouse over the input box for {agent_id}...")
    countdown(5, "Capturing input box coordinates")
    x, y = pyautogui.position()
    coords["input_box"] = {"x": x, "y": y}
    console.print(f"✓ Input box: ({x}, {y})")

    # Verify input box coordinates
    while True:
        try:
            response = Prompt.ask(
                "Are these coordinates correct?",
                choices=["yes", "no", "skip"],
                default="yes",
            )
            if response == "skip":
                return None
            if response == "no":
                return get_coordinates(agent_id)  # Retry
            break
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled")
            return None

    # Get copy button coordinates
    console.print(f"\n[cyan]Position your mouse over the copy button for {agent_id}...")
    countdown(5, "Capturing copy button coordinates")
    x, y = pyautogui.position()
    coords["copy_button"] = {"x": x, "y": y}
    console.print(f"✓ Copy button: ({x}, {y})")

    # Verify copy button coordinates
    while True:
        try:
            response = Prompt.ask(
                "Are these coordinates correct?",
                choices=["yes", "no", "skip"],
                default="yes",
            )
            if response == "skip":
                return None
            if response == "no":
                return get_coordinates(agent_id)  # Retry
            break
        except KeyboardInterrupt:
            console.print("\n[yellow]Operation cancelled")
            return None

    # Verify coordinates are different
    if (
        coords["input_box"]["x"] == coords["copy_button"]["x"]
        and coords["input_box"]["y"] == coords["copy_button"]["y"]
    ):
        console.print("[red]⚠️ Input box and copy button have the same coordinates!")
        while True:
            try:
                response = Prompt.ask(
                    "What would you like to do?",
                    choices=["retry", "skip"],
                    default="retry",
                )
                if response == "skip":
                    return None
                return get_coordinates(agent_id)  # Retry
            except KeyboardInterrupt:
                console.print("\n[yellow]Operation cancelled")
                return None

    return coords


def show_coordinates(coords: dict, agent_id: str):
    """Display current coordinates for an agent."""
    table = Table(title=f"Coordinates for {agent_id}")
    table.add_column("Element", style="cyan")
    table.add_column("X", justify="right")
    table.add_column("Y", justify="right")

    agent = coords.get(agent_id, {})
    if agent:
        table.add_row(
            "Input Box", str(agent["input_box"]["x"]), str(agent["input_box"]["y"])
        )
        table.add_row(
            "Copy Button",
            str(agent["copy_button"]["x"]),
            str(agent["copy_button"]["y"]),
        )
    console.print(table)


def main():
    # Load existing coordinates
    coords_path = Path("runtime/config/cursor_agent_coords.json")
    if not coords_path.exists():
        console.print("[red]❌ Coordinates file not found!")
        return

    with coords_path.open("r") as f:
        coords = json.load(f)

    # Show current coordinates
    console.print("\n[bold]Current coordinates:")
    for agent_id in sorted(coords.keys()):
        show_coordinates(coords, agent_id)

    # Get agent ID to map
    agent_id = Prompt.ask(
        "\nWhich agent would you like to map?",
        choices=[f"Agent-{i}" for i in range(1, 9)],
        default="Agent-5",
    )

    console.rule(f"[bold green]{agent_id}")

    # Get new coordinates
    new_coords = get_coordinates(agent_id)
    if new_coords:
        coords[agent_id] = new_coords
        console.print(f"\n[green]✓ {agent_id} mapped!")

        # Show new coordinates
        show_coordinates(coords, agent_id)

        # Save coordinates
        if Confirm.ask("\nSave coordinates?"):
            with coords_path.open("w") as f:
                json.dump(coords, f, indent=4)
            console.print("\n[green]✓ Coordinates saved!")
        else:
            console.print("\n[yellow]⚠️ Changes discarded")
    else:
        console.print(f"\n[yellow]⚠️ {agent_id} mapping cancelled")


if __name__ == "__main__":
    console.print("[bold]Dream.OS Single Agent Coordinate Mapper")
    console.print("Map coordinates for a single agent while preserving others.")
    main()
