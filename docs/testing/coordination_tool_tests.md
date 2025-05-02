# Test Cases for Core Coordination Tools

**Version:** 1.0
**Date:** [AUTO_DATE]
**Author:** Agent 1

**Related Task:** `DEFINE-COORD-TESTS-001` (Supersedes blocked task `c5e8a3f9-1a0b-4d7e-8c1a-f0b1d2e3c4d5`)

## Overview

This document outlines test cases for the core coordination mechanisms currently observed in the Dream.OS system, focusing on task board management and inter-agent communication via mailboxes.

## 1. ProjectBoardManager (`src/dreamos/coordination/project_board_manager.py`)

### 1.1 `claim_future_task(task_id, agent_id)`

*   **Test Case 1.1.1 (Success):**
    *   **Setup:** Ensure `task_id` exists in `future_tasks.json` and not in `working_tasks.json`.
    *   **Action:** Call `claim_future_task` with valid `task_id` and `agent_id`.
    *   **Expected:** Returns `True`. Task removed from `future_tasks.json`. Task added to `working_tasks.json` with status `WORKING`, correct `assigned_agent`, and `timestamp_claimed_utc`.
*   **Test Case 1.1.2 (Failure - Not Found):**
    *   **Setup:** Ensure `task_id` does NOT exist in `future_tasks.json`.
    *   **Action:** Call `claim_future_task`.
    *   **Expected:** Returns `False`. Logs warning. `future_tasks.json` and `working_tasks.json` remain unchanged.
