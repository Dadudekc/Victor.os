"""
Core Identity & Voice Engine for Dream.OS communications.

Codename: VictorVoiceEngine
Purpose: Enforces persona (tone, cadence, values, syntax, intent)
         across all AI-generated communication.
"""

import logging
from typing import Optional, Dict, Any, List

# Attempt to import AIChatAgent. Adjust path as necessary based on final project structure.
# This assumes AIChatAgent might live in social/ or a shared core/ location.
# For now, let's assume it's findable via standard paths or PYTHONPATH.
# If this fails, the import needs to be corrected based on AIChatAgent's location.
try:
    # Example: Adjust if AIChatAgent is moved to core or elsewhere
    # from core.ai_chat_agent import AIChatAgent
    from social.utils.ai_chat_agent import AIChatAgent # Using path from previous context
except ImportError as e:
    logging.error(f"Failed to import AIChatAgent. Ensure it's available in the path. Error: {e}")
    # Define a dummy class to allow scaffolding to proceed, but it will fail at runtime.
    class AIChatAgent:
        def __init__(self, *args, **kwargs):
             logging.warning("Using DUMMY AIChatAgent class due to import error.")
        def ask(self, *args, **kwargs) -> str:
             return "ERROR: AIChatAgent could not be imported."

logger = logging.getLogger(__name__)

class VictorVoiceEngine:
    """Unified voice engine to generate persona-aligned text."""

    def __init__(self, persona: str = "victor", tone: str = "default", temperature: float = 0.7):
        """Initializes the voice engine.

        Args:
            persona: The core persona identifier (e.g., "victor", "aria").
            tone: The specific tone to use (e.g., "default", "strategic").
            temperature: The generation temperature for the LLM.
        """
        self.persona = persona
        self.tone = tone
        self.temperature = temperature
        # Instantiate the underlying chat agent, passing necessary config
        # Assuming AIChatAgent is updated or compatible with agent_id usage if needed
        self.chat_agent = AIChatAgent(
            # agent_id=f"{self.persona}-{self.tone}-voice", # Consider if AIChatAgent needs an ID
            temperature=self.temperature
            # Pass model/provider if needed, or let AIChatAgent use defaults
        )
        logger.info(f"VictorVoiceEngine initialized for persona '{self.persona}', tone '{self.tone}'.")

    def speak(self, message_log: List[Dict[str, str]], tags: Optional[List[str]] = None, meta: Optional[Dict[str, Any]] = None) -> str:
        """
        Takes a message context (log) and generates a persona-aligned response.

        Args:
            message_log: A list of message dictionaries, typically alternating
                         roles like [{"role": "user", "content": "..."}, ...].
                         The system prompt will be prepended.
            tags: Optional list of tags to influence tone directives.
            meta: Optional metadata dictionary for context.

        Returns:
            The generated response string, or an error message.
        """
        try:
            # Inject the persona system prompt
            full_message_log_with_system = self._inject_persona_context(message_log, tags, meta)

            # Format the full message log for AIChatAgent.ask (which expects a single prompt string)
            # This simple concatenation might need refinement for complex conversation histories.
            prompt_str = ""
            for msg in full_message_log_with_system:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Simple formatting; adjust if needed for specific LLM expectations
                prompt_str += f"{role.upper()}:\n{content}\n\n"

            logger.debug(f"Generating prompt string: \n{prompt_str[:500]}...") # Log start of prompt

            # Use AIChatAgent's ask method
            response = self.chat_agent.ask(prompt=prompt_str.strip(), metadata=meta)

            if response:
                logger.info(f"VictorVoiceEngine generated response (Persona: {self.persona}, Tone: {self.tone})")
                return response
            else:
                logger.error("VictorVoiceEngine received empty response from AIChatAgent.")
                return "[VictorVoiceEngine Error: No response generated]"

        except Exception as e:
            logger.exception(f"Error during VictorVoiceEngine.speak: {e}")
            return f"[VictorVoiceEngine Error: {e}]"

    def _inject_persona_context(self, messages: List[Dict[str, str]], tags: Optional[List[str]] = None, meta: Optional[Dict[str, Any]]= None) -> List[Dict[str, str]]:
        """Prepends persona + tone system messages before submitting to the LLM."""
        tone_directives = self._get_tone_directives(tags)

        # Base persona prompt (adjust as needed)
        # TODO: Potentially load persona/tone prompts from files in /core/personas/ /core/tones/
        system_prompt = f"""
You are Victor's core voice identity. Embody strategic thinking, systems awareness, and decisive action. Your communication style is:
- **Precise:** Clear, concise, impactful.
- **Strategic:** Always considers the broader context and goals.
- **Convergent:** Focuses on integrating systems and ideas.
- **Dominant:** Assured, confident, avoids filler and hedging.
Respond according to the current tone directives.
{tone_directives}
""".strip()

        # Prepend the system prompt to the message list
        return [{'role': 'system', 'content': system_prompt}] + messages

    def _get_tone_directives(self, tags: Optional[List[str]] = None) -> str:
        """Returns specific tone guidance based on current setting or tags."""
        # More sophisticated logic could use tags or state
        current_tone = self.tone # Or determine from tags/meta

        # TODO: Load these from /core/tones/ perhaps
        if current_tone == "default":
            return "Tone: Default - Bold, decisive, systems-aware."
        elif current_tone == "strategic":
             return "Tone: Strategic - Focus on long-term implications, leverage points, and efficiency."
        elif current_tone == "networking":
            return "Tone: Networking - Speak with warm authority and clear vision. Offer connection and value."
        elif current_tone == "battle": # Example
            return "Tone: Battle - Cut through noise. Minimal words. Maximum impact. All signal, no static."
        elif current_tone == "introspective": # Example
             return "Tone: Introspective - Analyze underlying patterns, motivations, and potential optimizations."
        else:
             logger.warning(f"Unknown tone '{current_tone}', using default directives.")
             return "Tone: Default - Bold, decisive, systems-aware."

# Example usage (if run directly for testing)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("--- Testing VictorVoiceEngine --- ")

    # Requires AIChatAgent and its dependencies (e.g., social_config) to be available
    try:
        engine_default = VictorVoiceEngine(persona="victor", tone="default")
        engine_strategic = VictorVoiceEngine(persona="victor", tone="strategic")

        test_log = [
            {"role": "user", "content": "What is the primary goal of Dream.OS?"}
        ]

        print("\nTesting Default Tone:")
        response_default = engine_default.speak(test_log)
        print(f"Response:\n{response_default}")

        print("\nTesting Strategic Tone:")
        response_strategic = engine_strategic.speak(test_log)
        print(f"Response:\n{response_strategic}")

    except Exception as e:
        print(f"\nERROR during testing: {e}")
        print("Ensure AIChatAgent and its dependencies are correctly installed and configured.") 