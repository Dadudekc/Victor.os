#!/bin/bash
# Dream.OS Daily Verification Script
# This script runs the verification suite and logs the results

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
LOG_DIR="logs/verification/daily"
LOG_FILE="$LOG_DIR/verification_$TIMESTAMP.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

echo "Running Dream.OS verification suite..."
echo "Timestamp: $TIMESTAMP"
echo "Log file: $LOG_FILE"
echo

# Run verification
python -m src.dreamos.testing.run_verification --markdown --html > "$LOG_FILE" 2>&1

# Check the result
if grep -q "Overall Status: PASS" "$LOG_FILE"; then
    echo "Verification PASSED"
    exit 0
else
    echo "Verification FAILED"
    cat "$LOG_FILE"
    exit 1
fi 