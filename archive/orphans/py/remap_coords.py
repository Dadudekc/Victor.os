"""
Dream.OS Coordinate Remapper (Manual Input Version)

Shows current coordinates and allows manual input of new positions.
"""

import json
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm, IntPrompt
from rich.table import Table

console = Console()


def show_current_coords(coords: dict, agent_id: str):
    """Display current coordinates for an agent."""
    agent = coords.get(agent_id, {})
    table = Table(title=f"Current Coordinates for {agent_id}")
    table.add_column("Element", style="cyan")
    table.add_column("X", justify="right")
    table.add_column("Y", justify="right")

    if agent:
        table.add_row(
            "Input Box", str(agent["input_box"]["x"]), str(agent["input_box"]["y"])
        )
        table.add_row(
            "Copy Button",
            str(agent["copy_button"]["x"]),
            str(agent["copy_button"]["y"]),
        )
    else:
        table.add_row("No coordinates found", "-", "-")

    console.print(table)


def get_new_coords(agent_id: str) -> dict:
    """Get new coordinates via manual input."""
    console.rule(f"[bold green]New coordinates for {agent_id}")

    console.print("\n[cyan]Input Box Coordinates:")
    input_x = IntPrompt.ask("X coordinate")
    input_y = IntPrompt.ask("Y coordinate")

    console.print("\n[cyan]Copy Button Coordinates:")
    copy_x = IntPrompt.ask("X coordinate")
    copy_y = IntPrompt.ask("Y coordinate")

    return {
        "input_box": {"x": input_x, "y": input_y},
        "copy_button": {"x": copy_x, "y": copy_y},
    }


def main():
    # Load existing coordinates
    coords_path = Path("runtime/config/cursor_agent_coords.json")
    if not coords_path.exists():
        console.print("[red]❌ Coordinates file not found!")
        return

    with coords_path.open("r") as f:
        coords = json.load(f)

    # Remap Agents 6, 7, and 8
    for agent_id in ["Agent-6", "Agent-7", "Agent-8"]:
        console.print(f"\n[bold]=== {agent_id} ===")
        show_current_coords(coords, agent_id)

        if Confirm.ask(f"\nUpdate coordinates for {agent_id}?"):
            new_coords = get_new_coords(agent_id)
            coords[agent_id] = new_coords
            console.print(f"[green]✓ {agent_id} updated!")

            # Show new coordinates
            console.print("\n[bold]New coordinates:")
            show_current_coords(coords, agent_id)

    # Save updated coordinates
    if Confirm.ask("\nSave all changes?"):
        with coords_path.open("w") as f:
            json.dump(coords, f, indent=4)
        console.print("\n[green]✓ Coordinates saved!")
    else:
        console.print("\n[yellow]⚠️ Changes discarded")


if __name__ == "__main__":
    console.print("[bold]Dream.OS Coordinate Remapper (Manual Input)")
    console.print("Update coordinates for Agents 6, 7, and 8.")
    main()
