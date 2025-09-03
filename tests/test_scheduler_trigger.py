import pytest
import json
from unittest.mock import MagicMock
from pathlib import Path

# Import the class to be tested
from scripts.scheduler_trigger import ThreadManager

@pytest.fixture
def mock_client():
    """Fixture to create a mock LangGraphClient."""
    client = MagicMock()
    client.threads = MagicMock()
    return client

def test_thread_manager_create_new_thread(tmp_path, mock_client):
    """Test that a new thread is created if the map file doesn't exist."""
    mock_client.threads.create.return_value = {"thread_id": "new_thread_123"}

    thread_map_file = tmp_path / "threads.json"
    manager = ThreadManager(mock_client, thread_map_file)

    thread_id = manager.ensure_thread_id("EUR_USD", "M5")

    assert thread_id == "new_thread_123"
    mock_client.threads.create.assert_called_once()
    assert thread_map_file.exists()
    assert json.loads(thread_map_file.read_text()) == {"EUR_USD_M5": "new_thread_123"}

def test_thread_manager_reuse_verified_thread(tmp_path, mock_client):
    """Test that an existing, valid thread is reused."""
    thread_map_file = tmp_path / "threads.json"
    thread_map_file.write_text(json.dumps({"EUR_USD_M5": "existing_thread_456"}))

    mock_client.threads.get.return_value = {"thread_id": "existing_thread_456"}

    manager = ThreadManager(mock_client, thread_map_file)

    # Reset mock from the __init__ call which also verifies threads
    mock_client.threads.get.reset_mock()

    thread_id = manager.ensure_thread_id("EUR_USD", "M5")

    assert thread_id == "existing_thread_456"
    mock_client.threads.get.assert_called_once_with("existing_thread_456")

def test_thread_manager_recreate_stale_thread(tmp_path, mock_client, monkeypatch):
    """Test that a stale thread is recreated."""
    # Patch the verification on init to test ensure_thread_id in isolation
    monkeypatch.setattr(ThreadManager, "_verify_all_threads", lambda self: None)

    thread_map_file = tmp_path / "threads.json"
    thread_map_file.write_text(json.dumps({"EUR_USD_M5": "stale_thread_789"}))

    manager = ThreadManager(mock_client, thread_map_file)

    # Now, set up the mocks for the ensure_thread_id call
    mock_client.threads.get.side_effect = Exception("Not Found")
    mock_client.threads.create.return_value = {"thread_id": "recreated_thread_101"}

    thread_id = manager.ensure_thread_id("EUR_USD", "M5")

    assert thread_id == "recreated_thread_101"
    mock_client.threads.get.assert_called_once_with("stale_thread_789")
    mock_client.threads.create.assert_called_once()
    assert json.loads(thread_map_file.read_text()) == {"EUR_USD_M5": "recreated_thread_101"}

def test_thread_manager_wipes_map_on_session_restart(tmp_path, mock_client):
    """Test that the thread map is wiped if threads are stale on startup."""
    thread_map_file = tmp_path / "threads.json"
    thread_map_file.write_text(json.dumps({
        "EUR_USD_M5": "stale_thread_1",
        "GBP_USD_H1": "stale_thread_2"
    }))

    # Simulate all threads being stale
    mock_client.threads.get.side_effect = Exception("Not Found")

    manager = ThreadManager(mock_client, thread_map_file)

    assert manager._thread_map == {}
    assert json.loads(thread_map_file.read_text()) == {}
