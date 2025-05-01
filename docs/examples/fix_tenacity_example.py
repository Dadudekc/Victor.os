import logging

import tenacity

# {{ EDIT START: Add basic logging configuration }}
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# {{ EDIT END }}

# Assume logger is configured elsewhere - Now configured above
logger = logging.getLogger(__name__)


# Custom exception for retry demonstration
class TransientError(Exception):
    pass


# Function that sometimes fails
call_count = 0


def might_fail():
    global call_count
    call_count += 1
    if call_count % 4 != 0:  # Fail 3 out of 4 times
        logger.info(f"Attempt {call_count}: Failing with TransientError")
        raise TransientError("Simulated transient failure")
    else:
        logger.info(f"Attempt {call_count}: Success!")
        return "Operation Successful"


# Retry configuration
retryer = tenacity.Retrying(
    stop=tenacity.stop_after_attempt(5),  # Max 5 attempts
    wait=tenacity.wait_fixed(0.1),  # Wait 0.1s between retries
    retry=tenacity.retry_if_exception_type(TransientError),  # Only retry TransientError
    reraise=True,  # Reraise the exception if all retries fail
    # {{ EDIT START: Use standard before_sleep_log signature }}
    before_sleep=tenacity.before_sleep_log(
        logger, logging.WARNING, exc_info=True
    ),  # Log before waiting, include traceback
    # {{ EDIT END }}
)

# Execute the function with retries
try:
    # Reset call count for predictable execution
    call_count = 0
    logger.info("Starting operation with retries...")
    result = retryer.call(might_fail)
    logger.info(f"Final Result: {result}")
except TransientError as e:
    logger.error(
        f"Operation ultimately failed after {retryer.statistics.get('attempt_number', 'N/A')} attempts: {e}"
    )
except Exception as e:
    logger.error(f"An unexpected error occurred: {e}", exc_info=True)
finally:
    # Print the state of the retryer after the call
    # Ensure statistics are accessed safely
    stats = getattr(retryer, "statistics", {})
    logger.info(f"Retry statistics: {stats}")
