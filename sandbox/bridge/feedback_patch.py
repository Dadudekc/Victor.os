import json
import os
from datetime import datetime, timezone
import logging
import jsonschema # Needed for schema validation/defaults

# --- Configuration ---
BRIDGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../bridge')) # Go up two levels for bridge dir
FEEDBACK_DIR = os.path.join(BRIDGE_DIR, 'outgoing_feedback')
SCHEMA_PATH = os.path.join(BRIDGE_DIR, 'schemas/cursor_feedback_schema.json')

SANDBOX_BRIDGE_DIR = os.path.abspath(os.path.dirname(__file__))
ANOMALY_LOG = os.path.join(SANDBOX_BRIDGE_DIR, 'feedback_anomaly_log.jsonl')
PATCH_LOG = os.path.join(SANDBOX_BRIDGE_DIR, 'feedback_patch_log.jsonl')

MAX_PATCHES_PER_CYCLE = 5

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FeedbackPatcher")

# --- Load Schema ---
try:
    with open(SCHEMA_PATH, 'r') as f:
        feedback_schema = json.load(f)
    logger.info(f"Successfully loaded feedback schema from {SCHEMA_PATH}")
except Exception as e:
    logger.error(f"FATAL: Could not load feedback schema from {SCHEMA_PATH}: {e}. Exiting.")
    exit(1)

# --- Helper Functions ---
def read_jsonl_data(file_path):
    """Reads a JSON Lines file into a list of dicts."""
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                try:
                    if line.strip():
                        record = json.loads(line)
                        record['_original_line'] = i # Store original line number for updating
                        data.append(record)
                except json.JSONDecodeError as e:
                    logger.error(f"Skipping invalid JSON line in {file_path} at line {i+1}: {e}")
    except FileNotFoundError:
        logger.warning(f"Log file not found: {file_path}")
    return data

def write_jsonl_data(file_path, data):
    """Writes a list of dicts back to a JSON Lines file, removing temp fields."""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            for record in data:
                record_copy = record.copy()
                record_copy.pop('_original_line', None) # Remove helper field before writing
                json.dump(record_copy, f)
                f.write('\n')
    except Exception as e:
        logger.error(f"Failed to write data to {file_path}: {e}")

def append_jsonl(file_path, record):
    """Appends a record to a JSON Lines file."""
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            json.dump(record, f)
            f.write('\n')
    except Exception as e:
        logger.error(f"Failed to append to {file_path}: {e}")

def apply_schema_defaults_and_cleanup(data: dict, schema: dict):
    """Attempts to apply schema defaults and fix common issues."""
    patched_data = data.copy()
    is_patched = False

    # Apply defaults for missing required fields
    if 'required' in schema:
        for key in schema['required']:
            if key not in patched_data:
                default_value = None
                if key == 'timestamp': default_value = datetime.now(timezone.utc).isoformat()
                elif key == 'status': default_value = 'error' # Default to error if missing
                elif key == 'result': default_value = {'message': 'Result missing, patched with default.'}
                elif key == 'request_id': default_value = 'unknown_request_id_patched'
                elif key == 'command_type': default_value = 'unknown_command_patched'
                # Add other defaults based on schema if needed
                
                if default_value is not None:
                    patched_data[key] = default_value
                    logger.info(f"Patched missing required field '{key}' with default: {default_value}")
                    is_patched = True
                else:
                     logger.warning(f"Missing required field '{key}' and no default defined.")
                     # Mark as unpatchable for now?
    
    # Validate/fix enum fields (e.g., status)
    if 'status' in patched_data and 'properties' in schema and 'status' in schema['properties']:
        status_enum = schema['properties']['status'].get('enum')
        if status_enum and patched_data['status'] not in status_enum:
            logger.warning(f"Invalid status '{patched_data['status']}'. Resetting to 'error'.")
            patched_data['status'] = 'error'
            is_patched = True
            
    # Basic syntactic cleanup (very limited)
    # Example: Ensure result is not just a plain string if object expected (crude)
    # This part is highly speculative and fragile. Real JSON repair is complex.
    # if schema.get('properties',{}).get('result',{}).get('type') == 'object' and isinstance(patched_data.get('result'), str):
    #     try:
    #         # Attempt to parse string as JSON, if fails, wrap it
    #         parsed_res = json.loads(patched_data['result'])
    #         patched_data['result'] = parsed_res
    #     except json.JSONDecodeError:
    #         logger.warning("Result is string but object expected. Wrapping in message object.")
    #         patched_data['result'] = {"message": "Original string result", "data": patched_data['result']}
    #         is_patched = True
            
    # Validate against schema - useful after patching
    try:
        jsonschema.validate(instance=patched_data, schema=schema)
        logger.info("Patched data conforms to schema.")
    except jsonschema.exceptions.ValidationError as ve:
        logger.error(f"Patched data STILL fails schema validation: {ve.message}")
        # Decide if we should still write it or mark as failed patch
        is_patched = False # Consider patch failed if validation fails
        
    return patched_data, is_patched

