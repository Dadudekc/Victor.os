"""Test script for cursor coordinator with agent-4."""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from dreamos.core.coordination.agent_bus import AgentBus
from dreamos.core.coordination.message_patterns import TaskMessage
from dreamos.agents.cursor.cursor_coordinator import CursorCoordinator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('runtime/test_logs/agent4_resume_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def test_agent_4():
    """Test cursor coordinator with agent-4."""
    # Initialize paths
    base_dir = Path("runtime")
    gui_images_dir = base_dir / "gui_images"
    coords_file = base_dir / "config" / "cursor_agent_coords.json"
    thea_mailbox_dir = base_dir / "thea_mailbox"
    test_logs_dir = base_dir / "test_logs"
    
    # Create test logs directory if it doesn't exist
    test_logs_dir.mkdir(parents=True, exist_ok=True)
    
    # Verify required files exist
    if not coords_file.exists():
        logger.error(f"Coordinates file not found: {coords_file}")
        return
        
    if not gui_images_dir.exists():
        logger.error(f"GUI images directory not found: {gui_images_dir}")
        return
        
    # Load agent coordinates
    try:
        with open(coords_file) as f:
            coords = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load coordinates: {e}")
        return
    
    agent_4_coords = coords.get("agent-4")
    if not agent_4_coords:
        logger.error("Could not find coordinates for agent-4")
        return
        
    # Initialize coordinator
    try:
        bus = AgentBus()
        coordinator = CursorCoordinator(
            bus=bus,
            gui_images_dir=gui_images_dir,
            coords_file=coords_file,
            thea_mailbox_dir=thea_mailbox_dir,
            check_interval=0.5,  # Check more frequently for testing
            response_timeout=60.0  # Longer timeout for testing
        )
    except Exception as e:
        logger.error(f"Failed to initialize coordinator: {e}")
        return
    
    # Sample resume text for testing
    sample_resume = """
    JOHN DOE
    Software Engineer
    
    EXPERIENCE
    Senior Software Engineer | Tech Corp | 2020-Present
    - Led development of microservices architecture
    - Implemented CI/CD pipelines reducing deployment time by 40%
    - Mentored junior developers and conducted code reviews
    
    Software Engineer | Startup Inc | 2018-2020
    - Developed RESTful APIs using Python and FastAPI
    - Optimized database queries improving response time by 30%
    - Collaborated with UX team on frontend improvements
    
    SKILLS
    - Languages: Python, JavaScript, TypeScript
    - Frameworks: FastAPI, React, Django
    - Tools: Docker, Kubernetes, AWS
    - Databases: PostgreSQL, MongoDB
    
    EDUCATION
    B.S. Computer Science
    University of Technology | 2018
    """
    
    test_start_time = time.time()
    test_result = {
        "agent": "Agent-4",
        "task": "resume_analysis",
        "status": "pending",
        "start_time": datetime.fromtimestamp(test_start_time).isoformat(),
        "response": None,
        "end_time": None,
        "duration_seconds": None,
        "error": None
    }
    
    try:
        # Start coordinator
        await coordinator.start()
        logger.info("Started cursor coordinator")
        
        # Create test task
        task = TaskMessage(
            task_id="test_resume_1",
            task_type="resume_analysis",
            status="pending",
            input_data={
                "prompt": "Please analyze this resume and provide feedback on its strengths and areas for improvement.",
                "resume_text": sample_resume
            },
            metadata={
                "requires_thea": True,
                "priority": "high"
            }
        )
        
        # Register agent-4
        await coordinator.register_agent("agent-4", agent_4_coords, task)
        logger.info("Registered agent-4 for resume analysis")
        
        # Wait for response
        logger.info("Waiting for response from agent-4...")
        response = await coordinator.wait_for_response("agent-4")
        
        if response:
            logger.info(f"Received response from agent-4:\n{response}")
            test_result.update({
                "status": "success",
                "response": response,
                "end_time": datetime.fromtimestamp(time.time()).isoformat(),
                "duration_seconds": time.time() - test_start_time
            })
        else:
            logger.warning("No response received from agent-4")
            test_result.update({
                "status": "failed",
                "error": "No response received within timeout",
                "end_time": datetime.fromtimestamp(time.time()).isoformat(),
                "duration_seconds": time.time() - test_start_time
            })
            
    except Exception as e:
        logger.error(f"Error during test: {e}", exc_info=True)
        test_result.update({
            "status": "error",
            "error": str(e),
            "end_time": datetime.fromtimestamp(time.time()).isoformat(),
            "duration_seconds": time.time() - test_start_time
        })
    finally:
        logger.info("Stopping coordinator...")
        await coordinator.stop()
        await bus.close()
        
        # Save test results
        results_file = test_logs_dir / "agent4_resume_test.json"
        with open(results_file, 'w') as f:
            json.dump(test_result, f, indent=2)
        logger.info(f"Test results saved to {results_file}")
        
        logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(test_agent_4()) 