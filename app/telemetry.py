from __future__ import annotations
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from langchain_core.messages import BaseMessage
from langchain_core.messages import messages_to_dict

from app.settings import settings

class Tracer:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Tracer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.provider = settings.telemetry.tracing_provider
        self.local_path = Path(settings.telemetry.local.path)
        self.redact_keys = settings.telemetry.redact_keys
        self.csv_headers = [
            "ts_iso", "run_id", "thread_id", "assistant_id", "decision_key",
            "provider", "event_type", "node", "input_digest", "output_digest",
            "status", "error_type", "error_message", "latency_ms",
            "llm_provider", "llm_model", "tokens_in", "tokens_out", "cost_usd",
            "mode", "broker_provider", "data_provider", "app_version"
        ]

        self._initialized = True

    def _get_log_paths(self) -> (Path | None, Path | None):
        if "local" not in self.provider:
            return None, None

        self.local_path.mkdir(parents=True, exist_ok=True)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        csv_path = self.local_path / f"{today}_actions.csv" if "csv" in self.provider or "both" in self.provider else None
        jsonl_path = self.local_path / f"{today}_actions.jsonl" if "jsonl" in self.provider or "both" in self.provider else None

        if csv_path and not csv_path.exists():
            with open(csv_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                writer.writeheader()

        return csv_path, jsonl_path

    def _sanitize_for_json(self, data: Any) -> Any:
        """
        Recursively traverses data to redact sensitive keys and convert
        non-serializable objects (like LangChain messages) to dicts.
        """
        if isinstance(data, dict):
            sanitized_dict = {}
            for key, value in data.items():
                if key in self.redact_keys:
                    sanitized_dict[key] = "***REDACTED***"
                else:
                    sanitized_dict[key] = self._sanitize_for_json(value)
            return sanitized_dict
        elif isinstance(data, list):
            return [self._sanitize_for_json(item) for item in data]
        elif isinstance(data, BaseMessage):
            # For a single message object, convert it to a dict
            return messages_to_dict([data])[0]
        else:
            return data

    def log(self, event: Dict[str, Any]):
        if self.provider == "none":
            return

        csv_path, jsonl_path = self._get_log_paths()

        # Ensure standard fields are present
        event.setdefault("ts_iso", datetime.now(timezone.utc).isoformat())

        # Sanitize and prepare data for logging
        sanitized_event = self._sanitize_for_json(event)

        if jsonl_path:
            with open(jsonl_path, "a") as f:
                # We need a custom default handler for any types we missed
                f.write(json.dumps(sanitized_event, default=str) + "\n")

        if csv_path:
            # Create a digest for CSV
            csv_row = {k: sanitized_event.get(k, "") for k in self.csv_headers}

            input_data = sanitized_event.get("input", {})
            output_data = sanitized_event.get("output", {})

            csv_row["input_digest"] = str(input_data)[:200]
            csv_row["output_digest"] = str(output_data)[:200]

            with open(csv_path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                writer.writerow(csv_row)

# Singleton instance
tracer = Tracer()
