"""Carregamento, inferência e explicação local do modelo de churn."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.constants import CATEGORICAL_FEATURES, MODEL_FEATURES

logger = logging.getLogger(__name__)

FEATURE_LABELS = {
    "tenure": "Tempo como cliente",
    "MonthlyCharges": "Cobrança mensal",
    "TotalCharges": "Cobrança acumulada",
    "gender": "Gênero",
    "SeniorCitizen": "Pessoa idosa",
    "Partner": "Possui parceiro(a)",
    "Dependents": "Possui dependentes",
    "PhoneService": "Serviço telefônico",
    "MultipleLines": "Múltiplas linhas",
    "InternetService": "Tipo de internet",
    "OnlineSecurity": "Segurança online",
    "OnlineBackup": "Backup online",
    "DeviceProtection": "Proteção do dispositivo",
    "TechSupport": "Suporte técnico",
    "StreamingTV": "Streaming de TV",
    "StreamingMovies": "Streaming de filmes",
    "Contract": "Contrato",
    "PaperlessBilling": "Fatura digital",
    "PaymentMethod": "Forma de pagamento",
}


class ModelService:
    """Isola o artefato de ML e degrada com segurança quando ele não está disponível."""

    def __init__(self, artifact_path: Path) -> None:
        self.artifact_path = artifact_path
        self.artifact: dict[str, Any] | None = None
        self.load_error: str | None = None
        self.load()

    @property
    def available(self) -> bool:
        return self.artifact is not None

    @property
    def threshold(self) -> float:
        return float(self.artifact["threshold"]) if self.artifact else 0.5

    def load(self) -> None:
        try:
            artifact = joblib.load(self.artifact_path)
            required = {"pipeline", "threshold", "metadata"}
            if not isinstance(artifact, dict) or not required.issubset(artifact):
                raise ValueError("artefato incompatível")
            self.artifact = artifact
            self.load_error = None
            logger.info("Modelo carregado de %s", self.artifact_path)
        except Exception as exc:  # fallback é parte explícita do contrato
            self.artifact = None
            self.load_error = type(exc).__name__
            logger.warning("Modelo indisponível; fallback será usado: %s", type(exc).__name__)

    def predict(self, record: dict[str, object]) -> tuple[float, list[dict[str, object]], str]:
        if not self.artifact:
            probability, factors = self._fallback(record)
            return probability, factors, "fallback"

        try:
            frame = pd.DataFrame([record], columns=MODEL_FEATURES)
            pipeline = self.artifact["pipeline"]
            probability = float(pipeline.predict_proba(frame)[0, 1])
            if not math.isfinite(probability):
                raise ValueError("probabilidade inválida")
            factors = self._explain(frame, record)
            return min(max(probability, 0.0), 1.0), factors, "modelo"
        except Exception as exc:
            logger.exception("Falha durante inferência; usando fallback: %s", type(exc).__name__)
            probability, factors = self._fallback(record)
            return probability, factors, "fallback"

    def _explain(self, frame: pd.DataFrame, record: dict[str, object]) -> list[dict[str, object]]:
        pipeline = self.artifact["pipeline"]
        preprocessor = pipeline.named_steps["preprocessor"]
        classifier = pipeline.named_steps["classifier"]
        transformed = preprocessor.transform(frame)
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        values = np.asarray(transformed)[0]
        coefficients = classifier.coef_[0]
        names = preprocessor.get_feature_names_out()
        contributions = values * coefficients

        active = [
            (str(name), float(contribution))
            for name, contribution, value in zip(names, contributions, values, strict=True)
            if abs(float(value)) > 1e-12
        ]
        active.sort(key=lambda item: abs(item[1]), reverse=True)
        return [
            self._format_factor(name, contribution, record) for name, contribution in active[:4]
        ]

    @staticmethod
    def _format_factor(
        transformed_name: str, contribution: float, record: dict[str, object]
    ) -> dict[str, object]:
        name = transformed_name.split("__", 1)[-1]
        feature = name
        for candidate in CATEGORICAL_FEATURES:
            if name.startswith(f"{candidate}_"):
                feature = candidate
                break
        value = record[feature]
        if feature == "tenure":
            display_value = f"{value} meses"
        elif feature in {"MonthlyCharges", "TotalCharges"}:
            display_value = (
                f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )
        else:
            display_value = str(value)
        direction = "aumenta" if contribution > 0 else "reduz"
        return {
            "feature": FEATURE_LABELS.get(feature, feature),
            "value": display_value,
            "direction": direction,
            "impact": round(abs(contribution), 4),
            "explanation": f"Este valor {direction} o risco estimado pelo modelo.",
        }

    @staticmethod
    def _fallback(
        record: dict[str, object],
    ) -> tuple[float, list[dict[str, object]]]:
        """Heurística conservadora e transparente para indisponibilidade do modelo."""
        score = 0.20
        rules: list[tuple[str, str, float, str]] = []

        def apply(feature: str, explanation: str, weight: float) -> None:
            nonlocal score
            score += weight
            rules.append((feature, str(record[feature]), weight, explanation))

        if record["Contract"] == "Month-to-month":
            apply("Contract", "Contrato mensal aumenta a facilidade de saída.", 0.22)
        elif record["Contract"] == "Two year":
            apply("Contract", "Contrato de dois anos indica maior vínculo.", -0.16)
        if int(record["tenure"]) < 12:
            apply("tenure", "Clientes novos ainda têm pouco vínculo.", 0.15)
        elif int(record["tenure"]) >= 48:
            apply("tenure", "Relacionamento longo indica maior retenção.", -0.10)
        if record["InternetService"] == "Fiber optic":
            apply("InternetService", "Fibra aparece associada a maior risco na amostra.", 0.07)
        if record["TechSupport"] == "No":
            apply("TechSupport", "Ausência de suporte pode elevar fricção.", 0.06)
        if record["PaymentMethod"] == "Electronic check":
            apply("PaymentMethod", "Cheque eletrônico é um sinal de risco na amostra.", 0.08)

        probability = min(max(score, 0.05), 0.90)
        rules.sort(key=lambda item: abs(item[2]), reverse=True)
        factors = [
            {
                "feature": FEATURE_LABELS[feature],
                "value": value,
                "direction": "aumenta" if weight > 0 else "reduz",
                "impact": round(abs(weight), 4),
                "explanation": explanation,
            }
            for feature, value, weight, explanation in rules[:4]
        ]
        return probability, factors
