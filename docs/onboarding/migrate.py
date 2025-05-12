#!/usr/bin/env python3
"""
Dream.OS Migration System
Safely migrates files and updates imports with validation and rollback support.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .circular_import_detector import CircularImportDetector
from .import_rewriter import ImportRewriter
from .rollback_manifest import RollbackManifestGenerator
from .validators import MigrationValidator
from .style_validator import StyleValidator
from .migration_config import MigrationConfigLoader, MigrationConfigGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationExecutor:
    """Executes file migrations with validation and rollback support."""
    
    def __init__(self, root_dir: Path, dry_run: bool = False,
                 coverage_threshold: float = 80.0,
                 enforce_style: bool = True):
        self.root_dir = root_dir
        self.dry_run = dry_run
        self.coverage_threshold = coverage_threshold
        self.enforce_style = enforce_style
        self.manifest_generator = RollbackManifestGenerator(
            description="Dream.OS file migration"
        )
        self.validator = MigrationValidator(root_dir)
        self.style_validator = StyleValidator(root_dir, coverage_threshold)
        
    def validate_migration(self, source_files: List[Path], target_dir: Path,
                          coverage_path: Optional[Path] = None) -> bool:
        """Validate the migration plan before executing."""
        # Run all validators
        for file_path in source_files:
            # Run migration validators
            issues = self.validator.validate_file(file_path)
            self.validator.issues.extend(issues)
            
            # Run style and coverage validators
            if self.enforce_style:
                style_issues = self.style_validator.validate_file(file_path, coverage_path)
                self.style_validator.issues.extend(style_issues)
            
        # Check for circular imports
        detector = CircularImportDetector(self.root_dir)
        circular_deps = detector.detect()
        
        if circular_deps:
            detector.report()
            if any(dep.severity == "error" for dep in circular_deps):
                logger.error("❌ Migration blocked due to circular dependencies")
                return False
            else:
                logger.warning("⚠️ Migration will proceed with warnings")
        
        # Report validation issues
        self.validator.report()
        if self.validator.has_errors():
            logger.error("❌ Migration blocked due to validation errors")
            return False
            
        # Report style and coverage issues
        if self.enforce_style:
            self.style_validator.report()
            if self.style_validator.has_errors():
                logger.error("❌ Migration blocked due to style errors")
                return False
        
        # Validate target directory
        if not target_dir.exists():
            if self.dry_run:
                logger.info(f"Would create directory: {target_dir}")
            else:
                target_dir.mkdir(parents=True)
                logger.info(f"✅ Created directory: {target_dir}")
        
        # Validate source files
        for file_path in source_files:
            if not file_path.exists():
                logger.error(f"❌ Source file not found: {file_path}")
                return False
        
        return True
    
    def execute_migration(self, source_files: List[Path], target_dir: Path,
                         import_mappings: Optional[Dict[str, str]] = None,
                         coverage_path: Optional[Path] = None):
        """Execute the file migration."""
        if not self.validate_migration(source_files, target_dir, coverage_path):
            return False
            
        success = True
        for source_file in source_files:
            target_file = target_dir / source_file.name
            
            if self.dry_run:
                logger.info(f"Would move {source_file} to {target_file}")
            else:
                try:
                    # Record the move in the manifest
                    self.manifest_generator.add_file_move(
                        source_file, target_file,
                        file_type=source_file.suffix[1:]  # Remove the dot
                    )
                    
                    # Move the file
                    source_file.rename(target_file)
                    logger.info(f"✅ Moved {source_file} to {target_file}")
                    
                    # Update imports if it's a Python file
                    if source_file.suffix == '.py':
                        rewriter = ImportRewriter(self.root_dir)
                        if import_mappings:
                            rewriter.path_mappings = import_mappings
                        rewrites = rewriter.rewrite_imports(target_file)
                        
                        # Record the rewrites in the manifest
                        for rewrite in rewrites:
                            self.manifest_generator.add_import_rewrite(
                                target_file,
                                rewrite.old_path,
                                rewrite.new_path,
                                rewrite.line_number,
                                rewrite.node_type
                            )
                            
                except Exception as e:
                    logger.error(f"Failed to migrate {source_file}: {e}")
                    success = False
        
        if success and not self.dry_run:
            # Save the rollback manifest
            manifest_path = self.root_dir / 'migration_rollback_manifest.json'
            self.manifest_generator.save(manifest_path)
            
        return success

def main():
    parser = argparse.ArgumentParser(description="Dream.OS File Migration Tool")
    parser.add_argument("--source", required=True, help="Source file or directory")
    parser.add_argument("--target", required=True, help="Target directory")
    parser.add_argument("--config", help="Path to migration config YAML")
    parser.add_argument("--tag", help="Execute only mappings with this tag")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without executing")
    parser.add_argument("--coverage", help="Path to coverage.xml file")
    parser.add_argument("--coverage-threshold", type=float, default=80.0,
                       help="Minimum test coverage percentage (default: 80.0)")
    parser.add_argument("--no-style", action="store_true",
                       help="Skip style and coverage validation")
    args = parser.parse_args()
    
    root_dir = Path.cwd()
    source_path = root_dir / args.source
    target_dir = root_dir / args.target
    coverage_path = Path(args.coverage) if args.coverage else None
    
    # Handle config-driven migration
    if args.config:
        config_loader = MigrationConfigLoader(Path(args.config))
        config = config_loader.load()
        
        if args.tag:
            config = config_loader.get_mappings_for_tag(args.tag)
            
        # Convert string paths to Path objects
        source_files = [Path(p) for p in config.file_mappings.keys()]
        import_mappings = config.import_mappings
    else:
        # Get list of files to migrate
        source_files = []
        if source_path.is_file():
            source_files = [source_path]
        elif source_path.is_dir():
            source_files = list(source_path.rglob("*"))
            source_files = [f for f in source_files if f.is_file()]
        else:
            logger.error(f"Source path not found: {source_path}")
            sys.exit(1)
        import_mappings = None
    
    # Execute migration
    executor = MigrationExecutor(
        root_dir,
        args.dry_run,
        args.coverage_threshold,
        not args.no_style
    )
    success = executor.execute_migration(
        source_files,
        target_dir,
        import_mappings,
        coverage_path
    )
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 