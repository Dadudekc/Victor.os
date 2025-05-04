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

            # EDIT START: Pass account_url to AzureBlobChannel constructor
            # Initialize client first, then pass it
            if conn_str:
                blob_service_client = BlobServiceClient.from_connection_string(conn_str)
            elif account_url and sas_token:
                # Assume SAS token or other credential for account_url case
                blob_service_client = BlobServiceClient(
                    account_url=account_url, credential=sas_token
                )
            # TODO: Add support for other credential types if needed (e.g., DefaultAzureCredential)  # noqa: E501
            elif account_url:  # Maybe using DefaultAzureCredential?
                logger.warning(
                    "account_url provided without explicit credential (SAS/connection string). Assuming DefaultAzureCredential is configured."  # noqa: E501
                )
                from azure.identity import DefaultAzureCredential

                blob_service_client = BlobServiceClient(  # noqa: F841
                    account_url=account_url, credential=DefaultAzureCredential()
                )
            else:
                raise ValueError(
                    "Azure Blob config requires connection_string OR account_url (with optional sas_token)."  # noqa: E501
                )

            logger.info(f"Info: Using AzureBlobChannel (Container: {container_name})")
            return AzureBlobChannel(
                # Pass client directly if constructor supports it, else pass config values  # noqa: E501
                # Assuming constructor is updated as below:
                container_name=container_name,
                connection_string=conn_str,  # Pass original config values
                sas_token=sas_token,
                account_url=account_url,
                # blob_service_client=blob_service_client, # Alternative if constructor takes client  # noqa: E501
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
