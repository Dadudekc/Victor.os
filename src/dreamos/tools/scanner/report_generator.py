"""
Report generation module for the project scanner.

This module provides functionality to generate reports from the project scan results.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates reports from the project scan results, including markdown reports
    and context files for AI assistants.
    """

    def __init__(
        self,
        project_root: Path,
        analysis: Dict[str, Dict],
        analysis_output_path: Path,
        context_output_path: Path,
    ):
        self.project_root = project_root
        self.analysis = analysis
        self.analysis_output_path = analysis_output_path
        self.context_output_path = context_output_path
        self.report_data = {"files": len(analysis), "summary": {}}

    def load_existing_report(self, report_path: Path) -> Dict[str, Any]:
        """Load an existing report file if it exists."""
        if report_path.exists():
            try:
                with open(report_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load existing report {report_path}: {e}")
        return {}

    def save_report(self):
        """Save the analysis report in markdown format."""
        try:
            # Create the report directory if it doesn't exist
            self.analysis_output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build a markdown report
            md_content = f"# Project Scan Report\n\n"
            md_content += f"Total files analyzed: {len(self.analysis)}\n\n"
            
            # Add file statistics section
            md_content += "## File Statistics\n\n"
            extensions = {}
            for file_path, data in self.analysis.items():
                ext = data.get("extension", "unknown")
                extensions[ext] = extensions.get(ext, 0) + 1
            
            md_content += "### By File Type\n\n"
            md_content += "| Extension | Count |\n|-----------|-------|\n"
            for ext, count in sorted(extensions.items(), key=lambda x: x[1], reverse=True):
                md_content += f"| {ext} | {count} |\n"
            
            # Save the report
            with open(self.analysis_output_path, "w") as f:
                f.write(md_content)
                
            logger.info(f"Saved analysis report to {self.analysis_output_path}")
            
        except Exception as e:
            logger.error(f"Error saving report: {e}")
    
    def generate_init_files(self, overwrite: bool = True):
        """
        Generate __init__.py files for Python packages based on analyzing imports.
        This helps ensure proper Python module importing structure.
        
        Args:
            overwrite: Whether to overwrite existing __init__.py files
        """
        python_dirs = set()
        
        # Find all directories with Python files
        for file_path in self.analysis.keys():
            if file_path.endswith(".py"):
                # Get all parent directories
                parts = Path(file_path).parts
                for i in range(1, len(parts)):
                    parent_dir = Path(*parts[:i])
                    if parent_dir.exists():
                        python_dirs.add(parent_dir)
        
        # Generate __init__.py in each directory
        for dir_path in python_dirs:
            init_file = dir_path / "__init__.py"
            if not init_file.exists() or overwrite:
                try:
                    with open(init_file, "w") as f:
                        f.write(f'"""\n{dir_path.name} package\n"""\n\n')
                    logger.info(f"Generated {init_file}")
                except Exception as e:
                    logger.error(f"Failed to generate {init_file}: {e}")
            else:
                logger.debug(f"Skipping existing {init_file}")

    def load_existing_chatgpt_context(self) -> Dict[str, Any]:
        """Load an existing ChatGPT context file."""
        try:
            if self.context_output_path.exists():
                with open(self.context_output_path, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load existing context file: {e}")
        return {}

    def export_chatgpt_context(self, template_path: Optional[str] = None):
        """
        Export the analysis data in a format suitable for ChatGPT to provide project context.
        
        Args:
            template_path: Optional path to a template file to use for export
        """
        try:
            # Create context structure
            context_data = {}
            
            # Process each file
            for file_path, analysis in self.analysis.items():
                # Skip files with errors
                if "error" in analysis:
                    continue
                
                # Create the file entry
                file_entry = {
                    "type": "file",
                    "language": self._determine_language(analysis.get("extension", "")),
                    "size_bytes": analysis.get("size_bytes", 0),
                    "lines": analysis.get("lines", 0),
                }
                
                # Add imports if present
                if "imports" in analysis or "from_imports" in analysis:
                    file_entry["imports"] = analysis.get("imports", [])
                    file_entry["from_imports"] = analysis.get("from_imports", [])
                
                # Add functions if present
                if "functions" in analysis:
                    function_names = []
                    for func in analysis["functions"]:
                        if isinstance(func, dict) and "name" in func:
                            function_names.append(func["name"])
                        elif isinstance(func, str):
                            function_names.append(func)
                    file_entry["functions"] = function_names
                
                # Add classes if present
                if "classes" in analysis and analysis["classes"]:
                    file_entry["classes"] = list(analysis["classes"].keys())
                
                # Add complexity if present
                if "complexity" in analysis:
                    file_entry["complexity"] = analysis["complexity"]
                
                # Save to context data
                context_data[str(file_path).replace("/", "\\")] = file_entry
            
            # Save context data
            self.context_output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.context_output_path, "w") as f:
                json.dump(context_data, f, indent=2)
            
            logger.info(f"Exported ChatGPT context to {self.context_output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting ChatGPT context: {e}")
    
    def _determine_language(self, extension: str) -> str:
        """Determine the language from a file extension."""
        extension_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".rs": "rust",
            ".go": "go",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".html": "html",
            ".css": "css",
            ".md": "markdown",
            ".json": "json",
            ".xml": "xml",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".sh": "bash",
            ".bat": "batch",
            ".ps1": "powershell",
            ".sql": "sql",
        }
        return extension_map.get(extension.lower(), "text")
    
    def categorize_agents(self):
        """
        Analyze the codebase for agent-related files and categorize them.
        """
        agent_files = {}
        
        for file_path, data in self.analysis.items():
            # Check if the file is in an agent directory or has agent in the name
            if (
                "/agent" in file_path.lower() or 
                "\\agent" in file_path.lower() or 
                "agent_" in file_path.lower() or
                "_agent" in file_path.lower()
            ):
                agent_type = self._determine_agent_type(file_path, data)
                if agent_type:
                    agent_files.setdefault(agent_type, []).append(file_path)
        
        return agent_files
    
    def _determine_agent_type(self, file_path: str, data: Dict) -> Optional[str]:
        """
        Determine the type of agent from file path and analysis data.
        """
        # This is a very simple heuristic that could be improved
        if "agent0" in file_path.lower() or "agent-0" in file_path.lower():
            return "Agent-0"
        elif "agent1" in file_path.lower() or "agent-1" in file_path.lower():
            return "Agent-1"
        elif "agent2" in file_path.lower() or "agent-2" in file_path.lower():
            return "Agent-2"
        elif "agent3" in file_path.lower() or "agent-3" in file_path.lower():
            return "Agent-3"
        elif "agent4" in file_path.lower() or "agent-4" in file_path.lower():
            return "Agent-4"
        elif "agent5" in file_path.lower() or "agent-5" in file_path.lower():
            return "Agent-5"
        elif "agent6" in file_path.lower() or "agent-6" in file_path.lower():
            return "Agent-6"
        elif "agent7" in file_path.lower() or "agent-7" in file_path.lower():
            return "Agent-7"
        elif "agent8" in file_path.lower() or "agent-8" in file_path.lower():
            return "Agent-8"
        
        # Check imports and classes for agent keywords
        for imp in data.get("imports", []):
            if "agent" in imp.lower():
                return "Generic Agent"
                
        for cls in data.get("classes", {}).keys():
            if "agent" in cls.lower():
                return "Generic Agent"
                
        return None 