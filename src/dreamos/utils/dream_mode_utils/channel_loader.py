import logging  # EDIT: Add logging import  # noqa: I001
from typing import Optional

# from dotenv import load_dotenv # Remove direct env loading
from azure.storage.blob import BlobServiceClient
from dreamos.channels.azure_blob_channel import AzureBlobChannel
from dreamos.channels.local_blob_channel import LocalBlobChannel

# EDIT START: Import AppConfig and Azure config model
from dreamos.core.config import AppConfig, AzureBlobStorageConfig

# EDIT END


# Load environment variables from .env file
# load_dotenv() # REMOVED

# AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING") # REMOVED  # noqa: E501
# CONTAINER_NAME = "agent-memories" # REMOVED - Should come from config

logger = logging.getLogger(__name__)  # EDIT: Add module-level logger

# REMOVE old version of get_blob_channel
# def get_blob_channel(agent_id: str) -> AzureBlobChannel:
#     """Creates and returns an AzureBlobChannel instance for the given agent_id."""
#     if not AZURE_STORAGE_CONNECTION_STRING:
#         raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set.")  # noqa: E501
#
#     # Each agent gets a prefix within the container
#     blob_prefix = f"{agent_id}/"
#
#     blob_service_client = BlobServiceClient.from_connection_string(AZURE_STORAGE_CONNECTION_STRING)  # noqa: E501
#     return AzureBlobChannel(blob_service_client, CONTAINER_NAME, blob_prefix)


# EDIT START: Refactor get_blob_channel to use AppConfig
# def get_blob_channel():
def get_blob_channel(config: AppConfig):
    """Return a blob channel based on the AppConfig settings."""
    azure_config: Optional[AzureBlobStorageConfig] = getattr(
        config.integrations, "azure_blob", None
    )

    # EDIT START: Check config for use_local_blob flag (assuming it exists)
    # if config.memory_channel.use_local_blob or not azure_config:
    use_local = getattr(config.memory_channel, "use_local_blob", False)
    if use_local or not azure_config:
        # EDIT END
        if not azure_config and not use_local:
            logger.warning(
                "Warning: Azure Blob config not found, falling back to LocalBlobChannel."  # noqa: E501
            )  # Use logging?
        else:
            logger.info("Info: Using LocalBlobChannel based on config.")
        # EDIT START: Ensure local path comes from config
        local_path = getattr(
            config.paths, "memory_blobs_local_root", "./local_blob_storage"
        )
        # return LocalBlobChannel(root_path=config.paths.memory_blobs_local_root)
        return LocalBlobChannel(root_path=local_path)
        # EDIT END
    else:
        # Try AzureBlobChannel, fallback to LocalBlobChannel if misconfigured
        try:
            conn_str = azure_config.connection_string
            sas_token = azure_config.sas_token
            account_url = azure_config.account_url  # Get account_url from config
            container_name = (
                azure_config.container_name or "dreamos-tasks"
            )  # Default if not in config

            credential = None
            if conn_str:
                # Connection string handles auth internally
                blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            elif account_url:
                if sas_token:
                    # Use SAS token if provided
                    credential = sas_token
                    logger.info("Using SAS Token credential for Azure Blob Storage.")
                else:
                    # Attempt DefaultAzureCredential (async version)
                    logger.info(
                        "Attempting DefaultAzureCredential for Azure Blob Storage."
                    )
                    try:
                        from azure.identity.aio import DefaultAzureCredential

                        credential = DefaultAzureCredential()
                    except ImportError:
                        logger.error(
                            "Azure identity library not found ('pip install azure-identity'). Cannot use DefaultAzureCredential."  # noqa: E501
                        )
                        raise ValueError(
                            "Azure identity library required for DefaultAzureCredential"
                        )
                    except Exception as e:
                        logger.error(
                            f"Failed to initialize DefaultAzureCredential: {e}",
                            exc_info=True,
                        )
                        raise ValueError(
                            f"DefaultAzureCredential initialization failed: {e}"
                        )

                if credential:
                    blob_service_client = BlobServiceClient(
                        account_url=account_url, credential=credential
                    )
                else:
                    # This path should ideally not be reached if credential logic is correct
                    raise ValueError(
                        "Could not determine appropriate Azure credential."
                    )
            else:
                raise ValueError(
                    "Azure Blob config requires connection_string OR account_url."  # Removed sas_token from here
                )

            logger.info(f"Info: Using AzureBlobChannel (Container: {container_name})")
            # Pass the initialized client to the channel constructor
            return AzureBlobChannel(
                blob_service_client=blob_service_client,
                container_name=container_name,
            )
            # EDIT END
        except Exception as e:
            # Missing credentials or other errors -> fallback to local
            logger.warning(
                f"Warning: Failed to initialize AzureBlobChannel ({e}), falling back to LocalBlobChannel."  # noqa: E501
            )
            local_path = getattr(
                config.paths, "memory_blobs_local_root", "./local_blob_storage"
            )
            return LocalBlobChannel(root_path=local_path)


# EDIT END
