"""
Dream.OS Coordinate Mapper

Maps coordinates for all agent input boxes and copy buttons.
"""

import json
import time
from pathlib import Path
import pyautogui
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.live import Live
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
    countdown(3, "Capturing input box coordinates")
    x, y = pyautogui.position()
    coords["input_box"] = {"x": x, "y": y}
    console.print(f"✓ Input box: ({x}, {y})")
    
    # Verify input box coordinates
    if not Confirm.ask("Are these the correct input box coordinates?"):
        return get_coordinates(agent_id)  # Retry
    
    # Get copy button coordinates
    console.print(f"\n[cyan]Position your mouse over the copy button for {agent_id}...")
    countdown(3, "Capturing copy button coordinates")
    x, y = pyautogui.position()
    coords["copy_button"] = {"x": x, "y": y}
    console.print(f"✓ Copy button: ({x}, {y})")
    
    # Verify copy button coordinates
    if not Confirm.ask("Are these the correct copy button coordinates?"):
        return get_coordinates(agent_id)  # Retry
    
    # Verify coordinates are different
    if (coords["input_box"]["x"] == coords["copy_button"]["x"] and 
        coords["input_box"]["y"] == coords["copy_button"]["y"]):
        console.print("[red]⚠️ Input box and copy button have the same coordinates!")
        if not Confirm.ask("Do you want to retry?"):
            return get_coordinates(agent_id)  # Retry
    
    return coords

def show_coordinates(coords: dict, agent_id: str):
    """Display current coordinates for an agent."""
    table = Table(title=f"Coordinates for {agent_id}")
    table.add_column("Element", style="cyan")
    table.add_column("X", justify="right")
    table.add_column("Y", justify="right")
    
    agent = coords.get(agent_id, {})
    if agent:
        table.add_row("Input Box", 
                     str(agent["input_box"]["x"]), 
                     str(agent["input_box"]["y"]))
        table.add_row("Copy Button", 
                     str(agent["copy_button"]["x"]), 
                     str(agent["copy_button"]["y"]))
    console.print(table)

def main():
    # Initialize coordinates
    coords = {}
    
    # Map coordinates for all agents
    for i in range(1, 9):
        agent_id = f"Agent-{i}"
        console.rule(f"[bold green]{agent_id}")
        
        if Confirm.ask(f"Map coordinates for {agent_id}?"):
            coords[agent_id] = get_coordinates(agent_id)
            console.print(f"\n[green]✓ {agent_id} mapped!")
            
            # Show coordinates
            show_coordinates(coords, agent_id)
            
            # Final verification
            if not Confirm.ask("Are these coordinates correct?"):
                console.print("[yellow]Retrying...")
                i -= 1  # Retry this agent
                continue
        
        if not Confirm.ask("\nContinue to next agent?"):
            break
    
    # Save coordinates
    if coords and Confirm.ask("\nSave all coordinates?"):
        coords_path = Path("runtime/config/cursor_agent_coords.json")
        coords_path.parent.mkdir(parents=True, exist_ok=True)
        with coords_path.open("w") as f:
            json.dump(coords, f, indent=4)
        console.print("\n[green]✓ Coordinates saved!")
    else:
        console.print("\n[yellow]⚠️ Changes discarded")

if __name__ == "__main__":
    console.print("[bold]Dream.OS Coordinate Mapper")
    console.print("Map coordinates for all agent input boxes and copy buttons.")
    main() 