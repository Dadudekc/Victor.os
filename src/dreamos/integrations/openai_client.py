"""Client for interacting with OpenAI APIs."""

import asyncio  # noqa: I001
import logging
from typing import Optional

import openai
import tenacity

from dreamos.core.config import get_config
from . import APIError, IntegrationError

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(self):
        """Initializes the OpenAI client, loading configuration automatically via get_config."""
        try:
            config = get_config() # Load global config
            self.api_key = config.integrations.openai.api_key.get_secret_value() if config.integrations.openai.api_key else None
            self.api_base = config.integrations.openai.api_base if hasattr(config.integrations.openai, 'api_base') else None

            if not self.api_key:
                logger.warning("OpenAI API key not found in configuration. Client will be non-functional.")
                self._client = None
                self._functional = False
            else:
                # Configure the openai library
                openai.api_key = self.api_key
                if self.api_base:
                    openai.api_base = self.api_base
                self._client = openai
                self._functional = True
                logger.info(f"OpenAIClient initialized (API Base: {self.api_base or 'Default'}).")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client using get_config: {e}", exc_info=True)
            self._client = None
            self._functional = False
            # Optionally re-raise as IntegrationError
            # raise IntegrationError(f"Failed to initialize OpenAI client: {e}")

    def is_functional(self) -> bool:
        """Returns True if the client was initialized successfully and has an API key."""  # noqa: E501
        return self._functional

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=2, max=10),
        retry=tenacity.retry_if_exception_type(
            (
                openai.APIError,
                openai.APITimeoutError,
                openai.RateLimitError,
                openai.APIConnectionError,
                openai.InternalServerError,
            )
        ),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def get_completion(self, prompt: str, model: str = "gpt-4", **kwargs) -> str:
        """Gets a completion from the specified OpenAI model with retries."""
        if not self.is_functional():
            raise IntegrationError(
                "OpenAI client not functional (not initialized or API key missing)."
            )

        logger.debug(
            f"Requesting completion (model: {model}) for prompt: {prompt[:100]}..."
        )
        start_time = asyncio.get_event_loop().time()

        try:
            # Assuming basic chat completion structure
            response = await self._client.ChatCompletion.acreate(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs,  # Pass through other params like temperature, max_tokens
            )

            completion = response.choices[0].message["content"].strip()
            end_time = asyncio.get_event_loop().time()
            logger.info(
                f"Received OpenAI completion ({end_time - start_time:.2f}s). Length: {len(completion)}"  # noqa: E501
            )
            logger.debug(f"Completion (first 100 chars): {completion[:100]}")
            return completion

        # Specific OpenAI errors handled by tenacity or mapped below
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI Authentication Error: {e}. Disabling client.")
            self._functional = False  # Disable client after auth error
            raise IntegrationError(
                f"OpenAI Authentication Failed: {e}", original_exception=e
            )
        except openai.PermissionDeniedError as e:
            logger.error(f"OpenAI Permission Error: {e}")
            raise APIError(f"OpenAI Permission Denied: {e}", original_exception=e)
        except openai.BadRequestError as e:
            logger.error(f"OpenAI Invalid Request Error: {e}")
            raise APIError(f"OpenAI Invalid Request: {e}", original_exception=e)
        except openai.RateLimitError as e:
            logger.warning(
                f"OpenAI Rate Limit Error encountered: {e}"
            )  # Log specifically
            raise  # Re-raise for tenacity retry
        except (
            openai.APIError,
            openai.APITimeoutError,
            openai.APIConnectionError,
            openai.InternalServerError,
        ) as e:
            logger.warning(f"OpenAI API/Connection Error: {e}")
            raise  # Re-raise for tenacity retry
        except Exception as e:
            # Catch other unexpected issues
            logger.error(f"Unexpected error during OpenAI call: {e}", exc_info=True)
            raise APIError(
                f"Unexpected error communicating with OpenAI: {e}", original_exception=e
            )
