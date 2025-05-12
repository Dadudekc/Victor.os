#!/usr/bin/env python3
"""
Enhanced Migration Validators for Dream.OS
Validates Python files for common issues before migration.
"""

import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class ValidationIssue:
    """Represents a validation issue found in a file."""
    file: Path
    line: int
    message: str
    severity: str  # 'error' or 'warning'
    issue_type: str  # 'unused_import', 'mixed_tabs', 'conflict', etc.

class MigrationValidator:
    """Validates Python files for migration readiness."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.issues: List[ValidationIssue] = []
        self.module_names: Dict[str, List[Path]] = defaultdict(list)
        
    def _check_unused_imports(self, file_path: Path) -> List[ValidationIssue]:
        """Check for unused imports using AST."""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
                
            # Get all imports
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        imports.add(name.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            
            # Get all name references
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    used_names.add(node.id)
            
            # Check for unused imports
            for imp in imports:
                if imp not in used_names and not any(imp in name for name in used_names):
                    issues.append(ValidationIssue(
                        file=file_path,
                        line=0,  # TODO: Get actual line number
                        message=f"Unused import: {imp}",
                        severity="warning",
                        issue_type="unused_import"
                    ))
                    
        except Exception as e:
            logger.error(f"Error checking unused imports in {file_path}: {e}")
            
        return issues
    
    def _check_mixed_tabs_spaces(self, file_path: Path) -> List[ValidationIssue]:
        """Check for mixed tabs and spaces in indentation."""
        issues = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines, 1):
                if '\t' in line and ' ' in line[:len(line) - len(line.lstrip())]:
                    issues.append(ValidationIssue(
                        file=file_path,
                        line=i,
                        message="Mixed tabs and spaces in indentation",
                        severity="error",
                        issue_type="mixed_tabs"
                    ))
                    
        except Exception as e:
            logger.error(f"Error checking mixed tabs/spaces in {file_path}: {e}")
            
        return issues
    
    def _check_module_conflicts(self, file_path: Path) -> List[ValidationIssue]:
        """Check for potential module name conflicts."""
        issues = []
        try:
            # Get module name from path
            relative_path = file_path.relative_to(self.root_dir)
            module_name = str(relative_path).replace("/", ".").replace("\\", ".")[:-3]
            
            # Record this module
            self.module_names[module_name].append(file_path)
            
            # Check for conflicts
            if len(self.module_names[module_name]) > 1:
                conflicts = self.module_names[module_name]
                issues.append(ValidationIssue(
                    file=file_path,
                    line=0,
                    message=f"Module name conflict: {module_name} exists in multiple locations: {conflicts}",
                    severity="error",
                    issue_type="conflict"
                ))
                
        except Exception as e:
            logger.error(f"Error checking module conflicts in {file_path}: {e}")
            
        return issues
    
    def validate_file(self, file_path: Path) -> List[ValidationIssue]:
        """Run all validators on a single file."""
        if not file_path.suffix == '.py':
            return []
            
        issues = []
        issues.extend(self._check_unused_imports(file_path))
        issues.extend(self._check_mixed_tabs_spaces(file_path))
        issues.extend(self._check_module_conflicts(file_path))
        
        return issues
    
    def validate_directory(self, directory: Path) -> List[ValidationIssue]:
        """Run all validators on a directory of Python files."""
        all_issues = []
        
        for file_path in directory.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
                
            issues = self.validate_file(file_path)
            all_issues.extend(issues)
            
        return all_issues
    
    def report(self) -> None:
        """Report all validation issues found."""
        if not self.issues:
            logger.info("✅ No validation issues found!")
            return
            
        # Group issues by severity
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        
        if errors:
            logger.error("\n❌ Validation errors found:")
            for issue in errors:
                logger.error(f"\n  {issue.file}:{issue.line}")
                logger.error(f"  {issue.message}")
                
        if warnings:
            logger.warning("\n⚠️ Validation warnings found:")
            for issue in warnings:
                logger.warning(f"\n  {issue.file}:{issue.line}")
                logger.warning(f"  {issue.message}")
                
        # Summary
        logger.info(f"\nValidation summary:")
        logger.info(f"  - {len(errors)} errors")
        logger.info(f"  - {len(warnings)} warnings")
        
    def has_errors(self) -> bool:
        """Check if any validation errors were found."""
        return any(i.severity == "error" for i in self.issues) 