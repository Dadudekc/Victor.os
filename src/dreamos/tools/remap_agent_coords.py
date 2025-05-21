"""
Agent Coordinate Remapper for Dream.OS

This script helps remap agent coordinates by providing an interactive interface
to capture and validate input box and copy button positions for each agent.
"""

import json
import time
import logging
from pathlib import Path
import pyautogui
from rich.console import Console
from rich.prompt import Confirm, IntPrompt
from rich.table import Table
from rich.progress import Progress

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

class AgentCoordRemapper:
    def __init__(self):
        self.coords_path = Path("src/runtime/config/cursor_agent_coords.json")
        self.coords = self._load_coordinates()
        
    def _load_coordinates(self) -> dict:
        """Load existing coordinates or create new structure."""
        if self.coords_path.exists():
            with self.coords_path.open("r") as f:
                return json.load(f)
        return {}
        
    def _save_coordinates(self):
        """Save coordinates to file."""
        self.coords_path.parent.mkdir(parents=True, exist_ok=True)
        with self.coords_path.open("w") as f:
            json.dump(self.coords, f, indent=4)
        logger.info(f"✅ Saved coordinates to {self.coords_path}")
        
    def show_current_coords(self, agent_id: str):
        """Display current coordinates for an agent."""
        agent = self.coords.get(agent_id, {})
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
        
    def capture_coordinates(self, agent_id: str) -> dict:
        """Capture new coordinates for an agent."""
        console.rule(f"[bold green]Capturing coordinates for {agent_id}")
        
        # Show countdown and instructions
        with Progress() as progress:
            task = progress.add_task("[cyan]Position your mouse...", total=5)
            for i in range(5, 0, -1):
                progress.update(task, completed=5-i)
                console.print(f"\n[cyan]Move mouse to {agent_id}'s input box in {i} seconds...")
                time.sleep(1)
                
        # Get input box coordinates
        input_x, input_y = pyautogui.position()
        console.print(f"✓ Input box: ({input_x}, {input_y})")
        
        # Verify input box coordinates
        if not Confirm.ask("Are these input box coordinates correct?"):
            return self.capture_coordinates(agent_id)
            
        # Show countdown for copy button
        with Progress() as progress:
            task = progress.add_task("[cyan]Position your mouse...", total=5)
            for i in range(5, 0, -1):
                progress.update(task, completed=5-i)
                console.print(f"\n[cyan]Move mouse to {agent_id}'s copy button in {i} seconds...")
                time.sleep(1)
                
        # Get copy button coordinates
        copy_x, copy_y = pyautogui.position()
        console.print(f"✓ Copy button: ({copy_x}, {copy_y})")
        
        # Verify copy button coordinates
        if not Confirm.ask("Are these copy button coordinates correct?"):
            return self.capture_coordinates(agent_id)
            
        return {
            "input_box": {"x": input_x, "y": input_y},
            "copy_button": {"x": copy_x, "y": copy_y},
            "input_box_initial": {"x": input_x, "y": input_y}
        }
        
    def remap_agent(self, agent_id: str):
        """Remap coordinates for a specific agent."""
        self.show_current_coords(agent_id)
        
        if Confirm.ask(f"\nRemap coordinates for {agent_id}?"):
            new_coords = self.capture_coordinates(agent_id)
            self.coords[agent_id] = new_coords
            self._save_coordinates()
            console.print(f"\n[green]✓ Updated coordinates for {agent_id}")
            
    def remap_all_agents(self):
        """Remap coordinates for all agents."""
        agents = [f"Agent-{i}" for i in range(1, 9)]
        
        for agent_id in agents:
            self.remap_agent(agent_id)
            if not Confirm.ask("\nContinue to next agent?"):
                break
                
    def validate_coordinates(self, agent_id: str):
        """Validate coordinates by simulating a click."""
        agent = self.coords.get(agent_id, {})
        if not agent:
            console.print(f"[red]No coordinates found for {agent_id}")
            return
            
        console.print(f"\n[cyan]Validating coordinates for {agent_id}...")
        
        # Test input box
        try:
            pyautogui.click(agent["input_box"]["x"], agent["input_box"]["y"])
            time.sleep(0.5)
            console.print("[green]✓ Input box click successful")
        except Exception as e:
            console.print(f"[red]❌ Error clicking input box: {e}")
            
        # Test copy button
        try:
            pyautogui.click(agent["copy_button"]["x"], agent["copy_button"]["y"])
            time.sleep(0.5)
            console.print("[green]✓ Copy button click successful")
        except Exception as e:
            console.print(f"[red]❌ Error clicking copy button: {e}")

def main():
    remapper = AgentCoordRemapper()
    
    while True:
        console.print("\n[bold cyan]Dream.OS Agent Coordinate Remapper")
        console.print("1. Remap single agent")
        console.print("2. Remap all agents")
        console.print("3. Validate coordinates")
        console.print("4. Show current coordinates")
        console.print("5. Exit")
        
        choice = IntPrompt.ask("\nSelect an option", choices=["1", "2", "3", "4", "5"])
        
        if choice == 1:
            agent_num = IntPrompt.ask("Enter agent number", choices=[str(i) for i in range(1, 9)])
            remapper.remap_agent(f"Agent-{agent_num}")
        elif choice == 2:
            remapper.remap_all_agents()
        elif choice == 3:
            agent_num = IntPrompt.ask("Enter agent number", choices=[str(i) for i in range(1, 9)])
            remapper.validate_coordinates(f"Agent-{agent_num}")
        elif choice == 4:
            agent_num = IntPrompt.ask("Enter agent number", choices=[str(i) for i in range(1, 9)])
            remapper.show_current_coords(f"Agent-{agent_num}")
        elif choice == 5:
            break

if __name__ == "__main__":
    main() 