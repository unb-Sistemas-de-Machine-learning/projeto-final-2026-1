from __future__ import annotations

from pathlib import Path

from app.agent import RetentionAgent
from app.model_service import ModelService
from app.monitoring import Monitor
from app.schemas import CustomerProfile


def test_agent_uses_explicit_fallback(tmp_path: Path, high_risk_payload: dict[str, object]) -> None:
    model = ModelService(tmp_path / "missing.joblib")
    monitor = Monitor(tmp_path / "events.jsonl")
    agent = RetentionAgent(model, monitor)

    response = agent.analyze(CustomerProfile.model_validate(high_risk_payload))

    assert response.model_source == "fallback"
    assert response.risk_level == "alto"
    assert response.churn_probability == 0.78
    assert response.factors
    assert response.recommendations
    assert monitor.snapshot()["fallback_rate"] == 1.0
    log_content = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "test-001" not in log_content


def test_soft_guardrail_warns_about_implausible_charges(
    tmp_path: Path, high_risk_payload: dict[str, object]
) -> None:
    high_risk_payload["total_charges"] = 10.0
    agent = RetentionAgent(
        ModelService(tmp_path / "missing.joblib"),
        Monitor(tmp_path / "events.jsonl"),
    )

    response = agent.analyze(CustomerProfile.model_validate(high_risk_payload))

    assert response.guardrail_warnings
