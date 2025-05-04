import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from dreamos.core.config import AppConfig
from dreamos.integrations.openai_client import OpenAIClient
from dreamos.services.prompt_archive import FailedPromptArchiveService

logger = logging.getLogger("FeedbackEngineV2")


class FeedbackEngineV2:
    """
    FeedbackEngineV2 analyzes failed prompts using an LLM and provides root cause analysis
    and recommended fixes based on archived failure data.
    """  # noqa: E501

    def __init__(
        self,
        config: AppConfig,
        archive_service: Optional[FailedPromptArchiveService] = None,
        model: str = "gpt-4",
    ):
        """Initialize with AppConfig, optional archive service, and LLM model."""
        self.config = config
        self.archive_service = archive_service or FailedPromptArchiveService()
        self.model = getattr(
            getattr(self.config.tools, "feedback_engine", None), "llm_model", model
        )

        try:
            self.openai_client = OpenAIClient(config=self.config)
            logger.info("FeedbackEngineV2 initialized with OpenAIClient.")
        except Exception as e:
            logger.error(
                f"Failed to initialize OpenAI Client for FeedbackEngineV2: {e}",
                exc_info=True,
            )
            self.openai_client = None
            logger.warning(
                "FeedbackEngineV2 initialized WITHOUT a functional OpenAI client."
            )

    async def analyze_failures(
        self,
        filter_by_reason: Optional[str] = None,
        max_retry: Optional[int] = None,
        limit: Optional[int] = 10,
    ) -> List[Dict[str, Any]]:
        """
        Analyze a batch of archived failures and return AI-generated diagnostics.
        Uses the configured OpenAIClient.

        Args:
            filter_by_reason: only include failures matching this reason
            max_retry: include failures with retry_count <= max_retry
            limit: max number of failures to analyze

        Returns:
            A list of dicts: {prompt_id, analysis, error (optional)}
        """
        results: List[Dict[str, Any]] = []
        if not self.openai_client:
            logger.error("Cannot analyze failures: OpenAI client not available.")
            return []

        failures = self.archive_service.get_failures(filter_by_reason, max_retry)
        if not failures:
            logger.info("No failures found matching criteria.")
            return []

        analysis_tasks = []
        for entry in failures[:limit]:
            analysis_tasks.append(self._analyze_single_failure(entry))

        if analysis_tasks:
            results = await asyncio.gather(*analysis_tasks)
        return results

    async def _analyze_single_failure(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes a single failure entry using the LLM."""
        prompt_id = entry.get("prompt_id", "N/A")
        reason = entry.get("reason", "N/A")
        retry_count = entry.get("retry_count", "N/A")
        prompt_data = entry.get("prompt", {})

        system_prompt = (
            "You are an AI assistant that diagnoses failed prompts.\n"
            "Analyze the following failed prompt details and provide a concise analysis of why it likely failed and recommend how to fix it.\n"  # noqa: E501
            "Focus on actionable advice."
        )
        user_prompt = (
            f"Failed Prompt Details:\n"
            f"----------------------\n"
            f"Prompt ID: {prompt_id}\n"
            f"Reason Given: {reason}\n"
            f"Retry Count: {retry_count}\n"
            f"Original Prompt Data:\n```json\n{json.dumps(prompt_data, indent=2)}\n```\n"  # noqa: E501
            f"----------------------\n"
            f"Analysis and Recommendation:"
        )

        try:
            if hasattr(self.openai_client, "generate_chat_completion"):
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                max_tokens = getattr(
                    getattr(self.config.tools, "feedback_engine", None),
                    "llm_max_tokens",
                    300,
                )
                temperature = getattr(
                    getattr(self.config.tools, "feedback_engine", None),
                    "llm_temperature",
                    0.3,
                )
                ai_output = await self.openai_client.generate_chat_completion(
                    messages=messages,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
            else:
                logger.warning(
                    "OpenAIClient lacks generate_chat_completion, using generate_text. Prompt format may be suboptimal."  # noqa: E501
                )
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                max_tokens = getattr(
                    getattr(self.config.tools, "feedback_engine", None),
                    "llm_max_tokens",
                    300,
                )
                temperature = getattr(
                    getattr(self.config.tools, "feedback_engine", None),
                    "llm_temperature",
                    0.3,
                )
                ai_output = await self.openai_client.generate_text(
                    prompt=full_prompt,
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )

            logger.info(f"Analysis for {prompt_id} completed.")
            return {
                "prompt_id": prompt_id,
                "analysis": ai_output.strip(),
            }
        except Exception as e:
            logger.error(
                f"Unexpected error analyzing prompt {prompt_id}: {e}", exc_info=True
            )
            return {
                "prompt_id": prompt_id,
                "analysis": None,
                "error": f"Unexpected Error: {e}",
            }

    def save_analysis(
        self, results: List[Dict[str, Any]], output_file: Optional[str] = None
    ) -> bool:
        """
        Save analysis results to a JSON file.
        Uses configured path if output_file is None.
        """
        try:
            if output_file is None:
                default_path = getattr(
                    self.config.paths,
                    "failure_analysis_output",
                    Path("memory/failure_analysis.json"),
                )
                output_path = self.config.project_root / default_path
            else:
                output_path = Path(output_file)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved failure analysis to {output_path}")
            return True
        except Exception as e:
            logger.error(
                f"Failed to save analysis to {output_path}: {e}", exc_info=True
            )
            return False
