from abc import ABC, abstractmethod


class TTSInterface(ABC):
    """Abstract base class for Text-to-Speech engines."""

    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Synthesizes the given text to an audio file.

        Args:
            text: The text to synthesize.
            output_path: The path to save the generated audio file (e.g., .mp3, .wav).

        Returns:
            True if synthesis was successful, False otherwise.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Checks if the TTS engine and its dependencies are available.

        Returns:
            True if available, False otherwise.
        """
        pass
