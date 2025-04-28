import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

IMPORT_GRAPH_FILE = Path('import-graph.json')
OUTPUT_FILE = Path('orphaned-files.json')
# Consider common entry points or implicitly used files that shouldn't be marked orphaned
# e.g., main scripts, config files, __init__.py often imported implicitly or run directly
KNOWN_ENTRY_POINTS_OR_USED = {
    'src/__main__.py', # Example potential entry point
    'src/main.py',
    'src/app.py',
    'src/server.py',
    # __init__.py are implicitly used when importing packages
    # Might need a more sophisticated check later if __init__ files DO contain code
}

def find_orphaned_modules(graph_path: Path) -> list[str]:
    """Analyze import graph to find modules that are defined but never imported."""
    try:
        with open(graph_path, 'r', encoding='utf-8') as f:
            import_graph = json.load(f)
    except FileNotFoundError:
        logging.error(f"Import graph file not found: {graph_path}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {graph_path}: {e}")
        return []
    except Exception as e:
        logging.error(f"Error reading import graph {graph_path}: {e}")
        return []

    defined_modules = set(import_graph.keys())
    imported_modules_flat = set()

    # Map imported top-level names back to potential file paths within src/
    # This requires understanding the project structure & sys.path potentially
    # Simplistic approach: Check if an import name matches the start of a defined module path
    # e.g., import 'dreamos' might refer to files in 'src/dreamos/...'

    # Collect all unique top-level import names mentioned
    raw_imports = set()
    for imports_list in import_graph.values():
        for imp in imports_list:
            raw_imports.add(imp) # These are top-level names like 'os', 'dreamos', 'pathlib'

    # Attempt to resolve raw imports to project modules
    # This is a basic heuristic and might miss things or have false positives
    potentially_imported_project_modules = set()
    for imp_name in raw_imports:
        for defined_module in defined_modules:
            # Check if import name matches a package/directory name
            if defined_module.startswith(f'src/{imp_name}/'):
                 potentially_imported_project_modules.add(defined_module)
            # Check if import name matches a filename (minus .py)
            elif defined_module == f'src/{imp_name}.py':
                 potentially_imported_project_modules.add(defined_module)
            # Could add more checks (e.g., relative imports based on graph keys)
    
    # Alternative: A simpler check might be needed if the graph only contains stdlib/external imports
    # Let's check how many project files are actually listed in the values
    imported_in_graph_values = set()
    module_stems = {m.replace('src/', '').replace('/', '.').replace('.py', '') for m in defined_modules}

    for module, imports_list in import_graph.items():
        # Determine the package context of the importing module
        # package_context = module.replace('src/', '').rsplit('/', 1)[0].replace('/', '.') if '/' in module else ''
        
        for imp_name in imports_list:
            # Try to resolve imp_name relative to known modules
            possible_module_path_stem = imp_name # If it's absolute like dreamos.utils
            if imp_name.startswith('.'):
                 # Basic relative import handling needed here if graph included levels
                 pass # AST script didn't capture levels, so skip for now
            
            # Check if this resolved name matches any defined module stems
            if possible_module_path_stem in module_stems:
                 # Find the full path matching the stem
                 matched_defined = [m for m in defined_modules if m.replace('src/', '').replace('/', '.').replace('.py', '') == possible_module_path_stem]
                 if matched_defined:
                      imported_in_graph_values.add(matched_defined[0])
            # Also consider package imports (importing a directory implicitly imports __init__.py)
            possible_init_path = f"src/{possible_module_path_stem.replace('.', '/')}/__init__.py"
            if possible_init_path in defined_modules:
                 imported_in_graph_values.add(possible_init_path)


    logging.info(f"Defined modules: {len(defined_modules)}")
    logging.info(f"Unique imports resolved to project files: {len(imported_in_graph_values)}")

    # Orphaned = Defined - Imported (within project)
    # Also exclude known entry points and __init__.py files for now
    orphaned = defined_modules - imported_in_graph_values - KNOWN_ENTRY_POINTS_OR_USED
    
    # Filter out all __init__.py for simplicity in this first pass
    orphaned = {o for o in orphaned if not o.endswith('__init__.py')}

    logging.info(f"Found {len(orphaned)} potentially orphaned modules (excluding __init__.py and entry points)." )

    return sorted(list(orphaned))

def main():
    logging.info(f"Analyzing import graph: {IMPORT_GRAPH_FILE}")
    orphaned_files = find_orphaned_modules(IMPORT_GRAPH_FILE)

    logging.info(f"Writing orphaned file list to {OUTPUT_FILE}...")
    output_data = {
        "analysis_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "import_graph_source": str(IMPORT_GRAPH_FILE),
        "excluded_entry_points": sorted(list(KNOWN_ENTRY_POINTS_OR_USED)),
        "orphaned_files_count": len(orphaned_files),
        "orphaned_files": orphaned_files
    }
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)
        logging.info("Orphaned file analysis complete.")
    except Exception as e:
        logging.error(f"Failed to write output file {OUTPUT_FILE}: {e}")

if __name__ == "__main__":
    # Need datetime/timezone for timestamp
    from datetime import datetime, timezone 
    main() 