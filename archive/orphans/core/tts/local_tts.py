import logging
import os


# from .tts_interface import TTSInterface
class TTSInterface:  # Placeholder
    def synthesize(self, text: str, output_path: str) -> bool:
        pass

    def is_available(self) -> bool:
        pass


logger = logging.getLogger(__name__)

# Requires: pip install pyttsx3
# May also require OS-specific engines (NSSpeechSynthesizer on macOS, SAPI5 on Windows, eSpeak on Linux)
PYTTSX3_AVAILABLE = False
try:
    import pyttsx3

    PYTTSX3_AVAILABLE = True
    logger.info("pyttsx3 library found.")
except ImportError:
    logger.warning("pyttsx3 library not installed. LocalTTS will not be available.")
except Exception as e:
    logger.error(
        f"Error importing pyttsx3: {e}. LocalTTS may not be available.", exc_info=True
    )


class LocalTTS(TTSInterface):
    """TTS implementation using the pyttsx3 library for local synthesis."""

    def __init__(self):
        self.engine = None
        if PYTTSX3_AVAILABLE:  # Check library import before init attempt
            try:
                self.engine = pyttsx3.init()
                # Check if drivers were found
                # Some drivers might init but still be unusable, proxy check helps
                if (
                    not hasattr(self.engine, "proxy")
                    or self.engine.proxy is None
                    or not self.engine.driverName
                ):
                    logger.error(
                        "pyttsx3 init succeeded but no valid TTS driver/proxy found. LocalTTS unavailable."
                    )
                    self.engine = None  # Mark as unavailable
                else:
                    logger.info(
                        f"LocalTTS initialized using driver: {self.engine.driverName}"
                    )
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3 engine: {e}", exc_info=True)
                self.engine = None  # Ensure engine is None if init fails
        else:
            logger.info(
                "LocalTTS not initialized because pyttsx3 library is unavailable."
            )

    def is_available(self) -> bool:
        """Check if library is installed and engine initialized successfully."""
        # Engine must be successfully initialized
        return PYTTSX3_AVAILABLE and self.engine is not None

    def synthesize(self, text: str, output_path: str) -> bool:
        """Synthesizes text locally using pyttsx3."""
        if not self.is_available():
            logger.error(
                "LocalTTS (pyttsx3) is not available (check installation, drivers, and logs)."
            )
            return False
        if not text:
            logger.error("Cannot synthesize empty text.")
            return False
        if not output_path.lower().endswith((".wav", ".mp3")):
            # While save_to_file might work with other extensions on some platforms,
            # WAV is the most reliably supported format across pyttsx3 drivers.
            logger.warning(
                f"Output path {output_path} recommended to end with .wav for pyttsx3 compatibility. Proceeding."
            )

        try:
            logger.info(f"Synthesizing text locally using pyttsx3 to {output_path}...")
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Adjust properties if needed (rate, volume, voice)
            # rate = self.engine.getProperty('rate')
            # self.engine.setProperty('rate', rate-50)
            # voices = self.engine.getProperty('voices')
            # self.engine.setProperty('voice', voices[1].id) # Example: Set specific voice

            self.engine.save_to_file(text, output_path)
            self.engine.runAndWait()  # Blocks until speaking/saving is complete

            # Verify file creation (runAndWait should ensure this, but double check)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"LocalTTS synthesis successful: {output_path}")
                return True
            else:
                # This can happen if runAndWait fails silently or driver has issues
                logger.error(
                    "LocalTTS synthesis potentially failed: Output file not created or empty after runAndWait."
                )
                # Attempt cleanup just in case
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False
        except Exception as e:
            logger.error(f"LocalTTS (pyttsx3) synthesis failed: {e}", exc_info=True)
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
#     tts = LocalTTS()
#     if tts.is_available():
#         print("LocalTTS (pyttsx3) is available.")
#         # Create a temp dir for testing
#         if not os.path.exists("temp_audio"):
#              os.makedirs("temp_audio")
#         output_file = "temp_audio/test_local.wav" # WAV is generally safer
#         success = tts.synthesize("Hello from Dream OS using the local TTS engine.", output_file)
#         if success:
#             print(f"Synthesized {output_file} successfully.")
#         else:
#             print("Synthesis failed.")
#     else:
#         print("LocalTTS (pyttsx3) is not available. Install pyttsx3 and potentially OS drivers (SAPI5/NSSpeech/eSpeak).")
