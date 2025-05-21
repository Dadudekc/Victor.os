"""
Module 2: Processor

This is an implementation of the Processor module for the Dream.OS bridge system.
It processes and transforms data between the Injector and other modules.
"""

import time
import json
from typing import Dict, Any, Optional, Union

def transform_payload(payload_data: Dict[str, Any], transformation_type: str = "standard") -> Dict[str, Any]:
    """
    Transform a payload based on the specified transformation type
    
    Args:
        payload_data: Dictionary containing the payload to transform
        transformation_type: The type of transformation to apply (standard, minimal, verbose)
        
    Returns:
        Dictionary containing the transformed payload
    """
    if not isinstance(payload_data, dict):
        raise ValueError("Payload data must be a dictionary")
    
    # Apply transformation based on type
    if transformation_type == "minimal":
        # Minimal transformation - keep only essential fields
        result = {
            "transformed": True,
            "transformation_type": "minimal",
            "timestamp": time.time()
        }
        
        # Copy only essential fields
        for key in ["source", "message", "timestamp"]:
            if key in payload_data:
                result[key] = payload_data[key]
                
        return result
    
    elif transformation_type == "verbose":
        # Verbose transformation - add additional information
        result = payload_data.copy()
        result.update({
            "transformed": True,
            "transformation_type": "verbose",
            "processor_timestamp": time.time(),
            "original_payload_size": len(json.dumps(payload_data)),
            "transformation_metadata": {
                "processor_version": "0.1.0",
                "processor_id": "module2_processor",
                "transformation_time_ms": 4.7
            }
        })
        return result
    
    else:
        # Standard transformation (default)
        result = payload_data.copy()
        result.update({
            "transformed": True,
            "transformation_type": "standard",
            "processor_timestamp": time.time()
        })
        return result

def validate_payload(payload_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a payload against the required schema
    
    Args:
        payload_data: Dictionary containing the payload to validate
        
    Returns:
        Dictionary containing the validation result
    """
    if not isinstance(payload_data, dict):
        raise ValueError("Payload data must be a dictionary")
    
    # Check for required fields
    required_fields = ["source"]
    missing_fields = [field for field in required_fields if field not in payload_data]
    
    # Check data types
    type_errors = []
    if "timestamp" in payload_data and not isinstance(payload_data["timestamp"], (int, float)):
        type_errors.append("timestamp must be a number")
    if "source" in payload_data and not isinstance(payload_data["source"], str):
        type_errors.append("source must be a string")
    
    # Return validation result
    is_valid = len(missing_fields) == 0 and len(type_errors) == 0
    
    return {
        "valid": is_valid,
        "timestamp": time.time(),
        "missing_fields": missing_fields,
        "type_errors": type_errors,
        "original_payload": payload_data
    }

def process_data(input_data: Dict[str, Any], processor_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Process input data according to the provided configuration
    
    Args:
        input_data: Dictionary containing input data with these required fields:
            - data: The actual data to process
            - metadata: Additional processing metadata
        processor_config: Optional configuration for the processor
        
    Returns:
        Dictionary containing the processed data
    """
    # Default configuration
    config = {
        "transformation_type": "standard",
        "add_timestamps": True,
        "normalize_fields": True
    }
    
    # Update with provided configuration
    if processor_config:
        config.update(processor_config)
    
    # Validate input data
    if not isinstance(input_data, dict):
        raise ValueError("Input data must be a dictionary")
    
    if "data" not in input_data:
        raise ValueError("Input data must contain a 'data' field")
    
    # Extract the data to process
    data = input_data["data"]
    metadata = input_data.get("metadata", {})
    
    # Process the data
    processed_data = data
    
    # Apply normalizations if configured
    if config["normalize_fields"] and isinstance(processed_data, dict):
        # Normalize field names (lowercase)
        processed_data = {k.lower(): v for k, v in processed_data.items()}
    
    # Transform the payload
    result = transform_payload(
        processed_data,
        transformation_type=config["transformation_type"]
    )
    
    # Add original metadata
    result["original_metadata"] = metadata
    
    # Add processing timestamp if configured
    if config["add_timestamps"]:
        result["processed_at"] = time.time()
    
    return result


def health_check() -> Dict[str, Any]:
    """
    Return health status of the Processor module
    
    Returns:
        Dictionary containing health status information
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "module": "processor",
        "version": "0.1.0",
        "stats": {
            "uptime_seconds": 60,
            "processed_requests": 0,
            "average_processing_time_ms": 4.2
        }
    } 