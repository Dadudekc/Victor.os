import json
import os
from pathlib import Path
from typing import Dict, List, Set
import ast
import importlib.util
import sys
from collections import defaultdict

class ProjectScanner:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.analysis = {
            "project_root": str(root_dir),
            "num_files_analyzed": 0,
            "analysis_details": {},
            "file_counts": {
                "total_files": 0,
                "orphaned_files": 0,
                "missing_docs": 0,
                "modules": defaultdict(int)
            },
            "dependencies": {},
            "duplicate_code": defaultdict(list),
            "unused_imports": defaultdict(list)
        }
        
    def scan_file(self, file_path: Path) -> dict:
        """Analyze a single Python file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tree = ast.parse(content)
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Extract functions and classes
            functions = []
            classes = {}
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                    classes[node.name] = {
                        "methods": methods,
                        "docstring": ast.get_docstring(node),
                        "base_classes": [base.id for base in node.bases if isinstance(base, ast.Name)]
                    }
            
            return {
                "language": file_path.suffix,
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "complexity": len(functions) + len(classes)
            }
            
        except Exception as e:
            print(f"Error analyzing {file_path}: {str(e)}")
            return {
                "language": file_path.suffix,
                "functions": [],
                "classes": {},
                "imports": [],
                "complexity": 0,
                "error": str(e)
            }
    
    def find_orphaned_files(self) -> Set[Path]:
        """Find files that aren't imported anywhere"""
        all_files = set()
        imported_files = set()
        
        # Collect all Python files
        for path in self.root_dir.rglob("*.py"):
            if "venv" not in str(path) and "__pycache__" not in str(path):
                all_files.add(path)
        
        # Find imported files
        for path in all_files:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if node.module:
                            try:
                                spec = importlib.util.find_spec(node.module)
                                if spec and spec.origin:
                                    imported_files.add(Path(spec.origin))
                            except:
                                pass
            except:
                continue
        
        return all_files - imported_files
    
    def find_duplicate_code(self) -> Dict[str, List[str]]:
        """Find duplicate code blocks"""
        duplicates = defaultdict(list)
        code_blocks = defaultdict(list)
        
        for path in self.root_dir.rglob("*.py"):
            if "venv" not in str(path) and "__pycache__" not in str(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Simple block detection (can be improved)
                    blocks = content.split("\n\n")
                    for block in blocks:
                        if len(block.strip()) > 50:  # Only consider substantial blocks
                            code_blocks[block.strip()].append(str(path))
                except:
                    continue
        
        for block, files in code_blocks.items():
            if len(files) > 1:
                duplicates[block[:100] + "..."] = files
        
        return duplicates
    
    def scan(self):
        """Perform full project scan"""
        # Scan Python files
        for path in self.root_dir.rglob("*.py"):
            if "venv" not in str(path) and "__pycache__" not in str(path):
                rel_path = path.relative_to(self.root_dir)
                self.analysis["analysis_details"][str(rel_path)] = self.scan_file(path)
                self.analysis["num_files_analyzed"] += 1
                self.analysis["file_counts"]["total_files"] += 1
                
                # Track module usage
                module_parts = str(rel_path).split(os.sep)
                if len(module_parts) > 1:
                    self.analysis["file_counts"]["modules"][module_parts[0]] += 1
        
        # Find orphaned files
        orphaned = self.find_orphaned_files()
        self.analysis["file_counts"]["orphaned_files"] = len(orphaned)
        
        # Find duplicate code
        self.analysis["duplicate_code"] = self.find_duplicate_code()
        
        return self.analysis

def main():
    root_dir = Path(__file__).resolve().parents[2]
    scanner = ProjectScanner(root_dir)
    analysis = scanner.scan()
    
    # Save analysis
    output_file = root_dir / "project_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=4)
    
    print(f"Analysis complete. Results saved to {output_file}")
    print(f"Files analyzed: {analysis['num_files_analyzed']}")
    print(f"Orphaned files: {analysis['file_counts']['orphaned_files']}")
    print(f"Duplicate code blocks: {len(analysis['duplicate_code'])}")

if __name__ == "__main__":
    main() 