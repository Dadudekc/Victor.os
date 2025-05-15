#!/usr/bin/env python3
"""
Repository Integrity Checker

Validates the integrity of the Dream.OS repository structure and critical files.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class RepoIntegrityChecker:
    """Checks repository integrity and generates reports."""
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def check_critical_directories(self) -> bool:
        """Check that all critical directories exist."""
        critical_dirs = [
            "src/dreamos/core",
            "src/dreamos/utils",
            "src/dreamos/tools",
            "runtime/config",
            "runtime/agent_comms/agent_mailboxes",
            "tests"
        ]
        
        missing = []
        for dir_path in critical_dirs:
            full_path = self.repo_root / dir_path
            if not full_path.exists():
                missing.append(dir_path)
                self.errors.append(f"Missing critical directory: {dir_path}")
                
        return len(missing) == 0
        
    def check_agent_directories(self) -> bool:
        """Check agent mailbox directories."""
        mailboxes_dir = self.repo_root / "runtime/agent_comms/agent_mailboxes"
        if not mailboxes_dir.exists():
            self.errors.append("Agent mailboxes directory missing")
            return False
            
        valid = True
        for agent_dir in mailboxes_dir.glob("Agent-*"):
            if not all((
                (agent_dir / "inbox").exists(),
                (agent_dir / "outbox").exists(),
                (agent_dir / "processed").exists(),
                (agent_dir / "state").exists(),
                (agent_dir / "workspace").exists()
            )):
                self.errors.append(f"Incomplete directory structure for {agent_dir.name}")
                valid = False
                
        return valid
        
    def check_coordinate_files(self) -> bool:
        """Check agent coordinate files exist and are valid."""
        coords_file = self.repo_root / "runtime/config/cursor_agent_coords.json"
        copy_coords_file = self.repo_root / "runtime/config/cursor_agent_copy_coords.json"
        
        if not coords_file.exists():
            self.errors.append("Missing cursor_agent_coords.json")
            return False
            
        if not copy_coords_file.exists():
            self.errors.append("Missing cursor_agent_copy_coords.json")
            return False
            
        try:
            with coords_file.open() as f:
                coords = json.load(f)
                if not isinstance(coords, dict):
                    self.errors.append("Invalid cursor_agent_coords.json format")
                    return False
        except Exception as e:
            self.errors.append(f"Error reading cursor_agent_coords.json: {e}")
            return False
            
        try:
            with copy_coords_file.open() as f:
                copy_coords = json.load(f)
                if not isinstance(copy_coords, dict):
                    self.errors.append("Invalid cursor_agent_copy_coords.json format")
                    return False
        except Exception as e:
            self.errors.append(f"Error reading cursor_agent_copy_coords.json: {e}")
            return False
            
        return True
        
    def check_test_suite(self) -> bool:
        """Check test suite integrity."""
        tests_dir = self.repo_root / "tests"
        if not tests_dir.exists():
            self.errors.append("Missing tests directory")
            return False
            
        if not (tests_dir / "__init__.py").exists():
            self.warnings.append("Missing tests/__init__.py")
            
        # Check for critical test files
        critical_tests = [
            "core/test_devlog_formatter.py",
            "core/test_agent_identity.py",
            "test_empathy_intelligence.py"
        ]
        
        missing = []
        for test_file in critical_tests:
            if not (tests_dir / test_file).exists():
                missing.append(test_file)
                
        if missing:
            self.errors.append(f"Missing critical test files: {', '.join(missing)}")
            return False
            
        return True
        
    def check_utils_integrity(self) -> bool:
        """Check core utilities are present."""
        utils_dir = self.repo_root / "src/dreamos/core/utils"
        required_utils = [
            "class_utils.py",
            "config_utils.py",
            "dict_utils.py",
            "error_utils.py",
            "file_utils.py",
            "function_utils.py",
            "json_utils.py",
            "list_utils.py",
            "logging_utils.py",
            "path_utils.py",
            "string_utils.py",
            "time_utils.py",
            "validation.py"
        ]
        
        missing = []
        for util in required_utils:
            if not (utils_dir / util).exists():
                missing.append(util)
                
        if missing:
            self.errors.append(f"Missing core utilities: {', '.join(missing)}")
            return False
            
        return True
        
    def run_all_checks(self) -> bool:
        """Run all integrity checks."""
        checks = [
            self.check_critical_directories(),
            self.check_agent_directories(),
            self.check_coordinate_files(),
            self.check_test_suite(),
            self.check_utils_integrity()
        ]
        
        passed = all(checks)
        
        if self.warnings:
            logger.warning("Warnings found:")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")
                
        if self.errors:
            logger.error("Errors found:")
            for error in self.errors:
                logger.error(f"  - {error}")
                
        return passed

def main():
    """Main entry point."""
    repo_root = Path(__file__).resolve().parents[1]
    checker = RepoIntegrityChecker(repo_root)
    
    passed = checker.run_all_checks()
    
    if passed:
        logger.info("✅ All integrity checks passed")
        sys.exit(0)
    else:
        logger.error("❌ One or more integrity checks failed")
        sys.exit(1)

if __name__ == "__main__":
    main() 