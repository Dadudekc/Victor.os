#!/usr/bin/env python3
"""
Generate / refresh ai_docs/reports/module_map.md from project_analysis.json.

Improvements over previous script
• single‑source config via dataclass
• explicit Category enum + prefix map
• robust path normaliser (uses Path.is_relative_to on 3.9+)
• marker‑based MD injection  <!-- BEGIN CORE --> / <!-- END CORE -->
• tightened log messages + type hints
• minimal globals, early exits, safer IO
• Added 'Primary Role / Behaviors' column, populated for Agents.
• Enhanced 'Primary Role / Behaviors' for Services: type, pattern, role.
• Enhanced 'Primary Role / Behaviors' for Tools & Utilities: functionality classification.
• Extended 'Primary Role / Behaviors' to CORE, AUTOMATION, INTEGRATIONS, CLI.
• Added 'Dependencies' column population.
"""
from __future__ import annotations

import json, logging, re, sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Tuple, Set

# --- Adjust sys.path to allow finding devtools --- BEGIN
# This assumes the script is in devtools/ and we want to import devtools.dependency_extractor
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
# --- Adjust sys.path --- END

# Initialize logger early for import attempts
logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s: %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# Attempt to import the new dependency extractor
try:
    from devtools.dependency_extractor import extract_imports_from_file
    log.info("Successfully imported extract_imports_from_file from devtools.dependency_extractor")
except ImportError as e1:
    log.error(f"CRITICAL: Failed to import from devtools.dependency_extractor even after sys.path adjustment: {e1}.")
    sys.exit(1)


# ───────────────────────── config ──────────────────────────
@dataclass(frozen=True)
class Cfg:
    root: Path = Path(__file__).resolve().parents[1]
    analysis_json: Path = root / "reports" / "project_analysis.json"
    module_map_md: Path = root / "ai_docs" / "reports" / "module_map.md"
    dreamos_prefix: str = "src/dreamos/"


cfg = Cfg()

# ──────────────────────── categories ───────────────────────
class Category(Enum):
    CORE = auto()
    AGENTS = auto()
    TOOLS = auto()
    AUTOMATION = auto()
    SERVICES = auto()
    INTEGRATIONS = auto()
    CLI = auto()
    UTIL = auto()
    OTHER = auto()

PREFIX_MAP = {
    "core/": Category.CORE,
    "agents/": Category.AGENTS,
    "tools/": Category.TOOLS,
    "automation/": Category.AUTOMATION,
    "services/": Category.SERVICES,
    "integrations/": Category.INTEGRATIONS,
    "cli/": Category.CLI,
    "utils/": Category.UTIL, # For top-level src/dreamos/utils/
}

# For classifying internal dependencies
KNOWN_INTERNAL_TOP_LEVELS: Set[str] = {k.replace('/', '') for k in PREFIX_MAP.keys()}
KNOWN_INTERNAL_TOP_LEVELS.add('dreamos') # Add 'dreamos' itself (e.g. from dreamos.core import ...)
# Add sub-package names as well for more accurate internal classification if needed, e.g. 'dreamos.core', 'dreamos.agents'
# Example: if a file in src/dreamos/agents/foo.py imports dreamos.core.bar, 'dreamos' is the top-level from from_imports.
# The current extract_imports_from_file gets top-level, so 'dreamos' or 'core' (if directly under src/dreamos)

# Common standard library modules to potentially filter from "External" for brevity, if desired.
# For now, the filtering is minimal. A more robust approach could use sys.stdlib_module_names (Python 3.10+).
COMMON_STDLIB_MODULES: Set[str] = {
    'sys', 'os', 're', 'json', 'logging', 'enum', 'typing', 'pathlib', 
    'dataclasses', 'collections', 'itertools', 'functools', 'math', 'datetime',
    'time', 'subprocess', 'threading', 'multiprocessing', 'argparse', 'configparser',
    'shutil', 'tempfile', 'uuid', 'inspect', 'ast', 'asyncio', 'concurrent', 'socket',
    'http', 'urllib', 'copy', 'pickle', 'weakref', 'gc'
}

