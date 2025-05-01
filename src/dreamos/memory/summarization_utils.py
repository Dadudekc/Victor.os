# src/dreamos/memory/summarization_utils.py
import json
import logging
import zlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dreamos.core.errors import MemoryError as CoreMemoryError
from dreamos.core.utils.summarizer import BaseSummarizer
from dreamos.integrations.openai_client import OpenAIClient

# TODO: Consider moving _rewrite_memory_safely to a shared file utility module
# (e.g., memory/io_utils.py or core/utils/file_utils.py) as it's also used
# by compaction_utils.py.
from .compaction_utils import _rewrite_memory_safely

logger = logging.getLogger(__name__)


# EDIT START: Change inheritance to CoreMemoryError
class SummarizationError(CoreMemoryError):
    """Exception raised for errors during memory summarization."""

    pass


# EDIT END


def summarize_segment_chunk(
    chunk: List[Dict[str, Any]],
    policy: Dict[str, Any],
    summarizer: Optional[BaseSummarizer],
) -> Dict[str, Any]:
    """Generates a summary entry for a list of memory entries.

    Uses the provided summarizer if available, otherwise generates a placeholder.

    Args:
        chunk: A list of memory entry dictionaries to summarize.
        policy: The summarization policy dictionary.
        summarizer: An optional summarizer instance.

    Returns:
        A dictionary representing the summary entry, or an error dict.
    """
    if not chunk:
        return {"summary_error": "Empty chunk provided"}

    count = len(chunk)
    start_time_str = chunk[0].get("timestamp", "N/A")
    end_time_str = chunk[-1].get("timestamp", "N/A")

    summary_text = f"[Placeholder summary for {count} entries from ~{start_time_str} to ~{end_time_str}]"
    if summarizer:
        try:
            summary_text = summarizer.summarize_entries(chunk)
            logger.info(
                f"Generated actual summary for {count} entries using {type(summarizer).__name__}."
            )
        except Exception as e:
            logger.error(
                f"Summarizer failed: {e}. Falling back to placeholder.", exc_info=True
            )
            summary_text = f"[Summarizer Error ({e}). Placeholder summary for {count} entries from ~{start_time_str} to ~{end_time_str}]"
    else:
        logger.info(
            f"Generated placeholder summary for {count} entries (no summarizer provided)."
        )

    summary_entry = {
        "type": "memory_summary",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "original_entry_count": count,
        "time_range_start": start_time_str,
        "time_range_end": end_time_str,
        "summary_content": summary_text,
        "policy_used": policy,
    }
    return summary_entry


