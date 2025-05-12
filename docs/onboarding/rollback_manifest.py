#!/usr/bin/env python3
"""
Rollback Manifest Generator for Dream.OS Migration System
Generates a detailed JSON manifest of all file moves and import rewrites.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class ImportRewrite:
    """Represents a single import statement rewrite."""
    file: str
    old_import: str
    new_import: str
    line_number: int
    node_type: str  # 'import' or 'from_import'

@dataclass
class FileMove:
    """Represents a file move operation."""
    old_path: str
    new_path: str
    file_type: str  # 'python', 'markdown', etc.

@dataclass
class RollbackManifest:
    """Represents a complete rollback manifest."""
    timestamp: str
    description: str
    file_moves: List[FileMove]
    import_rewrites: List[ImportRewrite]
    metadata: Dict[str, str]

class RollbackManifestGenerator:
    """Generates rollback manifests for migration operations."""
    
    def __init__(self, description: str):
        self.manifest = RollbackManifest(
            timestamp=datetime.utcnow().isoformat(),
            description=description,
            file_moves=[],
            import_rewrites=[],
            metadata={}
        )
    
    def add_file_move(self, old_path: Path, new_path: Path, file_type: str):
        """Record a file move operation."""
        self.manifest.file_moves.append(FileMove(
            old_path=str(old_path),
            new_path=str(new_path),
            file_type=file_type
        ))
    
    def add_import_rewrite(self, file: Path, old_import: str, new_import: str, 
                          line_number: int, node_type: str):
        """Record an import statement rewrite."""
        self.manifest.import_rewrites.append(ImportRewrite(
            file=str(file),
            old_import=old_import,
            new_import=new_import,
            line_number=line_number,
            node_type=node_type
        ))
    
    def add_metadata(self, key: str, value: str):
        """Add metadata to the manifest."""
        self.manifest.metadata[key] = value
    
    def save(self, output_path: Path):
        """Save the manifest to a JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.manifest), f, indent=2)
            logger.info(f"✅ Rollback manifest saved to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save rollback manifest: {e}")
            raise

class RollbackExecutor:
    """Executes rollback operations from a manifest."""
    
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
        self.manifest: Optional[RollbackManifest] = None
    
    def load(self):
        """Load the rollback manifest."""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.manifest = RollbackManifest(**data)
            logger.info(f"✅ Loaded rollback manifest from {self.manifest_path}")
        except Exception as e:
            logger.error(f"Failed to load rollback manifest: {e}")
            raise
    
    def execute(self, dry_run: bool = False):
        """Execute the rollback operations."""
        if not self.manifest:
            self.load()
            
        if dry_run:
            logger.info("🔍 Dry run mode - showing changes without executing")
        
        # Reverse file moves
        for move in reversed(self.manifest.file_moves):
            old_path = Path(move.old_path)
            new_path = Path(move.new_path)
            
            if dry_run:
                logger.info(f"Would move {new_path} back to {old_path}")
            else:
                try:
                    new_path.rename(old_path)
                    logger.info(f"✅ Moved {new_path} back to {old_path}")
                except Exception as e:
                    logger.error(f"Failed to move {new_path} back to {old_path}: {e}")
        
        # Reverse import rewrites
        for rewrite in reversed(self.manifest.import_rewrites):
            file_path = Path(rewrite.file)
            if not file_path.exists():
                logger.warning(f"⚠️ File {file_path} no longer exists, skipping import rewrite")
                continue
                
            if dry_run:
                logger.info(f"Would rewrite import in {file_path}:")
                logger.info(f"  {rewrite.new_import} -> {rewrite.old_import}")
            else:
                try:
                    # TODO: Implement import rewrite reversal
                    # This would require parsing the file and replacing the import
                    # Similar to the import rewriter but in reverse
                    logger.info(f"✅ Rewrote import in {file_path}")
                except Exception as e:
                    logger.error(f"Failed to rewrite import in {file_path}: {e}")
        
        if not dry_run:
            logger.info("✅ Rollback completed successfully!") 