MD_MARKERS = {
    Category.CORE: ("<!-- BEGIN CORE -->", "<!-- END CORE -->"),
    Category.AGENTS: ("<!-- BEGIN AGENTS -->", "<!-- END AGENTS -->"),
    Category.TOOLS: ("<!-- BEGIN TOOLS -->", "<!-- END TOOLS -->"),
    Category.AUTOMATION: ("<!-- BEGIN AUTOMATION -->", "<!-- END AUTOMATION -->"),
    Category.SERVICES: ("<!-- BEGIN SERVICES -->", "<!-- END SERVICES -->"),
    Category.INTEGRATIONS: ("<!-- BEGIN INTEGRATIONS -->", "<!-- END INTEGRATIONS -->"),
    Category.CLI: ("<!-- BEGIN CLI -->", "<!-- END CLI -->"),
    Category.UTIL: ("<!-- BEGIN UTIL -->", "<!-- END UTIL -->"), 
}

TABLE_HEADER = (
    "| Path | Category | Key Symbols | Primary Role / Behaviors | Dependencies | Statefulness | "
    "Maturity | Recommendation | Notes |\\n"
    "|---|---|---|---|---|---|---|---|---|\\n"
)

# ───────────────── Classification Helpers ──────────────────
def _classify_service_type_and_pattern(class_name: str, methods: List[str], docstring: str) -> Tuple[str, str]:
    """Classifies service type and operational pattern based on keywords."""
    class_name_lower = class_name.lower()
    methods_lower = [m.lower() for m in methods]
    docstring_lower = docstring.lower() if docstring else ""

    service_type = "General"
    # Type classification based on class name primarily
    if "log" in class_name_lower or "logger" in class_name_lower:
        service_type = "Logging"
    elif "archive" in class_name_lower or "persist" in class_name_lower or "database" in class_name_lower or "store" in class_name_lower:
        service_type = "Persistence"
    elif "health" in class_name_lower or "monitor" in class_name_lower or "check" in class_name_lower:
        service_type = "Health/Monitoring"
    elif "scrape" in class_name_lower or "scraper" in class_name_lower or "fetch" in class_name_lower:
        service_type = "Scraping/Data-Collection"
    elif "orchestrat" in class_name_lower or "coordinator" in class_name_lower or "dispatch" in class_name_lower:
        service_type = "Orchestration/Coordination"
    elif "feedback" in class_name_lower or "review" in class_name_lower:
        service_type = "Feedback"
    elif "maintenance" in class_name_lower or "clean" in class_name_lower:
        service_type = "Maintenance"
    elif "event" in class_name_lower and "bus" not in class_name_lower : # distinguish from agent bus
        service_type = "Event-Handling"

    operational_pattern = "Passive/Event-Driven" 
    # Pattern detection based on method names and docstrings
    loop_keywords = ["run_loop", "_loop", "start_polling", "poll", "watch", "monitor_loop", "process_indefinitely"]
    schedule_keywords = ["schedule", "cron", "interval", "tick", "scheduled_task"]

    for method in methods_lower:
        if any(lk in method for lk in loop_keywords):
            operational_pattern = "Looped"
            break
        if any(sk in method for sk in schedule_keywords):
            operational_pattern = "Scheduled"
            break
    
    if operational_pattern == "Passive/Event-Driven": # Check docstring if methods didn't indicate
        if any(sk in docstring_lower for sk in schedule_keywords):
            operational_pattern = "Scheduled"
        elif any(lk in docstring_lower for lk in loop_keywords): # less likely for docstring to imply loop if no method does
             operational_pattern = "Looped"

    return service_type, operational_pattern

