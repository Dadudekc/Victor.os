import json
from unittest.mock import MagicMock, patch

import pytest

from dreamos.channels.azure_blob_channel import AzureBlobChannel


@patch("dream_mode.azure_blob_channel.BlobServiceClient")
def test_push_and_pull_task(mock_bsc):
    # Setup mock container
    mock_container = MagicMock()
    mock_bsc.return_value.get_container_client.return_value = mock_container

    channel = AzureBlobChannel(
        container_name="test", sas_token="fake_sas", connection_string=None
    )

    # Test push_task uploads correct JSON
    channel.push_task({"action": "test"})
    # upload_blob is called on the container client directly
    # get_container_client returns mock_container, so upload_blob is called via mock_container.upload_blob
    _, kwargs = mock_container.upload_blob.call_args
    uploaded_json = kwargs.get("data")
    assert json.loads(uploaded_json)["action"] == "test"

    # Mock tasks blob list and pull
    mock_blob = MagicMock(name="task-1.json")
    mock_container.list_blobs.return_value = [mock_blob]
    blob_client = MagicMock()
    blob_client.download_blob.return_value.readall.return_value = b'{"task": "run"}'
    mock_container.get_blob_client.return_value = blob_client

    tasks = channel.pull_tasks()
    assert tasks == [{"task": "run"}]
    blob_client.delete_blob.assert_called_once()


@patch("dream_mode.azure_blob_channel.BlobServiceClient")
def test_push_and_pull_result(mock_bsc):
    # Setup mock container
    mock_container = MagicMock()
    mock_bsc.return_value.get_container_client.return_value = mock_container

    channel = AzureBlobChannel(
        container_name="test", sas_token="fake_sas", connection_string=None
    )

    # Test push_result uploads correct JSON
    channel.push_result({"status": "done"})
    _, kwargs = mock_container.upload_blob.call_args
    uploaded_json = kwargs.get("data")
    assert json.loads(uploaded_json)["status"] == "done"

    # Mock results blob list and pull
    mock_blob = MagicMock(name="result-1.json")
    mock_container.list_blobs.return_value = [mock_blob]
    blob_client = MagicMock()
    blob_client.download_blob.return_value.readall.return_value = b'{"output": "42"}'
    mock_container.get_blob_client.return_value = blob_client

    results = channel.pull_results()
    assert results == [{"output": "42"}]
    blob_client.delete_blob.assert_called_once()
