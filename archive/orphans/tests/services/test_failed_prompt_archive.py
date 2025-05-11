import json  # noqa: I001
from pathlib import Path

import pytest
from dreamos.services.failed_prompt_archive import FailedPromptArchiveService

# Remove the skipped stub function
# @pytest.mark.skip(reason='Test stub for coverage tracking')
# def test_stub_for_failed_prompt_archive():
#     pass


@pytest.fixture
def archive_service(tmp_path: Path) -> FailedPromptArchiveService:
    """Provides a FailedPromptArchiveService instance using a temporary file."""
    archive_file = tmp_path / "failed_prompts.json"
    return FailedPromptArchiveService(archive_path=str(archive_file))


def test_archive_initialization_new(archive_service: FailedPromptArchiveService):
    """Test that the service initializes correctly when the file doesn't exist."""
    assert isinstance(archive_service.archive, list)
    assert len(archive_service.archive) == 0
    archive_path = Path(archive_service.archive_path)
    assert archive_path.parent.exists()  # Directory should be created
    # File might not exist until first write, which is fine


def test_archive_initialization_loads_existing(tmp_path: Path):
    """Test that the service loads data from an existing archive file."""
    archive_file = tmp_path / "existing_archive.json"
    existing_data = [
        {
            "prompt_id": "p1",
            "reason": "timeout",
            "retry_count": 1,
            "prompt": {"text": "t1"},
        },
    ]
    archive_file.write_text(json.dumps(existing_data), encoding="utf-8")

    service = FailedPromptArchiveService(archive_path=str(archive_file))
    assert len(service.archive) == 1
    assert service.archive[0]["prompt_id"] == "p1"


def test_log_failure_appends_and_writes(archive_service: FailedPromptArchiveService):
    """Test that log_failure adds an entry and writes to the file."""
    prompt_id = "test-prompt-001"
    prompt_data = {"text": "What is the airspeed velocity?"}
    reason = "Network Error"
    retry_count = 2

    archive_service.log_failure(prompt_id, prompt_data, reason, retry_count)

    assert len(archive_service.archive) == 1
    entry = archive_service.archive[0]
    assert entry["prompt_id"] == prompt_id
    assert entry["prompt"] == prompt_data
    assert entry["reason"] == reason
    assert entry["retry_count"] == retry_count
    assert "timestamp" in entry

    # Verify file content
    archive_path = Path(archive_service.archive_path)
    assert archive_path.exists()
    read_data = json.loads(archive_path.read_text(encoding="utf-8"))
    assert isinstance(read_data, list)
    assert len(read_data) == 1
    assert read_data[0]["prompt_id"] == prompt_id

    # Log another
    archive_service.log_failure("p2", {}, "timeout", 0)
    assert len(archive_service.archive) == 2
    read_data_2 = json.loads(archive_path.read_text(encoding="utf-8"))
    assert len(read_data_2) == 2


def test_get_failures_no_filter(archive_service: FailedPromptArchiveService):
    """Test retrieving all failures."""
    archive_service.log_failure("p1", {}, "timeout", 0)
    archive_service.log_failure("p2", {}, "error", 1)
    failures = archive_service.get_failures()
    assert len(failures) == 2


def test_get_failures_filter_by_reason(archive_service: FailedPromptArchiveService):
    """Test filtering failures by reason."""
    archive_service.log_failure("p1", {}, "timeout", 0)
    archive_service.log_failure("p2", {}, "error", 1)
    archive_service.log_failure("p3", {}, "timeout", 2)

    timeout_failures = archive_service.get_failures(filter_by_reason="timeout")
    assert len(timeout_failures) == 2
    assert timeout_failures[0]["prompt_id"] == "p1"
    assert timeout_failures[1]["prompt_id"] == "p3"

    error_failures = archive_service.get_failures(filter_by_reason="error")
    assert len(error_failures) == 1
    assert error_failures[0]["prompt_id"] == "p2"

    unknown_failures = archive_service.get_failures(filter_by_reason="unknown")
    assert len(unknown_failures) == 0


def test_get_failures_filter_by_max_retry(archive_service: FailedPromptArchiveService):
    """Test filtering failures by max retry count."""
    archive_service.log_failure("p1", {}, "timeout", 0)
    archive_service.log_failure("p2", {}, "error", 1)
    archive_service.log_failure("p3", {}, "timeout", 2)

    max_0_failures = archive_service.get_failures(max_retry=0)
    assert len(max_0_failures) == 1
    assert max_0_failures[0]["prompt_id"] == "p1"

    max_1_failures = archive_service.get_failures(max_retry=1)
    assert len(max_1_failures) == 2
    assert {f["prompt_id"] for f in max_1_failures} == {"p1", "p2"}

    max_5_failures = archive_service.get_failures(max_retry=5)
    assert len(max_5_failures) == 3


def test_get_by_prompt_id(archive_service: FailedPromptArchiveService):
    """Test retrieving failures by prompt ID."""
    archive_service.log_failure("p1", {"v": 1}, "timeout", 0)
    archive_service.log_failure("p2", {}, "error", 1)
    archive_service.log_failure("p1", {"v": 2}, "timeout", 1)  # Log p1 again

    p1_failures = archive_service.get_by_prompt_id("p1")
    assert len(p1_failures) == 2
    assert p1_failures[0]["prompt"]["v"] == 1
    assert p1_failures[1]["prompt"]["v"] == 2

    p2_failures = archive_service.get_by_prompt_id("p2")
    assert len(p2_failures) == 1

    p3_failures = archive_service.get_by_prompt_id("p3")
    assert len(p3_failures) == 0
