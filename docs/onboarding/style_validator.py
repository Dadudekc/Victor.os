#!/usr/bin/env python3
"""
Style and Coverage Validator for Dream.OS
Validates Python files for style compliance and test coverage.
"""

import ast
import logging
import subprocess
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

@dataclass
class StyleIssue:
    """Represents a style or coverage issue."""
    file: Path
    line: int
    message: str
    severity: str  # 'error' or 'warning'
    tool: str  # 'flake8', 'black', 'coverage'
    code: Optional[str] = None

class StyleValidator:
    """Validates Python files for style compliance and test coverage."""
    
    def __init__(self, root_dir: Path, coverage_threshold: float = 80.0):
        self.root_dir = root_dir
        self.coverage_threshold = coverage_threshold
        self.issues: List[StyleIssue] = []
        self.coverage_data: Dict[str, float] = {}
        
    def _run_flake8(self, file_path: Path) -> List[StyleIssue]:
        """Run flake8 on a Python file."""
        issues = []
        try:
            result = subprocess.run(
                ['flake8', str(file_path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            for line in result.stdout.splitlines():
                # Parse flake8 output: file:line:col:code message
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    _, line_num, _, message = parts
                    try:
                        line_num = int(line_num)
                    except ValueError:
                        line_num = 0
                    issues.append(StyleIssue(
                        file=file_path,
                        line=line_num,
                        message=message.strip(),
                        severity='error',  # flake8 issues are always errors
                        tool='flake8',
                        code=message.split()[0] if message else None
                    ))
                    
        except Exception as e:
            logger.error(f"Error running flake8 on {file_path}: {e}")
            
        return issues
    
    def _run_black(self, file_path: Path) -> List[StyleIssue]:
        """Check if file would be reformatted by black."""
        issues = []
        try:
            result = subprocess.run(
                ['black', '--check', '--quiet', str(file_path)],
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                issues.append(StyleIssue(
                    file=file_path,
                    line=0,
                    message="File would be reformatted by black",
                    severity='warning',
                    tool='black'
                ))
                
        except Exception as e:
            logger.error(f"Error running black on {file_path}: {e}")
            
        return issues
    
    def _parse_coverage_xml(self, coverage_path: Path) -> Dict[str, float]:
        """Parse coverage.xml to get per-file coverage percentages."""
        coverage_data = {}
        try:
            tree = ET.parse(coverage_path)
            root = tree.getroot()
            
            for package in root.findall('.//package'):
                for class_elem in package.findall('.//class'):
                    filename = class_elem.get('filename')
                    if filename:
                        try:
                            # Convert line-rate to percentage
                            line_rate = float(class_elem.get('line-rate', 0))
                            coverage_data[filename] = line_rate * 100
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid line-rate for {filename}")
                            coverage_data[filename] = 0.0
                        
        except Exception as e:
            logger.error(f"Error parsing coverage.xml: {e}")
            
        return coverage_data
    
    def _check_coverage(self, file_path: Path) -> List[StyleIssue]:
        """Check if file meets coverage threshold."""
        issues = []
        try:
            # Get relative path for coverage lookup
            rel_path = file_path.relative_to(self.root_dir)
            coverage = self.coverage_data.get(str(rel_path), 0.0)
            
            if coverage < self.coverage_threshold:
                issues.append(StyleIssue(
                    file=file_path,
                    line=0,
                    message=f"Test coverage {coverage:.1f}% below threshold {self.coverage_threshold}%",
                    severity='warning',
                    tool='coverage'
                ))
                
        except Exception as e:
            logger.error(f"Error checking coverage for {file_path}: {e}")
            
        return issues
    
    def validate_file(self, file_path: Path, coverage_path: Optional[Path] = None) -> List[StyleIssue]:
        """Run all style and coverage checks on a file."""
        if not file_path.suffix == '.py':
            return []
            
        issues = []
        
        # Run style checks
        issues.extend(self._run_flake8(file_path))
        issues.extend(self._run_black(file_path))
        
        # Run coverage check if coverage data is available
        if coverage_path and coverage_path.exists():
            if not self.coverage_data:
                self.coverage_data = self._parse_coverage_xml(coverage_path)
            issues.extend(self._check_coverage(file_path))
            
        return issues
    
    def validate_directory(self, directory: Path, coverage_path: Optional[Path] = None) -> List[StyleIssue]:
        """Run all validators on a directory of Python files."""
        all_issues = []
        
        for file_path in directory.rglob("*.py"):
            if "__pycache__" in str(file_path):
                continue
                
            issues = self.validate_file(file_path, coverage_path)
            all_issues.extend(issues)
            
        return all_issues
    
    def report(self) -> None:
        """Report all style and coverage issues found."""
        if not self.issues:
            logger.info("✅ No style or coverage issues found!")
            return
            
        # Group issues by tool
        tool_issues: Dict[str, List[StyleIssue]] = defaultdict(list)
        for issue in self.issues:
            tool_issues[issue.tool].append(issue)
            
        # Report by tool
        for tool, issues in tool_issues.items():
            logger.warning(f"\n{tool.upper()} issues found:")
            for issue in issues:
                severity = "❌" if issue.severity == "error" else "⚠️"
                logger.warning(f"\n{severity} {issue.file}:{issue.line}")
                logger.warning(f"  {issue.message}")
                
        # Summary
        logger.info(f"\nValidation summary:")
        for tool, issues in tool_issues.items():
            errors = len([i for i in issues if i.severity == "error"])
            warnings = len([i for i in issues if i.severity == "warning"])
            logger.info(f"  - {tool}: {errors} errors, {warnings} warnings")
            
    def has_errors(self) -> bool:
        """Check if any validation errors were found."""
        return any(i.severity == "error" for i in self.issues)
        
    def get_coverage_summary(self) -> Dict[str, float]:
        """Get a summary of coverage by file."""
        return self.coverage_data 