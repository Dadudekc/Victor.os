import os
import json
import logging
from typing import List, Optional, Dict, Any

import openai
from core.services.failed_prompt_archive import FailedPromptArchiveService

logger = logging.getLogger("FeedbackEngineV2")
logger.setLevel(logging.INFO)

class FeedbackEngineV2:
    """
    FeedbackEngineV2 analyzes failed prompts using an LLM and provides root cause analysis
    and recommended fixes based on archived failure data.
    """
    def __init__(self,
                 archive_service: Optional[FailedPromptArchiveService] = None,
                 model: str = "gpt-4"):
        """Initialize with optional archive service and LLM model."""
        self.archive_service = archive_service or FailedPromptArchiveService()
        self.model = model
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set; LLM calls will fail without key.")
        openai.api_key = api_key

    def analyze_failures(self,
                         filter_by_reason: Optional[str] = None,
                         max_retry: Optional[int] = None,
                         limit: Optional[int] = 10
                         ) -> List[Dict[str, Any]]:
        """
        Analyze a batch of archived failures and return AI-generated diagnostics.

        Args:
            filter_by_reason: only include failures matching this reason
            max_retry: include failures with retry_count <= max_retry
            limit: max number of failures to analyze

        Returns:
            A list of dicts: {prompt_id, analysis, raw_response, error (optional)}
        """
        results: List[Dict[str, Any]] = []
        failures = self.archive_service.get_failures(filter_by_reason, max_retry)
        for entry in failures[:limit]:
            prompt_id = entry.get("prompt_id")
            reason = entry.get("reason")
            retry_count = entry.get("retry_count")
            prompt_data = entry.get("prompt")

            # Compose the system prompt
            system_message = (
                f"You are an AI assistant that diagnoses failed prompts.\n"
                f"Prompt ID: {prompt_id}\n"
                f"Reason: {reason}\n"
                f"Retry Count: {retry_count}\n"
                f"Original Prompt Data: {json.dumps(prompt_data, indent=2)}\n"
                "Provide a concise analysis of why this prompt failed and recommend how to fix it."
            )

            try:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[{"role": "system", "content": system_message}]
                )
                ai_output = response.choices[0].message.content.strip()
                logger.info(f"Analysis for {prompt_id}: {ai_output}")
                results.append({
                    "prompt_id": prompt_id,
                    "analysis": ai_output,
                    "raw_response": response
                })
            except Exception as e:
                logger.error(f"Failed to analyze prompt {prompt_id}: {e}", exc_info=True)
                results.append({
                    "prompt_id": prompt_id,
                    "analysis": None,
                    "error": str(e)
                })
        return results

    def save_analysis(self, results: List[Dict[str, Any]], output_file: str = "memory/failure_analysis.json") -> bool:
        """
        Save analysis results to a JSON file.
        """
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Saved failure analysis to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save analysis to {output_file}: {e}", exc_info=True)
            return False 