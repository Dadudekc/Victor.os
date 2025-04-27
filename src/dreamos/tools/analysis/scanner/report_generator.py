# Report generation and agent categorization logic 

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)

class ReportGenerator:
    """Handles merging new analysis into existing project_analysis.json and chatgpt context."""

    def __init__(self, project_root: Path, analysis: Dict[str, Dict]):
        self.project_root = project_root
        # Store analysis results internally
        self._analysis: Dict[str, Dict] = analysis

    def load_existing_report(self, report_path: Path) -> Dict[str, Any]:
        """Loads any existing JSON report to preserve old entries."""
        if report_path.exists():
            try:
                with report_path.open("r", encoding="utf-8") as f:
                    # Handle empty file case
                    content = f.read()
                    if not content:
                        return {}
                    return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in existing report {report_path}: {e}. Starting fresh.")
            except Exception as e:
                logger.error(f"Error loading existing report {report_path}: {e}. Starting fresh.")
        return {}

    def save_report(self, filename: str = "project_analysis.json"):
        """
        Merge new analysis results into an old report (preserving old keys not in new analysis), then write it out.
        Old data is kept; new files are added or updated.
        Args:
            filename: The name of the report file (e.g., "project_analysis.json").
        """
        report_path = self.project_root / filename
        existing = self.load_existing_report(report_path)

        # Merge logic: new data overrides old entries with the same filename,
        # but preserves any old entries for files not in the current scan.
        merged = {**existing, **self._analysis} # Use internal analysis data

        try:
            with report_path.open("w", encoding="utf-8") as f:
                json.dump(merged, f, indent=4, ensure_ascii=False)
            logger.info(f"✅ Project analysis updated and saved to {report_path}")
        except Exception as e:
             logger.error(f"❌ Error saving report to {report_path}: {e}", exc_info=True)

    def generate_init_files(self, overwrite: bool = True):
        """Auto-generate __init__.py for all Python packages based on internal analysis."""
        package_modules = defaultdict(list)
        for rel_path, analysis_data in self._analysis.items(): # Use internal data
            if analysis_data.get("language") == ".py":
                file_path = Path(rel_path)
                if file_path.name == "__init__.py":
                    continue
                package_dir = file_path.parent
                # Exclude root directory from being treated as a package
                if str(package_dir) == '.': 
                    continue
                module_name = file_path.stem
                package_modules[str(package_dir)].append(module_name)

        for package_str, modules in package_modules.items():
            if not package_str: # Skip root pseudo-package
                 continue
            package_path = self.project_root / package_str
            init_file = package_path / "__init__.py"
            
            try:
                package_path.mkdir(parents=True, exist_ok=True)

                lines = [
                    "# AUTO-GENERATED __init__.py",
                    "# DO NOT EDIT MANUALLY - changes may be overwritten\n"
                ]
                imports_added = False
                for module in sorted(modules):
                    # Basic check for valid module name
                    if module.isidentifier():
                         lines.append(f"from . import {module}")
                         imports_added = True
                    else:
                         logger.warning(f"Skipping invalid module name '{module}' for import in {package_path}")
                         
                if imports_added:
                    lines.append("\n__all__ = [")
                    for module in sorted(modules):
                        if module.isidentifier():
                             lines.append(f"    '{module}',")
                    lines.append("]\n")
                else:
                     lines.append("\n# No valid modules found for __all__")
                     
                content = "\n".join(lines)

                if overwrite or not init_file.exists():
                    with init_file.open("w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"✅ Generated/Updated __init__.py in {package_path}")
                # else: (No need to log skipping if not overwriting)
                    # logger.info(f"ℹ️ Skipped {init_file} (already exists and overwrite=False)")
            except OSError as e:
                 logger.error(f"Error creating directory or writing __init__.py for {package_path}: {e}")
            except Exception as e:
                 logger.error(f"Unexpected error generating __init__.py for {package_path}: {e}", exc_info=True)

    def export_chatgpt_context(self, template_path: Optional[str] = None, output_filename: str = "chatgpt_project_context.json"):
        """
        Merges current analysis details with old chatgpt context file.
        Old keys remain unless overridden by new data from the current analysis.
        If no template, write merged JSON. Else use Jinja to render a custom format.
        Args:
             template_path: Optional path to a Jinja2 template file.
             output_filename: The name of the output file (e.g., "chatgpt_project_context.json").
        """
        context_path = self.project_root / output_filename
        logger.info(f"💾 Exporting ChatGPT context to: {context_path}")

        # Prepare the payload from the current analysis
        payload = {
            "project_root": str(self.project_root),
            "num_files_analyzed": len(self._analysis),
            "analysis_details": self._analysis # Use internal analysis data
        }

        # --- JSON Merging Logic (if no template) --- 
        if not template_path:
            existing_context = self.load_existing_report(context_path) # Use same loader
            # New data overrides same keys, but preserves everything else.
            merged_context = {**existing_context, **payload}
            try:
                with context_path.open("w", encoding="utf-8") as f:
                    json.dump(merged_context, f, indent=4, ensure_ascii=False)
                logger.info(f"✅ Merged ChatGPT context saved to: {context_path}")
            except Exception as e:
                logger.error(f"❌ Error writing merged ChatGPT context JSON: {e}", exc_info=True)
            return

        # --- Jinja Template Rendering Logic --- 
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
            
            template_file = Path(template_path)
            template_dir = template_file.parent
            template_name = template_file.name
            
            env = Environment(
                 loader=FileSystemLoader(str(template_dir)),
                 autoescape=select_autoescape()
            )
            template = env.get_template(template_name)

            # Pass the payload directly to the template context
            rendered = template.render(context=payload)
            
            with context_path.open("w", encoding="utf-8") as outf:
                outf.write(rendered)
            logger.info(f"✅ Rendered ChatGPT context using template '{template_path}' to: {context_path}")
            
        except ImportError:
            logger.error("⚠️ Jinja2 not installed. Cannot use template. Run `pip install jinja2` and re-try.")
        except Exception as e:
            logger.error(f"❌ Error rendering Jinja template '{template_path}': {e}", exc_info=True)

    # ----- Agent Categorization Methods ----- 
    # Moved here as they operate on the analysis data managed by the generator

    def categorize_agents(self):
        """
        Loops over analyzed Python classes in internal analysis data, assigning maturity & agent_type.
        Updates the internal self._analysis dictionary.
        """
        logger.info("Categorizing agents based on analysis data...")
        count = 0
        for file_path, result in self._analysis.items():
            # Ensure result is a dictionary and language is Python
            if isinstance(result, dict) and result.get("language") == ".py":
                 classes_data = result.get("classes")
                 # Ensure classes_data is a dictionary
                 if isinstance(classes_data, dict):
                     for class_name, class_info in classes_data.items():
                         # Ensure class_info is a dictionary before modifying
                         if isinstance(class_info, dict):
                              class_info["maturity"] = self._maturity_level(class_name, class_info)
                              class_info["agent_type"] = self._agent_type(class_name, class_info)
                              count += 1
                         else:
                              logger.warning(f"Skipping categorization for invalid class_info format: {class_name} in {file_path}")
                 # else: # No classes in this file or invalid format
                 #      pass 
        logger.info(f"Agent categorization applied to {count} classes.")
        # Note: No need to explicitly save here, save_report should be called afterwards if needed.

    def _maturity_level(self, class_name: str, class_data: Dict[str, Any]) -> str:
        """Assigns a maturity level based on heuristics."""
        score = 0
        if class_data.get("docstring"): score += 1
        if len(class_data.get("methods", [])) > 3: score += 1
        # Check base classes more robustly
        base_classes = class_data.get("base_classes", [])
        if base_classes and any(base for base in base_classes if base not in ("object", None, "complex_base")):
             score += 1
        # Check class name convention
        if class_name and class_name[0].isupper() and class_name != "complex_base": score += 1
        
        levels = {0: "Kiddie Script", 1: "Prototype", 2: "Developing", 3: "Core Asset", 4: "Core Asset"}
        return levels.get(score, "Unknown") # Use .get for safety

    def _agent_type(self, class_name: str, class_data: Dict[str, Any]) -> str:
        """Assigns an agent type based on heuristics."""
        doc = str(class_data.get("docstring", "")).lower()
        methods = set(class_data.get("methods", []))
        base_classes = set(str(b) for b in class_data.get("base_classes", []) if b) # Ensure strings

        # Prioritize specific method names
        if "run" in methods or "execute" in methods or "process" in methods: return "ActionAgent"
        if "predict" in methods or "analyze" in methods or "evaluate" in methods: return "SignalAgent"
        if "transform" in methods or "parse" in methods or "load" in methods or "save" in methods: return "DataAgent"
        if "render" in methods or "display" in methods: return "PresentationAgent"
        if "register" in methods or "manage" in methods or "coordinate" in methods: return "CoordinationAgent"

        # Check base classes (simple check)
        if any("agent" in b.lower() for b in base_classes): return "InheritedAgent" # Generic if base class implies agent
        if any("tool" in b.lower() for b in base_classes): return "Tool" # Could be a tool base class
        
        # Check keywords in documentation
        if "agent" in doc: return "DocAgent" # Identified by docstring
        if "tool" in doc: return "DocTool"
        if "util" in doc or "helper" in doc: return "Utility"
        if "config" in doc or "setting" in doc: return "Config"
        if "test" in doc or "fixture" in doc: return "TestAsset"

        # Default fallback
        return "Utility" 