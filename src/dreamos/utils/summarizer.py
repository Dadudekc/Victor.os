"""Abstract base class for text summarization utilities."""

from abc import ABC, abstractmethod
from typing import Optional


class BaseSummarizer(ABC):
    """Abstract base class for summarization components."""

    @abstractmethod
    async def summarize(self, text: str, max_length: Optional[int] = None, min_length: Optional[int] = None) -> str:
        """Generates a summary for the given text.

        Args:
            text: The input text to summarize.
            max_length: Optional maximum length for the summary (implementation specific).
            min_length: Optional minimum length for the summary (implementation specific).

        Returns:
            The generated summary string.

        Raises:
            NotImplementedError: If the method is not implemented by the subclass.
            Exception: For any implementation-specific errors during summarization.
        """
        pass

# Concrete implementations (e.g., LLM-based, extractive) would inherit from this:
#
# class MyLLMSummarizer(BaseSummarizer):
#     async def summarize(self, text: str, ...) -> str:
#         # ... implementation using an LLM API ...
#         pass
#
# class MyTextRankSummarizer(BaseSummarizer):
#     async def summarize(self, text: str, ...) -> str:
#         # ... implementation using TextRank algorithm ...
#         pass 