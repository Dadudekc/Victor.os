#!/usr/bin/env python3
"""
Migration Validation Script
Validates the onboarding documentation migration to ensure all files are in place
and references are correct.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set


class MigrationValidator:
    def __init__(self, root_dir: str = "runtime/onboarding"):
        self.root_dir = Path(root_dir)
        self.expected_files = {
            'core': {
                'onboarding_standards.md',
                'agent_onboarding_protocol.md',
                'validation_guide.md'
            },
            'protocols': {
                'devlog_standard.md',
                'continuous_autonomy.md',
                'agent_training.md'
            },
            'training': {
                'quickstart.md',
                'autonomous_operation.md'
            },
            'utils': {
                'onboarding_utils.py',
                'protocol_compliance.py',
                'validation_utils.py',
                'validate_migration.py'
            },
            'guides': {
                'onboarding_guide.md',
                'developer_guide.md'
            }
        }
        self.broken_refs: List[str] = []
        self.missing_files: List[str] = []
        self.import_errors: List[str] = []

    def validate_structure(self) -> bool:
        """Validate the directory structure and file presence."""
        all_valid = True
        for dir_name, expected_files in self.expected_files.items():
            dir_path = self.root_dir / dir_name
            if not dir_path.exists():
                print(f"❌ Missing directory: {dir_name}")
                all_valid = False
                continue

            for file_name in expected_files:
                file_path = dir_path / file_name
                if not file_path.exists():
                    print(f"❌ Missing file: {dir_name}/{file_name}")
                    self.missing_files.append(str(file_path))
                    all_valid = False

        return all_valid

    def validate_markdown_refs(self) -> bool:
        """Validate Markdown file references."""
        all_valid = True
        md_files = list(self.root_dir.rglob("*.md"))
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Check for old path references
                old_paths = re.findall(r'\]\(\.\./\.\./.*?\)', content)
                if old_paths:
                    print(f"❌ Old path references in {md_file}:")
                    for path in old_paths:
                        print(f"  - {path}")
                    self.broken_refs.extend(old_paths)
                    all_valid = False
            except Exception as e:
                print(f"❌ Error reading {md_file}: {e}")
                all_valid = False

        return all_valid

    def validate_python_imports(self) -> bool:
        """Validate Python file imports."""
        all_valid = True
        py_files = list(self.root_dir.rglob("*.py"))
        
        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for old import paths
                old_imports = re.findall(r'from\s+docs\..*?import|import\s+docs\..*?', content)
                if old_imports:
                    print(f"❌ Old import paths in {py_file}:")
                    for imp in old_imports:
                        print(f"  - {imp}")
                    self.import_errors.extend(old_imports)
                    all_valid = False
            except Exception as e:
                print(f"❌ Error reading {py_file}: {e}")
                all_valid = False

        return all_valid

    def run_validation(self) -> bool:
        """Run all validation checks."""
        print("\n🔍 Starting migration validation...\n")
        
        structure_valid = self.validate_structure()
        refs_valid = self.validate_markdown_refs()
        imports_valid = self.validate_python_imports()
        
        print("\n📊 Validation Summary:")
        print(f"✅ Directory Structure: {'Valid' if structure_valid else 'Invalid'}")
        print(f"✅ Markdown References: {'Valid' if refs_valid else 'Invalid'}")
        print(f"✅ Python Imports: {'Valid' if imports_valid else 'Invalid'}")
        
        if self.missing_files:
            print("\n❌ Missing Files:")
            for file in self.missing_files:
                print(f"  - {file}")
                
        if self.broken_refs:
            print("\n❌ Broken References:")
            for ref in self.broken_refs:
                print(f"  - {ref}")
                
        if self.import_errors:
            print("\n❌ Import Errors:")
            for imp in self.import_errors:
                print(f"  - {imp}")
        
        return all([structure_valid, refs_valid, imports_valid])

def main():
    validator = MigrationValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 