*   **Test Case 1.1.3 (Failure - Already Working):**
    *   **Setup:** Ensure `task_id` exists in `working_tasks.json`.
    *   **Action:** Call `claim_future_task`.
    *   **Expected:** Returns `False` (as it won't be found in `future_tasks.json`). Logs warning.
*   **Test Case 1.1.4 (Failure - Invalid Format):**
    *   **Setup:** Corrupt `future_tasks.json` (e.g., make it not a list).
    *   **Action:** Call `claim_future_task`.
    *   **Expected:** Returns `False`. Logs error about invalid format. Does not modify `working_tasks.json`.
*   **Test Case 1.1.5 (Concurrency - Conceptual):**
    *   **Setup:** Simulate two agents calling `claim_future_task` for the *same* `task_id` concurrently.
    *   **Expected:** Only one agent successfully claims the task (returns `True`, files updated correctly). The other agent fails (returns `False`). Requires nested file locks to function correctly.

### 1.2 `update_working_task(task_id, updates)`

*   **Test Case 1.2.1 (Success - Status Update):**
    *   **Setup:** Ensure `task_id` exists in `working_tasks.json`.
    *   **Action:** Call `update_working_task` with `updates = {'status': 'IN_PROGRESS'}`.
    *   **Expected:** Returns `True`. Task in `working_tasks.json` has status updated to `IN_PROGRESS` and `timestamp_updated` field updated.
*   **Test Case 1.2.2 (Success - Notes Update):**
    *   **Setup:** Ensure `task_id` exists in `working_tasks.json`.
    *   **Action:** Call `update_working_task` with `updates = {'notes': 'New note here'}`.
    *   **Expected:** Returns `True`. Task in `working_tasks.json` has `notes` field added/updated and `timestamp_updated` field updated.
*   **Test Case 1.2.3 (Failure - Not Found):**
    *   **Setup:** Ensure `task_id` does NOT exist in `working_tasks.json`.
    *   **Action:** Call `update_working_task`.
    *   **Expected:** Returns `False`. Logs warning. `working_tasks.json` remains unchanged.

### 1.3 `move_task_to_completed(task_id, final_updates)`

*   **Test Case 1.3.1 (Success):**
    *   **Setup:** Ensure `task_id` exists in `working_tasks.json`. Initialize `completed_tasks.json` (e.g., empty list).
    *   **Action:** Call `move_task_to_completed` with `final_updates = {'status': 'COMPLETED', 'notes': 'Final notes'}`.
    *   **Expected:** Returns `True`. Task removed from `working_tasks.json`. Task added to `completed_tasks.json` with status `COMPLETED`, updated `notes`, and updated `timestamp_updated` / `timestamp_completed`.
*   **Test Case 1.3.2 (Failure - Not Found):**
    *   **Setup:** Ensure `task_id` does NOT exist in `working_tasks.json`.
    *   **Action:** Call `move_task_to_completed`.
    *   **Expected:** Returns `False`. Logs warning. `working_tasks.json` and `completed_tasks.json` remain unchanged.
*   **Test Case 1.3.3 (Concurrency - Conceptual):**
    *   **Setup:** Simulate one agent calling `update_working_task` and another calling `move_task_to_completed` for the *same* `task_id` concurrently.
    *   **Expected:** Operations are serialized due to locks. One operation completes fully before the other starts. The final state depends on execution order, but the files should remain valid JSON. Requires nested file locks.

## 2. Mailbox Communication (`runtime/agent_comms/agent_mailboxes/`)

*   **Test Case 2.1 (Send Valid JSON):**
    *   **Setup:** Agent A prepares a valid JSON message string adhering to the defined schema.
    *   **Action:** Agent A writes the message to `AgentB/inbox/message_id.json`.
    *   **Expected:** File is created successfully with correct content.
*   **Test Case 2.2 (Receive Valid JSON):**
    *   **Setup:** A valid JSON message file exists in `AgentB/inbox/`.
    *   **Action:** Agent B lists its inbox, reads the file, parses the JSON.
    *   **Expected:** File read successfully. JSON parsing successful. Message content matches expected schema.
*   **Test Case 2.3 (Handle Non-JSON):**
    *   **Setup:** A non-JSON file (e.g., plain text) exists in `AgentB/inbox/`.
    *   **Action:** Agent B lists inbox and attempts to read/process the file as JSON.
    *   **Expected:** Agent B logs an error/warning about the invalid format, skips processing the file (or moves it to an error folder), and continues processing other valid messages. Does not crash.
*   **Test Case 2.4 (Schema Validation):**
    *   **Setup:** A JSON message file exists in `AgentB/inbox/` but is missing a required field (e.g., `sender_agent_id`).
    *   **Action:** Agent B reads and validates the message against the expected schema (requires a validation utility).
    *   **Expected:** Validation fails. Agent logs error/warning, skips processing (or moves to error folder).

## 3. Task Management CLI (`src/dreamos/cli/manage_tasks.py`)

*   **Test Case 3.1 (Claim - Success):**
    *   **Setup:** Task `T1` exists in `future_tasks.json`.
    *   **Action:** Run `python manage_tasks.py claim T1 Agent1`.
    *   **Expected:** Script exits 0. Logs success. Task `T1` moved to `working_tasks.json`, assigned to `Agent1`.
*   **Test Case 3.2 (Claim - Failure - Not Found):**
    *   **Setup:** Task `T_NotFound` does not exist in `future_tasks.json`.
    *   **Action:** Run `python manage_tasks.py claim T_NotFound Agent1`.
    *   **Expected:** Script exits non-zero. Logs error (task not found).
*   **Test Case 3.3 (Update Working - Success):**
    *   **Setup:** Task `T1` exists in `working_tasks.json`.
    *   **Action:** Run `python manage_tasks.py update T1 IN_PROGRESS --notes "Making progress"`.
    *   **Expected:** Script exits 0. Logs success. Task `T1` in `working_tasks.json` updated with status `IN_PROGRESS` and new notes.
*   **Test Case 3.4 (Update Completed - Success):**
    *   **Setup:** Task `T1` exists in `working_tasks.json`.
    *   **Action:** Run `python manage_tasks.py update T1 COMPLETED --notes "All done"`.
    *   **Expected:** Script exits 0. Logs success (task moved). Task `T1` removed from `working_tasks.json` and added to `completed_tasks.json` with status `COMPLETED` and notes.
*   **Test Case 3.5 (Update - Failure - Not Found):**
    *   **Setup:** Task `T_NotFound` does not exist in `working_tasks.json`.
    *   **Action:** Run `python manage_tasks.py update T_NotFound FAILED`.
    *   **Expected:** Script exits non-zero. Logs error (task not found).
*   **Test Case 3.6 (Invalid Action):**
    *   **Action:** Run `python manage_tasks.py invalid_action T1 ...`.
    *   **Expected:** Script exits non-zero. Shows argparse error about invalid choice.
*   **Test Case 3.7 (Missing Args - Claim):**
    *   **Action:** Run `python manage_tasks.py claim T1`.
    *   **Expected:** Script exits non-zero. Shows argparse error about missing `agent_id`.
*   **Test Case 3.8 (Missing Args - Update):**
    *   **Action:** Run `python manage_tasks.py update T1`.
    *   **Expected:** Script exits non-zero. Shows argparse error about missing `status`.