def _classify_tool_util_functionality(file_path: str, classes: Dict[str,dict], functions: List[str], docstring: str) -> str:
    """Classifies tool/utility functionality based on names, content, and docstrings."""
    path_lower = file_path.lower()
    content_signature = " ".join(list(classes.keys()) + functions).lower() + (docstring.lower() if docstring else "")

    if "cli" in path_lower or "command" in path_lower or "argparse" in content_signature or "click" in content_signature:
        return "CLI Command/Support"
    if "file" in path_lower or "path" in path_lower or "io" in content_signature or "read" in content_signature or "write" in content_signature:
        return "File/Path Operations"
    if "test" in path_lower or "assert" in content_signature or "pytest" in content_signature:
        return "Testing Support/Utilities"
    if "util" in path_lower or "helper" in path_lower:
        if "string" in content_signature or "str_" in content_signature: return "String Manipulation Utility"
        if "date" in content_signature or "time" in content_signature: return "Date/Time Utility"
        if "config" in content_signature: return "Configuration Helper"
        return "General Utility"
    if "format" in path_lower or "lint" in path_lower or "style" in path_lower:
        return "Code Formatting/Linting"
    if "parse" in path_lower or "parser" in content_signature or "lex" in content_signature or "token" in content_signature:
        return "Parsing/Lexing Utility"
    if "validat" in path_lower or "schema" in content_signature or "ensure" in content_signature:
        return "Data Validation/Schema"
    if "serializ" in path_lower or "json" in content_signature and "load" in content_signature : return "Serialization (JSON)"
    if "calculat" in path_lower or "math" in content_signature or "stat" in content_signature : return "Calculation/Math Utility"
    if "network" in path_lower or "http" in content_signature or "request" in content_signature : return "Network Operations"
    if "security" in path_lower or "crypto" in content_signature or "auth" in content_signature : return "Security/Cryptography"
    if "log" in path_lower or "logger" in content_signature : return "Logging Utility"
    if "convert" in path_lower or "transform" in content_signature: return "Data Conversion/Transformation"
    if "analy" in path_lower or "scan" in path_lower or "report" in content_signature : return "Analysis/Reporting Tool"
    
    # Fallback based on primary class/function names if specific keywords aren't hit
    if classes: 
        main_class_name = list(classes.keys())[0]
        return f"{main_class_name} (Tool/Utility)" 
    if functions: 
        return f"Functions for {functions[0].replace('_', ' ')} (Tool/Utility)" 

    return "General Purpose Tool/Utility"

def _get_primary_class_docstring(classes: Dict[str, dict]) -> str:
    if not classes: return ""
    for class_name, class_data in classes.items():
        docstring = class_data.get("docstring")
        if isinstance(docstring, str) and docstring.strip():
            return docstring
    return ""

# ───────────────────────── helpers ─────────────────────────
def load_analysis(path: Path) -> Dict[str, dict]:
    """Return parsed JSON or exit loudly."""
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        log.error("analysis file missing: %s", path)
        sys.exit(1)
    except json.JSONDecodeError as e:
        log.error("malformed JSON: %s — %s", path, e)
        sys.exit(1)


def normalise(raw: str) -> str:
    """Ensure unix slashes & prepend dreamos prefix if file exists there."""
    p = raw.replace("\\", "/")
    if p.startswith(cfg.dreamos_prefix):
        return p
    candidate_full_path_str = f"{cfg.dreamos_prefix}{p}"
    if (cfg.root / candidate_full_path_str).exists():
         return candidate_full_path_str
    if Path(p).exists() and Path(p).is_file():
        return p 
    log.warning(f"Path {p} could not be reliably normalized or confirmed to exist starting with {cfg.dreamos_prefix}")
    return p # fallback – may be outside Dream.OS or malformed


def categorize(path: str) -> Category:
    if not path.startswith(cfg.dreamos_prefix):
        return Category.OTHER
    rel = path[len(cfg.dreamos_prefix) :]
    if rel.startswith("core/utils/"):
        return Category.UTIL
    for prefix, cat in PREFIX_MAP.items():
        if rel.startswith(prefix):
            return cat
    return Category.OTHER


