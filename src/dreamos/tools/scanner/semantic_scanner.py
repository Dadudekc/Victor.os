"""
Semantic scanner for enhanced code search capabilities.

This module provides semantic analysis and search capabilities for code,
including code structure analysis, dependency tracking, and semantic indexing.
"""

import ast
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict

from dreamos.core.config import AppConfig
from dreamos.tools.scanner.base_scanner import BaseScanner
from dreamos.tools.scanner.language_analyzer import LanguageAnalyzer

logger = logging.getLogger(__name__)

class SemanticScanner(BaseScanner):
    """Semantic scanner for enhanced code search capabilities."""
    
    def __init__(self, config: AppConfig):
        """Initialize semantic scanner with configuration."""
        super().__init__(config)
        self.language_analyzer = LanguageAnalyzer()
        self._semantic_index: Dict[str, Any] = {}
        self._index_file = Path(config.paths.cache_dir) / "semantic_index.json"
        
    async def scan(self, project_path: Path) -> Dict[str, Any]:
        """Scan project for semantic information."""
        try:
            # Extract semantic information from code
            semantic_info = await self._extract_semantic_info(project_path)
            
            # Build semantic index
            semantic_index = await self._build_semantic_index(semantic_info)
            
            # Save index for future use
            await self._save_semantic_index(semantic_index)
            
            return {
                "semantic_info": semantic_info,
                "semantic_index": semantic_index
            }
            
        except Exception as e:
            logger.error(f"Error scanning project: {e}")
            return {}
            
    async def search(
        self,
        query: str,
        project_path: Optional[Path] = None
    ) -> List[Dict[str, Any]]:
        """Search code using semantic capabilities."""
        try:
            # Load semantic index
            semantic_index = await self._load_semantic_index(project_path)
            
            # Perform semantic search
            results = await self._semantic_search(query, semantic_index)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching code: {e}")
            return []
            
    async def analyze(self, code_path: Path) -> Dict[str, Any]:
        """Analyze code for semantic information."""
        try:
            # Extract semantic information
            semantic_info = await self._extract_semantic_info(code_path)
            
            # Analyze code structure
            structure_info = await self._analyze_code_structure(code_path)
            
            # Analyze code dependencies
            dependency_info = await self._analyze_dependencies(code_path)
            
            return {
                "semantic_info": semantic_info,
                "structure_info": structure_info,
                "dependency_info": dependency_info
            }
            
        except Exception as e:
            logger.error(f"Error analyzing code: {e}")
            return {}
            
    async def _extract_semantic_info(self, path: Path) -> Dict[str, Any]:
        """Extract semantic information from code."""
        try:
            if not path.exists():
                return {}
                
            if path.is_file():
                return await self._analyze_file(path)
            else:
                return await self._analyze_directory(path)
                
        except Exception as e:
            logger.error(f"Error extracting semantic info from {path}: {e}")
            return {}
            
    async def _analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single file for semantic information."""
        try:
            content = file_path.read_text()
            
            # Parse AST
            tree = ast.parse(content)
            
            # Extract information
            info = {
                "imports": [],
                "classes": {},
                "functions": {},
                "variables": {},
                "docstrings": {},
                "type_hints": {},
                "decorators": {}
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        info["imports"].append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        info["imports"].append(f"{module}.{name.name}")
                elif isinstance(node, ast.ClassDef):
                    info["classes"][node.name] = {
                        "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
                        "docstring": ast.get_docstring(node),
                        "methods": {},
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                    }
                elif isinstance(node, ast.FunctionDef):
                    info["functions"][node.name] = {
                        "args": [arg.arg for arg in node.args.args],
                        "returns": self._get_return_type(node),
                        "docstring": ast.get_docstring(node),
                        "decorators": [d.id for d in node.decorator_list if isinstance(d, ast.Name)]
                    }
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            info["variables"][target.id] = {
                                "type": self._infer_type(node.value),
                                "value": ast.unparse(node.value)
                            }
                            
            return info
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
            return {}
            
    async def _analyze_directory(self, dir_path: Path) -> Dict[str, Any]:
        """Analyze a directory for semantic information."""
        try:
            info = {
                "files": {},
                "modules": {},
                "dependencies": set()
            }
            
            for file_path in dir_path.rglob("*.py"):
                if file_path.is_file():
                    file_info = await self._analyze_file(file_path)
                    info["files"][str(file_path.relative_to(dir_path))] = file_info
                    
                    # Extract module dependencies
                    for imp in file_info.get("imports", []):
                        info["dependencies"].add(imp)
                        
            return info
            
        except Exception as e:
            logger.error(f"Error analyzing directory {dir_path}: {e}")
            return {}
            
    async def _build_semantic_index(self, semantic_info: Dict[str, Any]) -> Dict[str, Any]:
        """Build semantic index from semantic information."""
        try:
            index = {
                "classes": {},
                "functions": {},
                "variables": {},
                "imports": {},
                "dependencies": set()
            }
            
            for file_path, file_info in semantic_info.get("files", {}).items():
                # Index classes
                for class_name, class_info in file_info.get("classes", {}).items():
                    index["classes"][class_name] = {
                        "file": file_path,
                        "bases": class_info["bases"],
                        "docstring": class_info["docstring"],
                        "methods": class_info["methods"]
                    }
                    
                # Index functions
                for func_name, func_info in file_info.get("functions", {}).items():
                    index["functions"][func_name] = {
                        "file": file_path,
                        "args": func_info["args"],
                        "returns": func_info["returns"],
                        "docstring": func_info["docstring"]
                    }
                    
                # Index variables
                for var_name, var_info in file_info.get("variables", {}).items():
                    index["variables"][var_name] = {
                        "file": file_path,
                        "type": var_info["type"],
                        "value": var_info["value"]
                    }
                    
                # Index imports
                for imp in file_info.get("imports", []):
                    if imp not in index["imports"]:
                        index["imports"][imp] = set()
                    index["imports"][imp].add(file_path)
                    
                # Add dependencies
                index["dependencies"].update(file_info.get("dependencies", set()))
                
            return index
            
        except Exception as e:
            logger.error(f"Error building semantic index: {e}")
            return {}
            
    async def _save_semantic_index(self, index: Dict[str, Any]):
        """Save semantic index to file."""
        try:
            # Convert sets to lists for JSON serialization
            serializable_index = {
                "classes": index["classes"],
                "functions": index["functions"],
                "variables": index["variables"],
                "imports": {k: list(v) for k, v in index["imports"].items()},
                "dependencies": list(index["dependencies"])
            }
            
            self._index_file.parent.mkdir(parents=True, exist_ok=True)
            self._index_file.write_text(json.dumps(serializable_index, indent=2))
            
        except Exception as e:
            logger.error(f"Error saving semantic index: {e}")
            
    async def _load_semantic_index(self, project_path: Optional[Path]) -> Dict[str, Any]:
        """Load semantic index for project."""
        try:
            if self._index_file.exists():
                data = json.loads(self._index_file.read_text())
                
                # Convert lists back to sets
                return {
                    "classes": data["classes"],
                    "functions": data["functions"],
                    "variables": data["variables"],
                    "imports": {k: set(v) for k, v in data["imports"].items()},
                    "dependencies": set(data["dependencies"])
                }
            else:
                # If no index exists, create one
                if project_path:
                    semantic_info = await self._extract_semantic_info(project_path)
                    return await self._build_semantic_index(semantic_info)
                return {}
                
        except Exception as e:
            logger.error(f"Error loading semantic index: {e}")
            return {}
            
    async def _semantic_search(
        self,
        query: str,
        semantic_index: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using index."""
        try:
            results = []
            query = query.lower()
            
            # Search classes
            for class_name, class_info in semantic_index["classes"].items():
                if (query in class_name.lower() or
                    query in class_info["docstring"].lower() if class_info["docstring"] else False):
                    results.append({
                        "type": "class",
                        "name": class_name,
                        "file": class_info["file"],
                        "docstring": class_info["docstring"]
                    })
                    
            # Search functions
            for func_name, func_info in semantic_index["functions"].items():
                if (query in func_name.lower() or
                    query in func_info["docstring"].lower() if func_info["docstring"] else False):
                    results.append({
                        "type": "function",
                        "name": func_name,
                        "file": func_info["file"],
                        "docstring": func_info["docstring"]
                    })
                    
            # Search variables
            for var_name, var_info in semantic_index["variables"].items():
                if query in var_name.lower():
                    results.append({
                        "type": "variable",
                        "name": var_name,
                        "file": var_info["file"],
                        "type": var_info["type"]
                    })
                    
            return results
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            return []
            
    async def _analyze_code_structure(self, code_path: Path) -> Dict[str, Any]:
        """Analyze code structure."""
        try:
            if not code_path.exists():
                return {}
                
            content = code_path.read_text()
            tree = ast.parse(content)
            
            structure = {
                "imports": [],
                "classes": [],
                "functions": [],
                "variables": [],
                "complexity": self._calculate_complexity(tree)
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        structure["imports"].append(name.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for name in node.names:
                        structure["imports"].append(f"{module}.{name.name}")
                elif isinstance(node, ast.ClassDef):
                    structure["classes"].append({
                        "name": node.name,
                        "bases": [base.id for base in node.bases if isinstance(base, ast.Name)],
                        "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)])
                    })
                elif isinstance(node, ast.FunctionDef):
                    structure["functions"].append({
                        "name": node.name,
                        "args": len(node.args.args),
                        "returns": bool(node.returns)
                    })
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            structure["variables"].append(target.id)
                            
            return structure
            
        except Exception as e:
            logger.error(f"Error analyzing code structure: {e}")
            return {}
            
    async def _analyze_dependencies(self, code_path: Path) -> Dict[str, Any]:
        """Analyze code dependencies."""
        try:
            if not code_path.exists():
                return {}
                
            content = code_path.read_text()
            tree = ast.parse(content)
            
            dependencies = {
                "imports": set(),
                "from_imports": set(),
                "relative_imports": set(),
                "builtins": set(),
                "third_party": set()
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        dependencies["imports"].add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        if node.level > 0:
                            dependencies["relative_imports"].add(node.module)
                        else:
                            dependencies["from_imports"].add(node.module)
                            
            # Categorize imports
            for imp in dependencies["imports"]:
                if imp in __builtins__:
                    dependencies["builtins"].add(imp)
                else:
                    dependencies["third_party"].add(imp)
                    
            return {k: list(v) for k, v in dependencies.items()}
            
        except Exception as e:
            logger.error(f"Error analyzing dependencies: {e}")
            return {}
            
    def _get_return_type(self, node: ast.FunctionDef) -> str:
        """Get return type annotation from function node."""
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Subscript):
                return ast.unparse(node.returns)
        return "Any"
        
    def _infer_type(self, node: ast.AST) -> str:
        """Infer type from AST node."""
        if isinstance(node, ast.Num):
            return type(node.n).__name__
        elif isinstance(node, ast.Str):
            return "str"
        elif isinstance(node, ast.List):
            return "List"
        elif isinstance(node, ast.Dict):
            return "Dict"
        elif isinstance(node, ast.Tuple):
            return "Tuple"
        elif isinstance(node, ast.Set):
            return "Set"
        elif isinstance(node, ast.NameConstant):
            return type(node.value).__name__
        return "Any"
        
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate code complexity using cyclomatic complexity."""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.FunctionDef,
                               ast.ClassDef, ast.Try, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
                
        return complexity 