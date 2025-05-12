#!/usr/bin/env python3
"""
Migration Configuration Handler for Dream.OS
Supports config-driven file and import mappings.
"""

import yaml
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

@dataclass
class MigrationMapping:
    """Represents a single file or import mapping."""
    source: str
    target: str
    description: Optional[str] = None
    tags: List[str] = None

@dataclass
class MigrationConfig:
    """Represents a complete migration configuration."""
    file_mappings: Dict[str, str]  # source -> target paths
    import_mappings: Dict[str, str]  # old -> new import paths
    tags: Set[str]
    description: str

class MigrationConfigLoader:
    """Loads and validates migration configurations."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config: Optional[MigrationConfig] = None
        
    def _validate_mappings(self, mappings: Dict[str, str]) -> bool:
        """Validate that mappings are well-formed."""
        for source, target in mappings.items():
            # Check for duplicate targets
            if list(mappings.values()).count(target) > 1:
                logger.error(f"Duplicate target path: {target}")
                return False
                
            # Check for self-mappings
            if source == target:
                logger.error(f"Self-mapping detected: {source}")
                return False
                
            # Check for invalid paths
            try:
                Path(source)
                Path(target)
            except Exception as e:
                logger.error(f"Invalid path in mapping: {e}")
                return False
                
        return True
        
    def load(self) -> MigrationConfig:
        """Load and validate the migration configuration."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                
            # Extract mappings
            file_mappings = data.get('file_mappings', {})
            import_mappings = data.get('import_mappings', {})
            tags = set(data.get('tags', []))
            description = data.get('description', '')
            
            # Validate mappings
            if not self._validate_mappings(file_mappings):
                raise ValueError("Invalid file mappings")
            if not self._validate_mappings(import_mappings):
                raise ValueError("Invalid import mappings")
                
            self.config = MigrationConfig(
                file_mappings=file_mappings,
                import_mappings=import_mappings,
                tags=tags,
                description=description
            )
            
            logger.info(f"✅ Loaded migration config from {self.config_path}")
            return self.config
            
        except Exception as e:
            logger.error(f"Failed to load migration config: {e}")
            raise
            
    def get_mappings_for_tag(self, tag: str) -> MigrationConfig:
        """Get a subset of mappings for a specific tag."""
        if not self.config:
            self.load()
            
        # Filter mappings by tag
        tagged_mappings = {}
        for source, target in self.config.file_mappings.items():
            if tag in self.config.tags:
                tagged_mappings[source] = target
                
        return MigrationConfig(
            file_mappings=tagged_mappings,
            import_mappings=self.config.import_mappings,
            tags={tag},
            description=f"Tagged migration: {tag}"
        )

class MigrationConfigGenerator:
    """Generates migration configurations from existing codebase."""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        
    def generate_from_directory(self, source_dir: Path, target_dir: Path,
                              description: str = "") -> MigrationConfig:
        """Generate mappings from a source directory to a target directory."""
        file_mappings = {}
        import_mappings = {}
        
        # Generate file mappings
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_dir)
                target_path = target_dir / relative_path
                file_mappings[str(file_path)] = str(target_path)
                
                # For Python files, also generate import mappings
                if file_path.suffix == '.py':
                    module_name = str(relative_path).replace("/", ".").replace("\\", ".")[:-3]
                    target_module = str(target_path.relative_to(self.root_dir)).replace("/", ".").replace("\\", ".")[:-3]
                    import_mappings[module_name] = target_module
                    
        return MigrationConfig(
            file_mappings=file_mappings,
            import_mappings=import_mappings,
            tags=set(),
            description=description
        )
        
    def save(self, config: MigrationConfig, output_path: Path):
        """Save a migration configuration to YAML."""
        try:
            data = {
                'file_mappings': config.file_mappings,
                'import_mappings': config.import_mappings,
                'tags': list(config.tags),
                'description': config.description
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False)
                
            logger.info(f"✅ Saved migration config to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save migration config: {e}")
            raise 