def fmt_row(module_path_key: str, data: dict, cat: Category) -> str:
    """
    Formats a single row for the markdown table.
    module_path_key is the path as found in project_analysis.json (e.g., "src/dreamos/core/config.py")
    data is the dict of analysis data for that module.
    cat is the determined Category enum.
    """
    log.debug(f"fmt_row: Processing {module_path_key} for category {cat.name}")
    symbols: List[str] = []
    key_classes = data.get("classes") or {}
    key_functions = data.get("functions") or []
    
    symbols += [f"Class: {c}" for c in key_classes][:2]
    symbols += [f"Func: {f}" for f in key_functions][:2]
    symbol_str = ", ".join(symbols) or "N/A"
    if len(symbols) < (len(key_classes) + len(key_functions)):
        symbol_str += ", …"

    role_behaviors = "N/A"
    main_class_docstring = _get_primary_class_docstring(key_classes)
    first_line_doc = main_class_docstring.split('\n')[0].strip() if main_class_docstring else ""
    
    if cat == Category.AGENTS and key_classes:
        main_class_name = list(key_classes.keys())[0]
        doc_summary = (first_line_doc[:75] + '…') if len(first_line_doc) > 75 else first_line_doc
        if not doc_summary: doc_summary = "No detailed docstring."
        agent_class_data = key_classes.get(main_class_name, {})
        methods = agent_class_data.get("methods", [])[:3]
        methods_str = ", ".join(methods) or "No distinct methods."
        role_behaviors = f"{main_class_name}: {doc_summary}. Key Actions: {methods_str}"
        if doc_summary == "No detailed docstring." and methods_str != "No distinct methods.":
            role_behaviors = f"{main_class_name} (No detailed docstring). Key Actions: {methods_str}"
        elif not methods:
             role_behaviors = f"{main_class_name}: {doc_summary}"
    
    elif cat == Category.SERVICES and key_classes:
        main_class_name = list(key_classes.keys())[0]
        methods = key_classes[main_class_name].get("methods", [])
        service_type, op_pattern = _classify_service_type_and_pattern(main_class_name, methods, main_class_docstring)
        first_line_docstring = main_class_docstring.split('\n')[0].strip() if main_class_docstring else ""
        summary_role = (first_line_docstring[:60] + '…') if len(first_line_docstring) > 60 else first_line_docstring
        if not summary_role: summary_role = "Handles specific backend tasks or events."
        role_behaviors = f"Type: {service_type} ({op_pattern}). Role: {summary_role}"

    elif (cat == Category.TOOLS or cat == Category.UTIL or (cat == Category.CORE and "utils" in module_path_key)) and (key_classes or key_functions):
        role_behaviors = _classify_tool_util_functionality(module_path_key, key_classes, key_functions, main_class_docstring)

    elif cat == Category.CORE and (key_classes or key_functions):
        summary = (first_line_doc[:75] + '…') if len(first_line_doc) > 75 else first_line_doc
        if key_classes: role_behaviors = f"Core Component: {list(key_classes.keys())[0]}. Purpose: {summary or 'Core system functionality'}"
        elif key_functions: role_behaviors = f"Core Functions: {key_functions[0]}. Purpose: {summary or 'Core system operations'}"
        else: role_behaviors = "Core system module."

    elif cat == Category.AUTOMATION and (key_classes or key_functions):
        summary = (first_line_doc[:75] + '…') if len(first_line_doc) > 75 else first_line_doc
        if key_classes: main_entity = list(key_classes.keys())[0]
        elif key_functions: main_entity = key_functions[0]
        else: main_entity = Path(module_path_key).name
        role_behaviors = f"Automation: {main_entity}. Role: {summary or 'Automates Dream.OS tasks or workflows'}"
        if "orchestrat" in module_path_key: role_behaviors += " (Orchestration Focus)"
        if "cursor" in module_path_key: role_behaviors += " (Cursor Interaction)"
        if "swarm" in module_path_key: role_behaviors += " (Swarm Control)"

    elif cat == Category.INTEGRATIONS and (key_classes or key_functions):
        summary = (first_line_doc[:75] + '…') if len(first_line_doc) > 75 else first_line_doc
        target_service = "External System"
        if "openai" in module_path_key: target_service = "OpenAI API"
        elif "discord" in module_path_key: target_service = "Discord API"
        elif "azure" in module_path_key: target_service = "Azure Services"
        elif "cursor" in module_path_key: target_service = "Cursor Application"
        elif "browser" in module_path_key: target_service = "Web Browser"
        main_entity_name = list(key_classes.keys())[0] if key_classes else Path(module_path_key).name
        role_behaviors = f"Integration: {main_entity_name} with {target_service}. Purpose: {summary or 'Interface for external communication'}"

    elif cat == Category.CLI and (key_classes or key_functions):
        summary = (first_line_doc[:75] + '…') if len(first_line_doc) > 75 else first_line_doc
        main_entity_name = list(key_classes.keys())[0] if key_classes else Path(module_path_key).stem.replace('_',' ').title()
        role_behaviors = f"CLI Interface: {main_entity_name}. Purpose: {summary or 'Exposes functionality via command line'}"

    # --- Dependency Extraction ---
    dependencies_str = "N/A"
    actual_file_path = cfg.root / module_path_key 
    log.debug(f"  fmt_row: Actual file path for imports: {actual_file_path}")
    if actual_file_path.suffix == '.py' and actual_file_path.exists():
        try:
            direct_imports, from_imports = extract_imports_from_file(actual_file_path)
            log.debug(f"    Extracted imports - Direct: {direct_imports}, From: {from_imports}")
            internal_deps_list = set()
            external_deps_list = set()
            
            all_extracted_imports = direct_imports.union(from_imports)
            
            current_module_name_part = actual_file_path.stem

            for imp_item in all_extracted_imports:
                if imp_item == current_module_name_part:
                    continue
                if imp_item in KNOWN_INTERNAL_TOP_LEVELS:
                    if imp_item != module_path_key.split('/')[2] if len(module_path_key.split('/')) > 2 else True:
                        internal_deps_list.add(imp_item)
                elif imp_item not in COMMON_STDLIB_MODULES:
                    external_deps_list.add(imp_item)
            
            dep_parts = []
            if internal_deps_list:
                dep_parts.append(f"Internal: `{', '.join(sorted(list(internal_deps_list)))}`")
            if external_deps_list:
                dep_parts.append(f"External: `{', '.join(sorted(list(external_deps_list)))}`")
            
            if dep_parts:
                dependencies_str = ". ".join(dep_parts)
            log.debug(f"    Formatted dependencies: {dependencies_str}")
        except Exception as e_import_extract:
            log.error(f"    Error during import extraction/processing for {actual_file_path}: {e_import_extract}")
            dependencies_str = "Error extracting"
    elif actual_file_path.suffix == '.py':
        log.warning(f"  fmt_row: Python file {actual_file_path} does not exist, cannot extract imports.")
        dependencies_str = "File not found"

    statefulness_str = "TBD"
    maturity_str = "TBD"
    recommendation_str = "TBD"
    notes_str = ""

    row_content = f"| {module_path_key} | {cat.name} | {symbol_str} | {role_behaviors} | {dependencies_str} | {statefulness_str} | {maturity_str} | {recommendation_str} | {notes_str} |\\n"
    log.debug(f"  fmt_row: Generated row: {row_content.strip()}")
    return row_content


