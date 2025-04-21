"""
AzureBlobChannel: simple push/pull interface for JSON tasks/results via Azure Blob Storage.
"""

import os
import json
import uuid
import time
import logging
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

try:
    from azure.storage.blob import BlobServiceClient
    from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
except ImportError:
    BlobServiceClient = None
    ResourceNotFoundError = Exception
    HttpResponseError = Exception

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class AzureBlobChannel:
    def __init__(
        self,
        container_name: str,
        sas_token: str = None,
        connection_string: str = None,
        max_retries: int = 3,
        retry_delay: int = 2,
        timeout_secs: int = 10,
    ):
        """
        Initialize channel. Provide connection_string or sas_token (with AZURE_STORAGE_ACCOUNT_URL).
        """
        if not BlobServiceClient:
            raise ImportError("azure-storage-blob not installed")
        if connection_string:
            self.blob_service = BlobServiceClient.from_connection_string(connection_string)
        elif sas_token:
            account_url = os.getenv("AZURE_STORAGE_ACCOUNT_URL", None)
            self.blob_service = BlobServiceClient(account_url=account_url, credential=sas_token)
        else:
            raise ValueError("Either connection_string or sas_token must be provided.")
        self.container_client = self.blob_service.get_container_client(container_name)
        try:
            self.container_client.create_container()
        except Exception:
            pass

        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout_secs = timeout_secs

    def _safe_upload(self, blob_name: str, data: str) -> None:
        for attempt in range(1, self.max_retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self.container_client.upload_blob,
                        name=blob_name,
                        data=data,
                        overwrite=True
                    )
                    future.result(timeout=self.timeout_secs)
                return
            except (ResourceNotFoundError, HttpResponseError, FuturesTimeout, OSError, ConnectionError) as e:
                logger.warning(f"upload_blob attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempt - 1)))
                else:
                    logger.error(f"upload_blob failed after {attempt} attempts")
                    raise

    def _safe_download(self, blob_name: str) -> bytes:
        for attempt in range(1, self.max_retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        lambda: self.container_client.get_blob_client(blob_name).download_blob().readall()
                    )
                    data = future.result(timeout=self.timeout_secs)
                return data
            except (ResourceNotFoundError, HttpResponseError, FuturesTimeout, OSError, ConnectionError) as e:
                logger.warning(f"download_blob attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempt - 1)))
                else:
                    logger.error(f"download_blob failed after {attempt} attempts")
                    raise

    def _safe_delete(self, blob_name: str) -> None:
        for attempt in range(1, self.max_retries + 1):
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        lambda: self.container_client.get_blob_client(blob_name).delete_blob()
                    )
                    future.result(timeout=self.timeout_secs)
                return
            except (ResourceNotFoundError, HttpResponseError, FuturesTimeout, OSError, ConnectionError) as e:
                logger.warning(f"delete_blob attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** (attempt - 1)))
                else:
                    logger.error(f"delete_blob failed after {attempt} attempts")
                    raise

    def push_task(self, task: Dict) -> None:
        """Upload a JSON blob representing one task."""
        blob_name = f"task-{uuid.uuid4()}.json"
        data = json.dumps(task)
        self._safe_upload(blob_name, data)

    def pull_tasks(self) -> List[Dict]:
        """List & download new task blobs, then delete them."""
        tasks: List[Dict] = []
        for blob in self.container_client.list_blobs(name_starts_with="task-"):
            name = blob.name
            try:
                raw = self._safe_download(name)
                task = json.loads(raw)
                tasks.append(task)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in task blob {name}")
            self._safe_delete(name)
        return tasks

    def push_result(self, result: Dict) -> None:
        """Upload JSON blob of a result from an agent."""
        blob_name = f"result-{uuid.uuid4()}.json"
        data = json.dumps(result)
        self._safe_upload(blob_name, data)

    def pull_results(self) -> List[Dict]:
        """List & download result blobs, then delete them."""
        results: List[Dict] = []
        for blob in self.container_client.list_blobs(name_starts_with="result-"):
            name = blob.name
            try:
                raw = self._safe_download(name)
                res = json.loads(raw)
                results.append(res)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON in result blob {name}")
            self._safe_delete(name)
        return results

    def healthcheck(self) -> bool:
        """Upload, download, and delete a test blob to ensure connectivity."""
        test_data = {"ping": time.time()}
        blob_name = f"health-{uuid.uuid4()}.json"
        try:
            payload = json.dumps(test_data)
            self._safe_upload(blob_name, payload)
            raw = self._safe_download(blob_name)
            _ = json.loads(raw)
            self._safe_delete(blob_name)
            return True
        except Exception as e:
            logger.error(f"Healthcheck failed: {e}", exc_info=True)
            return False 