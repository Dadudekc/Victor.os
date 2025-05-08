# src/dreamos/core/tts/elevenlabs_tts.py
import logging
import os
from typing import Optional, Any # Added Any

# Placeholder for config access
# from dreamos.core.config import AppConfig
class AppConfig: # Placeholder
    def __init__(self):
        # Attempt to get from env var first for flexibility
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY", None)
        # In a real AppConfig, you'd load from a file or other source
        # and potentially override env vars based on config settings.
        if not self.elevenlabs_api_key:
             logger.warning("ELEVENLABS_API_KEY not found in environment or config.")

# from .tts_interface import TTSInterface
class TTSInterface: # Placeholder
    def synthesize(self, text: str, output_path: str) -> bool: pass
    def is_available(self) -> bool: pass

logger = logging.getLogger(__name__)

# Requires: pip install elevenlabs
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    logger.warning("ElevenLabs library not installed. ElevenLabsTTS will not be available.")
    # Define dummy classes if import fails to prevent NameErrors later
    class ElevenLabs: pass
    def save(*args, **kwargs): pass


class ElevenLabsTTS(TTSInterface):
    """TTS implementation using the ElevenLabs API."""

    def __init__(self, config: Optional[AppConfig] = None):
        self.api_key = None
        # Prioritize config object if provided
        if config and config.elevenlabs_api_key:
            self.api_key = config.elevenlabs_api_key
        if not self.api_key: # Fallback to env var if not in config or config not provided
             self.api_key = os.environ.get("ELEVENLABS_API_KEY")

        self.client = None
        if ELEVENLABS_AVAILABLE and self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                # Optionally test connection or list voices here
                # voices = self.client.voices.get_all()
                # logger.info(f"Found {len(voices.voices)} voices.")
                logger.info("ElevenLabsTTS initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs client (check API key validity?): {e}", exc_info=True)
                self.client = None # Ensure client is None if init fails
        elif not ELEVENLABS_AVAILABLE:
             logger.error("Cannot initialize ElevenLabsTTS: Library not installed ('pip install elevenlabs').")
        else: # API Key missing
             logger.error("Cannot initialize ElevenLabsTTS: API key missing (set ELEVENLABS_API_KEY env var or provide via config).")


    def is_available(self) -> bool:
        """Check if library is installed, API key is provided, and client initialized."""
        # Check all conditions required for operation
        return ELEVENLABS_AVAILABLE and bool(self.api_key) and self.client is not None

    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesizes text using ElevenLabs."""
        if not self.is_available():
            logger.error("ElevenLabsTTS is not available (check API key, installation, and initialization logs).")
            return False
        if not text:
            logger.error("Cannot synthesize empty text.")
            return False

        try:
            logger.info(f"Synthesizing text with ElevenLabs to {output_path}...")
            # Simple generation - enhance with specific voice, model, stability settings later
            audio = self.client.generate(
                text=text,
                voice="Rachel", # Example voice - make configurable
                model="eleven_multilingual_v2" # Example model - make configurable
            )
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            save(audio, output_path)
            logger.info(f"ElevenLabs synthesis successful: {output_path}")
            return True
        except Exception as e:
            logger.error(f"ElevenLabs synthesis failed: {e}", exc_info=True)
            # Clean up potentially partially created file
            if os.path.exists(output_path):
                 try:
                     os.remove(output_path)
                     logger.info(f"Cleaned up partial file: {output_path}")
                 except OSError:
                      pass
            return False

# Example usage
# if __name__ == '__main__':
#     logging.basicConfig(level=logging.INFO) # Ensure logs are visible
#     if not os.environ.get("ELEVENLABS_API_KEY"):
#         print("Warning: ELEVENLABS_API_KEY environment variable not set.")
#
#     tts = ElevenLabsTTS(config=AppConfig()) # Use placeholder config
#     if tts.is_available():
#         print("ElevenLabs is available.")
#         # Create a temp dir for testing
#         if not os.path.exists("temp_audio"):
#              os.makedirs("temp_audio")
#         output_file = "temp_audio/test_elevenlabs.mp3"
#         success = tts.synthesize("Hello from Dream OS using Eleven Labs.", output_file)
#         if success:
#             print(f"Synthesized {output_file} successfully.")
#         else:
#             print("Synthesis failed.")
#     else:
#         print("ElevenLabs is not available.") 