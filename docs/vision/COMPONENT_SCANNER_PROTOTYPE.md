# Dream.OS Component Scanner Prototype

**Version:** 0.1.0  
**Last Updated:** 2024-07-23  
**Status:** PROTOTYPE  
**Author:** Agent-5 (Task System Engineer)

## Overview

This document outlines the prototype design for a component scanner tool that will discover and catalog all executable components within the Dream.OS project. This is the first step toward implementing the centralized launcher system outlined in the [Centralized Launcher Plan](CENTRALIZED_LAUNCHER_PLAN.md).

## Scanner Implementation

Below is a prototype implementation for the component scanner tool. This code would be placed in `src/dreamos/launcher/scanner.py`:

```python
"""
Dream.OS Component Scanner

A tool to discover and catalog all executable components in the Dream.OS project.
"""

import os
import sys
import ast
import json
import logging
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Set, Any

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("dreamos.launcher.scanner")

# Constants
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Adjust based on actual location
REGISTRY_DIR = PROJECT_ROOT / "runtime" / "launcher"
REGISTRY_FILE = REGISTRY_DIR / "component_registry.json"
EXCLUDED_DIRS = {".git", ".vscode", "__pycache__", "venv", "env", ".env", "node_modules"}
EXCLUDED_FILES = {"setup.py", "__init__.py"}

class ComponentScanner:
    """Scanner for discovering executable components in the Dream.OS project."""
    
    def __init__(self):
        """Initialize the component scanner."""
        self.components = {}
        self.registry_dir = REGISTRY_DIR
        self.registry_file = REGISTRY_FILE
        
        # Ensure registry directory exists
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
    def scan_directory(self, directory: Path, exclude_patterns: Set[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Scan a directory recursively for executable Python scripts.
        
        Args:
            directory: The directory to scan
            exclude_patterns: Patterns to exclude
            
        Returns:
            Dictionary of discovered components
        """
        if exclude_patterns is None:
            exclude_patterns = set()
            
        logger.info(f"Scanning directory: {directory}")
        
        for item in directory.iterdir():
            # Skip excluded directories and patterns
            if item.name in EXCLUDED_DIRS or any(pattern in str(item) for pattern in exclude_patterns):
                logger.debug(f"Skipping excluded item: {item}")
                continue
                
            if item.is_dir():
                # Recursively scan subdirectories
                sub_components = self.scan_directory(item, exclude_patterns)
                self.components.update(sub_components)
            elif item.is_file() and item.suffix == ".py" and item.name not in EXCLUDED_FILES:
                # Process Python files
                component = self._analyze_python_file(item)
                if component:
                    component_id = component["component_id"]
                    self.components[component_id] = component
                    logger.info(f"Discovered component: {component_id} ({component['name']})")
                    
        return self.components
        
    def _analyze_python_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a Python file for component metadata.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Component metadata dict or None if not a component
        """
        try:
            # Read the file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Parse the AST
            tree = ast.parse(content)
            
            # Check if this has a main block
            has_main_block = False
            has_executable_code = False
            docstring = None
            
            # Extract the module docstring if present
            if (tree.body and isinstance(tree.body[0], ast.Expr) and 
                isinstance(tree.body[0].value, ast.Str)):
                docstring = tree.body[0].value.s
                
            # Look for if __name__ == "__main__" block
            for node in ast.walk(tree):
                if (isinstance(node, ast.If) and 
                    isinstance(node.test, ast.Compare) and
                    isinstance(node.test.left, ast.Name) and
                    node.test.left.id == "__name__" and
                    isinstance(node.test.comparators[0], ast.Str) and
                    node.test.comparators[0].s == "__main__"):
                    has_main_block = True
                    break
                    
            # Check if the file contains class definitions
            has_classes = any(isinstance(node, ast.ClassDef) for node in tree.body)
            
            # If it's not an executable file or a class definition, skip it
            if not has_main_block and not has_classes:
                return None
                
            # Generate a component ID from the file path
            rel_path = file_path.relative_to(PROJECT_ROOT)
            component_id = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            
            # Extract name from the filename or docstring
            name = file_path.stem
            description = ""
            
            if docstring:
                # Try to extract a better name and description from the docstring
                lines = docstring.strip().split("\n")
                if lines:
                    # First line is typically a title
                    name = lines[0].strip()
                    
                    # Rest is description
                    if len(lines) > 1:
                        description = "\n".join(lines[1:]).strip()
            
            # Determine the component type
            component_type = "utility"  # Default
            if "agent" in str(file_path).lower():
                component_type = "agent"
            elif "service" in str(file_path).lower():
                component_type = "service"
            elif "tool" in str(file_path).lower() or "cli" in str(file_path).lower():
                component_type = "tool"
                
            # Create the component metadata
            component = {
                "component_id": component_id,
                "name": name,
                "description": description,
                "entry_point": str(rel_path),
                "type": component_type,
                "owner_agent": self._infer_owner_agent(file_path),
                "dependencies": [],  # Would require more sophisticated analysis
                "required_env_vars": [],  # Would require more sophisticated analysis
                "config_files": [],  # Would require more sophisticated analysis
                "suggested_args": "",
                "documentation": self._find_documentation(file_path),
                "tags": self._infer_tags(file_path, content),
                "is_executable": has_main_block,
                "has_classes": has_classes,
                "discovery_timestamp": str(datetime.datetime.now().isoformat())
            }
            
            return component
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return None
            
    def _infer_owner_agent(self, file_path: Path) -> str:
        """Infer the owner agent based on file path."""
        path_str = str(file_path).lower()
        
        if "agent1" in path_str or "captain" in path_str:
            return "agent-1"
        elif "agent2" in path_str or "infrastructure" in path_str:
            return "agent-2"
        elif "agent3" in path_str or "loop" in path_str:
            return "agent-3"
        elif "agent4" in path_str or "integration" in path_str:
            return "agent-4"
        elif "agent5" in path_str or "task" in path_str:
            return "agent-5"
        elif "agent6" in path_str or "feedback" in path_str:
            return "agent-6"
        elif "agent7" in path_str or "ux" in path_str or "ui" in path_str:
            return "agent-7"
        elif "agent8" in path_str or "test" in path_str:
            return "agent-8"
        else:
            return "unassigned"
            
    def _infer_tags(self, file_path: Path, content: str) -> List[str]:
        """Infer tags based on file path and content."""
        tags = []
        path_str = str(file_path).lower()
        
        # Add tags based on directory structure
        if "agent" in path_str:
            tags.append("agent")
        if "tool" in path_str:
            tags.append("tool")
        if "service" in path_str:
            tags.append("service")
        if "test" in path_str:
            tags.append("test")
        if "social" in path_str:
            tags.append("social")
        if "discord" in path_str:
            tags.append("discord")
            
        # Add tags based on imports in the content
        if "discord" in content:
            tags.append("discord")
        if "flask" in content or "fastapi" in content:
            tags.append("web")
        if "tkinter" in content:
            tags.append("gui")
        if "pytest" in content:
            tags.append("test")
            
        return list(set(tags))  # Remove duplicates
            
    def _find_documentation(self, file_path: Path) -> str:
        """Find documentation file for this component."""
        # Look for markdown files with similar names in docs directories
        filename = file_path.stem
        potential_docs = []
        
        # Check in docs directory
        docs_dir = PROJECT_ROOT / "docs"
        if docs_dir.exists():
            for doc_file in docs_dir.glob(f"**/{filename}*.md"):
                potential_docs.append(str(doc_file.relative_to(PROJECT_ROOT)))
                
        # If no direct match, look for module documentation
        if not potential_docs:
            module_path = file_path.parent
            module_name = module_path.name
            for doc_file in docs_dir.glob(f"**/{module_name}*.md"):
                potential_docs.append(str(doc_file.relative_to(PROJECT_ROOT)))
                
        return potential_docs[0] if potential_docs else ""
            
    def save_registry(self) -> None:
        """Save the component registry to a JSON file."""
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump({
                    "registry_version": "0.1.0",
                    "generated_at": str(datetime.datetime.now().isoformat()),
                    "component_count": len(self.components),
                    "components": self.components
                }, f, indent=2)
                
            logger.info(f"Saved component registry to {self.registry_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving registry: {str(e)}")
            return False
            
    def load_registry(self) -> Dict[str, Any]:
        """Load the component registry from a JSON file."""
        if not self.registry_file.exists():
            logger.warning(f"Registry file does not exist: {self.registry_file}")
            return {}
            
        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.components = data.get("components", {})
                logger.info(f"Loaded {len(self.components)} components from registry")
                return data
        except Exception as e:
            logger.error(f"Error loading registry: {str(e)}")
            return {}
            
    def generate_component_report(self, output_file: Optional[Path] = None) -> str:
        """
        Generate a Markdown report of discovered components.
        
        Args:
            output_file: Optional file to write the report to
            
        Returns:
            Markdown report as a string
        """
        if not self.components:
            return "No components discovered."
            
        # Group components by type
        components_by_type = {}
        for comp_id, comp in self.components.items():
            comp_type = comp["type"]
            if comp_type not in components_by_type:
                components_by_type[comp_type] = []
            components_by_type[comp_type].append(comp)
            
        # Sort components by name within each type
        for comp_type in components_by_type:
            components_by_type[comp_type].sort(key=lambda x: x["name"])
            
        # Build the report
        report = ["# Dream.OS Component Registry\n"]
        report.append(f"**Generated:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report.append(f"**Total Components:** {len(self.components)}\n")
        
        # Summary by type
        report.append("## Component Summary\n")
        for comp_type, comps in components_by_type.items():
            report.append(f"- **{comp_type.capitalize()}**: {len(comps)} components\n")
            
        # Detailed listing by type
        for comp_type, comps in components_by_type.items():
            report.append(f"\n## {comp_type.capitalize()} Components\n")
            
            for comp in comps:
                report.append(f"### {comp['name']}\n")
                report.append(f"- **ID**: `{comp['component_id']}`\n")
                report.append(f"- **Entry Point**: `{comp['entry_point']}`\n")
                report.append(f"- **Owner**: {comp['owner_agent']}\n")
                
                if comp['description']:
                    report.append(f"\n{comp['description']}\n")
                    
                if comp['tags']:
                    report.append(f"\n**Tags**: {', '.join(comp['tags'])}\n")
                    
                if comp['documentation']:
                    report.append(f"\n**Documentation**: [{comp['documentation']}]({comp['documentation']})\n")
                    
                report.append("\n")
                
        # Join the report
        report_text = "".join(report)
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(report_text)
                logger.info(f"Saved component report to {output_file}")
            except Exception as e:
                logger.error(f"Error saving report: {str(e)}")
                
        return report_text

def main():
    """Main entry point for the component scanner."""
    import argparse
    import datetime
    
    parser = argparse.ArgumentParser(description="Dream.OS Component Scanner")
    parser.add_argument("--project-root", type=str, help="Root directory of the Dream.OS project")
    parser.add_argument("--exclude", type=str, nargs="+", help="Directories to exclude")
    parser.add_argument("--report", type=str, help="Generate a report file")
    args = parser.parse_args()
    
    # Set project root
    global PROJECT_ROOT
    if args.project_root:
        PROJECT_ROOT = Path(args.project_root)
        
    # Set exclude patterns
    exclude_patterns = set(args.exclude) if args.exclude else set()
    
    # Initialize scanner
    scanner = ComponentScanner()
    
    # Scan the project
    scanner.scan_directory(PROJECT_ROOT, exclude_patterns)
    
    # Save the registry
    scanner.save_registry()
    
    # Generate a report if requested
    if args.report:
        report_file = Path(args.report)
        scanner.generate_component_report(report_file)
    else:
        # Print summary to console
        print(f"Discovered {len(scanner.components)} components.")
        print(f"Registry saved to {scanner.registry_file}")

if __name__ == "__main__":
    main()
```

