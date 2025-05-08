import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any

# Setup logger
logger = logging.getLogger("FeedbackEngine")
logger.setLevel(logging.INFO)


class FeedbackEngine:
    """
    FeedbackEngine - Parses AI responses, updates persistent memory,
    tracks reinforcement loops, and evolves Victor.OS intelligence.
    """

    def __init__(
        self,
        memory_file: str = "memory/persistent_memory.json",
        feedback_log_file: str = "memory/feedback_log.json",
    ):
        self.memory_file = memory_file
        self.feedback_log_file = feedback_log_file
        self.memory_state = {}
        self.feedback_log = []
        self.context_memory = {
            "recent_responses": [],
            "user_profiles": {},
            "platform_memories": {},
        }

        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=2)

        logger.info(
            f"🧠 FeedbackEngine initializing with memory file: {self.memory_file}"
        )
        self._load_memory()

    # ---------------------------------------------------
    # MEMORY MANAGEMENT
    # ---------------------------------------------------
    def _load_memory(self):
        """Load persistent memory state from file."""
        if not os.path.exists(self.memory_file):
            logger.warning(
                f"⚠️ No memory file found at {self.memory_file}. Starting with empty memory state."  # noqa: E501
            )
            self.memory_state = {}
            return

        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                self.memory_state = json.load(f)  # noqa: F821
            logger.info(f"✅ Memory loaded from {self.memory_file}")
        except Exception as e:
            logger.exception(f"❌ Failed to load memory: {e}")
            self.memory_state = {}

    def _save_memory(self):
        """Save current memory state to file."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
                with open(self.memory_file, "w", encoding="utf-8") as f:
                    json.dump(self.memory_state, f, indent=4, ensure_ascii=False)  # noqa: F821
                logger.info(f"💾 Memory saved to {self.memory_file}")
            except Exception as e:
                logger.exception(f"❌ Failed to save memory: {e}")

    def save_memory_async(self):
        """Async save operation."""
        self._executor.submit(self._save_memory)

    # ---------------------------------------------------
    # MEMORY UPDATE HANDLER
    # ---------------------------------------------------
    def parse_and_update_memory(self, ai_response: str, chat_context: dict = None):
        """
        Parse MEMORY_UPDATE block from AI response and apply updates.
        Expects block in JSON format after a label like MEMORY_UPDATE.
        Now accepts optional chat_context.
        """
        logger.info("🔍 Parsing AI response for MEMORY_UPDATE block...")
        if chat_context:
            logger.info(f"🗒️ Received chat context for memory update: {chat_context}")

        if "MEMORY_UPDATE" not in ai_response:
            logger.warning("⚠️ No MEMORY_UPDATE block found in response.")
            return

        try:
            memory_block = ai_response.split("MEMORY_UPDATE")[-1].strip()
            json_block = memory_block[
                memory_block.find("{") : memory_block.rfind("}") + 1
            ]

            updates = json.loads(json_block)  # noqa: F821
            logger.info(f"✅ Parsed MEMORY_UPDATE: {updates}")

            # Pass context along to apply_memory_updates
            self.apply_memory_updates(updates, chat_context=chat_context)

        except Exception as e:
            logger.exception(f"❌ Failed to parse MEMORY_UPDATE block: {e}")

    def apply_memory_updates(self, updates: dict, chat_context: dict = None):
        """
        Apply structured updates to memory state.
        Supports list and scalar values.
        If chat_context is provided, stores it under _last_update_context.
        """
        logger.info(f"🧬 Applying memory updates: {updates}")
        with self._lock:
            for key, value in updates.items():
                if isinstance(value, list):
                    self.memory_state.setdefault(key, [])
                    for item in value:
                        if item not in self.memory_state[key]:
                            self.memory_state[key].append(item)
                else:
                    self.memory_state[key] = value
            
            # Store context associated with this update batch (Option A)
            if chat_context:
                 # Store context associated with this batch of updates
                 # Decide which fields are most valuable (e.g., link, time, maybe title)
                 context_to_store = {
                     field: chat_context.get(field)
                     for field in ["link", "last_active_time", "title"] 
                     if chat_context.get(field) is not None
                 }
                 if context_to_store: # Only add if we have something valuable
                    self.memory_state['_last_update_context'] = {
                        'timestamp': datetime.now().isoformat(),
                        'context': context_to_store
                    } 
                    logger.info(f"Stored update context: {context_to_store}")
                 else:
                    logger.info("Chat context provided, but no key fields found to store.")
            else:
                # Optional: Clear last context if none provided for this update?
                # if '_last_update_context' in self.memory_state:
                #    del self.memory_state['_last_update_context']
                pass # No context provided

            logger.info("✅ Memory state updated.")
        self.save_memory_async()

    # ---------------------------------------------------
    # FEEDBACK LOOP TRACKING
    # ---------------------------------------------------
    def log_feedback(
        self, prompt_name: str, score: float, hallucination: bool, notes: str = ""
    ):
        """
        Logs reinforcement learning feedback per prompt execution.
        """
        feedback_entry = {
            "timestamp": datetime.now().isoformat(),
            "prompt_name": prompt_name,
            "score": score,
            "hallucination": hallucination,
            "notes": notes,
        }

        logger.info(f"📝 Logging feedback: {feedback_entry}")

        with self._lock:
            self.feedback_log.append(feedback_entry)

    def export_feedback_log(self):
        """Exports feedback log to a JSON file."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.feedback_log_file), exist_ok=True)
                with open(self.feedback_log_file, "w", encoding="utf-8") as f:
                    json.dump(self.feedback_log, f, indent=4, ensure_ascii=False)  # noqa: F821
                logger.info(f"📤 Feedback log exported to {self.feedback_log_file}")
            except Exception as e:
                logger.exception(f"❌ Failed to export feedback log: {e}")

    # ---------------------------------------------------
    # REINFORCEMENT LEARNING (Optional Expansion)
    # ---------------------------------------------------
    def analyze_feedback(self):
        """
        Analyze feedback log for learning patterns.
        Returns prompts to review or suggestions.
        """
        logger.info("🔎 Analyzing feedback logs for insights...")

        low_score_threshold = 0.5
        problem_prompts = [
            f["prompt_name"]
            for f in self.feedback_log
            if f["score"] < low_score_threshold or f["hallucination"]
        ]

        if problem_prompts:
            logger.warning(f"⚠️ Prompts needing review: {problem_prompts}")
        else:
            logger.info("✅ No major issues detected in feedback.")

        return problem_prompts

    # ---------------------------------------------------
    # REVIEW CURRENT MEMORY
    # ---------------------------------------------------
    def review_memory(self):
        """Returns current memory state."""
        logger.info("📖 Reviewing memory state:")
        for key, value in self.memory_state.items():
            logger.info(f"{key}: {value}")

        return self.memory_state

    # ---------------------------------------------------
    # CONTEXTUAL FEEDBACK LOOP MANAGEMENT
    # ---------------------------------------------------
    def feedback_loop(self, new_entry: Dict[str, Any]):  # noqa: F821
        """
        Updates internal contextual memory with a new interaction.
        Includes user profiles, platform-specific memories, and recent responses.
        """
        logger.info(
            f"🔁 Feedback loop processing new entry for user {new_entry.get('user', 'unknown')}..."  # noqa: E501
        )

        user = new_entry.get("user", "unknown")
        platform = new_entry.get("platform", "general")
        ai_output = new_entry.get("ai_output", "")

        with self._lock:
            # Update recent responses
            self.context_memory["recent_responses"].append(new_entry)

            # Update user profiles
            if user != "unknown":
                profile = self.context_memory["user_profiles"].setdefault(
                    user, {"last_interactions": []}
                )
                profile["last_interactions"].append(new_entry)

            # Update platform memories
            self.context_memory["platform_memories"].setdefault(platform, []).append(
                ai_output
            )

        logger.info(f"✅ Feedback loop updated for {user}.")
        self.save_context_memory_async()

    def save_context_memory_async(self):
        """Async save for contextual memory (optional)."""
        self._executor.submit(self.save_context_db)

    def save_context_db(self, context_file: str = "memory/context_memory.json"):
        """Save contextual memory database."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(context_file), exist_ok=True)
                with open(context_file, "w", encoding="utf-8") as f:
                    json.dump(self.context_memory, f, indent=4, ensure_ascii=False)  # noqa: F821
                logger.info(f"💾 Context memory saved to {context_file}")
            except Exception as e:
                logger.exception(f"❌ Failed to save context memory: {e}")

    def review_context_memory(self):
        """Review context memory structure."""
        logger.info("📖 Reviewing context memory:")
        for section, entries in self.context_memory.items():
            logger.info(f"{section}: {len(entries)} entries")
        return self.context_memory
