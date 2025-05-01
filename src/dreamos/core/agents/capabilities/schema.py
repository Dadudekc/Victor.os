# src/dreamos/core/agents/capabilities/schema.py
# -*- coding: utf-8 -*-
"""Defines the data structures (schema) for representing agent capabilities
in the centralized registry.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

# TODO: Consider standardizing on Pydantic models instead of @dataclass for consistency and validation.

# Type alias for flexibility, could be replaced by a more specific JSON Schema type
JsonSchema = Dict[str, Any]


@dataclass
class CapabilitySchema:
    """Defines the expected input, output, and error data structures for a capability."""

    input_schema: Optional[JsonSchema] = None
    output_schema: Optional[JsonSchema] = None
    error_schema: Optional[JsonSchema] = None
    # Example: Might detail required/optional fields later
    # required_inputs: List[str] = field(default_factory=list)
    # optional_inputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the schema to a dictionary."""
        return {
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "error_schema": self.error_schema,
        }


@dataclass
class CapabilityMetadata:
    """Metadata associated with a capability."""

    version: str = "1.0.0"  # Semantic versioning preferred
    description: Optional[str] = None
    tags: List[str] = field(
        default_factory=list
    )  # e.g., ["code_analysis", "python", "refactoring"]
    maturity: str = (
        "experimental"  # e.g., experimental, alpha, beta, stable, deprecated
    )
    owner_agent_id: Optional[str] = None  # Agent primarily responsible or origin
    dependencies: List[str] = field(
        default_factory=list
    )  # List of capability_ids it depends on

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the metadata to a dictionary."""
        return {
            "version": self.version,
            "description": self.description,
            "tags": self.tags,
            "maturity": self.maturity,
            "owner_agent_id": self.owner_agent_id,
            "dependencies": self.dependencies,
        }


@dataclass
class CapabilityPerformance:
    """Estimated or measured performance characteristics."""

    avg_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None  # 95th percentile latency
    throughput_tasks_per_sec: Optional[float] = None
    cost_units: Optional[float] = (
        None  # Arbitrary units, could be tokens, credits, etc.
    )
    cost_currency: Optional[str] = None  # e.g., "tokens", "credits", "USD"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the performance data to a dictionary."""
        return {
            "avg_latency_ms": self.avg_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "throughput_tasks_per_sec": self.throughput_tasks_per_sec,
            "cost_units": self.cost_units,
            "cost_currency": self.cost_currency,
        }


@dataclass
class CapabilityResourceRequirements:
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

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the resource requirements to a dictionary."""
        return {
            "cpu_cores_avg": self.cpu_cores_avg,
            "cpu_cores_peak": self.cpu_cores_peak,
            "memory_mb_avg": self.memory_mb_avg,
            "memory_mb_peak": self.memory_mb_peak,
            "gpu_required": self.gpu_required,
            "gpu_type": self.gpu_type,
            "network_bandwidth_mbps": self.network_bandwidth_mbps,
            "storage_gb_required": self.storage_gb_required,
        }


@dataclass
class AgentCapability:
    """Represents a single capability offered by an agent, registered in the central registry."""

    agent_id: str  # ID of the agent offering this capability
    capability_id: str  # Unique identifier for this capability across the swarm (e.g., "code.python.format.black")

    # Nested structures for organization
    schema_definition: CapabilitySchema = field(default_factory=CapabilitySchema)
    metadata: CapabilityMetadata = field(default_factory=CapabilityMetadata)
    performance: CapabilityPerformance = field(default_factory=CapabilityPerformance)
    resource_requirements: CapabilityResourceRequirements = field(
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

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the entire capability object to a dictionary."""
        return {
            "agent_id": self.agent_id,
            "capability_id": self.capability_id,
            "schema_definition": self.schema_definition.to_dict(),
            "metadata": self.metadata.to_dict(),
            "performance": self.performance.to_dict(),
            "resource_requirements": self.resource_requirements.to_dict(),
            "is_active": self.is_active,
            "registered_at_utc": self.registered_at_utc,
            "last_updated_utc": self.last_updated_utc,
            "last_verified_utc": self.last_verified_utc,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapability":
        """Deserializes an AgentCapability object from a dictionary."""
        schema_def = CapabilitySchema(**data.get("schema_definition", {}))
        metadata = CapabilityMetadata(**data.get("metadata", {}))
        performance = CapabilityPerformance(**data.get("performance", {}))
        resources = CapabilityResourceRequirements(
            **data.get("resource_requirements", {})
        )

        return cls(
            agent_id=data["agent_id"],
            capability_id=data["capability_id"],
            schema_definition=schema_def,
            metadata=metadata,
            performance=performance,
            resource_requirements=resources,
            is_active=data.get("is_active", True),
            registered_at_utc=data.get("registered_at_utc"),
            last_updated_utc=data.get("last_updated_utc"),
            last_verified_utc=data.get("last_verified_utc"),
        )
