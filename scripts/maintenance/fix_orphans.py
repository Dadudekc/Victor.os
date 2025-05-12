import os
import sys
import logging
from pathlib import Path
import ast
import black
import autopep8
from datetime import datetime
from typing import List, Dict, Set, Tuple
import re

# Setup logging
log_dir = Path("runtime/logs")
log_dir.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=log_dir / "orphan_cleanup.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class OrphanCleaner:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.archive_dir = root_dir / "archive" / "orphans"
        self.deleted_log = log_dir / "deleted_orphans.log"
        self.fixed_files: List[Path] = []
        self.deleted_files: List[Path] = []
        self.failed_files: List[Tuple[Path, str]] = []
        
    def is_python_file(self, path: Path) -> bool:
        """Check if file is a Python file and not in excluded directories"""
        return (
            path.suffix == '.py' and
            'venv' not in str(path) and
            '__pycache__' not in str(path) and
            '.pytest_cache' not in str(path)
        )
    
    def fix_malformed_imports(self, content: str) -> str:
        """Fix malformed imports like 'from . import dreamos.core.events.base_event'"""
        # Fix relative imports with dots
        content = re.sub(
            r'from \. import ([a-zA-Z0-9_.]+)',
            r'from \1 import *',
            content
        )
        
        # Fix direct imports with dots
        content = re.sub(
            r'import \. ([a-zA-Z0-9_.]+)',
            r'import \1',
            content
        )
        
        return content
    
    def check_syntax(self, file_path: Path) -> bool:
        """Check if Python file has valid syntax"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            return True
        except SyntaxError as e:
            logging.error(f"Syntax error in {file_path}: {str(e)}")
            return False
        except Exception as e:
            logging.error(f"Error reading {file_path}: {str(e)}")
            return False
    
    def fix_syntax(self, file_path: Path) -> bool:
        """Attempt to fix syntax errors using black and autopep8"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Fix malformed imports first
            content = self.fix_malformed_imports(content)
            
            # Try black first
            try:
                mode = black.Mode()
                fixed_content = black.format_str(content, mode=mode)
            except:
                # Fall back to autopep8
                fixed_content = autopep8.fix_code(content)
            
            # Verify the fix
            ast.parse(fixed_content)
            
            # Write back if different
            if fixed_content != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                logging.info(f"Fixed syntax in {file_path}")
                return True
                
        except Exception as e:
            logging.error(f"Failed to fix {file_path}: {str(e)}")
            return False
    
    def handle_init_file(self, file_path: Path) -> bool:
        """Handle __init__.py files specially"""
        try:
            # If it's an empty or nearly empty __init__.py, stub it
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if len(content) < 100:  # Arbitrary threshold
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write('"""Archived module. Do not use."""\n')
                logging.info(f"Stubbed {file_path}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error handling {file_path}: {str(e)}")
            return False
    
    def process_file(self, file_path: Path) -> None:
        """Process a single file"""
        if not self.is_python_file(file_path):
            return
            
        if not self.check_syntax(file_path):
            if file_path.name == '__init__.py':
                if self.handle_init_file(file_path):
                    self.fixed_files.append(file_path)
                    return
            
            if self.fix_syntax(file_path):
                self.fixed_files.append(file_path)
            else:
                self.failed_files.append((file_path, "Syntax fix failed"))
    
    def cleanup(self) -> None:
        """Main cleanup process"""
        logging.info("Starting orphan cleanup process")
        
        # Process all Python files in archive/orphans
        for file_path in self.archive_dir.rglob("*.py"):
            self.process_file(file_path)
        
        # Log results
        logging.info(f"Fixed {len(self.fixed_files)} files")
        logging.info(f"Failed to fix {len(self.failed_files)} files")
        
        # Create summary
        summary = [
            "=== Orphan Cleanup Summary ===",
            f"Timestamp: {datetime.now().isoformat()}",
            f"Files fixed: {len(self.fixed_files)}",
            f"Files failed: {len(self.failed_files)}",
            "\nFixed files:",
            *[f"- {f}" for f in self.fixed_files],
            "\nFailed files:",
            *[f"- {f}: {reason}" for f, reason in self.failed_files]
        ]
        
        # Write summary to log
        with open(self.deleted_log, 'w', encoding='utf-8') as f:
            f.write("\n".join(summary))
        
        # Create .DEPRECATED marker
        deprecated_marker = self.archive_dir / ".DEPRECATED_DO_NOT_USE"
        deprecated_marker.touch()
        
        logging.info("Cleanup process completed")

def main():
    root_dir = Path(__file__).resolve().parents[2]
    cleaner = OrphanCleaner(root_dir)
    cleaner.cleanup()
    
    print(f"Cleanup complete. See {cleaner.deleted_log} for details.")

if __name__ == "__main__":
    main() 