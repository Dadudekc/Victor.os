import logging
import threading
import time

logger = logging.getLogger("PromptExecutor")
logger.setLevel(logging.INFO)


class PromptExecutionService:
    """
    PromptExecutionService handles sending prompts and retrieving responses.
    It manages execution cycles for single chats or cycles across multiple prompts.
    Now supports model switching, feedback integration, and parallel execution.
    """

    def __init__(
        self,
        driver_manager,
        prompt_manager,
        feedback_engine=None,
        model="gpt-4o-mini",
        cycle_speed=2,
        stable_wait=10,
    ):
        self.driver_manager = driver_manager
        self.prompt_manager = prompt_manager
        self.feedback_engine = feedback_engine
        self.cycle_speed = cycle_speed  # Delay between prompts in sequence
        self.stable_wait = stable_wait  # Default wait time for stable response
        self.driver = self.driver_manager.driver
        self.model = model

    # ----------------------------------------
    # PROMPT MANAGEMENT
    # ----------------------------------------

    def get_prompt(self, prompt_name: str) -> str:
        """
        Retrieve a prompt text from the prompt manager.
        """
        logger.info(f"🔍 Retrieving prompt: {prompt_name}")
        return self.prompt_manager.get_prompt(prompt_name)

    # ----------------------------------------
    # MAIN EXECUTION
    # ----------------------------------------

    def execute_prompt_cycle(self, prompt_text: str, chat_context: dict = None) -> str:
        """
        Sends a prompt to an active chat, waits for a response, and returns the result.
        Adapts behavior depending on the model in use.
        Accepts an optional chat_context dictionary with metadata from the scraper.
        """
        logger.info(f"🚀 Executing prompt cycle using model '{self.model}'...")

        original_prompt_text = (
            prompt_text  # Preserve original for logging or comparison
        )

        if chat_context:
            logger.info(f"🗒️ Received chat context: {chat_context}")
            context_strings = []
            # Add title if available and seems useful (e.g., for disambiguation)
            # title = chat_context.get("title")
            # if title:
            #     context_strings.append(f"Chat Title: \"{title}\"")

            last_active = chat_context.get("last_active_time")
            if last_active:
                context_strings.append(f"Last Active: {last_active}")

            snippet = chat_context.get("snippet")
            if snippet:
                # Potentially truncate snippet if too long
                max_snippet_len = 150  # Configurable?
                truncated_snippet = (
                    snippet[:max_snippet_len] + "..."
                    if len(snippet) > max_snippet_len
                    else snippet
                )
                context_strings.append(f'Previous Snippet: "{truncated_snippet}"')

            if context_strings:
                # Construct a clear, well-formatted context prefix
                context_prefix = "[Chat Context Summary]\n"
                for item in context_strings:
                    context_prefix += f"- {item}\n"
                context_prefix += "[End Context Summary]\n\n"

                prompt_text = context_prefix + original_prompt_text
                logger.info(
                    f"INFO: Augmented prompt with context. Original prompt start: '{original_prompt_text[:100]}...', New prompt start: '{prompt_text[:250]}...'"
                )
            else:
                logger.info(
                    "INFO: Chat context provided, but no fields (snippet, last_active_time) deemed suitable for direct prompt augmentation in this cycle."
                )
        else:
            logger.info(
                "🗒️ No chat context provided for this cycle, using original prompt."
            )

        # Send the prompt
        self._send_prompt(prompt_text)

        # Wait for response stabilization (model-specific)
        wait_time = self._determine_wait_time()
        logger.info(f"⏳ Waiting {wait_time} seconds for response stabilization...")
        time.sleep(wait_time)

        # Retrieve the response from chat
        response = self._fetch_response()

        # Model-specific post processing
        if response and "jawbone" in self.model:
            response = self._post_process_jawbone_response(response)

        # Log and return
        if not response:
            logger.warning("⚠️ No response detected after sending prompt.")
        else:
            logger.info(f"✅ Response received. Length: {len(response)} characters.")

        # Direct feedback loop (optional)
        if self.feedback_engine:
            # Pass chat_context to FeedbackEngine
            memory_update = self.feedback_engine.parse_and_update_memory(
                response,
                chat_context=chat_context,  # Pass the context here
            )
            if memory_update:
                logger.info(f"🧠 Memory updated: {memory_update}")

        return response

    def execute_prompts_single_chat(
        self, prompt_list: list, chat_context: dict = None
    ) -> list:
        """
        Executes a list of prompts in sequence on a single chat.
        Returns a list of responses.
        Accepts an optional chat_context dictionary (passed to each prompt cycle).
        """
        logger.info(
            f"🔁 Starting sequential prompt execution on a single chat ({len(prompt_list)} prompts)..."
        )
        if chat_context:
            logger.info(f"🗒️ Using base chat context for sequence: {chat_context}")

        responses = []

        for prompt_name in prompt_list:
            prompt_text = self.get_prompt(prompt_name)

            logger.info(f"📝 Sending prompt: {prompt_name}")
            # Pass chat_context to each prompt execution
            response = self.execute_prompt_cycle(prompt_text, chat_context=chat_context)

            responses.append({"prompt_name": prompt_name, "response": response})

            time.sleep(self.cycle_speed)

        logger.info("🎉 Sequential prompt cycle complete.")
        return responses

    def execute_prompts_concurrently(self, chat_link, prompt_list):
        """
        Launch prompt execution threads for a single chat (one thread per prompt).
        """
        logger.info(
            f"🚀 Executing {len(prompt_list)} prompts concurrently on chat: {chat_link}"
        )

        threads = []

        # Load chat in the browser before launching prompts
        self.driver_manager.load_chat(chat_link)
        time.sleep(2)

        for prompt_name in prompt_list:
            thread = threading.Thread(
                target=self._execute_single_prompt_thread, args=(chat_link, prompt_name)
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        logger.info("✅ All prompt executions completed concurrently.")

    # ----------------------------------------
    # THREAD EXECUTION FOR SINGLE PROMPT
    # ----------------------------------------

    def _execute_single_prompt_thread(
        self, chat_link, prompt_name, chat_context: dict = None
    ):
        """
        Executes a single prompt in its own thread.
        Accepts an optional chat_context dictionary.
        """
        logger.info(f"📝 [Thread] Executing prompt '{prompt_name}' on chat {chat_link}")
        if chat_context:
            logger.info(f"🗒️ [Thread] Received chat context: {chat_context}")

        prompt_text = self.get_prompt(prompt_name)
        response = self.execute_prompt_cycle(
            prompt_text, chat_context=chat_context
        )  # Pass context here too

        if not response:
            logger.warning(
                f"⚠️ [Thread] No response for prompt '{prompt_name}' on chat {chat_link}"
            )
            return

        # Feedback integration (if feedback engine provided)
        if self.feedback_engine:
            # Pass chat_context to FeedbackEngine
            memory_update = self.feedback_engine.parse_and_update_memory(
                response,
                chat_context=chat_context,  # Pass context here too
            )
            if memory_update:
                logger.info(f"🧠 [Thread] Memory updated: {memory_update}")

        logger.info(f"✅ [Thread] Completed prompt '{prompt_name}' on chat {chat_link}")

    # ----------------------------------------
    # MODEL BEHAVIOR HANDLING
    # ----------------------------------------

    def _determine_wait_time(self):
        """
        Adjust wait time dynamically based on model.
        """
        if "mini" in self.model:
            return 5
        elif "jawbone" in self.model:
            return 15
        else:
            return self.stable_wait

    def _post_process_jawbone_response(self, response: str) -> str:
        """
        Post-process Jawbone model responses if needed.
        """
        logger.info("🔧 Post-processing Jawbone response...")
        cleaned_response = response.replace("[Start]", "").replace("[End]", "").strip()
        return cleaned_response

    # ----------------------------------------
    # INTERNAL HELPERS
    # ----------------------------------------

    def _send_prompt(self, prompt_text: str):
        """
        Sends a prompt to the active chat input field.
        """
        logger.info("💬 Locating input field to send prompt...")
        logger.debug(
            f"Attempting to send prompt text: {prompt_text[:500]}... (potentially augmented)"
        )

        try:
            # Locate the input text area
            input_box = self.driver.find_element(
                "xpath", "//textarea[@data-id='root-textarea']"
            )
            input_box.clear()
            input_box.send_keys(prompt_text)
            time.sleep(1)  # Optional delay to simulate typing

            # Locate and click the send button
            send_button = self.driver.find_element(
                "xpath", "//button[@data-testid='send-button']"
            )
            send_button.click()

            logger.info("✅ Prompt sent successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to send prompt: {e}")

    def _fetch_response(self) -> str:
        """
        Retrieves the latest assistant response from the chat window.
        """
        logger.info("🔍 Fetching latest response from chat...")

        try:
            # Find all message elements, select the last one
            messages = self.driver.find_elements(
                "xpath",
                "//div[contains(@class, 'prose') and not(contains(@class, 'markdown'))]",  # noqa: E501
            )
            if not messages:
                logger.warning("⚠️ No messages found.")
                return ""

            latest_message = messages[-1]
            response_text = latest_message.text

            logger.info(f"📝 Retrieved response: {response_text[:75]}...")
            return response_text

        except Exception as e:
            logger.error(f"❌ Failed to fetch response: {e}")
            return ""

    # Renaming this to match what ChatCycleController calls, and adding context
    def send_prompt_and_wait(self, prompt_text: str, chat_context: dict = None) -> str:
        """
        Public wrapper for execute_prompt_cycle.
        This is the method intended to be called by external orchestrators like ChatCycleController.
        Accepts an optional chat_context dictionary.
        """
        # This method primarily calls execute_prompt_cycle, passing through the context.
        # Actual sending logic is within execute_prompt_cycle and its private methods.
        return self.execute_prompt_cycle(prompt_text, chat_context=chat_context)