## Usage Instructions

To use the component scanner:

1. **Run the Scanner:**
   ```bash
   python -m dreamos.launcher.scanner --project-root /path/to/dream.os --report component_report.md
   ```

2. **View the Generated Registry:**
   The scanner will create a registry file at `runtime/launcher/component_registry.json`.

3. **Review the Component Report:**
   If you specified the `--report` option, a Markdown report will be generated with details about all discovered components.

## Example Output

The component scanner will generate a registry that looks similar to this:

```json
{
  "registry_version": "0.1.0",
  "generated_at": "2024-07-23T15:30:45.123456",
  "component_count": 42,
  "components": {
    "src.dreamos.integrations.social.social_scout": {
      "component_id": "src.dreamos.integrations.social.social_scout",
      "name": "Dream.OS Social Scout - Lead Finding and Opportunity Detection",
      "description": "A module for automated social media scanning to detect leads, opportunities, and relevant discussions across platforms.",
      "entry_point": "src/dreamos/integrations/social/social_scout.py",
      "type": "service",
      "owner_agent": "agent-4",
      "dependencies": [],
      "required_env_vars": [],
      "config_files": [],
      "suggested_args": "",
      "documentation": "docs/integrations/social_scout.md",
      "tags": ["social", "integration"],
      "is_executable": true,
      "has_classes": true,
      "discovery_timestamp": "2024-07-23T15:30:45.123456"
    }
    // Additional components would be listed here
  }
}
```

## Next Steps

After implementing this component scanner prototype, the next steps would be:

1. **Enhanced Dependency Analysis:**
   Implement more sophisticated analysis to detect dependencies between components.

2. **Configuration Detection:**
   Add detection of configuration files and environment variables.

3. **Integration with Launcher:**
   Use the generated registry as the foundation for the launcher system.

4. **Manual Registry Enhancement:**
   Create tools to manually enhance the registry with additional metadata.

This component scanner represents the first step towards building a comprehensive, centralized management system for Dream.OS components, addressing the need for better component discovery and organization.

---

*This prototype will be implemented and refined based on the needs of the Dream.OS project and the centralized launcher system.* 