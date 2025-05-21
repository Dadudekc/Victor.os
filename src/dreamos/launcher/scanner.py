"""
Dream.OS Component Scanner

A tool to discover and catalog all executable components in the Dream.OS project.
Based on the prototype defined in docs/vision/COMPONENT_SCANNER_PROTOTYPE.md.
"""

import os
import sys
import ast
import json
import logging
import datetime
import importlib.util
import re
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
REPORT_FILE = PROJECT_ROOT / "docs" / "architecture" / "COMPONENT_REGISTRY.md"
EXCLUDED_DIRS = {".git", ".vscode", "__pycache__", "venv", "env", ".env", "node_modules"}
EXCLUDED_FILES = {"setup.py", "__init__.py"}

class ComponentScanner:
    """Scanner for discovering executable components in the Dream.OS project."""
    
    def __init__(self):
        """Initialize the component scanner."""
        self.components = {}
        self.registry_dir = REGISTRY_DIR
        self.registry_file = REGISTRY_FILE
        self.report_file = REPORT_FILE
        
        # Ensure registry directory exists
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
        # Create architecture directory if it doesn't exist
        self.report_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Initialized ComponentScanner with registry at {self.registry_file}")
    
    def scan_directory(self, directory: Path) -> List[Dict]:
        """Scan directory for Python files and analyze them."""
        try:
            results = []
            for path in directory.rglob("*.py"):
                # Skip excluded directories and files
                if any(part in EXCLUDED_DIRS for part in path.parts):
                    continue
                if path.name in EXCLUDED_FILES:
                    continue
                    
                # Analyze file
                file_info = {
                    "path": str(path.relative_to(directory)),
                    "size": path.stat().st_size,
                    "modified": path.stat().st_mtime,
                    "analysis": self.analyze_python_file(path)
                }
                
                # Add metadata
                file_info["owner_agent"] = self.infer_owner_agent(file_info)
                file_info["tags"] = self.infer_tags(file_info)
                file_info["documentation"] = self.find_documentation(file_info)
                
                results.append(file_info)
                
            # Update components registry
            self.components = {
                "files": results,
                "last_scan": datetime.now().isoformat()
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")
            return []
            
    def analyze_python_file(self, file_path: Path) -> Dict:
        """Analyze a Python file for imports, classes, and functions."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Basic analysis
            analysis = {
                "imports": [],
                "classes": [],
                "functions": [],
                "docstrings": [],
                "line_count": len(content.splitlines())
            }
            
            # Parse imports
            import_pattern = r"^(?:from\s+(\S+)\s+import\s+(\S+)|import\s+(\S+))"
            for line in content.splitlines():
                if match := re.match(import_pattern, line.strip()):
                    if match.group(1):  # from x import y
                        analysis["imports"].append(f"{match.group(1)}.{match.group(2)}")
                    else:  # import x
                        analysis["imports"].append(match.group(3))
                        
            # Parse classes and functions
            class_pattern = r"class\s+(\w+)"
            func_pattern = r"def\s+(\w+)"
            for line in content.splitlines():
                if match := re.match(class_pattern, line.strip()):
                    analysis["classes"].append(match.group(1))
                elif match := re.match(func_pattern, line.strip()):
                    analysis["functions"].append(match.group(1))
                    
            # Extract docstrings
            docstring_pattern = r'"""(.*?)"""'
            analysis["docstrings"] = re.findall(docstring_pattern, content, re.DOTALL)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {}
            
    def infer_owner_agent(self, file_info: Dict) -> Optional[str]:
        """Infer the owner agent of a file based on its content and location."""
        try:
            # Check for agent-specific imports
            for imp in file_info["analysis"]["imports"]:
                if "agent" in imp.lower():
                    return imp.split(".")[-1]
                    
            # Check for agent-specific classes
            for cls in file_info["analysis"]["classes"]:
                if "agent" in cls.lower():
                    return cls
                    
            # Check file path for agent indicators
            path = file_info["path"].lower()
            if "agent" in path:
                return path.split("/")[0]
                
            return None
            
        except Exception as e:
            logger.error(f"Error inferring owner agent: {e}")
            return None
            
    def infer_tags(self, file_info: Dict) -> List[str]:
        """Infer tags for a file based on its content and structure."""
        try:
            tags = set()
            
            # Add language tag
            tags.add("python")
            
            # Add framework tags
            for imp in file_info["analysis"]["imports"]:
                if "dreamos" in imp:
                    tags.add("dreamos")
                if "pytest" in imp:
                    tags.add("test")
                if "unittest" in imp:
                    tags.add("test")
                    
            # Add type tags
            if file_info["analysis"]["classes"]:
                tags.add("class")
            if file_info["analysis"]["functions"]:
                tags.add("function")
                
            # Add documentation tag if docstrings present
            if file_info["analysis"]["docstrings"]:
                tags.add("documented")
                
            return sorted(list(tags))
            
        except Exception as e:
            logger.error(f"Error inferring tags: {e}")
            return []
            
    def find_documentation(self, file_info: Dict) -> List[Dict]:
        """Find related documentation for a file."""
        try:
            docs = []
            file_path = Path(file_info["path"])
            
            # Check for adjacent markdown files
            for ext in [".md", ".rst", ".txt"]:
                doc_path = file_path.with_suffix(ext)
                if doc_path.exists():
                    docs.append({
                        "path": str(doc_path),
                        "type": "adjacent",
                        "format": ext[1:]
                    })
                    
            # Check for docs directory
            docs_dir = file_path.parent / "docs"
            if docs_dir.exists():
                for doc_file in docs_dir.glob("*.md"):
                    if doc_file.stem in file_path.stem:
                        docs.append({
                            "path": str(doc_file),
                            "type": "docs_dir",
                            "format": "md"
                        })
                        
            return docs
            
        except Exception as e:
            logger.error(f"Error finding documentation: {e}")
            return []
            
    def save_registry(self, registry: Dict) -> bool:
        """Save the file registry to disk."""
        try:
            # Ensure registry directory exists
            self.registry_dir.mkdir(parents=True, exist_ok=True)
            
            # Save registry
            with open(self.registry_file, "w") as f:
                json.dump(registry, f, indent=2)
                
            logger.info(f"Saved registry to {self.registry_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
            return False
            
    def load_registry(self) -> Dict:
        """Load the file registry from disk."""
        try:
            registry_path = Path("runtime/registry/file_registry.json")
            if not registry_path.exists():
                return {"files": [], "last_scan": None}
                
            with open(registry_path, "r") as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {"files": [], "last_scan": None}
            
    def generate_report(self, registry: Dict) -> str:
        """Generate a report of the file registry."""
        try:
            report = []
            report.append("# Dream.OS Component Registry Report")
            report.append(f"\nGenerated: {datetime.now().isoformat()}")
            report.append(f"Total Files: {len(registry.get('files', []))}")
            
            # File type statistics
            file_types = {}
            for file in registry.get("files", []):
                ext = Path(file["path"]).suffix
                file_types[ext] = file_types.get(ext, 0) + 1
                
            report.append("\n## File Types")
            for ext, count in sorted(file_types.items()):
                report.append(f"- {ext}: {count}")
                
            # Owner agent statistics
            owners = {}
            for file in registry.get("files", []):
                owner = file.get("owner_agent", "unknown")
                owners[owner] = owners.get(owner, 0) + 1
                
            report.append("\n## Owner Agents")
            for owner, count in sorted(owners.items()):
                report.append(f"- {owner}: {count}")
                
            # Tag statistics
            tags = {}
            for file in registry.get("files", []):
                for tag in file.get("tags", []):
                    tags[tag] = tags.get(tag, 0) + 1
                    
            report.append("\n## Tags")
            for tag, count in sorted(tags.items()):
                report.append(f"- {tag}: {count}")
                
            # Save report to file
            with open(self.report_file, "w") as f:
                f.write("\n".join(report))
                
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return "Error generating report"

def main():
    """Main entry point for the component scanner."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Dream.OS Component Scanner")
    parser.add_argument("--project-root", type=str, help="Root directory of the Dream.OS project")
    parser.add_argument("--exclude", type=str, nargs="+", help="Directories or patterns to exclude")
    parser.add_argument("--report", type=str, help="Generate a report file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Set project root
    global PROJECT_ROOT
    if args.project_root:
        PROJECT_ROOT = Path(args.project_root)
    
    # Set report file
    global REPORT_FILE
    if args.report:
        REPORT_FILE = Path(args.report)
    
    # Set exclude patterns
    exclude_patterns = set(args.exclude) if args.exclude else set()
    
    # Initialize scanner
    scanner = ComponentScanner()
    
    # Load existing registry if available
    existing_components = scanner.load_registry()
    if existing_components:
        scanner.components = existing_components.get("files", [])
        logger.info(f"Loaded {len(scanner.components)} components from existing registry")
    
    # Scan the project
    logger.info(f"Scanning project root: {PROJECT_ROOT}")
    scanner.scan_directory(PROJECT_ROOT)
    
    # Save the registry
    if scanner.save_registry(scanner.components):
        logger.info(f"Saved registry with {len(scanner.components)} components")
    else:
        logger.error("Failed to save registry")
    
    # Generate a report
    report = scanner.generate_report(scanner.components)
    logger.info(f"Generated component report at {REPORT_FILE}")
    
    # Print summary
    print(f"Discovered {len(scanner.components)} components")
    print(f"Registry saved to {scanner.registry_file}")
    print(f"Report saved to {scanner.report_file}")

if __name__ == "__main__":
    main() 