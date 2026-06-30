"""Schemas públicos da API e guardrails estruturais de entrada."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

YesNo = Literal["Yes", "No"]
InternetAddon = Literal["Yes", "No", "No internet service"]


class CustomerProfile(BaseModel):
    """Perfil mínimo utilizado pelo modelo IBM Telco Customer Churn."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "customer_id": "demo-001",
                "gender": "Female",
                "senior_citizen": 0,
                "partner": "No",
                "dependents": "No",
                "tenure": 3,
                "phone_service": "Yes",
                "multiple_lines": "No",
                "internet_service": "Fiber optic",
                "online_security": "No",
                "online_backup": "No",
                "device_protection": "No",
                "tech_support": "No",
                "streaming_tv": "Yes",
                "streaming_movies": "Yes",
                "contract": "Month-to-month",
                "paperless_billing": "Yes",
                "payment_method": "Electronic check",
                "monthly_charges": 95.5,
                "total_charges": 286.5,
            }
        },
    )

    customer_id: str | None = Field(default=None, max_length=64)
    gender: Literal["Female", "Male"]
    senior_citizen: Literal[0, 1]
    partner: YesNo
    dependents: YesNo
    tenure: int = Field(ge=0, le=72, description="Meses como cliente")
    phone_service: YesNo
    multiple_lines: Literal["Yes", "No", "No phone service"]
    internet_service: Literal["DSL", "Fiber optic", "No"]
    online_security: InternetAddon
    online_backup: InternetAddon
    device_protection: InternetAddon
    tech_support: InternetAddon
    streaming_tv: InternetAddon
    streaming_movies: InternetAddon
    contract: Literal["Month-to-month", "One year", "Two year"]
    paperless_billing: YesNo
    payment_method: Literal[
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)",
    ]
    monthly_charges: float = Field(ge=0, le=200)
    total_charges: float = Field(ge=0, le=20_000)

    @model_validator(mode="after")
    def validate_service_dependencies(self) -> CustomerProfile:
        if self.phone_service == "No" and self.multiple_lines != "No phone service":
            raise ValueError(
                "multiple_lines deve ser 'No phone service' quando phone_service é 'No'."
            )
        if self.phone_service == "Yes" and self.multiple_lines == "No phone service":
            raise ValueError(
                "multiple_lines não pode ser 'No phone service' quando phone_service é 'Yes'."
            )

        addons = (
            self.online_security,
            self.online_backup,
            self.device_protection,
            self.tech_support,
            self.streaming_tv,
            self.streaming_movies,
        )
        if self.internet_service == "No" and any(
            value != "No internet service" for value in addons
        ):
            raise ValueError(
                "Serviços de internet devem ser 'No internet service' "
                "quando internet_service é 'No'."
            )
        if self.internet_service != "No" and any(
            value == "No internet service" for value in addons
        ):
            raise ValueError(
                "Serviços de internet não podem ser 'No internet service' "
                "quando há conexão DSL ou fibra."
            )
        return self

    def to_model_record(self) -> dict[str, object]:
        """Converte nomes amigáveis da API para o contrato do dataset."""
        return {
            "gender": self.gender,
            "SeniorCitizen": self.senior_citizen,
            "Partner": self.partner,
            "Dependents": self.dependents,
            "tenure": self.tenure,
            "PhoneService": self.phone_service,
            "MultipleLines": self.multiple_lines,
            "InternetService": self.internet_service,
            "OnlineSecurity": self.online_security,
            "OnlineBackup": self.online_backup,
            "DeviceProtection": self.device_protection,
            "TechSupport": self.tech_support,
            "StreamingTV": self.streaming_tv,
            "StreamingMovies": self.streaming_movies,
            "Contract": self.contract,
            "PaperlessBilling": self.paperless_billing,
            "PaymentMethod": self.payment_method,
            "MonthlyCharges": self.monthly_charges,
            "TotalCharges": self.total_charges,
        }


class RiskFactor(BaseModel):
    feature: str
    value: str
    direction: Literal["aumenta", "reduz"]
    impact: float = Field(description="Contribuição absoluta no logit do modelo")
    explanation: str


class Recommendation(BaseModel):
    priority: Literal["alta", "média", "baixa"]
    action: str
    reason: str


class PredictionResponse(BaseModel):
    request_id: str
    churn_probability: float = Field(ge=0, le=1)
    churn_percentage: str
    risk_level: Literal["baixo", "moderado", "alto"]
    decision_threshold: float = Field(ge=0, le=1)
    prediction: Literal["provável churn", "provável permanência"]
    factors: list[RiskFactor]
    recommendations: list[Recommendation]
    confidence_note: str
    model_source: Literal["modelo", "fallback"]
    latency_ms: float
    guardrail_warnings: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    model_loaded: bool
    version: str
