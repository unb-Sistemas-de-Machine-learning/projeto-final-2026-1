"""Telemetria mínima, local e sem persistir o perfil do cliente."""

from __future__ import annotations

import json
import logging
import threading
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Monitor:
    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self._lock = threading.Lock()
        self._counters: Counter[str] = Counter()
        self._latency_total = 0.0

    def record(self, event: dict[str, Any]) -> None:
        safe_event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": event["request_id"],
            "risk_level": event["risk_level"],
            "model_source": event["model_source"],
            "latency_ms": event["latency_ms"],
            "warning_count": event["warning_count"],
        }
        with self._lock:
            self._counters["requests_total"] += 1
            self._counters[f"source_{event['model_source']}"] += 1
            self._counters[f"risk_{event['risk_level']}"] += 1
            self._latency_total += float(event["latency_ms"])
            try:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(safe_event, ensure_ascii=False) + "\n")
            except OSError as exc:
                # Observabilidade não deve derrubar a funcionalidade principal.
                self._counters["log_write_errors"] += 1
                logger.warning("Não foi possível persistir telemetria: %s", type(exc).__name__)

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            total = self._counters["requests_total"]
            return {
                **dict(self._counters),
                "average_latency_ms": round(self._latency_total / total, 2) if total else 0.0,
                "fallback_rate": round(self._counters["source_fallback"] / total, 4)
                if total
                else 0.0,
            }