# --- Core Patching Logic ---
def patch_feedback_anomalies():
    logger.info("Starting feedback anomaly patching cycle...")
    anomaly_data = read_jsonl_data(ANOMALY_LOG)
    
    if not anomaly_data:
        logger.info(f"Anomaly log {ANOMALY_LOG} is empty or not found. Nothing to patch.")
        return

    patched_count = 0
    updated_anomaly_indices = set()

    for i, anomaly in enumerate(anomaly_data):
        if patched_count >= MAX_PATCHES_PER_CYCLE:
            logger.info(f"Reached max patches for this cycle ({MAX_PATCHES_PER_CYCLE}).")
            break

        if anomaly.get('patched') is True:
            # logger.debug(f"Skipping already patched anomaly: {anomaly.get('original_filename')}")
            continue
            
        # Autonomy Chain Step 6: Skip rejected by HEXMIRE (assuming a field like 'status' or 'rejected_by')
        if anomaly.get('status') == 'rejected' and anomaly.get('rejected_by') == 'HEXMIRE':
             logger.info(f"Skipping anomaly rejected by HEXMIRE: {anomaly.get('original_filename')}")
             continue

        # Autonomy Chain Step 2: Load corresponding file
        original_filename = anomaly.get('original_filename')
        if not original_filename:
            logger.error(f"Anomaly record missing 'original_filename'. Cannot process. Record: {anomaly}")
            continue
            
        feedback_filepath = os.path.join(FEEDBACK_DIR, original_filename)
        
        try:
            with open(feedback_filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # Try parsing - might fail if severely malformed
                feedback_payload = json.loads(content) 
            logger.info(f"Loaded feedback file: {original_filename}")
            
            # Autonomy Chain Step 3: Apply schema defaults and cleanup
            patched_payload, success = apply_schema_defaults_and_cleanup(feedback_payload, feedback_schema)
            
            if success:
                # Autonomy Chain Step 4: Overwrite original file
                with open(feedback_filepath, 'w', encoding='utf-8') as f:
                    json.dump(patched_payload, f, indent=2) # Write cleaned data
                logger.info(f"Overwrote original file {original_filename} with patched data.")
                
                # Mark anomaly as patched in memory
                anomaly['patched'] = True
                anomaly['patched_timestamp'] = datetime.now(timezone.utc).isoformat()
                updated_anomaly_indices.add(anomaly['_original_line']) # Track which records were modified
                patched_count += 1

                # Autonomy Chain Step 5: Append action metadata
                patch_action = {
                    "patch_timestamp": anomaly['patched_timestamp'],
                    "processed_filename": original_filename,
                    "anomaly_details": anomaly.get('error_type', 'unknown'),
                    "status": "patched"
                }
                append_jsonl(PATCH_LOG, patch_action)
            else:
                 logger.error(f"Failed to patch {original_filename}. Schema validation failed after cleanup attempts.")
                 # Optionally mark as failed patch in anomaly log?
                 # anomaly['patch_status'] = 'failed'
                 # updated_anomaly_indices.add(anomaly['_original_line'])
                 patch_action = {
                    "patch_timestamp": datetime.now(timezone.utc).isoformat(),
                    "processed_filename": original_filename,
                    "anomaly_details": anomaly.get('error_type', 'unknown'),
                    "status": "patch_failed"
                }
                 append_jsonl(PATCH_LOG, patch_action)
                 
        except FileNotFoundError:
            logger.error(f"Feedback file {original_filename} listed in anomaly log not found in {FEEDBACK_DIR}.")
            # Mark anomaly as file_not_found?
            # anomaly['patch_status'] = 'file_not_found'
            # updated_anomaly_indices.add(anomaly['_original_line'])
        except json.JSONDecodeError as e:
            logger.error(f"Could not decode JSON from {original_filename}: {e}. Cannot patch this file currently.")
            # Mark anomaly as unparseable?
            # anomaly['patch_status'] = 'unparseable'
            # updated_anomaly_indices.add(anomaly['_original_line'])
        except Exception as e:
            logger.error(f"Unexpected error processing {original_filename}: {e}", exc_info=True)
            # Mark anomaly as error?
            # anomaly['patch_status'] = 'processing_error'
            # updated_anomaly_indices.add(anomaly['_original_line'])

    # Update the anomaly log file if changes were made
    if updated_anomaly_indices:
        logger.info(f"Updating anomaly log {ANOMALY_LOG} with patch statuses.")
        # Reconstruct the list based on original line numbers to maintain order
        updated_data = [None] * (max(updated_anomaly_indices) + 1)
        processed_lines = set()
        for record in anomaly_data:
            line_num = record['_original_line']
            if line_num in updated_anomaly_indices:
                 updated_data[line_num] = record
                 processed_lines.add(line_num)
        # Fill in unchanged lines
        current_index = 0
        for record in anomaly_data:
             line_num = record['_original_line']
             if line_num not in processed_lines:
                 while updated_data[current_index] is not None:
                     current_index += 1
                 if current_index < len(updated_data):
                     updated_data[current_index] = record
                 else: # Should not happen if logic is correct
                      logger.error("Index mismatch while reconstructing anomaly log - potential data loss.")
                      updated_data.append(record) # Append at end as fallback
                 current_index += 1
        
        # Filter out None placeholders if any gaps existed
        final_data = [rec for rec in updated_data if rec is not None]
        write_jsonl_data(ANOMALY_LOG, final_data)

    logger.info(f"Patching cycle complete. Patched {patched_count} anomalies.")

# --- Main Execution ---
if __name__ == "__main__":
    # Create mock anomaly log if it doesn't exist
    if not os.path.exists(ANOMALY_LOG):
        logger.warning(f"Creating mock anomaly log file: {ANOMALY_LOG}")
        mock_anomalies = [
            {"original_filename": "feedback_malformed_test_001.json", "error_type": "Missing Timestamp", "details": "timestamp field absent", "patched": False},
            {"original_filename": "feedback_malformed_test_002.json", "error_type": "Invalid Status", "details": "status field was 'PENDING'", "patched": False},
            {"original_filename": "feedback_already_patched_003.json", "error_type": "N/A", "details": "Previously patched example", "patched": True},
            {"original_filename": "feedback_rejected_hexmire_004.json", "error_type": "Validation Failed", "details": "Schema validation failed structurally", "status": "rejected", "rejected_by": "HEXMIRE", "patched": False},
            {"original_filename": "feedback_needs_patch_005.json", "error_type": "Missing Result", "details": "result field absent", "patched": False},
            {"original_filename": "feedback_needs_patch_006.json", "error_type": "Missing Request ID", "details": "request_id absent", "patched": False} # Example for >5 limit
        ]
        # Also create corresponding mock feedback files
        os.makedirs(FEEDBACK_DIR, exist_ok=True)
        with open(os.path.join(FEEDBACK_DIR, "feedback_malformed_test_001.json"), 'w') as f: json.dump({"request_id": "req-001", "command_type": "list_dir", "status": "success", "result": {}}, f)
        with open(os.path.join(FEEDBACK_DIR, "feedback_malformed_test_002.json"), 'w') as f: json.dump({"request_id": "req-002", "timestamp": datetime.now(timezone.utc).isoformat(), "command_type": "read_file", "status": "PENDING", "result": {}}, f)
        with open(os.path.join(FEEDBACK_DIR, "feedback_already_patched_003.json"), 'w') as f: json.dump({"request_id": "req-003", "timestamp": datetime.now(timezone.utc).isoformat(), "command_type": "edit_file", "status": "success", "result": {}}, f)
        with open(os.path.join(FEEDBACK_DIR, "feedback_rejected_hexmire_004.json"), 'w') as f: json.dump({"request_id": "req-004", "timestamp": datetime.now(timezone.utc).isoformat(), "command_type": "run_terminal", "status": "error", "result": {}}, f)
        with open(os.path.join(FEEDBACK_DIR, "feedback_needs_patch_005.json"), 'w') as f: json.dump({"request_id": "req-005", "timestamp": datetime.now(timezone.utc).isoformat(), "command_type": "grep_search", "status": "success" }, f)
        with open(os.path.join(FEEDBACK_DIR, "feedback_needs_patch_006.json"), 'w') as f: json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "command_type": "file_search", "status": "success", "result": {}}, f)
        
        write_jsonl_data(ANOMALY_LOG, mock_anomalies)
        logger.info("Mock anomaly log and corresponding feedback files created.")
        
    patch_feedback_anomalies() 