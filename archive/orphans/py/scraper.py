import datetime
import json
import os
import uuid

LOG_FILE = "runtime/modules/chatgpt_scraper/scraper_log.jsonl"


def log_interaction(prompt: str, response: str, tags: list[str] = None):
    """Logs a prompt-response interaction to the JSONL file."""

    log_entry = {
        "response_id": str(uuid.uuid4()),
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "prompt": prompt,
        "response": response,
        "tags": tags if tags else [],
    }

    try:
        # Ensure directory exists (though created by prior step, good practice)
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

        with open(LOG_FILE, "a", encoding="utf-8") as f:
            json.dump(log_entry, f)
            f.write("\n")
        print(f"Successfully logged interaction {log_entry['response_id']}")
        return True, log_entry["response_id"]
    except Exception as e:
        print(f"Error logging interaction: {e}")
        # In a real scenario, might route this to Module 3's logger if it existed
        return False, None


# Directive 4: Test Input Injection
if __name__ == "__main__":
    print("Executing test input injection...")
    test_prompt = "Write a Python function to reverse a string."
    test_response = "def reverse_string(s):\n    return s[::-1]"

    success, logged_id = log_interaction(
        test_prompt, test_response, tags=["test", "python"]
    )

    if success:
        print(f"Test injection successful. Logged ID: {logged_id}")
    else:
        print("Test injection failed.")

    # Add another test case
    success2, logged_id2 = log_interaction(
        "What is the capital of France?",
        "The capital of France is Paris.",
        tags=["test", "geography"],
    )
    if success2:
        print(f"Second test injection successful. Logged ID: {logged_id2}")
    else:
        print("Second test injection failed.")
