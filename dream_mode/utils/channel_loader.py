import os

from dreamos.memory.blob_channel_memory import LocalBlobChannel


def get_blob_channel():
    """Return a blob channel based on the USE_LOCAL_BLOB setting."""
    if os.getenv("USE_LOCAL_BLOB", "0") == "1":
        return LocalBlobChannel()
    else:
        # Try AzureBlobChannel, fallback to LocalBlobChannel if misconfigured
        try:
            from dream_mode.azure_blob_channel import AzureBlobChannel
            return AzureBlobChannel(
                container_name=os.getenv("AZURE_CONTAINER", "dreamos-tasks"),
                sas_token=os.getenv("AZURE_SAS_TOKEN")
            )
        except Exception:
            # Missing credentials or other errors -> fallback to local
            return LocalBlobChannel() 
