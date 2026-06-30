"""Agente que orquestra modelo, explicação, guardrails e ações de retenção."""

from __future__ import annotations

import time
import uuid

from app.model_service import ModelService
from app.monitoring import Monitor
from app.schemas import CustomerProfile, PredictionResponse, Recommendation


class RetentionAgent:
    def __init__(self, model: ModelService, monitor: Monitor) -> None:
        self.model = model
        self.monitor = monitor

    def analyze(self, profile: CustomerProfile) -> PredictionResponse:
        started_at = time.perf_counter()
        request_id = str(uuid.uuid4())
        record = profile.to_model_record()

        warnings = self._soft_guardrails(profile)
        probability, factors, source = self.model.predict(record)
        threshold = self.model.threshold
        risk_level = self._risk_level(probability, threshold)
        recommendations = self._retention_playbook(profile, probability)

        # Guardrail de saída: nunca expõe números fora do domínio ou resposta sem justificativa.
        probability = min(max(float(probability), 0.0), 1.0)
        if not factors:
            factors = [
                {
                    "feature": "Risco-base",
                    "value": "perfil sem sinal dominante",
                    "direction": "reduz",
                    "impact": 0.0,
                    "explanation": "Nenhum fator isolado dominou a estimativa.",
                }
            ]

        latency_ms = round((time.perf_counter() - started_at) * 1_000, 2)
        response = PredictionResponse(
            request_id=request_id,
            churn_probability=round(probability, 4),
            churn_percentage=f"{probability * 100:.1f}%",
            risk_level=risk_level,
            decision_threshold=round(threshold, 4),
            prediction=("provável churn" if probability >= threshold else "provável permanência"),
            factors=factors,
            recommendations=recommendations,
            confidence_note=self._confidence_note(probability, threshold, source, warnings),
            model_source=source,
            latency_ms=latency_ms,
            guardrail_warnings=warnings,
        )
        self.monitor.record(
            {
                "request_id": request_id,
                "risk_level": risk_level,
                "model_source": source,
                "latency_ms": latency_ms,
                "warning_count": len(warnings),
            }
        )
        return response

    @staticmethod
    def _risk_level(probability: float, threshold: float) -> str:
        if probability >= 0.60:
            return "alto"
        if probability >= threshold:
            return "moderado"
        return "baixo"

    @staticmethod
    def _soft_guardrails(profile: CustomerProfile) -> list[str]:
        warnings: list[str] = []
        expected_total = profile.monthly_charges * profile.tenure
        if profile.tenure == 0 and profile.total_charges > profile.monthly_charges:
            warnings.append(
                "Cobrança acumulada incomum para cliente com zero mês de contrato; "
                "confirme os dados."
            )
        elif profile.tenure >= 3 and expected_total > 0:
            relative_difference = abs(profile.total_charges - expected_total) / expected_total
            if relative_difference > 0.65:
                warnings.append(
                    "Cobrança acumulada diverge bastante de mensalidade × tempo; "
                    "descontos ou dados incorretos podem afetar a estimativa."
                )
        return warnings

    @staticmethod
    def _retention_playbook(profile: CustomerProfile, probability: float) -> list[Recommendation]:
        actions: list[Recommendation] = []
        priority = "alta" if probability >= 0.5 else "média"

        if profile.contract == "Month-to-month":
            actions.append(
                Recommendation(
                    priority=priority,
                    action="Oferecer migração voluntária para plano anual com benefício claro.",
                    reason="Contratos mensais têm menor barreira de saída.",
                )
            )
        if profile.tech_support == "No":
            actions.append(
                Recommendation(
                    priority=priority,
                    action="Agendar contato proativo de suporte e revisar problemas recorrentes.",
                    reason="Ausência de suporte pode ampliar atritos não resolvidos.",
                )
            )
        if profile.payment_method == "Electronic check":
            actions.append(
                Recommendation(
                    priority="média",
                    action="Oferecer débito automático, sem condicionar o atendimento à adesão.",
                    reason="A forma de pagamento aparece associada ao risco na amostra.",
                )
            )
        if profile.tenure <= 6:
            actions.append(
                Recommendation(
                    priority="alta" if probability >= 0.5 else "média",
                    action=(
                        "Executar uma jornada de boas-vindas e confirmar a ativação dos serviços."
                    ),
                    reason="Os primeiros meses são uma janela crítica para criar vínculo.",
                )
            )
        if profile.monthly_charges >= 85:
            actions.append(
                Recommendation(
                    priority="média",
                    action="Revisar aderência do pacote e remover serviços que não geram valor.",
                    reason="Cobrança mensal elevada pode aumentar sensibilidade a preço.",
                )
            )
        if not actions:
            actions.append(
                Recommendation(
                    priority="baixa",
                    action="Manter acompanhamento regular, sem oferta invasiva.",
                    reason="O perfil não acionou uma intervenção específica do playbook.",
                )
            )
        return actions[:3]

    @staticmethod
    def _confidence_note(
        probability: float, threshold: float, source: str, warnings: list[str]
    ) -> str:
        if source == "fallback":
            return (
                "Estimativa de contingência: o modelo não estava disponível. "
                "Use apenas para triagem e revise manualmente."
            )
        if warnings:
            return "Há inconsistências plausíveis nos dados. Confirme o cadastro antes de agir."
        if abs(probability - threshold) <= 0.05:
            return (
                "Caso próximo ao limiar de decisão; recomenda-se revisão humana antes do contato."
            )
        return (
            "Estimativa para apoio à decisão, não uma certeza. "
            "Combine-a com contexto e revisão humana."
        )
