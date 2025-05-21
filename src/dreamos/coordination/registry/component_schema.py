"""
Component schema for the Dream.OS component registry.

This module defines the schema and validation rules for components
in the Dream.OS system.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator
import uuid

class ComponentMetadata(BaseModel):
    """Metadata for a component."""
    version: str = Field(..., description="Component version")
    author: str = Field(..., description="Component author")
    description: str = Field(..., description="Component description")
    tags: List[str] = Field(default_factory=list, description="Component tags")
    dependencies: List[str] = Field(default_factory=list, description="Component dependencies")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Component(BaseModel):
    """A Dream.OS component."""
    component_id: str = Field(..., description="Unique component identifier")
    name: str = Field(..., description="Component name")
    type: str = Field(..., description="Component type")
    path: str = Field(..., description="Path to component")
    metadata: ComponentMetadata = Field(..., description="Component metadata")
    status: str = Field(default="active", description="Component status")
    config: Dict[str, Any] = Field(default_factory=dict, description="Component configuration")

    @validator('component_id')
    def validate_component_id(cls, v):
        """Validate component ID format."""
        if not v.startswith('comp_'):
            raise ValueError("Component ID must start with 'comp_'")
        return v

    @validator('type')
    def validate_type(cls, v):
        """Validate component type."""
        valid_types = {'agent', 'service', 'utility', 'plugin', 'module'}
        if v not in valid_types:
            raise ValueError(f"Invalid component type. Must be one of: {valid_types}")
        return v

    @validator('status')
    def validate_status(cls, v):
        """Validate component status."""
        valid_statuses = {'active', 'inactive', 'deprecated', 'testing'}
        if v not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        return v

class ComponentSchema:
    """Schema for component validation."""
    
    @staticmethod
    def validate(component: Dict[str, Any]) -> bool:
        """Validate a component against the schema.
        
        Args:
            component: Component data to validate
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If validation fails
        """
        try:
            Component(**component)
            return True
        except Exception as e:
            raise ValueError(f"Component validation failed: {str(e)}")

    @staticmethod
    def get_schema() -> Dict[str, Any]:
        """Get the JSON schema for components.
        
        Returns:
            JSON schema dictionary
        """
        return json.loads(Component.schema_json())

def create_component(
    name: str,
    version: str,
    description: str,
    type: str,
    owner: str,
    path: str,
    dependencies: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    entry_point: Optional[str] = None,
    config_schema: Optional[Dict[str, Any]] = None,
    documentation: Optional[str] = None
) -> ComponentMetadata:
    """Helper function to create a new component."""
    return ComponentMetadata(
        name=name,
        version=version,
        description=description,
        type=type,
        owner=owner,
        path=path,
        dependencies=dependencies or [],
        tags=tags or [],
        entry_point=entry_point,
        config_schema=config_schema,
        documentation=documentation
    )

# Component types
COMPONENT_TYPES = {
    "AGENT": "agent",
    "SERVICE": "service",
    "UTILITY": "utility",
    "LIBRARY": "library",
    "PLUGIN": "plugin",
    "MODULE": "module"
}

# Component statuses
COMPONENT_STATUS = {
    "ACTIVE": "active",
    "DEPRECATED": "deprecated",
    "MAINTENANCE": "maintenance",
    "EXPERIMENTAL": "experimental",
    "ARCHIVED": "archived"
}

# Health statuses
HEALTH_STATUS = {
    "HEALTHY": "healthy",
    "DEGRADED": "degraded",
    "UNHEALTHY": "unhealthy",
    "UNKNOWN": "unknown"
}

def update_component_status(component: ComponentMetadata, new_status: str) -> ComponentMetadata:
    """Update a component's status."""
    if new_status not in COMPONENT_STATUS.values():
        raise ValueError(f"Invalid status: {new_status}")
    component.status = new_status
    component.updated_at = datetime.utcnow()
    return component

def update_health_status(component: ComponentMetadata, new_status: str) -> ComponentMetadata:
    """Update a component's health status."""
    if new_status not in HEALTH_STATUS.values():
        raise ValueError(f"Invalid health status: {new_status}")
    component.health_status = new_status
    component.updated_at = datetime.utcnow()
    return component

def add_dependency(component: ComponentMetadata, dependency: str) -> ComponentMetadata:
    """Add a dependency to a component."""
    if dependency not in component.dependencies:
        component.dependencies.append(dependency)
        component.updated_at = datetime.utcnow()
    return component

def remove_dependency(component: ComponentMetadata, dependency: str) -> ComponentMetadata:
    """Remove a dependency from a component."""
    if dependency in component.dependencies:
        component.dependencies.remove(dependency)
        component.updated_at = datetime.utcnow()
    return component

def add_tag(component: ComponentMetadata, tag: str) -> ComponentMetadata:
    """Add a tag to a component."""
    if tag not in component.tags:
        component.tags.append(tag)
        component.updated_at = datetime.utcnow()
    return component

def remove_tag(component: ComponentMetadata, tag: str) -> ComponentMetadata:
    """Remove a tag from a component."""
    if tag in component.tags:
        component.tags.remove(tag)
        component.updated_at = datetime.utcnow()
    return component

def update_metrics(component: ComponentMetadata, metrics: Dict[str, Any]) -> ComponentMetadata:
    """Update component metrics."""
    component.metrics = metrics
    component.updated_at = datetime.utcnow()
    return component

def update_test_coverage(component: ComponentMetadata, coverage: float) -> ComponentMetadata:
    """Update component test coverage."""
    if not 0 <= coverage <= 100:
        raise ValueError("Coverage must be between 0 and 100")
    component.test_coverage = coverage
    component.last_tested = datetime.utcnow()
    component.updated_at = datetime.utcnow()
    return component 