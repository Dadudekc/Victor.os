"""
Dream.OS Coordinate Validator

Validates agent coordinates by:
1. Showing a visual preview
2. Testing clicks
3. Verifying window/tab
4. Testing input typing
5. Verifying clipboard content
6. Verifying correct agent
"""

import json
import time
import pyperclip
from pathlib import Path
import pyautogui
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text

console = Console()

def get_window_info() -> str:
    """Get info about the currently active window."""
    try:
        win = pyautogui.getActiveWindow()
        if win:
            return f"Title: {win.title}\nSize: {win.width}x{win.height}"
        return "No active window"
    except Exception as e:
        return f"Error: {e}"

def verify_agent_number(agent_id: str) -> bool:
    """Verify we're clicking the correct agent's input box."""
    console.print("\n[yellow]⚠️  Please verify:")
    console.print("1. Look at the input box that was clicked")
    console.print("2. Check which agent number is shown above it")
    console.print(f"3. Confirm if it matches {agent_id}")
    
    return Confirm.ask("Is this the correct agent?")

def show_coordinate_grid(coords: dict, agent_id: str):
    """Display a visual grid showing the coordinates."""
    agent = coords.get(agent_id, {})
    if not agent:
        console.print("[red]No coordinates found for this agent")
        return

    # Get screen size
    screen_width, screen_height = pyautogui.size()
    
    # Create a simple grid representation
    grid = [[' ' for _ in range(80)] for _ in range(24)]
    
    # Mark the coordinates
    def mark_point(x, y, char):
        # Convert screen coordinates to grid coordinates
        grid_x = int((x + screen_width/2) * 80 / screen_width)
        grid_y = int((y + screen_height/2) * 24 / screen_height)
        if 0 <= grid_x < 80 and 0 <= grid_y < 24:
            grid[grid_y][grid_x] = char

    # Mark input box and copy button
    input_box = agent["input_box"]
    copy_button = agent["copy_button"]
    mark_point(input_box["x"], input_box["y"], "I")
    mark_point(copy_button["x"], copy_button["y"], "C")

    # Print the grid
    console.print("\n[bold cyan]Coordinate Grid (I=Input Box, C=Copy Button):")
    console.print("+" + "-" * 80 + "+")
    for row in grid:
        console.print("|" + "".join(row) + "|")
    console.print("+" + "-" * 80 + "+")

def test_coordinates(coords: dict, agent_id: str):
    """Test the coordinates by clicking, typing, and verifying clipboard."""
    agent = coords.get(agent_id, {})
    if not agent:
        console.print("[red]No coordinates found for this agent")
        return

    console.print(f"\n[bold]Testing coordinates for {agent_id}")
    
    # Test input box
    console.print("\n[cyan]Testing input box...")
    try:
        # Click input box
        pyautogui.click(agent["input_box"]["x"], agent["input_box"]["y"])
        time.sleep(0.5)
        win_info = get_window_info()
        console.print(f"✓ Clicked input box\n{win_info}")
        
        # Verify we're on the correct agent
        if not verify_agent_number(agent_id):
            console.print("[red]❌ Wrong agent selected! Coordinates need adjustment.")
            return
        
        # Type test message
        test_message = f"Test message for {agent_id}"
        pyautogui.write(test_message)
        time.sleep(0.5)
        console.print(f"✓ Typed test message: {test_message}")
    except Exception as e:
        console.print(f"[red]❌ Error with input box: {e}")
        return

    # Test copy button
    console.print("\n[cyan]Testing copy button...")
    try:
        # Click copy button
        pyautogui.click(agent["copy_button"]["x"], agent["copy_button"]["y"])
        time.sleep(0.5)
        win_info = get_window_info()
        console.print(f"✓ Clicked copy button\n{win_info}")
        
        # Check clipboard
        clipboard_content = pyperclip.paste()
        console.print(f"✓ Clipboard content: {clipboard_content}")
        
        # Verify clipboard content
        if test_message in clipboard_content:
            console.print("[green]✓ Clipboard verification successful!")
        else:
            console.print("[yellow]⚠️ Clipboard content doesn't match test message")
    except Exception as e:
        console.print(f"[red]❌ Error with copy button: {e}")

def main():
    # Load coordinates
    coords_path = Path("runtime/config/cursor_agent_coords.json")
    if not coords_path.exists():
        console.print("[red]❌ Coordinates file not found!")
        return
    
    with coords_path.open("r") as f:
        coords = json.load(f)
    
    # Validate Agents 6, 7, and 8
    for agent_id in ["Agent-6", "Agent-7", "Agent-8"]:
        console.rule(f"[bold green]{agent_id}")
        
        # Show current coordinates
        table = Table(title=f"Current Coordinates for {agent_id}")
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
        
        # Show coordinate grid
        show_coordinate_grid(coords, agent_id)
        
        # Test coordinates
        if Confirm.ask(f"\nTest coordinates for {agent_id}?"):
            test_coordinates(coords, agent_id)
        
        if not Confirm.ask(f"\nContinue to next agent?"):
            break

if __name__ == "__main__":
    console.print("[bold]Dream.OS Coordinate Validator")
    console.print("Validates coordinates for Agents 6, 7, and 8.")
    main() 