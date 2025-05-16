import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from continuous_operation import ContinuousOperationHandler
from monitor_continuous_operation import ContinuousOperationMonitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_continuous_operation():
    """Validate the continuous operation implementation."""
    queue_dir = Path(__file__).parent
    handler = ContinuousOperationHandler(queue_dir)
    monitor = ContinuousOperationMonitor(queue_dir)
    
    # Test cycle management
    assert handler.cycle_count == 0, "Initial cycle count should be 0"
    handler.increment_cycle()
    assert handler.cycle_count == 1, "Cycle count should increment"
    
    # Test cycle health
    assert handler.check_cycle_health(), "Cycle health check should pass"
    
    # Test prompt processing
    result = handler.process_prompt("Agent-1", "test prompt")
    assert not result, "Should not meet minimum cycles yet"
    
    # Process enough prompts to meet minimum cycles
    for _ in range(24):
        handler.process_prompt("Agent-1", "test prompt")
    
    assert handler.cycle_count == 25, "Should reach minimum cycles"
    assert handler.process_prompt("Agent-1", "test prompt"), "Should meet minimum cycles"
    
    # Test monitor health check
    assert monitor.check_operation_health(), "Monitor health check should pass"
    
    # Verify logs exist
    assert (queue_dir / "operation_log.jsonl").exists(), "Operation log should exist"
    assert (queue_dir / "monitor_log.jsonl").exists(), "Monitor log should exist"
    
    # Verify prompt file
    assert handler.prompts_file.exists(), "Prompts file should exist"
    with open(handler.prompts_file) as f:
        prompts = [json.loads(line) for line in f]
        assert len(prompts) > 0, "Should have recorded prompts"
    
    logger.info("Continuous operation validation passed")
    return True

if __name__ == "__main__":
    try:
        validate_continuous_operation()
        print("Validation successful")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        sys.exit(1) 