"""Client for interacting with Azure Blob Storage."""

import logging  # noqa: I001
from typing import Optional

import tenacity  # Add tenacity for retry logic
from azure.core.exceptions import AzureError, ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient  # Import async client

from dreamos.core.config import get_config
from . import APIError, IntegrationError, AzureBlobError

logger = logging.getLogger(__name__)


class AzureBlobError(IntegrationError):
    pass


class AzureBlobClient:
    def __init__(self):
        """Initializes the Azure Blob client, loading config via get_config."""
        self.blob_service_client = None
        self._functional = False
        self.connection_string = None # Initialize

        try:
            config = get_config()
            # Assuming path like: config.integrations.azure_blob.connection_string
            conn_str_secret = config.integrations.azure_blob.connection_string if hasattr(config.integrations, 'azure_blob') else None
            self.connection_string = conn_str_secret.get_secret_value() if conn_str_secret else None

            if not self.connection_string:
                logger.warning("Azure Blob connection string not found in config. Client will be non-functional.")
            else:
                self.blob_service_client = BlobServiceClient.from_connection_string(
                    self.connection_string
                )
                self._functional = True
                logger.info("AzureBlobClient initialized successfully.")

        except ValueError as e:
            logger.error(f"Invalid Azure Blob connection string format in config: {e}")
            raise AzureBlobError(f"Invalid Azure Blob connection string format: {e}")
        except ImportError:
             logger.error("'azure-storage-blob' package is required. Please install it.")
             raise AzureBlobError("'azure-storage-blob' package not installed.")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Blob client using get_config: {e}", exc_info=True)
            self._functional = False # Ensure non-functional on error
            # raise AzureBlobError(f"Failed to initialize Azure Blob client: {e}")

        if not self._functional:
            logger.warning("AzureBlobClient is non-functional after attempting config load.")

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
                "AzureBlobClient not functional (check connection string and initialization)."  # noqa: E501
            )

        logger.debug(
            f"Attempting to upload blob {blob_name} to container {container_name}."
        )
        try:
            async with self.blob_service_client:
                blob_client = self.blob_service_client.get_blob_client(
                    container=container_name, blob=blob_name
                )
                await blob_client.upload_blob(data, overwrite=True)
                logger.info(
                    f"Successfully uploaded blob {blob_name} to container {container_name}."  # noqa: E501
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
                "AzureBlobClient not functional (check connection string and initialization)."  # noqa: E501
            )

        logger.debug(
            f"Attempting to download blob {blob_name} from container {container_name}."
        )
        try:
            async with self.blob_service_client:
                blob_client = self.blob_service_client.get_blob_client(
                    container=container_name, blob=blob_name
                )
                download_stream = await blob_client.download_blob()
                data = await download_stream.readall()
                logger.info(
                    f"Successfully downloaded blob {blob_name} from container {container_name} ({len(data)} bytes)."  # noqa: E501
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
        if self.blob_service_client:
            try:
                await self.blob_service_client.close()
                logger.info("AzureBlobClient connection closed.")
            except Exception as e:
                logger.error(f"Error closing AzureBlobClient: {e}", exc_info=True)
            finally:
                self.blob_service_client = None
                self._functional = False
