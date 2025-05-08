"""Client for interacting with Discord (Bot and Webhooks)."""

import asyncio  # noqa: I001
import logging
from typing import Optional

import aiohttp
import tenacity

from dreamos.core.config import get_config
from . import APIError, IntegrationError

logger = logging.getLogger(__name__)

DISCORD_API_BASE = (
    "https://discord.com/api/v10"  # Example base URL, use appropriate version
)


class DiscordClient:
    def __init__(self):
        """Initializes the Discord client, loading config via get_config."""
        self.client = None  # aiohttp session
        self._functional = False
        try:
            config = get_config()
            self.bot_token = config.integrations.discord.bot_token.get_secret_value() if config.integrations.discord.bot_token else None
            self.webhook_url = config.integrations.discord.webhook_url if hasattr(config.integrations.discord, 'webhook_url') else None

            if not self.bot_token and not self.webhook_url:
                logger.warning("Discord bot token and webhook URL not found in config. Client will be non-functional.")
            else:
                self._functional = True
                logger.info(f"DiscordClient initialized (Token: {'set' if self.bot_token else 'unset'}, Webhook: {'set' if self.webhook_url else 'unset'})")

        except Exception as e:
             logger.error(f"Failed to initialize DiscordClient using get_config: {e}", exc_info=True)
             # Ensure fields are None if init fails
             self.bot_token = None
             self.webhook_url = None
             self._functional = False

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if self.client is None or self.client.closed:
            self.client = aiohttp.ClientSession()
            logger.debug("Created new aiohttp ClientSession.")
        return self.client

    async def close_session(self):
        """Close the aiohttp session if it exists."""
        if self.client and not self.client.closed:
            await self.client.close()
            logger.debug("Closed aiohttp ClientSession.")
            self.client = None

    def is_webhook_functional(self) -> bool:
        return self.webhook_url is not None

    def is_bot_functional(self) -> bool:
        return self.bot_token is not None

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=5),
        retry=tenacity.retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError)
        ),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def send_webhook_message(
        self, content: str, username: str = None, avatar_url: str = None, **kwargs
    ):
        """Sends a message via the configured webhook with retries."""
        if not self.is_webhook_functional():
            raise IntegrationError("Webhook URL not configured for DiscordClient.")

        session = await self._get_session()
        payload = {
            "content": content,
        }
        if username:
            payload["username"] = username
        if avatar_url:
            payload["avatar_url"] = avatar_url
        # Allow overriding standard payload keys via kwargs if needed
        payload.update(kwargs)

        logger.debug(
            f"Sending webhook message (User: {username or 'Default'}): {content[:100]}..."  # noqa: E501
        )
        start_time = asyncio.get_event_loop().time()

        try:
            async with session.post(self.webhook_url, json=payload) as response:
                end_time = asyncio.get_event_loop().time()
                response_text = await response.text()
                if 200 <= response.status < 300:
                    logger.info(
                        f"Discord webhook message sent successfully ({end_time - start_time:.2f}s). Status: {response.status}"  # noqa: E501
                    )
                else:
                    logger.warning(
                        f"Discord webhook request failed with status {response.status}. Response: {response_text}. Retrying if possible..."  # noqa: E501
                    )
                    response.raise_for_status()  # Let tenacity retry based on ClientResponseError  # noqa: E501
        except aiohttp.ClientResponseError as e:
            # This block is reached after retries are exhausted
            logger.error(
                f"Discord webhook failed after retries: Status {e.status}, Message: {e.message}"  # noqa: E501
            )
            # Map specific non-retryable errors if needed (e.g., 400, 401, 403, 404)
            if e.status in [400, 401, 403, 404]:
                raise IntegrationError(
                    f"Discord webhook failed (Status {e.status}): {e.message}",
                    original_exception=e,
                )
            else:  # Treat other ClientResponseErrors as API errors
                raise APIError(
                    f"Discord webhook failed after retries (Status {e.status}): {e.message}",  # noqa: E501
                    original_exception=e,
                )
        except asyncio.TimeoutError as e:
            logger.error("Discord webhook timed out after retries.")
            raise APIError(
                "Discord webhook timed out after retries.", original_exception=e
            )
        except Exception as e:
            # Catch other aiohttp errors or unexpected issues
            logger.error(
                f"Unexpected error sending Discord webhook: {e}", exc_info=True
            )
            if isinstance(e, (aiohttp.ClientError)):
                raise APIError(
                    f"Discord webhook client error: {e}", original_exception=e
                )  # Let tenacity handle retry for some?
            else:
                raise APIError(
                    f"Unexpected error sending Discord webhook: {e}",
                    original_exception=e,
                )

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=5),
        # Retry on network errors and specific Discord rate limits (429)
        retry=tenacity.retry_if_exception_type(
            (aiohttp.ClientError, asyncio.TimeoutError, APIError)
        ),  # Retry APIError in case of 429
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def send_bot_message(self, channel_id: int | str, content: str, **kwargs):
        """Sends a message via the bot user using Discord HTTP API."""
        if not self.is_bot_functional():
            raise IntegrationError("Bot token not configured for DiscordClient.")

        session = await self._get_session()
        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        headers = {
            "Authorization": f"Bot {self.bot_token}",
            "Content-Type": "application/json",
            "User-Agent": "DreamOS (DiscordClient, v0.1)",
        }
        payload = {"content": content}
        payload.update(kwargs)  # Allow adding embeds, components etc. via kwargs

        logger.debug(f"Sending bot message to channel {channel_id}: {content[:100]}...")
        start_time = asyncio.get_event_loop().time()

        try:
            async with session.post(url, headers=headers, json=payload) as response:
                end_time = asyncio.get_event_loop().time()
                response_text = await response.text()
                if 200 <= response.status < 300:
                    logger.info(
                        f"Discord bot message sent successfully ({end_time - start_time:.2f}s). Status: {response.status}"  # noqa: E501
                    )
                else:
                    logger.warning(
                        f"Discord bot message request failed with status {response.status}. Response: {response_text}. Retrying if possible..."  # noqa: E501
                    )
                    # Raise specific error for rate limiting (429) to allow retry via APIError  # noqa: E501
                    if response.status == 429:
                        raise APIError(
                            f"Discord Rate Limit (429). Response: {response_text}",
                            status_code=429,
                        )
                    response.raise_for_status()  # Trigger retry for other client errors

        except aiohttp.ClientResponseError as e:
            logger.error(
                f"Discord bot message failed after retries: Status {e.status}, Message: {e.message}"  # noqa: E501
            )
            if e.status == 401 or e.status == 403:  # Unauthorized/Forbidden
                self._functional = False  # Disable bot if token invalid/perms missing
                raise IntegrationError(
                    f"Discord bot auth/permission error (Status {e.status}): {e.message}",  # noqa: E501
                    original_exception=e,
                )
            elif e.status == 400 or e.status == 404:  # Bad Request / Not Found
                raise IntegrationError(
                    f"Discord bot request error (Status {e.status}): {e.message}",
                    original_exception=e,
                )
            else:  # Includes 429 if retry failed
                raise APIError(
                    f"Discord bot message failed after retries (Status {e.status}): {e.message}",  # noqa: E501
                    original_exception=e,
                    status_code=e.status,
                )
        except asyncio.TimeoutError as e:
            logger.error("Discord bot message timed out after retries.")
            raise APIError(
                "Discord bot message timed out after retries.", original_exception=e
            )
        except Exception as e:
            logger.error(
                f"Unexpected error sending Discord bot message: {e}", exc_info=True
            )
            if isinstance(e, (aiohttp.ClientError)):
                raise APIError(
                    f"Discord bot message client error: {e}", original_exception=e
                )
            else:
                raise APIError(
                    f"Unexpected error sending Discord bot message: {e}",
                    original_exception=e,
                )


# Removed asyncio import