def build_tables(analysis: Dict[str, dict]) -> Dict[Category, List[str]]:
    """Build markdown tables grouped by category."""
    log.info(f"build_tables: Starting with {len(analysis)} items.")
    tables: Dict[Category, List[str]] = {cat: [TABLE_HEADER] for cat in Category if cat != Category.OTHER}
    if Category.OTHER not in tables : tables[Category.OTHER] = [TABLE_HEADER]

    sorted_paths = sorted(analysis.keys())
    processed_count = 0

    for path_key in sorted_paths:
        log.debug(f"  build_tables: Processing path_key: {path_key}")
        data = analysis.get(path_key) # Use .get() for safety
        if data is None:
            log.warning(f"    build_tables: No data found for path_key {path_key} in analysis dict. Skipping.")
            continue

        cat = categorize(path_key)
        log.debug(f"    build_tables: Categorized {path_key} as {cat.name}")
        
        # Logic for adding to tables based on category and markers
        if cat != Category.OTHER: # Process explicitly defined categories that should have markers
            if cat in tables and cat in MD_MARKERS: # Check if this category is intended for a marked section
                row = fmt_row(path_key, data, cat)
                if row.strip():
                    tables[cat].append(row)
                    processed_count +=1
                    log.debug(f"      build_tables: Added {cat.name} {path_key} to table. Row: {bool(row.strip())}")
                else:
                    log.debug(f"      build_tables: fmt_row for {cat.name} {path_key} produced empty/whitespace row.")
            else:
                log.debug(f"      build_tables: Skipped {cat.name} {path_key} as it's not OTHER but lacks MD_MARKER entry (or table).")
        elif path_key.startswith(cfg.dreamos_prefix): # Process OTHER category only if it's a dreamos path
            # This ensures 'OTHER' things inside src/dreamos are at least processed by fmt_row.
            # Their inclusion in the final .md depends on MD_MARKERS and inject_tables for Category.OTHER.
            if Category.OTHER not in tables: tables[Category.OTHER] = [TABLE_HEADER] # Should already exist
            row = fmt_row(path_key, data, cat)
            if row.strip():
                tables[Category.OTHER].append(row)
                processed_count += 1
                log.debug(f"      build_tables: Added OTHER (dreamos prefixed) {path_key} to OTHER table. Row: {bool(row.strip())}")
            else:
                log.debug(f"      build_tables: fmt_row for OTHER (dreamos prefixed) {path_key} produced empty/whitespace row.")
        else: # Non-dreamos prefix and OTHER, or some other skip condition (e.g. OTHER and no dreamos prefix)
            log.debug(f"      build_tables: Skipped {path_key} (Category: {cat.name}). It's OTHER and not dreamos_prefix, or failed previous conditions.")

    log.info(f"build_tables: Finished. Processed {processed_count} items into rows.")
    for cat_name, tbl_lines in tables.items():
        log.debug(f"  Final table for {cat_name.name} has {len(tbl_lines)-1} data rows.")
    return tables


