"""
Product output schema for Dream.OS.

This module defines the JSON schema for validating product outputs,
ensuring they meet quality standards and contain all required metadata.
"""

from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime

class ProductOutputMetadata(BaseModel):
    """Metadata for a product output."""
    created_at: datetime = Field(..., description="Timestamp when the output was created")
    created_by: str = Field(..., description="ID of the agent that created the output")
    version: str = Field(..., description="Version of the output format")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Quality score of the output")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the output")
    dependencies: List[str] = Field(default_factory=list, description="Dependencies required for the output")
    metrics: Dict[str, float] = Field(default_factory=dict, description="Performance metrics for the output")

class CodeOutput(BaseModel):
    """Code-based product output."""
    type: str = Field("code", const=True)
    content: str = Field(..., description="The actual code content")
    language: str = Field(..., description="Programming language of the code")
    metadata: ProductOutputMetadata

class DocumentationOutput(BaseModel):
    """Documentation-based product output."""
    type: str = Field("documentation", const=True)
    content: str = Field(..., description="The documentation content")
    format: str = Field(..., description="Format of the documentation (e.g., markdown, rst)")
    metadata: ProductOutputMetadata

class DataOutput(BaseModel):
    """Data-based product output."""
    type: str = Field("data", const=True)
    content: Dict[str, any] = Field(..., description="The data content")
    format: str = Field(..., description="Format of the data (e.g., json, yaml)")
    metadata: ProductOutputMetadata

class ProductOutput(BaseModel):
    """Base model for all product outputs."""
    output_id: str = Field(..., description="Unique identifier for the output")
    task_id: str = Field(..., description="ID of the task that generated this output")
    output_type: str = Field(..., description="Type of output (code, documentation, data)")
    content: Union[CodeOutput, DocumentationOutput, DataOutput]
    metadata: ProductOutputMetadata
    validation_status: str = Field(..., description="Status of output validation")
    validation_errors: List[str] = Field(default_factory=list, description="Any validation errors found")

# JSON Schema for validation
PRODUCT_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["output_id", "task_id", "output_type", "content", "metadata", "validation_status"],
    "properties": {
        "output_id": {"type": "string"},
        "task_id": {"type": "string"},
        "output_type": {"type": "string", "enum": ["code", "documentation", "data"]},
        "content": {
            "oneOf": [
                {"$ref": "#/definitions/code_output"},
                {"$ref": "#/definitions/documentation_output"},
                {"$ref": "#/definitions/data_output"}
            ]
        },
        "metadata": {"$ref": "#/definitions/metadata"},
        "validation_status": {"type": "string", "enum": ["valid", "invalid", "pending"]},
        "validation_errors": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "definitions": {
        "metadata": {
            "type": "object",
            "required": ["created_at", "created_by", "version", "quality_score"],
            "properties": {
                "created_at": {"type": "string", "format": "date-time"},
                "created_by": {"type": "string"},
                "version": {"type": "string"},
                "quality_score": {"type": "number", "minimum": 0, "maximum": 1},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "dependencies": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "metrics": {
                    "type": "object",
                    "additionalProperties": {"type": "number"}
                }
            }
        },
        "code_output": {
            "type": "object",
            "required": ["type", "content", "language", "metadata"],
            "properties": {
                "type": {"type": "string", "enum": ["code"]},
                "content": {"type": "string"},
                "language": {"type": "string"},
                "metadata": {"$ref": "#/definitions/metadata"}
            }
        },
        "documentation_output": {
            "type": "object",
            "required": ["type", "content", "format", "metadata"],
            "properties": {
                "type": {"type": "string", "enum": ["documentation"]},
                "content": {"type": "string"},
                "format": {"type": "string"},
                "metadata": {"$ref": "#/definitions/metadata"}
            }
        },
        "data_output": {
            "type": "object",
            "required": ["type", "content", "format", "metadata"],
            "properties": {
                "type": {"type": "string", "enum": ["data"]},
                "content": {"type": "object"},
                "format": {"type": "string"},
                "metadata": {"$ref": "#/definitions/metadata"}
            }
        }
    }
} 