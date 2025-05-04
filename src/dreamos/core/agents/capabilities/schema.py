# src/dreamos/core/agents/capabilities/schema.py
# -*- coding: utf-8 -*-
"""Defines the data structures (schema) for representing agent capabilities
in the centralized registry.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Type alias for flexibility, could be replaced by a more specific JSON Schema type
JsonSchema = Dict[str, Any]


class CapabilitySchema(BaseModel):
    """Defines the expected input, output, and error data structures for a capability."""  # noqa: E501

    input_schema: Optional[JsonSchema] = None
    output_schema: Optional[JsonSchema] = None
    error_schema: Optional[JsonSchema] = None
    # Example: Might detail required/optional fields later
    # required_inputs: List[str] = Field(default_factory=list)
    # optional_inputs: List[str] = Field(default_factory=list)


class CapabilityMetadata(BaseModel):
    """Metadata associated with a capability."""

    version: str = "1.0.0"  # Semantic versioning preferred
    description: Optional[str] = None
    tags: List[str] = Field(
        default_factory=list
    )  # e.g., ["code_analysis", "python", "refactoring"]
    maturity: str = (
        "experimental"  # e.g., experimental, alpha, beta, stable, deprecated
    )
    owner_agent_id: Optional[str] = None  # Agent primarily responsible or origin
    dependencies: List[str] = Field(
        default_factory=list
    )  # List of capability_ids it depends on


class CapabilityPerformance(BaseModel):
    """Estimated or measured performance characteristics."""

    avg_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None  # 95th percentile latency
    throughput_tasks_per_sec: Optional[float] = None
    cost_units: Optional[float] = (
        None  # Arbitrary units, could be tokens, credits, etc.
    )
    cost_currency: Optional[str] = None  # e.g., "tokens", "credits", "USD"


class CapabilityResourceRequirements(BaseModel):
    """Estimated resource needs for executing the capability."""

    cpu_cores_avg: Optional[float] = None
    cpu_cores_peak: Optional[float] = None
    memory_mb_avg: Optional[int] = None
    memory_mb_peak: Optional[int] = None
    gpu_required: bool = False
    gpu_type: Optional[str] = None  # e.g., "nvidia_a100", "any"
    network_bandwidth_mbps: Optional[float] = None
    storage_gb_required: Optional[float] = (
        None  # Temporary storage needed during execution
    )


class AgentCapability(BaseModel):
    """Represents a single capability offered by an agent, registered in the central registry."""  # noqa: E501

    agent_id: str  # ID of the agent offering this capability
    capability_id: str  # Unique identifier for this capability across the swarm (e.g., "code.python.format.black")  # noqa: E501

    # Nested structures for organization
    schema_definition: CapabilitySchema = Field(default_factory=CapabilitySchema)
    metadata: CapabilityMetadata = Field(default_factory=CapabilityMetadata)
    performance: CapabilityPerformance = Field(default_factory=CapabilityPerformance)
    resource_requirements: CapabilityResourceRequirements = Field(
        default_factory=CapabilityResourceRequirements
    )

    # Status and Timestamps
    is_active: bool = (
        True  # Allows temporarily disabling a capability without unregistering
    )
    registered_at_utc: Optional[str] = None  # ISO Format timestamp
    last_updated_utc: Optional[str] = None  # ISO Format timestamp
    last_verified_utc: Optional[str] = (
        None  # Timestamp of last successful health check/verification
    )