# ──────────────────────── MD injection ─────────────────────
def inject_tables(md_path: Path, tables: Dict[Category, List[str]]) -> None:
    log.info(f"Attempting to inject tables into {md_path}")
    try:
        content = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
    except Exception as e:
        log.error(f"Error reading markdown file {md_path}: {e}")
        return

    for cat, table_lines in tables.items():
        if cat not in MD_MARKERS: continue
        start_marker, end_marker = MD_MARKERS[cat]
        # Ensure markers are regex-safe if they contain special characters (they don't here)
        pattern = re.compile(f"{re.escape(start_marker)}(.*?){re.escape(end_marker)}", re.DOTALL)
        table_md = "".join(table_lines)
        replacement = f"{start_marker}\n{table_md}{end_marker}"
        
        if pattern.search(content):
            content = pattern.sub(replacement, content)
            log.info(f"Replaced section for {cat.name}")
        else:
            # If markers not found, append new section (or log warning)
            log.warning(f"Markers for {cat.name} not found in {md_path}. Appending section.")
            content += f"\n## {cat.name.title().replace('_', ' ')}\n{replacement}\n"
    
    try:
        md_path.write_text(content, encoding="utf-8")
        log.info(f"Successfully wrote updated content to {md_path}")
    except Exception as e:
        log.error(f"Error writing updated markdown to {md_path}: {e}")


# ─────────────────────────── main ──────────────────────────
def main() -> None:
    log.info("--- module_mapper.py script started ---")
    if not cfg.analysis_json.exists():
        log.error(f"project_analysis.json not found at {cfg.analysis_json}")
        sys.exit(1)
    
    log.info(f"Loading analysis from: {cfg.analysis_json}")
    analysis_data = load_analysis(cfg.analysis_json)
    log.info(f"Loaded {len(analysis_data)} entries from analysis data.")
    
    log.info("Building module map tables...")
    tables = build_tables(analysis_data)
    log.info(f"Built tables for {len(tables)} categories.")
    
    log.info(f"Injecting tables into: {cfg.module_map_md}")
    if not cfg.module_map_md.parent.exists():
        cfg.module_map_md.parent.mkdir(parents=True, exist_ok=True)
        log.info(f"Created directory {cfg.module_map_md.parent}")
    # Ensure the file exists before inject_tables tries to read it, if it might be created new.
    # The new inject_tables handles reading an empty string if file doesn't exist, 
    # but it's better if it exists. If markers are missing, it appends.
    if not cfg.module_map_md.exists(): 
        cfg.module_map_md.touch()
        log.info(f"Touched/created {cfg.module_map_md} before injection.")

    inject_tables(cfg.module_map_md, tables)
    log.info("--- module_mapper.py script finished ---")


if __name__ == "__main__":
    # Set higher logging level for script execution if desired for debugging
    logging.getLogger().setLevel(logging.DEBUG) # Uncomment for DEBUG level
    main() 