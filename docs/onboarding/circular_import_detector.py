#!/usr/bin/env python3
"""
Circular Import Detector for Dream.OS Migration System
Detects and reports circular dependencies between modules.
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class CircularDependency:
    """Represents a circular dependency between modules."""
    cycle: List[str]
    files: List[Path]
    severity: str  # 'error' or 'warning'

class CircularImportDetector:
    """Detects circular dependencies between Python modules."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.import_graph: Dict[str, Set[str]] = defaultdict(set)
        self.module_to_file: Dict[str, Path] = {}
        self.circular_deps: List[CircularDependency] = []
        
    def _parse_file(self, file_path: Path) -> List[str]:
        """Parse a Python file and extract its imports."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return imports

    def _build_import_graph(self):
        """Build a graph of module dependencies."""
        for file_path in self.root_dir.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
                
            relative_path = file_path.relative_to(self.root_dir)
            module_name = str(relative_path).replace("/", ".").replace("\\", ".")[:-3]
            
            self.module_to_file[module_name] = file_path
            imports = self._parse_file(file_path)
            
            for imp in imports:
                # Only track internal imports
                if imp.startswith("docs.") or imp.startswith("src."):
                    self.import_graph[module_name].add(imp)

    def _detect_cycles(self):
        """Detect circular dependencies using DFS."""
        visited = set()
        path = []
        
        def dfs(module: str):
            if module in path:
                # Found a cycle
                cycle_start = path.index(module)
                cycle = path[cycle_start:] + [module]
                
                # Get the files involved
                files = [self.module_to_file.get(m) for m in cycle if m in self.module_to_file]
                files = [f for f in files if f is not None]
                
                # Determine severity based on cycle length
                severity = "error" if len(cycle) <= 3 else "warning"
                
                self.circular_deps.append(CircularDependency(
                    cycle=cycle,
                    files=files,
                    severity=severity
                ))
                return
                
            if module in visited:
                return
                
            visited.add(module)
            path.append(module)
            
            for imp in self.import_graph.get(module, []):
                if imp in self.import_graph:
                    dfs(imp)
                    
            path.pop()
            
        # Start DFS from each module
        for module in self.import_graph:
            if module not in visited:
                dfs(module)

    def detect(self) -> List[CircularDependency]:
        """Run the circular dependency detection."""
        self._build_import_graph()
        self._detect_cycles()
        return self.circular_deps

    def report(self) -> None:
        """Report detected circular dependencies."""
        if not self.circular_deps:
            logger.info("✅ No circular dependencies detected!")
            return
            
        logger.warning("\n⚠️ Circular dependencies detected:")
        for dep in self.circular_deps:
            severity = "❌" if dep.severity == "error" else "⚠️"
            logger.warning(f"\n{severity} Cycle: {' -> '.join(dep.cycle)}")
            logger.warning("Files involved:")
            for file in dep.files:
                logger.warning(f"  - {file}") 