# Report generation and agent categorization logic

import asyncio
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Optional

# Optional Jinja2 import
try:
    from jinja2 import Template
except ImportError:
    Template = None

logger = logging.getLogger(__name__)

# EDIT START: Remove default relative dir - will be passed in\n# DEFAULT_REPORTS_DIR_REL = \"reports\"\n# EDIT END


class ReportGenerator:
    """Handles merging new analysis into existing reports and context files. Async I/O."""

    def __init__(self, reports_dir_abs: Path, analysis: Dict[str, Dict]):
        self.analysis = (
            analysis  # e.g., { 'subdir/file.py': {language:..., classes:...}, ... }
        )
        self.reports_dir_abs = reports_dir_abs.resolve()
        # Define standard output paths based on reports_dir_abs
        self.report_file_path = self.reports_dir_abs / "project_analysis.json"
        self.context_file_path = self.reports_dir_abs / "chatgpt_project_context.json"
        logger.debug(
            f"ReportGenerator initialized. Reports dir: {self.reports_dir_abs}"
        )

    async def load_existing_report(self, report_path: Path) -> Dict[str, Any]:
        """Loads any existing JSON report file. Async."""
        if not await asyncio.to_thread(report_path.exists):
            return {}
        
        def _sync_load():
            try:
                with report_path.open("r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Error decoding JSON from {report_path}: {e}. Starting fresh."
                )
            except Exception as e:
                logger.error(f"Error loading report {report_path}: {e}")
            return {}
        return await asyncio.to_thread(_sync_load)

    async def save_report(self):
        """
        Merge new analysis results and save the main analysis report. Async.
        """  # noqa: E501
        report_path = self.report_file_path
        logger.info(f"Saving project analysis report to: {report_path}")

        async def _sync_save_report_io():
            self.reports_dir_abs.mkdir(parents=True, exist_ok=True)
            existing = await self.load_existing_report(report_path)
            merged = {**existing, **self.analysis}

        # Separated directory creation and loading from the main save logic for clarity with async
        try:
            if not await asyncio.to_thread(self.reports_dir_abs.exists):
                await asyncio.to_thread(self.reports_dir_abs.mkdir, parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Failed to create reports directory {self.reports_dir_abs}: {e}"
            )
            return

        existing_report_data = await self.load_existing_report(report_path)
        merged = {**existing_report_data, **self.analysis}

        def _sync_final_write():
            try:
                with report_path.open("w", encoding="utf-8") as f:
                    json.dump(merged, f, indent=4)
                logger.info(f"✅ Project analysis updated and saved to {report_path}")
            except IOError as e:
                logger.error(
                    f"Failed to write project analysis report to {report_path}: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Unexpected error saving report to {report_path}: {e}",
                    exc_info=True,
                )
        
        await asyncio.to_thread(_sync_final_write)

    async def generate_init_files(self, overwrite: bool = True):
        """Auto-generate __init__.py for all Python packages. Async file I/O."""
        package_modules = defaultdict(list)
        for rel_path in self.analysis.keys():
            if rel_path.endswith(".py"):
                file_path = Path(rel_path)
                if file_path.name == "__init__.py":
                    continue
                package_dir = file_path.parent
                module_name = file_path.stem
                package_modules[str(package_dir)].append(module_name)

        for package_str, modules in package_modules.items():
            package_abs_path = self.reports_dir_abs / package_str
            init_file = package_abs_path / "__init__.py"

            def _sync_io_for_init():
                package_abs_path.mkdir(parents=True, exist_ok=True)
                lines = [
                    "# AUTO-GENERATED __init__.py",
                    "# DO NOT EDIT MANUALLY - changes may be overwritten\n",
                ]
                for module in sorted(modules):
                    lines.append(f"from . import {module}")
                lines.append("\n__all__ = [")
                for module in sorted(modules):
                    lines.append(f"    '{module}',")
                lines.append("]\n")
                content = "\n".join(lines)
                
                if overwrite or not init_file.exists():
                    with init_file.open("w", encoding="utf-8") as f:
                        f.write(content)
                    logger.info(f"✅ Generated __init__.py in {package_abs_path}")
                    return True
                else:
                    logger.info(f"ℹ️ Skipped {init_file} (already exists)")
                    return False
            
            # Handle exists() check asynchronously before deciding to run _sync_io_for_init
            init_exists = await asyncio.to_thread(init_file.exists)
            if overwrite or not init_exists:
                await asyncio.to_thread(_sync_io_for_init)
            else:
                logger.info(f"ℹ️ Skipped {init_file} (already exists)")

    async def load_existing_chatgpt_context(self, context_path: Path) -> Dict[str, Any]:
        """Load any existing chatgpt_project_context.json. Async."""
        if not await asyncio.to_thread(context_path.exists):
            return {}
        def _sync_load_context():
            try:
                with context_path.open("r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            except json.JSONDecodeError as e:
                logger.error(
                    f"Error decoding JSON from {context_path}: {e}. Starting fresh."
                )
            except Exception as e:
                logger.error(
                    f"Error loading context {context_path}: {e}"
                )
            return {}
        return await asyncio.to_thread(_sync_load_context)

    async def export_chatgpt_context(
        self,
        template_path: Optional[str] = None,
        output_filename: str = "chatgpt_project_context.json",
    ):
        """Merges/renders context to chatgpt_project_context.json. Async file I/O."""
        context_output_path = self.reports_dir_abs / output_filename
        logger.info(f"💾 Writing ChatGPT context to: {context_output_path}")

        try:
            if not await asyncio.to_thread(self.reports_dir_abs.exists):
                await asyncio.to_thread(self.reports_dir_abs.mkdir, parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"Failed to create reports directory {self.reports_dir_abs}: {e}"
            )
            return

        async def _sync_export_no_template():
            existing_context = await self.load_existing_chatgpt_context(context_output_path)
            payload = {
                "project_root": str(self.reports_dir_abs),
                "num_files_analyzed": len(self.analysis),
                "analysis_details": self.analysis,
            }
            merged_context = {**existing_context, **payload}
            try:
                with context_output_path.open("w", encoding="utf-8") as f:
                    json.dump(merged_context, f, indent=4)
                logger.info(f"✅ Merged ChatGPT context saved to: {context_output_path}")
            except IOError as e:
                logger.error(f"Failed to write context to {context_output_path}: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error saving context to {context_output_path}: {e}",
                    exc_info=True,
                )
        
        async def _sync_export_with_template():
            if not Template:
                logger.error(
                    "⚠️ Jinja2 not installed, but a template path was provided. Run `pip install jinja2`."
                )
                return
            try:
                def _read_template():
                    with open(template_path, "r", encoding="utf-8") as tf:
                        return tf.read()
                template_content = await asyncio.to_thread(_read_template)
                
                t = Template(template_content)
                context_dict = {
                    "project_root": str(self.reports_dir_abs),
                    "analysis": self.analysis,
                    "num_files_analyzed": len(self.analysis),
                }
                rendered = t.render(context=context_dict)
                
                def _write_rendered():
                    with context_output_path.open("w", encoding="utf-8") as outf:
                        outf.write(rendered)
                await asyncio.to_thread(_write_rendered)
                logger.info(
                    f"✅ Rendered ChatGPT context using template to: {context_output_path}"
                )
            except FileNotFoundError:
                logger.error(f"❌ Template file not found: {template_path}")
            except Exception as e:
                logger.error(f"❌ Error rendering Jinja template: {e}", exc_info=True)

        if not template_path:
            existing_context = await self.load_existing_chatgpt_context(context_output_path)
            payload = {
                "project_root": str(self.reports_dir_abs),
                "num_files_analyzed": len(self.analysis),
                "analysis_details": self.analysis,
            }
            merged_context = {**existing_context, **payload}
            def _sync_write_json_context():
                try:
                    with context_output_path.open("w", encoding="utf-8") as f:
                        json.dump(merged_context, f, indent=4)
                    logger.info(f"✅ Merged ChatGPT context saved to: {context_output_path}")
                except IOError as e:
                    logger.error(f"Failed to write context to {context_output_path}: {e}")
                except Exception as e:
                    logger.error(
                        f"Unexpected error saving context to {context_output_path}: {e}",
                        exc_info=True,
                    )
            await asyncio.to_thread(_sync_write_json_context)
        else:
            await _sync_export_with_template()

    # categorize_agents is CPU-bound, can remain synchronous internally.
    # ProjectScanner calls save_report (now async) after this.
    def categorize_agents(self):
        """Categorizes files in the analysis results based on heuristics.

        Adds an 'agent_category' key to the analysis details for each file.
        Categories: 'Agent', 'Core', 'Service', 'Tool', 'Util', 'Config', 'Test', 'Other'
        """  # noqa: E501
        logger.info("Categorizing analyzed files...")
        if not self.analysis:
            logger.warning("Analysis data is empty, cannot categorize agents.")
            return

        categorized_count = 0
        for file_path_str, details in self.analysis.items():
            category = "Other"  # Default
            file_path = Path(file_path_str)
            parts = file_path.parts

            # Rule 1: Path-based categorization
            if "tests" in parts:
                category = "Test"
            elif "config" in parts:
                category = "Config"
            elif "agents" in parts:
                category = "Agent"
            elif "services" in parts:
                category = "Service"
            elif "core" in parts:
                category = "Core"
            elif "tools" in parts:
                category = "Tool"
            elif "utils" in parts:
                category = "Util"
            # Add more path rules if needed (e.g., 'integrations', 'gui')

            # Rule 2: Filename contains '_agent'
            if category == "Other" and "_agent.py" in file_path.name:
                category = "Agent"

            # Rule 3: Class inherits from BaseAgent (if class info available)
            if category == "Other" and details.get("language") == "python":
                classes = details.get("classes", [])
                for class_info in classes:
                    if "BaseAgent" in class_info.get("base_classes", []):
                        category = "Agent"
                        break  # Found an agent class in this file

            # Assign the determined category
            details["agent_category"] = category
            if category != "Other":
                categorized_count += 1

        logger.info(
            f"Categorization complete. Assigned categories to {categorized_count} files."  # noqa: E501
        )

    def _maturity_level(self, class_name: str, class_data: Dict[str, Any]) -> str:
        """Assigns a maturity level based on heuristics."""
        score = 0
        if class_data.get("docstring"):
            score += 1
        if len(class_data.get("methods", [])) > 3:
            score += 1
        # Check base classes more robustly
        base_classes = class_data.get("base_classes", [])
        if base_classes and any(
            base
            for base in base_classes
            if base not in ("object", None, "complex_base")
        ):
            score += 1
        # Check class name convention
        if class_name and class_name[0].isupper() and class_name != "complex_base":
            score += 1

        levels = {
            0: "Kiddie Script",
            1: "Prototype",
            2: "Developing",
            3: "Core Asset",
            4: "Core Asset",
        }
        return levels.get(score, "Unknown")  # Use .get for safety

    def _agent_type(self, class_name: str, class_data: Dict[str, Any]) -> str:
        """Assigns an agent type based on heuristics."""
        doc = str(class_data.get("docstring", "")).lower()
        methods = set(class_data.get("methods", []))
        base_classes = set(
            str(b) for b in class_data.get("base_classes", []) if b
        )  # Ensure strings

        # Prioritize specific method names
        if "run" in methods or "execute" in methods or "process" in methods:
            return "ActionAgent"
        if "predict" in methods or "analyze" in methods or "evaluate" in methods:
            return "SignalAgent"
        if (
            "transform" in methods
            or "parse" in methods
            or "load" in methods
            or "save" in methods
        ):
            return "DataAgent"
        if "render" in methods or "display" in methods:
            return "PresentationAgent"
        if "register" in methods or "manage" in methods or "coordinate" in methods:
            return "CoordinationAgent"

        # Check base classes (simple check)
        if any("agent" in b.lower() for b in base_classes):
            return "InheritedAgent"  # Generic if base class implies agent
        if any("tool" in b.lower() for b in base_classes):
            return "Tool"  # Could be a tool base class

        # Check keywords in documentation
        if "agent" in doc:
            return "DocAgent"  # Identified by docstring
        if "tool" in doc:
            return "DocTool"
        if "util" in doc or "helper" in doc:
            return "Utility"
        if "config" in doc or "setting" in doc:
            return "Config"
        if "test" in doc or "fixture" in doc:
            return "TestAsset"

        # Default fallback
        return "Utility"
