# THEA Relay Message Schema v1.0

This document defines the standard message schema for responses relayed *through* THEA (The Holographic Executive Assistant) to other agents within the Dream.OS ecosystem.

## Required Fields

All messages sent via THEA to another agent **MUST** contain the following fields in their top-level JSON structure:

1.  `recipient_agent_id` (String)
    *   **Description:** The unique identifier of the agent intended to receive this message.
    *   **Example:** `"Agent-4"`

2.  `context_id` (String / UUID)
    *   **Description:** A unique identifier linking this message to a specific interaction, request, or session managed by THEA. This allows the recipient agent to correlate the message with prior context if needed.
    *   **Example:** `"f47ac10b-58cc-4372-a567-0e02b2c3d479"`

3.  `message_type` (String)
    *   **Description:** A standardized string indicating the nature or purpose of the message content. This helps the recipient agent route the message appropriately.
    *   **Example:** `"TASK_RESULT"`, `"STATUS_UPDATE"`, `"USER_QUERY_FORWARD"`, `"ERROR_REPORT"`
    *   *(Note: A controlled vocabulary or Enum for `message_type` should be established and maintained separately.)*

4.  `content` (Object / String / Any)
    *   **Description:** The actual payload of the message. The structure and type of this field depend entirely on the `message_type` and the specific information being conveyed.
    *   **Example (for `message_type: "TASK_RESULT"`):**
        ```json
        {
          "task_id": "TASK-123",
          "status": "COMPLETED",
          "summary": "Data processing finished.",
          "output_files": ["/path/to/result.csv"]
        }
        ```
    *   **Example (for `message_type: "USER_QUERY_FORWARD"`):**
        ```json
        {
          "query_text": "What is the current status of task DEFINE-THEA-MESSAGE-SCHEMA-001?",
          "user_id": "captain_user"
        }
        ```

## Example Message

```json
{
  "recipient_agent_id": "Agent-Logistics",
  "context_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "message_type": "INVENTORY_ALERT",
  "content": {
    "item_sku": "XYZ-001",
    "current_level": 5,
    "threshold": 10,
    "alert_level": "LOW"
  }
}
```