def summarize_segment_file(
    file_path: Path, policy: Dict[str, Any], summarizer: Optional[BaseSummarizer]
) -> bool:
    """Loads a memory segment file, summarizes a chunk if needed, and saves the result.

    Reads a JSON segment file (plain or zlib compressed). Based on the policy
    (trigger_threshold_entries, summarize_n_oldest), it identifies the oldest
    chunk of entries exceeding the threshold, generates a summary using
    `summarize_segment_chunk`, replaces the chunk with the summary entry, and
    rewrites the file atomically using `_rewrite_memory_safely`.

    Args:
        file_path: The Path object of the segment file to potentially summarize.
        policy: The summarization policy dictionary. Expected keys:
                - 'trigger_threshold_entries': Min entries before summarization is triggered.
                - 'summarize_n_oldest': Number of oldest entries to summarize in one go.
                - 'min_chunk_size': Minimum number of entries required to form a chunk for summarization.
        summarizer: The summarizer instance to use.

    Returns:
        True if the process completed (including no summarization needed), False if an error occurred.
    """
    logger.info(f"Starting summarization process for: {file_path}")
    if not file_path.exists() or file_path.stat().st_size == 0:
        logger.warning(f"Summarization skipped: File not found or empty - {file_path}")
        return True  # Nothing to summarize

    summarize_threshold = policy.get("trigger_threshold_entries", 200)
    summarize_chunk_size = policy.get("summarize_n_oldest", 50)
    min_entries_to_summarize = policy.get("min_chunk_size", 10)

    if summarize_chunk_size < min_entries_to_summarize:
        logger.warning(
            f"Policy misconfiguration: summarize_n_oldest ({summarize_chunk_size}) < min_chunk_size ({min_entries_to_summarize}). Adjusting chunk size."
        )
        summarize_chunk_size = min_entries_to_summarize

    is_compressed = file_path.suffix == ".z"
    original_data: Optional[List[Dict[str, Any]]] = None

    try:
        if is_compressed:
            with open(file_path, "rb") as f:
                compressed_data = f.read()
            json_str = zlib.decompress(compressed_data).decode("utf-8")
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                json_str = f.read()

        if not json_str.strip():
            logger.warning(
                f"Summarization skipped: File content is empty - {file_path}"
            )
            return True

        original_data = json.loads(json_str)
        if not isinstance(original_data, list):
            # EDIT START: Raise specific error
            # logger.error(f"Summarization failed: Expected a list in file {file_path}, found {type(original_data)}")
            # return False
            raise SummarizationError(
                f"Expected a list in file {file_path}, found {type(original_data)}"
            )
            # EDIT END

    except json.JSONDecodeError as e:
        # EDIT START: Raise specific error
        logger.error(
            f"Failed to parse segment file {file_path} for summarization: {e}",
            exc_info=True,
        )
        # return False
        raise SummarizationError(f"Failed to parse JSON in {file_path}") from e
        # EDIT END
    except Exception as e:
        # EDIT START: Raise specific error
        logger.error(
            f"Failed to load segment file {file_path} for summarization: {e}",
            exc_info=True,
        )
        # return False
        raise SummarizationError(f"Failed to load file {file_path}") from e
        # EDIT END

    if original_data is None:
        return False

    try:
        # Identify chunk to summarize
        if (
            len(original_data) >= summarize_threshold
            and len(original_data) >= summarize_chunk_size
        ):
            chunk_to_summarize = original_data[:summarize_chunk_size]
            remaining_data = original_data[summarize_chunk_size:]
            logger.info(
                f"Identified chunk of {len(chunk_to_summarize)} entries for summarization in {file_path} (Total: {len(original_data)})"
            )

            summary_entry = summarize_segment_chunk(
                chunk_to_summarize, policy, summarizer
            )

            if "summary_error" in summary_entry:
                # EDIT START: Raise specific error
                err_msg = f"Summarization failed for chunk in {file_path}: {summary_entry['summary_error']}"
                logger.error(err_msg)
                # return False
                raise SummarizationError(err_msg)
                # EDIT END

            new_data = [summary_entry] + remaining_data

            logger.info(
                f"Saving summarized data to {file_path} ({len(new_data)} entries replacing {len(original_data)})..."
            )
            if _rewrite_memory_safely(file_path, new_data, is_compressed):
                return True
            else:
                # EDIT START: Raise specific error
                logger.error(f"Summarization failed during save for {file_path}")
                # return False
                raise SummarizationError(f"Failed during atomic save for {file_path}")
                # EDIT END
        else:
            logger.info(
                f"No summarization needed for {file_path} based on current policy/size ({len(original_data)} entries)."
            )
            return True  # No action needed is considered success
    except Exception as e:
        # Catch errors from summarize_segment_chunk (if it raises) or other unexpected issues
        logger.error(
            f"Error during summarization processing for {file_path}: {e}", exc_info=True
        )
        # Don't mask original SummarizationError if raised above
        if not isinstance(e, SummarizationError):
            raise SummarizationError(
                f"Error during summarization data processing for {file_path}"
            ) from e
        else:
            raise  # Re-raise original SummarizationError


