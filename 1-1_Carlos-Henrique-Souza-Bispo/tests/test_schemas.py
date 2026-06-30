from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import CustomerProfile


def test_valid_profile_maps_to_dataset_columns(high_risk_payload: dict[str, object]) -> None:
    profile = CustomerProfile.model_validate(high_risk_payload)

    record = profile.to_model_record()

    assert record["SeniorCitizen"] == 0
    assert record["MonthlyCharges"] == 95.5
    assert "customer_id" not in record


def test_rejects_inconsistent_phone_service(
    high_risk_payload: dict[str, object],
) -> None:
    high_risk_payload["phone_service"] = "No"
    high_risk_payload["multiple_lines"] = "Yes"

    with pytest.raises(ValidationError, match="No phone service"):
        CustomerProfile.model_validate(high_risk_payload)


def test_rejects_inconsistent_internet_addons(
    high_risk_payload: dict[str, object],
) -> None:
    high_risk_payload["internet_service"] = "No"

    with pytest.raises(ValidationError, match="No internet service"):
        CustomerProfile.model_validate(high_risk_payload)


def test_rejects_unknown_fields(high_risk_payload: dict[str, object]) -> None:
    high_risk_payload["annual_income"] = 50_000

    with pytest.raises(ValidationError, match="Extra inputs"):
        CustomerProfile.model_validate(high_risk_payload)
