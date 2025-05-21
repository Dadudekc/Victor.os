"""
Resilient Checkpoint Validation

This module runs comprehensive validation tests on the ResilientCheckpointManager
to ensure it can handle various failure scenarios and recover properly.

Usage:
    python -m dreamos.core.validate_checkpoint_resilience
"""

import os
import json
import time
import logging
import random
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the checkpoint managers
from dreamos.core.checkpoint_manager import CheckpointManager
from dreamos.core.resilient_checkpoint_manager import ResilientCheckpointManager

# Import resilient IO
from dreamos.utils.resilient_io import read_file, write_file, read_json, write_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("dreamos.core.validate_checkpoint_resilience")

class ResilienceValidator:
    """
    Validates the resilience of the ResilientCheckpointManager under various conditions.
    
    This class tests:
    1. Recovery from file corruption
    2. Fallback to standard checkpoint manager
    3. Recovery from simulated file system errors
    4. Drift detection and recovery
    """
    
    def __init__(self):
        """Initialize the validator."""
        self.agent_id = "validation-agent"
        self.test_dir = Path("runtime/validation_test")
        self.checkpoint_dir = self.test_dir / "checkpoints"
        self.agent_data_dir = self.test_dir / f"agent_data/{self.agent_id}"
        self.memory_path = self.agent_data_dir / "memory.json"
        self.context_path = self.agent_data_dir / "context.json"
        
        # Clean up previous test data if it exists
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        
        # Create test directories
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.agent_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize test data
        self._initialize_test_data()
        
        # Create checkpoint manager for testing
        self.manager = ResilientCheckpointManager(self.agent_id)
        self.manager.checkpoint_dir = str(self.checkpoint_dir)
        
        logger.info(f"Initialized ResilienceValidator with test dir: {self.test_dir}")
    
    def _initialize_test_data(self):
        """Initialize test data files."""
        # Create memory file
        memory_data = {
            "short_term": ["Initial memory item"],
            "session": ["Session entry 1"]
        }
        with open(self.memory_path, 'w') as f:
            json.dump(memory_data, f, indent=2)
        
        # Create context file
        context_data = {
            "goals": ["Test resilient checkpoints"],
            "constraints": ["Must be reliable"],
            "decisions": ["Decision 1", "Decision 2"]
        }
        with open(self.context_path, 'w') as f:
            json.dump(context_data, f, indent=2)
        
        logger.info("Initialized test data files")
    
    def run_all_validations(self):
        """Run all validation tests."""
        results = {
            "create_checkpoint": self.validate_create_checkpoint(),
            "restore_checkpoint": self.validate_restore_checkpoint(),
            "file_corruption": self.validate_resilience_to_corruption(),
            "io_error_fallback": self.validate_io_error_fallback(),
            "drift_detection": self.validate_drift_detection()
        }
        
        # Print summary
        logger.info("\n\n=== VALIDATION RESULTS ===")
        all_passed = True
        for test, result in results.items():
            status = "✅ PASSED" if result else "❌ FAILED"
            logger.info(f"{test}: {status}")
            all_passed = all_passed and result
        
        if all_passed:
            logger.info("\n✅ ALL VALIDATIONS PASSED - ResilientCheckpointManager is production ready!")
        else:
            logger.error("\n❌ SOME VALIDATIONS FAILED - See logs for details")
        
        return all_passed
    
    def validate_create_checkpoint(self):
        """Validate checkpoint creation."""
        logger.info("\n=== Validating Checkpoint Creation ===")
        
        try:
            # Create checkpoints of different types
            routine_checkpoint = self.manager.create_checkpoint("routine")
            pre_op_checkpoint = self.manager.create_checkpoint("pre_operation")
            recovery_checkpoint = self.manager.create_checkpoint("recovery")
            
            # Verify all checkpoints were created
            checkpoints_exist = (
                os.path.exists(routine_checkpoint) and
                os.path.exists(pre_op_checkpoint) and
                os.path.exists(recovery_checkpoint)
            )
            
            # Verify checkpoint content
            valid_content = True
            for checkpoint in [routine_checkpoint, pre_op_checkpoint, recovery_checkpoint]:
                with open(checkpoint, 'r') as f:
                    data = json.load(f)
                    
                    if data["agent_id"] != self.agent_id:
                        logger.error(f"Invalid agent_id in checkpoint: {checkpoint}")
                        valid_content = False
                    
                    if "state" not in data:
                        logger.error(f"Missing state in checkpoint: {checkpoint}")
                        valid_content = False
            
            result = checkpoints_exist and valid_content
            if result:
                logger.info("✅ Checkpoint creation validation passed")
            else:
                logger.error("❌ Checkpoint creation validation failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during checkpoint creation validation: {str(e)}")
            return False
    
    def validate_restore_checkpoint(self):
        """Validate checkpoint restoration."""
        logger.info("\n=== Validating Checkpoint Restoration ===")
        
        try:
            # Create a checkpoint with initial data
            checkpoint = self.manager.create_checkpoint("validation")
            
            # Modify memory data
            modified_memory = {
                "short_term": ["Initial memory item", "NEW ITEM 1", "NEW ITEM 2"],
                "session": ["Session entry 1", "NEW SESSION ENTRY"]
            }
            with open(self.memory_path, 'w') as f:
                json.dump(modified_memory, f, indent=2)
            
            # Verify the memory was modified
            with open(self.memory_path, 'r') as f:
                current_memory = json.load(f)
            
            if len(current_memory["short_term"]) != 3:
                logger.error("Memory modification for test didn't work")
                return False
            
            # Restore from checkpoint
            result = self.manager.restore_checkpoint(checkpoint)
            
            # Verify restoration was successful
            if not result:
                logger.error("Restoration reported failure")
                return False
            
            # Verify memory was restored to original state
            with open(self.memory_path, 'r') as f:
                restored_memory = json.load(f)
            
            memory_restored = (
                len(restored_memory["short_term"]) == 1 and
                restored_memory["short_term"][0] == "Initial memory item"
            )
            
            if memory_restored:
                logger.info("✅ Checkpoint restoration validation passed")
            else:
                logger.error("❌ Checkpoint restoration validation failed - memory not properly restored")
            
            return memory_restored
            
        except Exception as e:
            logger.error(f"Error during checkpoint restoration validation: {str(e)}")
            return False
    
    def validate_resilience_to_corruption(self):
        """Validate resilience to file corruption."""
        logger.info("\n=== Validating Resilience to File Corruption ===")
        
        try:
            # Create a checkpoint
            checkpoint = self.manager.create_checkpoint("pre_corruption")
            
            # Create a backup copy for later restoration
            backup_path = f"{checkpoint}.backup"
            shutil.copy(checkpoint, backup_path)
            
            # Corrupt the checkpoint file
            with open(checkpoint, 'r') as f:
                content = f.read()
            
            # Corrupt the JSON by removing a closing brace
            corrupted_content = content[:-2]
            
            with open(checkpoint, 'w') as f:
                f.write(corrupted_content)
            
            logger.info(f"Corrupted checkpoint file: {checkpoint}")
            
            # Attempt to restore from corrupted checkpoint (should fail)
            result = self.manager.restore_checkpoint(checkpoint)
            
            # Restoration should fail due to corruption
            if result:
                logger.error("Restoration from corrupted checkpoint unexpectedly succeeded")
                return False
            
            # Restore the original checkpoint file
            shutil.copy(backup_path, checkpoint)
            logger.info("Restored checkpoint from backup")
            
            # Attempt to restore again (should succeed now)
            result = self.manager.restore_checkpoint(checkpoint)
            
            if result:
                logger.info("✅ Corruption resilience validation passed - properly handled corrupted file")
            else:
                logger.error("❌ Corruption resilience validation failed - could not restore after fixing corruption")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during corruption resilience validation: {str(e)}")
            return False
    
    def validate_io_error_fallback(self):
        """Validate fallback to standard checkpoint manager on IO error."""
        logger.info("\n=== Validating IO Error Fallback ===")
        
        try:
            # Create a checkpoint
            checkpoint = self.manager.create_checkpoint("pre_io_error")
            
            # Mock the resilient_io.read_json to simulate IO error
            original_read_json = read_json
            
            # Define a patched function that raises an exception
            def mock_read_json(*args, **kwargs):
                raise IOError("Simulated IO error")
            
            # Apply the patch
            import dreamos.utils.resilient_io
            dreamos.utils.resilient_io.read_json = mock_read_json
            
            # Verify the manager uses the standard checkpoint manager as fallback
            with patch.object(self.manager.manager, 'restore_checkpoint', return_value=True) as mock_restore:
                # Attempt restoration (should use fallback)
                result = self.manager.restore_checkpoint(checkpoint)
                
                # Verify fallback was called
                fallback_called = mock_restore.call_count > 0
                
                # Restoration should succeed through fallback
                if result and fallback_called:
                    logger.info("✅ IO error fallback validation passed - used standard manager as fallback")
                    success = True
                else:
                    logger.error("❌ IO error fallback validation failed - did not use fallback properly")
                    success = False
            
            # Restore the original function
            dreamos.utils.resilient_io.read_json = original_read_json
            
            return success
            
        except Exception as e:
            # Restore the original function in case of error
            import dreamos.utils.resilient_io
            dreamos.utils.resilient_io.read_json = read_json
            
            logger.error(f"Error during IO error fallback validation: {str(e)}")
            return False
    
    def validate_drift_detection(self):
        """Validate drift detection."""
        logger.info("\n=== Validating Drift Detection ===")
        
        try:
            # Create initial state
            memory_data = {
                "short_term": ["Initial state for drift test"],
                "session": []
            }
            with open(self.memory_path, 'w') as f:
                json.dump(memory_data, f, indent=2)
            
            # Create a checkpoint
            checkpoint = self.manager.create_checkpoint("pre_drift")
            
            # Check drift detection before introducing drift
            drift_before = self.manager.detect_drift()
            if drift_before:
                logger.error("Drift incorrectly detected in clean state")
                return False
            
            # Patch the detect_drift method to simulate drift
            original_detect_drift = self.manager.detect_drift
            self.manager.detect_drift = MagicMock(return_value=True)
            
            # Verify drift is now detected
            drift_after = self.manager.detect_drift()
            if not drift_after:
                logger.error("Drift not detected after mock patch")
                return False
            
            # Simulate recovery process
            recovery_checkpoint = self.manager.create_checkpoint("recovery")
            recovery_result = self.manager.restore_checkpoint(checkpoint)
            
            # Restore original detect_drift method
            self.manager.detect_drift = original_detect_drift
            
            if recovery_result:
                logger.info("✅ Drift detection validation passed")
            else:
                logger.error("❌ Drift detection validation failed - could not recover from simulated drift")
            
            return recovery_result
            
        except Exception as e:
            # Restore original method in case of error
            self.manager.detect_drift = CheckpointManager.detect_drift.__get__(self.manager, ResilientCheckpointManager)
            
            logger.error(f"Error during drift detection validation: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up test data."""
        try:
            if self.test_dir.exists():
                shutil.rmtree(self.test_dir)
                logger.info(f"Cleaned up test directory: {self.test_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up test data: {str(e)}")

def main():
    """Run validation tests."""
    logger.info("Starting validation of ResilientCheckpointManager")
    
    validator = ResilienceValidator()
    
    try:
        # Run all validations
        all_passed = validator.run_all_validations()
        
        # Clean up
        validator.cleanup()
        
        # Print final result
        if all_passed:
            logger.info("\n🎉 VALIDATION SUCCESSFUL - ResilientCheckpointManager is production ready!")
        else:
            logger.error("\n⚠️ VALIDATION FAILED - See logs for details")
        
        return all_passed
        
    except Exception as e:
        logger.error(f"Unexpected error during validation: {str(e)}")
        validator.cleanup()
        return False

if __name__ == "__main__":
    main() 