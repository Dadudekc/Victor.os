import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

# Adjust import based on actual project structure
from dreamos.memory.memory_manager import DatabaseManager


@pytest.fixture
def temp_db_file(tmp_path):
    """Provides a temporary path for the SQLite database file."""
    return tmp_path / "test_engagement.db"


@pytest.fixture
def db_manager(temp_db_file):
    """Provides a DatabaseManager instance using the temp file and closes it after."""
    manager = DatabaseManager(db_path=temp_db_file)
    yield manager
    manager.close()


# --- Test Cases ---


def test_db_manager_initialization_creates_db_and_tables(temp_db_file):
    """Test that initializing DatabaseManager creates the DB file and expected tables."""
    assert not temp_db_file.exists()
    manager = DatabaseManager(db_path=temp_db_file)
    assert temp_db_file.exists()

    # Verify tables exist
    conn = sqlite3.connect(temp_db_file)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='interactions';"
    )
    assert cursor.fetchone() is not None, "'interactions' table not created."
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations_metadata';"
    )
    assert cursor.fetchone() is not None, "'conversations_metadata' table not created."
    conn.close()
    manager.close()


def test_record_interaction_inserts_data(db_manager, temp_db_file):
    """Test recording a simple interaction."""
    interaction_data = {
        "platform": "test_platform",
        "username": "test_user",
        "interaction_id": "interaction_123",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "response": "Test response content.",
        "sentiment": "neutral",
        "success": True,
        "chatgpt_url": "http://example.com/chat",
    }
    db_manager.record_interaction(interaction_data)

    # Verify data in DB
    conn = sqlite3.connect(temp_db_file)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM interactions WHERE interaction_id = ?", ("interaction_123",)
    )
    row = cursor.fetchone()
    assert row is not None
    # Basic checks on inserted data (column order depends on SELECT *)
    assert row[1] == interaction_data["platform"]
    assert row[2] == interaction_data["username"]
    assert row[3] == interaction_data["interaction_id"]
    assert row[7] == (1 if interaction_data["success"] else 0)
    conn.close()


def test_initialize_conversation_inserts_metadata(db_manager, temp_db_file):
    """Test initializing conversation metadata."""
    interaction_id = "conv_abc"
    metadata = {"agent_type": "responder", "initial_prompt": "Hello!"}
    db_manager.initialize_conversation(interaction_id, metadata)

    # Verify data in DB
    conn = sqlite3.connect(temp_db_file)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT metadata FROM conversations_metadata WHERE interaction_id = ?",
        (interaction_id,),
    )
    row = cursor.fetchone()
    assert row is not None
    loaded_metadata = json.loads(row[0])
    assert loaded_metadata == metadata
    conn.close()


def test_initialize_conversation_ignores_duplicate(db_manager, temp_db_file):
    """Test that initializing the same conversation twice doesn't error and keeps the first."""
    interaction_id = "conv_xyz"
    metadata1 = {"version": 1}
    metadata2 = {"version": 2}

    db_manager.initialize_conversation(interaction_id, metadata1)
    first_timestamp = datetime.now(timezone.utc)
    # Simulate small delay
    threading.Event().wait(0.01)
    db_manager.initialize_conversation(
        interaction_id, metadata2
    )  # Try initializing again

    conn = sqlite3.connect(temp_db_file)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT metadata, initialized_at FROM conversations_metadata WHERE interaction_id = ?",
        (interaction_id,),
    )
    row = cursor.fetchone()
    assert row is not None
    loaded_metadata = json.loads(row[0])
    initialized_at_str = row[1]
    # Should still have the first metadata due to INSERT OR IGNORE
    assert loaded_metadata == metadata1
    # Check timestamp is close to the first call (allow some slack)
    initialized_at = datetime.fromisoformat(initialized_at_str.replace("Z", "+00:00"))
    assert (
        abs((initialized_at - first_timestamp).total_seconds()) < 1
    )  # Check timestamp is close to first init
    conn.close()


def test_fetch_conversation_retrieves_interactions(db_manager):
    """Test fetching all interactions for a given conversation ID."""
    interaction_id = "fetch_conv_1"
    ts1 = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc).isoformat()
    ts2 = datetime(2023, 1, 1, 10, 5, 0, tzinfo=timezone.utc).isoformat()

    data1 = {
        "interaction_id": interaction_id,
        "timestamp": ts1,
        "response": "First message",
        "success": True,
    }
    data2 = {
        "interaction_id": interaction_id,
        "timestamp": ts2,
        "response": "Second message",
        "success": False,
    }
    other_data = {
        "interaction_id": "other_conv",
        "timestamp": ts1,
        "response": "Different convo",
        "success": True,
    }

    db_manager.record_interaction(data1)
    db_manager.record_interaction(data2)
    db_manager.record_interaction(other_data)

    conversation = db_manager.fetch_conversation(interaction_id)
    assert len(conversation) == 2
    # Results are ordered by timestamp ASC
    assert conversation[0]["response"] == "First message"
    assert conversation[0]["success"] == 1  # Note: SQLite stores bools as 0/1
    assert conversation[1]["response"] == "Second message"
    assert conversation[1]["success"] == 0


def test_fetch_conversation_empty_result(db_manager):
    """Test fetching a conversation with no interactions."""
    assert db_manager.fetch_conversation("non_existent_id") == []


# Potential future test: Thread safety (more complex to set up reliably)
# def test_db_manager_thread_safety(db_manager):
#     # ... setup to have multiple threads calling record_interaction ...
#     # ... verify data integrity after threads complete ...
#     pass