async def summarize_conversations(
    conversations: List[Dict[str, Any]],
    strategy: str = "simple_concat",
    llm_client: Optional[OpenAIClient] = None,
    max_length: int = 2000,
) -> str:
    """Summarizes a list of conversation dictionaries based on a specified strategy.

    Args:
        conversations: A list of dictionaries, each representing a message
                       or turn in a conversation. Expected to have keys like
                       'sender', 'content', 'timestamp'.
        strategy: The summarization method to use.
                  - 'simple_concat': Concatenates 'sender': 'content' pairs,
                    truncated to `max_length`.
                  - 'llm_abstractive': (Requires `llm_client`) Uses an LLM to
                    generate an abstractive summary.
        llm_client: An optional LLM client instance (required for 'llm_abstractive').
                    Expected to have a method like `generate_text(prompt: str, max_tokens: int) -> str`.
        max_length: The approximate maximum character length for the summary
                    (primarily enforced for 'simple_concat', used as token guidance for LLM).

    Returns:
        A string containing the generated summary.

    Raises:
        SummarizationError: If the strategy is 'llm_abstractive' but no `llm_client`
                            is provided, or if the LLM call fails.
        ValueError: If an unknown strategy is provided.
    """
    logger.debug(
        f"Summarizing {len(conversations)} conversation entries using strategy: {strategy}"
    )

    if strategy == "simple_concat":
        summary_parts = []
        current_length = 0
        for entry in conversations:
            sender = entry.get("sender", "Unknown")
            content = entry.get("content", "")
            part = f"{sender}: {content}\n"
            if current_length + len(part) > max_length:
                remaining_len = max_length - current_length
                if remaining_len > 3:
                    summary_parts.append(part[: remaining_len - 3] + "...")
                break  # Stop adding parts once max_length is reached
            summary_parts.append(part)
            current_length += len(part)
        return "".join(summary_parts).strip()

    elif strategy == "llm_abstractive":
        if llm_client is None:
            logger.error(
                "LLM client required for 'llm_abstractive' strategy but none provided."
            )
            raise SummarizationError(
                "LLM client not provided for abstractive summarization."
            )

        # TODO: Actual LLM integration -> DONE
        prompt = _build_llm_summary_prompt(conversations)
        # Estimate max tokens based on desired character length (very rough)
        # Adjust model name/params as needed based on client/config
        estimated_max_tokens = max(50, max_length // 4)
        try:
            # Assuming the client has a compatible method like generate_text
            # Adapt this call based on the actual llm_client implementation
            summary = await llm_client.generate_text(
                prompt=prompt,
                max_tokens=estimated_max_tokens,
                # Add other relevant parameters like model, temperature if needed
                # model="gpt-3.5-turbo-instruct", # Example
                temperature=0.5,
            )
            logger.info(f"LLM summary generated successfully ({len(summary)} chars).")
            return summary.strip()  # Return the generated summary
        except Exception as e:
            # Catch specific client errors if possible
            logger.error(f"LLM summarization failed: {e}", exc_info=True)
            raise SummarizationError(f"LLM summarization failed: {e}") from e
    else:
        logger.error(f"Unknown summarization strategy: {strategy}")
        raise ValueError(f"Unknown summarization strategy: {strategy}")


def _build_llm_summary_prompt(conversations: List[Dict[str, Any]]) -> str:
    """(Internal helper) Constructs a prompt for LLM-based summarization."""
    # Format conversation for the prompt
    formatted_convo = "\n".join(
        [
            f"{entry.get('sender', 'Unknown')}: {entry.get('content', '')}"
            for entry in conversations
        ]
    )

    prompt = (
        f"Summarize the following conversation concisely.\n"
        f"Focus on the key topics discussed and decisions made.\n\n"
        f"Conversation:\n---\n{formatted_convo}\n---\n\n"
        f"Summary:"
    )
    return prompt


# Potential BaseSummarizer implementation using the above function
# class LLMConversationSummarizer(BaseSummarizer):
#     def __init__(self, llm_client):
#         self.llm_client = llm_client
#
#     def summarize_entries(self, entries: List[Dict[str, Any]]) -> str:
#         # Assuming entries are conversation dictionaries
#         return summarize_conversations(entries, strategy='llm_abstractive', llm_client=self.llm_client)
