#!/usr/bin/env python3
"""
Dream.OS Import Path Rewriter
Safely rewrites import statements using AST parsing and validation.
"""

import ast
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ImportRewrite:
    """Represents a single import statement rewrite."""
    old_path: str
    new_path: str
    line_number: int
    node_type: str  # 'import' or 'from_import'

class ImportRewriter(ast.NodeTransformer):
    """AST-based import statement rewriter."""
    
    def __init__(self, path_mappings: Dict[str, str]):
        self.path_mappings = path_mappings
        self.rewrites: List[ImportRewrite] = []
        
    def visit_Import(self, node: ast.Import) -> ast.Import:
        """Handle 'import x.y.z' statements."""
        for name in node.names:
            old_path = name.name
            if old_path in self.path_mappings:
                new_path = self.path_mappings[old_path]
                name.name = new_path
                self.rewrites.append(ImportRewrite(
                    old_path=old_path,
                    new_path=new_path,
                    line_number=node.lineno,
                    node_type='import'
                ))
        return node
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        """Handle 'from x.y.z import a' statements."""
        if node.module in self.path_mappings:
            old_path = node.module
            new_path = self.path_mappings[old_path]
            node.module = new_path
            self.rewrites.append(ImportRewrite(
                old_path=old_path,
                new_path=new_path,
                line_number=node.lineno,
                node_type='from_import'
            ))
        return node

    def rewrite_imports(self, file_path: Path) -> List[ImportRewrite]:
        """
        Rewrite import statements in a Python file using AST.
        
        Args:
            file_path: Path to the Python file
        
        Returns:
            List of rewrites performed
        """
        try:
            # Read the file
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            # Rewrite imports
            new_tree = self.visit(tree)
            
            # Validate the new AST
            ast.fix_missing_locations(new_tree)
            
            # Generate new content
            new_content = ast.unparse(new_tree)
            
            # Write back to file
            with open(file_path, 'w') as f:
                f.write(new_content)
            
            # Validate the changes
            validator = ImportValidator(file_path)
            flake8_ok, flake8_output = validator.run_flake8()
            mypy_ok, mypy_output = validator.run_mypy()
            
            if not (flake8_ok and mypy_ok):
                logger.warning(f"Import validation failed for {file_path}")
                logger.warning(f"flake8 output: {flake8_output}")
                logger.warning(f"mypy output: {mypy_output}")
                return []
            
            return self.rewrites
            
        except Exception as e:
            logger.error(f"Failed to rewrite imports in {file_path}: {e}")
            return []

class ImportValidator:
    """Validates Python imports using flake8 and mypy."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.flake8_config = Path('.flake8')
        self.mypy_config = Path('mypy.ini')
    
    def run_flake8(self) -> Tuple[bool, str]:
        """Run flake8 on the file."""
        try:
            cmd = ['flake8', str(self.file_path)]
            if self.flake8_config.exists():
                cmd.extend(['--config', str(self.flake8_config)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0, result.stdout
        except Exception as e:
            logger.error(f"flake8 validation failed: {e}")
            return False, str(e)
    
    def run_mypy(self) -> Tuple[bool, str]:
        """Run mypy on the file."""
        try:
            cmd = ['mypy', str(self.file_path)]
            if self.mypy_config.exists():
                cmd.extend(['--config-file', str(self.mypy_config)])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0, result.stdout
        except Exception as e:
            logger.error(f"mypy validation failed: {e}")
            return False, str(e)

def get_standard_mappings() -> Dict[str, str]:
    """Get standard import path mappings for Dream.OS."""
    return {
        'src.dreamos.agents.utils.onboarding_utils': 'docs.onboarding.core.onboarding_utils',
        'src.dreamos.core.utils.onboarding_utils': 'docs.onboarding.core.onboarding_utils',
        'src.dreamos.agents.task_feedback_router': 'docs.onboarding.training.task_feedback_router',
        'src.dreamos.agents.agent9_response_injector': 'docs.onboarding.training.agent9_response_injector',
        'src.dreamos.agents.context_router_agent': 'docs.onboarding.training.context_router_agent',
    }

if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description="Rewrite Python import statements using AST")
    parser.add_argument("file", help="Python file to process")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing")
    args = parser.parse_args()
    
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File {file_path} does not exist")
        sys.exit(1)
    
    rewriter = ImportRewriter(get_standard_mappings())
    rewrites = rewriter.rewrite_imports(file_path)
    
    if args.dry_run:
        print("Would perform the following rewrites:")
        for rewrite in rewrites:
            print(f"  Line {rewrite.line_number}: {rewrite.old_path} -> {rewrite.new_path}")
    else:
        if rewrites:
            print(f"Successfully rewrote imports in {file_path}")
            for rewrite in rewrites:
                print(f"  Line {rewrite.line_number}: {rewrite.old_path} -> {rewrite.new_path}")
        else:
            print(f"Failed to rewrite imports in {file_path}")
            sys.exit(1) 