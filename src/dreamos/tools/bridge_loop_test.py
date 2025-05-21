#!/usr/bin/env python3
"""
Bridge Loop Test Implementation
Task TEST-001: Bridge loop test task
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
import json

from dreamos.core.coordination.agent_bus import AgentBus, EventType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BridgeLoopTest:
    """Bridge loop test implementation"""
    
    def __init__(self):
        self.agent_bus = AgentBus()
        self.test_results: Dict[str, Any] = {}
        
    async def run_test(self):
        """Run bridge loop test"""
        try:
            # Start agent bus
            await self.agent_bus.start()
            logger.info("AgentBus started for bridge loop test")
            
            # Subscribe to test events
            await self.agent_bus.subscribe(EventType.AGENT_HEARTBEAT.value, self._handle_heartbeat)
            await self.agent_bus.subscribe(EventType.AGENT_RESPONSE.value, self._handle_response)
            
            # Publish test events
            await self.agent_bus.publish(EventType.AGENT_HEARTBEAT.value, {
                "agent_id": "Agent-5",
                "timestamp": "2025-05-20T01:24:52"
            })
            
            await self.agent_bus.publish(EventType.AGENT_RESPONSE.value, {
                "agent_id": "Agent-5",
                "response": "Bridge loop test response",
                "timestamp": "2025-05-20T01:24:53"
            })
            
            # Wait for event processing
            await asyncio.sleep(5)
            
            # Stop agent bus
            await self.agent_bus.stop()
            logger.info("AgentBus stopped after bridge loop test")
            
            # Log test results
            self._log_test_results()
            
        except Exception as e:
            logger.error(f"Error in bridge loop test: {e}")
            raise
            
    async def _handle_heartbeat(self, event_type: str, data: Dict[str, Any]):
        """Handle heartbeat event"""
        logger.info(f"Received heartbeat: {data}")
        self.test_results["heartbeat"] = data
        
    async def _handle_response(self, event_type: str, data: Dict[str, Any]):
        """Handle response event"""
        logger.info(f"Received response: {data}")
        self.test_results["response"] = data
        
    def _log_test_results(self):
        """Log test results"""
        results_file = Path("runtime/test_results/bridge_loop_test.json")
        results_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_file, "w") as f:
            json.dump(self.test_results, f, indent=2)
        logger.info(f"Test results logged to {results_file}")

async def main():
    """Main entry point"""
    test = BridgeLoopTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main()) 