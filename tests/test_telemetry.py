import pytest
import json
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime, timezone

from app.telemetry import Tracer
from app.settings import settings

@pytest.fixture
def tracer(monkeypatch):
    """Fixture to provide a tracer instance with a mocked file system."""
    # Reset the singleton for each test
    Tracer._instance = None

    # Mock settings for predictable paths and redaction
    monkeypatch.setattr(settings.telemetry, "tracing_provider", "local_both")
    monkeypatch.setattr(settings.telemetry.local, "path", "test_traces/")
    monkeypatch.setattr(settings.telemetry, "redact_keys", ["api_key", "secret"])

    return Tracer()

def test_tracer_log_creates_files(tracer, tmp_path):
    """Test that log files are created with headers on first write."""
    # Point the tracer to a temporary directory
    tracer.local_path = tmp_path / "traces"

    event = {"event_type": "test_event", "run_id": "123"}
    tracer.log(event)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    csv_path = tracer.local_path / f"{today}_actions.csv"
    jsonl_path = tracer.local_path / f"{today}_actions.jsonl"

    assert csv_path.exists()
    assert jsonl_path.exists()

    # Check that CSV has a header
    with open(csv_path, "r") as f:
        header = f.readline().strip()
        assert "ts_iso" in header
        assert "run_id" in header

def test_tracer_redaction(tracer, tmp_path):
    """Test that sensitive keys are redacted from logs."""
    tracer.local_path = tmp_path / "traces"

    event = {
        "event_type": "test_event",
        "input": {
            "api_key": "my_secret_key",
            "user": "testuser",
            "secret": "another_secret"
        }
    }

    # We need to capture the written content
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        tracer.log(event)

        # Find the call to the jsonl file write
        # This is complex, let's test the _redact method directly

    sanitized = tracer._redact(event)
    assert sanitized["input"]["api_key"] == "***REDACTED***"
    assert sanitized["input"]["secret"] == "***REDACTED***"
    assert sanitized["input"]["user"] == "testuser"

def test_tracer_file_rotation(monkeypatch, tmp_path):
    """Test that log files are rotated based on date."""
    # Mock datetime.now to control the date
    mock_date_1 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mock_date_2 = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

    Tracer._instance = None
    tracer1 = Tracer()
    tracer1.local_path = tmp_path / "traces"

    with patch("app.telemetry.datetime") as mock_dt:
        mock_dt.now.return_value = mock_date_1
        tracer1.log({"event_type": "event1"})

    assert (tmp_path / "traces" / "2024-01-01_actions.csv").exists()

    # Create a new tracer instance to simulate a new day
    Tracer._instance = None
    tracer2 = Tracer()
    tracer2.local_path = tmp_path / "traces"

    with patch("app.telemetry.datetime") as mock_dt:
        mock_dt.now.return_value = mock_date_2
        tracer2.log({"event_type": "event2"})

    assert (tmp_path / "traces" / "2024-01-02_actions.csv").exists()
