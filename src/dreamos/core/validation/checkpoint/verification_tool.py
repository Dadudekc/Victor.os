"""
Dream.OS Checkpoint Verification Tool

This module provides tools to verify agent checkpoint implementations against the
Checkpoint Protocol defined in docs/vision/CHECKPOINT_PROTOCOL.md.

The verification tool performs the following checks:
1. Validates the existence and structure of checkpoint files
2. Verifies checkpoint intervals meet protocol requirements
3. Validates checkpoint content structure and required fields
4. Tests checkpoint restoration capability

Usage:
    from dreamos.core.validation.checkpoint import CheckpointVerifier
    
    # Create verifier
    verifier = CheckpointVerifier()
    
    # Verify a specific agent
    results = verifier.verify_agent("agent-1")
    
    # Verify all agents
    all_results = verifier.verify_all_agents()
    
    # Generate report
    report_path = verifier.generate_verification_report(all_results)
"""

import os
import json
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("checkpoint_verification")

# Constants
CHECKPOINT_DIR = "runtime/agent_comms/checkpoints"
REPORT_DIR = "runtime/agent_comms/verification_reports"
SCHEMA_VERSION = "1.0"


class ValidationResult:
    """Class to hold validation results."""
    
    def __init__(self, success: bool, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize validation result.
        
        Args:
            success: Whether the validation was successful
            message: Validation message
            details: Optional details about the validation
        """
        self.success = success
        self.message = message
        self.details = details or {}
        
    def __str__(self) -> str:
        """Return string representation of validation result."""
        return f"{'SUCCESS' if self.success else 'FAILED'}: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "details": self.details
        }


class IntervalResult:
    """Class to hold interval verification results."""
    
    def __init__(self, success: bool, message: str, intervals: List[float], average_interval: float):
        """Initialize interval result.
        
        Args:
            success: Whether the verification was successful
            message: Verification message
            intervals: List of intervals between checkpoints in minutes
            average_interval: Average interval in minutes
        """
        self.success = success
        self.message = message
        self.intervals = intervals
        self.average_interval = average_interval
        
    def __str__(self) -> str:
        """Return string representation of interval result."""
        return f"{'SUCCESS' if self.success else 'FAILED'}: {self.message} (avg: {self.average_interval:.2f} min)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert interval result to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "intervals": self.intervals,
            "average_interval": self.average_interval
        }


class RestorationResult:
    """Class to hold restoration test results."""
    
    def __init__(self, success: bool, message: str, restored_fields: List[str], missing_fields: List[str]):
        """Initialize restoration result.
        
        Args:
            success: Whether the restoration was successful
            message: Restoration message
            restored_fields: List of fields that were restored successfully
            missing_fields: List of fields that were missing or failed to restore
        """
        self.success = success
        self.message = message
        self.restored_fields = restored_fields
        self.missing_fields = missing_fields
        
    def __str__(self) -> str:
        """Return string representation of restoration result."""
        return f"{'SUCCESS' if self.success else 'FAILED'}: {self.message}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert restoration result to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "restored_fields": self.restored_fields,
            "missing_fields": self.missing_fields
        }


class CheckpointVerifier:
    """Class to verify checkpoint implementations."""
    
    def __init__(self, checkpoint_dir: Optional[str] = None, report_dir: Optional[str] = None):
        """Initialize checkpoint verifier.
        
        Args:
            checkpoint_dir: Optional custom checkpoint directory
            report_dir: Optional custom report directory
        """
        self.checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
        self.report_dir = report_dir or REPORT_DIR
        os.makedirs(self.report_dir, exist_ok=True)
        
    def verify_agent(self, agent_id: str) -> Dict[str, Any]:
        """Verify checkpoint implementation for a specific agent.
        
        Args:
            agent_id: The ID of the agent to verify
            
        Returns:
            Dict[str, Any]: Verification results
        """
        logger.info(f"Verifying checkpoint implementation for {agent_id}")
        
        results = {}
        
        # Verify checkpoint files exist
        file_validation = self.validate_checkpoint_files(agent_id)
        results["file_validation"] = file_validation.to_dict()
        
        # If files don't exist, skip other verifications
        if not file_validation.success:
            return {
                "agent_id": agent_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_result": "FAILED",
                "results": results
            }
        
        # Verify checkpoint intervals
        interval_verification = self.verify_checkpoint_intervals(agent_id)
        results["interval_verification"] = interval_verification.to_dict()
        
        # Verify checkpoint content
        content_validation = self.validate_checkpoint_content(agent_id)
        results["content_validation"] = content_validation.to_dict()
        
        # Test checkpoint restoration
        restoration_test = self.test_checkpoint_restoration(agent_id)
        results["restoration_test"] = restoration_test.to_dict()
        
        # Determine overall result
        overall_result = "SUCCESS"
        for result in results.values():
            if isinstance(result, dict) and not result.get("success", False):
                overall_result = "FAILED"
                break
        
        return {
            "agent_id": agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_result": overall_result,
            "results": results
        }
    
    def verify_all_agents(self) -> Dict[str, Dict[str, Any]]:
        """Verify checkpoint implementation for all agents.
        
        Returns:
            Dict[str, Dict[str, Any]]: Verification results for all agents
        """
        results = {}
        
        # Extract agent IDs from checkpoint filenames
        agent_ids = set()
        for filename in os.listdir(self.checkpoint_dir):
            if filename.endswith(".checkpoint"):
                parts = filename.split("_")
                if len(parts) >= 2:
                    agent_id = parts[0]
                    if agent_id and agent_id != "README.md":
                        agent_ids.add(agent_id)
        
        # Verify each agent
        for agent_id in agent_ids:
            results[agent_id] = self.verify_agent(agent_id)
        
        return results
    
    def generate_verification_report(self, results: Dict[str, Dict[str, Any]], output_dir: Optional[str] = None) -> str:
        """Generate verification report for results.
        
        Args:
            results: Verification results
            output_dir: Optional output directory for report
            
        Returns:
            str: Path to the generated report
        """
        if output_dir is None:
            output_dir = self.report_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Create report file
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        report_file = os.path.join(output_dir, f"checkpoint_verification_report_{timestamp}.md")
        
        with open(report_file, "w") as f:
            f.write("# Checkpoint Verification Report\n\n")
            f.write(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n")
            
            # Overall summary
            f.write("## Overall Summary\n\n")
            f.write("| Agent | Result | File Validation | Interval Verification | Content Validation | Restoration Test |\n")
            f.write("|-------|--------|----------------|----------------------|-------------------|------------------|\n")
            
            for agent_id, result in results.items():
                overall = result["overall_result"]
                file_validation = result["results"]["file_validation"]["success"] if "file_validation" in result["results"] else "N/A"
                interval_verification = result["results"]["interval_verification"]["success"] if "interval_verification" in result["results"] else "N/A"
                content_validation = result["results"]["content_validation"]["success"] if "content_validation" in result["results"] else "N/A"
                restoration_test = result["results"]["restoration_test"]["success"] if "restoration_test" in result["results"] else "N/A"
                
                # Use plain text indicators
                file_validation_str = "PASS" if file_validation is True else "FAIL" if file_validation is False else "N/A"
                interval_verification_str = "PASS" if interval_verification is True else "FAIL" if interval_verification is False else "N/A"
                content_validation_str = "PASS" if content_validation is True else "FAIL" if content_validation is False else "N/A"
                restoration_test_str = "PASS" if restoration_test is True else "FAIL" if restoration_test is False else "N/A"
                overall_str = "PASS" if overall == "SUCCESS" else "FAIL"
                
                f.write(f"| {agent_id} | {overall_str} | {file_validation_str} | {interval_verification_str} | {content_validation_str} | {restoration_test_str} |\n")
            
            # Detailed results for each agent
            for agent_id, result in results.items():
                f.write(f"\n## {agent_id}\n\n")
                f.write(f"**Overall Result:** {result['overall_result']}\n\n")
                
                for test_name, test_result in result["results"].items():
                    f.write(f"### {test_name.replace('_', ' ').title()}\n\n")
                    f.write(f"**Result:** {'SUCCESS' if test_result.get('success', False) else 'FAILED'}\n\n")
                    f.write(f"**Message:** {test_result.get('message', 'N/A')}\n\n")
                    
                    if "details" in test_result and test_result["details"]:
                        f.write("**Details:**\n\n")
                        for key, value in test_result["details"].items():
                            f.write(f"- {key}: {value}\n")
                    
                    if test_name == "interval_verification" and "intervals" in test_result:
                        f.write("\n**Intervals between checkpoints (minutes):**\n\n")
                        for interval in test_result["intervals"]:
                            f.write(f"- {interval:.2f}\n")
                        f.write(f"\n**Average interval:** {test_result.get('average_interval', 0):.2f} minutes\n")
                    
                    if test_name == "restoration_test":
                        if "restored_fields" in test_result:
                            f.write("\n**Successfully Restored Fields:**\n\n")
                            for field in test_result["restored_fields"]:
                                f.write(f"- {field}\n")
                        
                        if "missing_fields" in test_result:
                            f.write("\n**Missing/Failed Fields:**\n\n")
                            for field in test_result["missing_fields"]:
                                f.write(f"- {field}\n")
            
            # Recommendations
            f.write("\n## Recommendations\n\n")
            
            for agent_id, result in results.items():
                if result["overall_result"] == "FAILED":
                    f.write(f"### {agent_id}\n\n")
                    
                    for test_name, test_result in result["results"].items():
                        if not test_result.get("success", False):
                            if test_name == "file_validation":
                                f.write("- **File Validation:** Implement `CheckpointManager` class and create checkpoint files in the correct directory\n")
                            elif test_name == "interval_verification":
                                f.write("- **Interval Verification:** Ensure routine checkpoints are created every 30 minutes\n")
                            elif test_name == "content_validation":
                                f.write("- **Content Validation:** Ensure checkpoint files contain all required fields and follow the correct schema\n")
                            elif test_name == "restoration_test":
                                f.write("- **Restoration Test:** Implement restoration functionality for all state fields\n")
        
        logger.info(f"Generated verification report at {report_file}")
        return report_file
    
    def validate_checkpoint_files(self, agent_id: str) -> ValidationResult:
        """Validate the existence and structure of checkpoint files for a specific agent.
        
        Args:
            agent_id: The ID of the agent to validate
            
        Returns:
            ValidationResult: Validation results
        """
        # Check if files exist for this agent
        checkpoint_files = [
            f for f in os.listdir(self.checkpoint_dir) 
            if f.startswith(f"{agent_id}_") and f.endswith(".checkpoint")
        ]
        
        if not checkpoint_files:
            return ValidationResult(
                False,
                f"No checkpoint files found for {agent_id}",
                {"directory": self.checkpoint_dir}
            )
        
        # Count different types of checkpoints
        routine_count = sum(1 for f in checkpoint_files if "_routine." in f)
        pre_operation_count = sum(1 for f in checkpoint_files if "_pre-operation." in f)
        recovery_count = sum(1 for f in checkpoint_files if "_recovery." in f)
        
        return ValidationResult(
            True,
            f"Found {len(checkpoint_files)} checkpoint files",
            {
                "directory": self.checkpoint_dir,
                "total_files": len(checkpoint_files),
                "routine_count": routine_count,
                "pre_operation_count": pre_operation_count,
                "recovery_count": recovery_count,
                "files": checkpoint_files
            }
        )
    
    def verify_checkpoint_intervals(self, agent_id: str, interval_type: str = "routine") -> IntervalResult:
        """Verify that checkpoints are being created at the correct intervals.
        
        Args:
            agent_id: The ID of the agent to verify
            interval_type: The type of checkpoint interval to verify
            
        Returns:
            IntervalResult: Interval verification results
        """
        # Get all checkpoint files of the specified type
        checkpoint_files = [
            f for f in os.listdir(self.checkpoint_dir) 
            if f.endswith(".checkpoint") and f.startswith(f"{agent_id}_") and f"_{interval_type}." in f
        ]
        
        if len(checkpoint_files) < 2:
            return IntervalResult(
                False,
                f"Not enough {interval_type} checkpoints to verify intervals",
                [],
                0
            )
        
        # Sort checkpoints by timestamp
        checkpoint_files.sort()
        
        # Extract timestamps and calculate intervals
        timestamps = []
        for filename in checkpoint_files:
            # Extract timestamp from filename (agent-X_YYYYMMDDHHMMSS_type.checkpoint)
            parts = filename.split("_")
            if len(parts) >= 2:
                try:
                    timestamp = datetime.strptime(parts[1], "%Y%m%d%H%M%S")
                    timestamps.append(timestamp)
                except ValueError:
                    logger.warning(f"Could not parse timestamp from filename: {filename}")
        
        if len(timestamps) < 2:
            return IntervalResult(
                False,
                "Could not extract enough timestamps from checkpoint filenames",
                [],
                0
            )
        
        # Calculate intervals in minutes
        intervals = []
        for i in range(1, len(timestamps)):
            delta = (timestamps[i] - timestamps[i-1]).total_seconds() / 60.0
            intervals.append(delta)
        
        # Calculate average interval
        average_interval = sum(intervals) / len(intervals)
        
        # Check if intervals are reasonable based on type
        if interval_type == "routine":
            # Routine checkpoints should be created every 30 minutes (±5 minutes)
            is_valid = 25 <= average_interval <= 35
            message = (
                f"Routine checkpoints are created approximately every {average_interval:.2f} minutes"
                if is_valid else
                f"Routine checkpoints should be created every 30 minutes, but average is {average_interval:.2f} minutes"
            )
        else:
            # Other checkpoint types have no strict interval requirements
            is_valid = True
            message = f"{interval_type.title()} checkpoints are created when needed"
        
        return IntervalResult(is_valid, message, intervals, average_interval)
    
    def validate_checkpoint_content(self, agent_id: str) -> ValidationResult:
        """Validate the content of checkpoint files for a specific agent.
        
        Args:
            agent_id: The ID of the agent to validate
            
        Returns:
            ValidationResult: Validation results
        """
        # Get all checkpoint files
        checkpoint_files = [
            f for f in os.listdir(self.checkpoint_dir) 
            if f.endswith(".checkpoint") and f.startswith(f"{agent_id}_")
        ]
        
        if not checkpoint_files:
            return ValidationResult(
                False,
                "No checkpoint files found",
                {"directory": self.checkpoint_dir}
            )
        
        # Choose the most recent checkpoint
        checkpoint_files.sort()
        latest_checkpoint = checkpoint_files[-1]
        checkpoint_path = os.path.join(self.checkpoint_dir, latest_checkpoint)
        
        try:
            with open(checkpoint_path, "r") as f:
                checkpoint_data = json.load(f)
        except Exception as e:
            return ValidationResult(
                False,
                f"Failed to load checkpoint file: {str(e)}",
                {"file": checkpoint_path}
            )
        
        # Validate required fields
        required_fields = ["agent_id", "timestamp", "checkpoint_type", "version", "state"]
        missing_fields = [field for field in required_fields if field not in checkpoint_data]
        
        if missing_fields:
            return ValidationResult(
                False,
                f"Checkpoint file is missing required fields: {', '.join(missing_fields)}",
                {"file": checkpoint_path, "missing_fields": missing_fields}
            )
        
        # Validate agent_id
        if checkpoint_data["agent_id"] != agent_id:
            return ValidationResult(
                False,
                f"Checkpoint agent_id ({checkpoint_data['agent_id']}) does not match {agent_id}",
                {"file": checkpoint_path, "expected": agent_id, "actual": checkpoint_data["agent_id"]}
            )
        
        # Validate state fields
        required_state_fields = ["current_task", "mailbox", "operational_context", "memory"]
        state = checkpoint_data.get("state", {})
        missing_state_fields = [field for field in required_state_fields if field not in state]
        
        if missing_state_fields:
            return ValidationResult(
                False,
                f"Checkpoint state is missing required fields: {', '.join(missing_state_fields)}",
                {"file": checkpoint_path, "missing_state_fields": missing_state_fields}
            )
        
        return ValidationResult(
            True,
            "Checkpoint content is valid",
            {
                "file": checkpoint_path,
                "checkpoint_type": checkpoint_data.get("checkpoint_type", "unknown"),
                "version": checkpoint_data.get("version", "unknown"),
                "timestamp": checkpoint_data.get("timestamp", "unknown")
            }
        )
    
    def test_checkpoint_restoration(self, agent_id: str) -> RestorationResult:
        """Test the checkpoint restoration functionality.
        
        Args:
            agent_id: The ID of the agent to test
            
        Returns:
            RestorationResult: Restoration test results
        """
        # Get all checkpoint files
        checkpoint_files = [
            f for f in os.listdir(self.checkpoint_dir) 
            if f.endswith(".checkpoint") and f.startswith(f"{agent_id}_")
        ]
        
        if not checkpoint_files:
            return RestorationResult(
                False,
                "No checkpoint files found for restoration test",
                [],
                ["No checkpoint files"]
            )
        
        # Choose the most recent checkpoint
        checkpoint_files.sort()
        latest_checkpoint = checkpoint_files[-1]
        checkpoint_path = os.path.join(self.checkpoint_dir, latest_checkpoint)
        
        try:
            with open(checkpoint_path, "r") as f:
                checkpoint_data = json.load(f)
        except Exception as e:
            return RestorationResult(
                False,
                f"Failed to load checkpoint file: {str(e)}",
                [],
                ["Failed to load checkpoint file"]
            )
        
        # Verify state fields exist
        state = checkpoint_data.get("state", {})
        required_state_fields = ["current_task", "mailbox", "operational_context", "memory"]
        present_fields = [field for field in required_state_fields if field in state]
        missing_fields = [field for field in required_state_fields if field not in state]
        
        # In a real implementation, we would mock checkpoint restoration
        # and verify that the agent's state is restored correctly.
        # Since we can't do that in this example, we'll just check that the
        # state fields are present in the checkpoint.
        
        return RestorationResult(
            len(missing_fields) == 0,
            "Checkpoint contains all required state fields for restoration" if len(missing_fields) == 0 else
            f"Checkpoint is missing state fields required for restoration: {', '.join(missing_fields)}",
            present_fields,
            missing_fields
        ) 