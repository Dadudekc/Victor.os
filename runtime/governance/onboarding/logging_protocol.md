# Dream.OS Logging Standards

This document outlines the standard practices for logging within the Dream.OS codebase.

## Guiding Principles

- **Consistency:** Logs should be consistent in format and level across the system.
- **Clarity:** Log messages should be clear and provide sufficient context.
- **Central Configuration:** Logging behavior (levels, destinations, format) should be configured centrally.
- **Performance:** Logging should not unduly impact application performance.

## Standard Practices

1.  **Primary Logging:**
    - Use Python's built-in `logging` module.
    - Obtain loggers within modules using: `logger = logging.getLogger(__name__)`.
    - For major, distinct components (e.g., AgentBus, FeedbackEngine), specific named loggers (`logging.getLogger("AgentBus")`) are acceptable if documented.
    - Agents should use agent-specific loggers obtained via `logging.getLogger(agent_id)` (typically handled within `BaseAgent`).

2.  **Configuration:**
    - Logging is configured *exclusively* by the `setup_logging(config: AppConfig)` function in `src/dreamos/config.py`.
    - **Do not** call `logging.basicConfig()` or manually add handlers/formatters within individual modules.
    - Log levels, handlers (Console, File), and format are determined by the `LoggingConfig` section of the application configuration (`runtime/config/config.yaml` or defaults).

3.  **Structured Agent Logs:**
    - For logging key agent actions (task claims, completions, state changes, significant events) in a structured format for analysis, use the `log_agent_event` function from `src/dreamos/core/logging/swarm_logger.py`.
    - This function writes to the dedicated `runtime/logs/agent_activity_log.jsonl` (or as configured).

4.  **Log Levels:**
    - Use standard log levels appropriately:
        - `DEBUG`: Detailed diagnostic information useful for developers during debugging (e.g., function entry/exit, intermediate variable values, detailed steps). Should generally be disabled in production configs.
        - `INFO`: High-level confirmation of normal operational milestones (e.g., service started, task completed, configuration loaded, significant user action).
        - `WARNING`: Indicates potential issues, recoverable errors, or use of fallback behavior (e.g., optional configuration missing, retrying an operation, resource nearing limit).
        - `ERROR`: A specific operation failed, but the application can likely continue (e.g., processing one message failed, specific request timed out).
        - `CRITICAL`: Severe error indicating a major failure, likely leading to application termination or significant malfunction.

5.  **`print()` Statement Usage:**
    - **Forbidden** for logging, debugging, or status reporting within library code (`src/dreamos/` modules, except potentially `cli`).
    - Replace debug/status `print`s with appropriate `logger.debug()`, `logger.info()`, etc.
    - **Allowed** *only* for direct user output in dedicated Command-Line Interface (CLI) tools intended for interactive use (e.g., scripts in `src/dreamos/cli/` or some tools in `src/dreamos/tools/` that explicitly generate reports to stdout).
    - Remove commented-out `print` statements.

6.  **Log Message Format:**
    - The standard log format is configured centrally in `config.py` (`setup_logging`) and applies to all standard logs.
    - Default format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`

7.  **Sensitive Information:**
    - Be cautious not to log sensitive information (API keys, passwords, personal data) unless absolutely necessary and properly secured/masked.

## Implementation Details & Technical Notes

*(Consolidated from Developer Notes)*

- **Central Setup:** As stated, logging is configured exclusively by `setup_logging()` in `src/dreamos/config.py`. This function typically sets up:
    - A `logging.StreamHandler` for console output (default level INFO, standard format).
    - A `logging.handlers.RotatingFileHandler` for file output (default path `logs/agent.log`, default level DEBUG, JSON Lines format).
- **Log Rotation:** File rotation is handled by `RotatingFileHandler`. Default settings (verify in `config.py` or setup code) are often around 10MB file size with 5 backups retained.
- **Structured Log Format (`logs/agent.log` - JSON Lines):**
    - Each line is a JSON object.
    - **Common Fields (Verify current implementation in `config.py` formatter):**
        ```json
        {
          "timestamp": "<ISO 8601 UTC>",
          "level": "<LEVEL_NAME>",
          "message": "<Formatted log message>",
          "logger": "<logger_name>"
          // Potentially other fields like "component", "agent_id" if custom formatter used
        }
        ```
    - **Error Fields:** For logs with level `ERROR` or higher, or when `exc_info=True` is used, additional fields are typically included:
        ```json
        {
          // ... common fields ...
          "file": "<pathname>",
          "line": <lineno>,
          "function": "<funcName>",
          "exception": {
            "type": "<ExceptionType>",
            "message": "<Exception message>",
            "traceback": "<Formatted traceback>"
          }
        }
        ```
    - **Extra Context:** Additional data can be added using the `extra` dictionary parameter in logging calls (`logger.info("Msg", extra={"key": "value"})`). These appear under an `"extra"` key in the JSON log if the formatter supports it.
- **Structured Agent Activity Log:** The dedicated `log_agent_event` function (`src/dreamos/core/logging/swarm_logger.py`) writes specific structured events (task status, etc.) to `runtime/logs/agent_activity_log.jsonl` for easier parsing of key agent lifecycle events.

## Future Considerations

- **Structured Logging (Standard Logs):** Investigate using `logging.LogRecord` attributes (`extra` dictionary) and custom formatters/handlers to add more structured data (e.g., request IDs, session IDs) to standard log messages if needed for improved analysis, potentially integrating with systems like ELK or Datadog.
- **Performance Profiling:** If specific logging becomes a performance bottleneck, consider techniques like log sampling or asynchronous logging handlers.
