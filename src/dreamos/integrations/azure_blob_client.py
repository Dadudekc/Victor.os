"""Client for interacting with Azure Blob Storage."""

import asyncio  # Keep for placeholder sleep
import logging

import tenacity  # Add tenacity for retry logic
from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient  # Import async client

from dreamos.utils.config_utils import get_config

from . import APIError, IntegrationError

logger = logging.getLogger(__name__)


class AzureBlobClient:
    def __init__(self):
        """Initializes the Azure Blob client using configuration."""
        self.connection_string = get_config(
            "integrations.azure_blob.connection_string", default=None
        )
        self._client = None
        self._functional = False

        if self.connection_string:
            try:
                # Initialize async client
                self._client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                self._functional = True
                logger.info("AzureBlobClient initialized successfully.")
            except ValueError as e:
                logger.error(
                    f"Invalid Azure Blob Storage connection string provided: {e}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to initialize Azure BlobServiceClient: {e}", exc_info=True
                )
        else:
            logger.warning(
                "Azure Blob connection string not found in config (integrations.azure_blob.connection_string). Client non-functional."
            )

        if not self._functional:
            logger.warning("AzureBlobClient is non-functional.")

    def is_functional(self) -> bool:
        return self._functional

    # Basic retry strategy (can be enhanced)
    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=5),
        retry=tenacity.retry_if_exception_type(
            AzureError
        ),  # Retry on general Azure core errors
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def upload_blob(self, container_name: str, blob_name: str, data: bytes | str):
        """Uploads data to a blob in the specified container."""
        if not self.is_functional():
            raise IntegrationError(
                "AzureBlobClient not functional (check connection string and initialization)."
            )

        logger.debug(
            f"Attempting to upload blob {blob_name} to container {container_name}."
        )
        try:
            async with self._client:
                blob_client = self._client.get_blob_client(
                    container=container_name, blob=blob_name
                )
                await blob_client.upload_blob(data, overwrite=True)
                logger.info(
                    f"Successfully uploaded blob {blob_name} to container {container_name}."
                )
        except ResourceNotFoundError:
            logger.error(f"Container '{container_name}' not found for blob upload.")
            raise IntegrationError(f"Azure container '{container_name}' not found.")
        except AzureError as e:
            logger.error(f"Azure error during blob upload {blob_name}: {e}")
            raise APIError(f"Azure error during upload: {e}", original_exception=e)
        except Exception as e:
            logger.error(
                f"Unexpected error during blob upload {blob_name}: {e}", exc_info=True
            )
            raise APIError(
                f"Unexpected error during Azure upload: {e}", original_exception=e
            )

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=5),
        retry=tenacity.retry_if_exception_type(AzureError),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def download_blob(self, container_name: str, blob_name: str) -> bytes:
        """Downloads data from a blob."""
        if not self.is_functional():
            raise IntegrationError(
                "AzureBlobClient not functional (check connection string and initialization)."
            )

        logger.debug(
            f"Attempting to download blob {blob_name} from container {container_name}."
        )
        try:
            async with self._client:
                blob_client = self._client.get_blob_client(
                    container=container_name, blob=blob_name
                )
                download_stream = await blob_client.download_blob()
                data = await download_stream.readall()
                logger.info(
                    f"Successfully downloaded blob {blob_name} from container {container_name} ({len(data)} bytes)."
                )
                return data
        except ResourceNotFoundError:
            logger.error(
                f"Blob '{blob_name}' not found in container '{container_name}'."
            )
            raise IntegrationError(
                f"Azure blob '{blob_name}' in container '{container_name}' not found."
            )
        except AzureError as e:
            logger.error(f"Azure error during blob download {blob_name}: {e}")
            raise APIError(f"Azure error during download: {e}", original_exception=e)
        except Exception as e:
            logger.error(
                f"Unexpected error during blob download {blob_name}: {e}", exc_info=True
            )
            raise APIError(
                f"Unexpected error during Azure download: {e}", original_exception=e
            )

    async def close(self):
        """Closes the underlying client connection gracefully."""
        if self._client:
            try:
                await self._client.close()
                logger.info("AzureBlobClient connection closed.")
            except Exception as e:
                logger.error(f"Error closing AzureBlobClient: {e}", exc_info=True)
            finally:
                self._client = None
                self._functional = False
