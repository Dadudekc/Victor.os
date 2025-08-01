"""
Checkpoint Integration Example for Agent-2 (Infrastructure Agent)

This script demonstrates how to integrate the CheckpointManager into the Infrastructure Agent's
operational loop to prevent drift in long-running sessions.

Generated by: dreamos.utils.checkpoint_integration
Date: 2025-05-18
"""

import time
import logging
import os
import json
import sys
import subprocess
from typing import List, Dict, Any, Optional

from dreamos.core.checkpoint_manager import CheckpointManager
from dreamos.utils.checkpoint_integration import (
    setup_checkpoint_system,
    check_and_create_checkpoint,
    controlled_restart,
    checkpoint_operation
)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("agent-2.infrastructure")

class InfrastructureAgent:
    """
    Infrastructure Agent implementation with checkpoint integration.
    
    This class demonstrates how to integrate checkpoint capabilities
    into the Infrastructure Agent's operational logic, with special
    emphasis on handling infrastructure system state.
    """
    
    def __init__(self):
        """Initialize the Infrastructure Agent with checkpoint support."""
        self.agent_id = "Agent-2"
        self.role = "Infrastructure Engineer"
        self.current_task_id = None
        self.current_task_status = None
        self.task_context = {}
        self.infra_state = {
            "services": {},
            "deployments": {},
            "resource_usage": {}
        }
        self.memory = {
            "short_term": [],
            "session": []
        }
        
        # Initialize checkpoint system
        self.checkpoint_manager, self.last_checkpoint_time = setup_checkpoint_system(self.agent_id)
        self.session_start_time = time.time()
        
        # Customize checkpoint manager for infrastructure-specific state
        self._customize_checkpoint_manager()
        
    def _customize_checkpoint_manager(self):
        """Customize the checkpoint manager with infrastructure-specific state handlers."""
        # Store the original methods
        original_get_task_state = self.checkpoint_manager._get_current_task_state
        original_restore_task_state = self.checkpoint_manager._restore_task_state
        original_get_operational_context = self.checkpoint_manager._get_operational_context
        original_restore_operational_context = self.checkpoint_manager._restore_operational_context
        original_get_memory_state = self.checkpoint_manager._get_memory_state
        original_restore_memory_state = self.checkpoint_manager._restore_memory_state
        
        # Override with customized methods
        def get_task_state():
            # Try the default implementation
            state = original_get_task_state()
            
            # Add infrastructure-specific task state
            infra_state = {
                "id": self.current_task_id,
                "status": self.current_task_status,
                "progress_percentage": self._calculate_progress(),
                "context": self.task_context,
                "infra_related": self._is_infra_related_task()
            }
            
            # Merge with default state
            state.update(infra_state)
            return state
            
        def restore_task_state(task_state):
            # Use default implementation
            original_restore_task_state(task_state)
            
            # Add infrastructure-specific restoration
            if task_state:
                self.current_task_id = task_state.get("id")
                self.current_task_status = task_state.get("status")
                self.task_context = task_state.get("context", {})
                
        def get_operational_context():
            # Get default context
            context = original_get_operational_context()
            
            # Enhance with infrastructure-specific context
            infra_context = {
                "system_state": self._get_system_state(),
                "service_status": self._get_service_status(),
                "infra_state": self.infra_state
            }
            context.update(infra_context)
            return context
            
        def restore_operational_context(operational_context):
            # Use default implementation
            original_restore_operational_context(operational_context)
            
            # Add infrastructure-specific restoration
            if operational_context and "infra_state" in operational_context:
                self.infra_state = operational_context["infra_state"]
                
        def get_memory_state():
            # Get default memory state
            memory = original_get_memory_state()
            
            # Enhance with infrastructure-specific memory
            memory.update(self.memory)
            return memory
            
        def restore_memory_state(memory_state):
            # Use default implementation
            original_restore_memory_state(memory_state)
            
            # Add infrastructure-specific restoration
            if memory_state:
                self.memory = memory_state
                
        # Apply the customized methods
        self.checkpoint_manager._get_current_task_state = get_task_state
        self.checkpoint_manager._restore_task_state = restore_task_state
        self.checkpoint_manager._get_operational_context = get_operational_context
        self.checkpoint_manager._restore_operational_context = restore_operational_context
        self.checkpoint_manager._get_memory_state = get_memory_state
        self.checkpoint_manager._restore_memory_state = restore_memory_state
        
    def _calculate_progress(self) -> int:
        """Calculate task progress percentage based on infrastructure-specific logic."""
        # In a real implementation, this would calculate actual progress
        return 65  # Dummy value for example
        
    def _is_infra_related_task(self) -> bool:
        """Determine if current task is infrastructure-related."""
        # Simplified check for example purposes
        if self.current_task_id and ("INFRA" in self.current_task_id or "TOOL" in self.current_task_id):
            return True
        return False
        
    def _get_system_state(self) -> Dict[str, Any]:
        """Get current system state for checkpointing."""
        # In a real implementation, this would get actual system metrics
        return {
            "cpu_usage": 32.5,
            "memory_usage": 45.2,
            "disk_usage": 68.7,
            "uptime": 345600  # 4 days in seconds
        }
        
    def _get_service_status(self) -> Dict[str, str]:
        """Get status of key services for checkpointing."""
        # In a real implementation, this would check actual services
        return {
            "database": "running",
            "web_server": "running",
            "task_queue": "running",
            "file_service": "running"
        }
    
    @checkpoint_operation
    def process_mailbox(self, checkpoint_manager):
        """
        Process Infrastructure Agent's mailbox with checkpoint protection.
        
        This function demonstrates how to use the checkpoint_operation decorator
        to automatically create checkpoints before and after critical operations.
        """
        logger.info("Infrastructure Agent processing mailbox...")
        
        # Simulate mailbox processing
        time.sleep(1)
        
        # Add to memory
        self.memory["short_term"].append({
            "action": "process_mailbox",
            "timestamp": time.time()
        })
        
        logger.info("Mailbox processing complete")
        
    def update_infrastructure_state(self):
        """
        Update and monitor infrastructure state with checkpoint protection.
        
        This demonstrates using manual checkpoint creation for critical operations.
        """
        logger.info("Updating infrastructure state...")
        
        # Creating a pre-operation checkpoint before state update
        pre_op_checkpoint = self.checkpoint_manager.create_checkpoint("pre_operation")
        logger.info(f"Created pre-operation checkpoint: {pre_op_checkpoint}")
        
        try:
            # Simulate infrastructure monitoring
            time.sleep(1)
            
            # Update infrastructure state
            self.infra_state = {
                "services": self._get_service_status(),
                "deployments": {
                    "api_service": "v1.2.3",
                    "web_frontend": "v2.0.1",
                    "database": "v3.1.0"
                },
                "resource_usage": self._get_system_state()
            }
            
            # Successful completion checkpoint
            post_op_checkpoint = self.checkpoint_manager.create_checkpoint("post_operation")
            logger.info(f"Created post-operation checkpoint: {post_op_checkpoint}")
            
        except Exception as e:
            # Create recovery checkpoint on error
            recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
            logger.error(f"Error during infrastructure update: {str(e)}")
            logger.info(f"Recovery checkpoint created: {recovery_checkpoint}")
            
    def perform_system_maintenance(self):
        """
        Perform system maintenance operations with checkpoint protection.
        
        This demonstrates checkpointing for particularly risky operations.
        """
        logger.info("Performing system maintenance...")
        
        # Extra-important pre-operation checkpoint
        recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
        logger.info(f"Created recovery checkpoint before maintenance: {recovery_checkpoint}")
        
        try:
            # Simulate maintenance operations
            logger.info("Step 1: Checking system integrity...")
            time.sleep(1)
            
            logger.info("Step 2: Cleaning temporary files...")
            time.sleep(1)
            
            logger.info("Step 3: Optimizing database...")
            time.sleep(1)
            
            # Record maintenance in infrastructure state
            self.infra_state["last_maintenance"] = time.time()
            
            # Successful completion checkpoint
            post_op_checkpoint = self.checkpoint_manager.create_checkpoint("post_operation")
            logger.info(f"Maintenance completed successfully, checkpoint: {post_op_checkpoint}")
            
        except Exception as e:
            # Create additional recovery checkpoint on error
            recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
            logger.error(f"Error during maintenance: {str(e)}")
            logger.info(f"Additional recovery checkpoint created: {recovery_checkpoint}")
            # In a real implementation, this might initiate additional recovery steps
            
    def operational_loop(self):
        """
        Main operational loop with checkpoint integration.
        
        This demonstrates a complete integration of checkpointing into
        the Infrastructure Agent's operational loop.
        """
        logger.info("Starting Infrastructure Agent operational loop...")
        
        # Main operational loop
        while True:  # In real implementation, there would be a proper exit condition
            try:
                # 1. Process mailbox
                self.process_mailbox(self.checkpoint_manager)
                
                # 2. Update infrastructure state
                self.update_infrastructure_state()
                
                # 3. Conditional maintenance (every 5 minutes in this example)
                if int(time.time()) % 300 < 5:  # Roughly every 5 minutes
                    self.perform_system_maintenance()
                
                # 4. Regular checkpoint creation
                self.last_checkpoint_time = check_and_create_checkpoint(
                    self.checkpoint_manager,
                    self.last_checkpoint_time
                )
                
                # 5. Check for session refresh to prevent drift
                current_time = time.time()
                if current_time - self.session_start_time >= 7200:  # 2 hours
                    logger.info("Session duration exceeds 2 hours, initiating controlled restart")
                    recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
                    controlled_restart(recovery_checkpoint)
                    break  # Exit loop after restart
                    
                # Simulate short delay between operations
                time.sleep(5)
                
            except Exception as e:
                # Create recovery checkpoint on error
                recovery_checkpoint = self.checkpoint_manager.create_checkpoint("recovery")
                logger.error(f"Error during operation: {str(e)}")
                logger.info(f"Recovery checkpoint created: {recovery_checkpoint}")
                
                # Continue loop instead of breaking (resilience)
                continue
                
        logger.info("Infrastructure Agent operational loop terminated")

if __name__ == "__main__":
    # Create and run the Infrastructure Agent
    infrastructure_agent = InfrastructureAgent()
    infrastructure_agent.operational_loop() 