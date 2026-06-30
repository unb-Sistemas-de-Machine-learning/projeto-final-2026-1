"""Pipeline reproduzível de download, treino, avaliação e persistência."""

from __future__ import annotations

import argparse
import json
import logging
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.config import BASE_DIR, settings
from app.constants import (
    CATEGORICAL_FEATURES,
    DATASET_URL,
    MODEL_FEATURES,
    NUMERIC_FEATURES,
    TARGET,
)

logger = logging.getLogger(__name__)
DEFAULT_DATA_PATH = BASE_DIR / "data" / "raw" / "Telco-Customer-Churn.csv"


def download_dataset(destination: Path = DEFAULT_DATA_PATH) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        logger.info("Dataset já existe em %s", destination)
        return destination
    logger.info("Baixando dataset da IBM...")
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "RetentionAI/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())
    return destination


def load_dataset(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    frame = pd.read_csv(path)
    missing = set(MODEL_FEATURES + [TARGET]) - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset incompatível; colunas ausentes: {sorted(missing)}")
    frame["TotalCharges"] = pd.to_numeric(frame["TotalCharges"], errors="coerce")
    frame = frame.dropna(subset=[TARGET]).copy()
    target = frame[TARGET].map({"No": 0, "Yes": 1})
    if target.isna().any():
        raise ValueError("A coluna Churn contém rótulos desconhecidos.")
    return frame[MODEL_FEATURES], target.astype(int)


def build_pipeline() -> Pipeline:
    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )
    return Pipeline(
        [
            ("preprocessor", preprocessor),
            (
                "classifier",
                LogisticRegression(max_iter=1_000, random_state=42),
            ),
        ]
    )


def choose_threshold(y_true: pd.Series, probabilities: np.ndarray) -> float:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    beta_squared = 4.0
    scores = (
        (1 + beta_squared)
        * precision[:-1]
        * recall[:-1]
        / (beta_squared * precision[:-1] + recall[:-1] + 1e-12)
    )
    return float(thresholds[int(np.argmax(scores))])


def group_metrics(
    y_true: pd.Series, predictions: np.ndarray, groups: pd.Series
) -> dict[str, dict[str, float | int]]:
    result: dict[str, dict[str, float | int]] = {}
    for group in sorted(groups.astype(str).unique()):
        mask = groups.astype(str) == group
        group_y = y_true.loc[mask]
        group_pred = predictions[mask.to_numpy()]
        tn, fp, fn, tp = confusion_matrix(group_y, group_pred, labels=[0, 1]).ravel()
        result[group] = {
            "samples": int(mask.sum()),
            "recall": round(float(tp / (tp + fn)), 4) if tp + fn else 0.0,
            "false_positive_rate": round(float(fp / (fp + tn)), 4) if fp + tn else 0.0,
            "positive_prediction_rate": round(float(np.mean(group_pred)), 4),
        }
    return result


def train(data_path: Path, artifact_path: Path, metrics_path: Path) -> dict[str, object]:
    features, target = load_dataset(data_path)
    train_x, test_x, train_y, test_y = train_test_split(
        features,
        target,
        test_size=0.20,
        random_state=42,
        stratify=target,
    )
    pipeline = build_pipeline()
    pipeline.fit(train_x, train_y)
    probabilities = pipeline.predict_proba(test_x)[:, 1]
    threshold = choose_threshold(test_y, probabilities)
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(test_y, predictions).ravel()

    metrics: dict[str, object] = {
        "trained_at": datetime.now(UTC).isoformat(),
        "dataset": {
            "source": DATASET_URL,
            "rows_after_cleaning": int(len(features)),
            "positive_rate": round(float(target.mean()), 4),
            "license": "Apache License 2.0 (repositório oficial da IBM).",
        },
        "split": {
            "train_rows": int(len(train_x)),
            "test_rows": int(len(test_x)),
            "random_state": 42,
        },
        "decision_threshold": round(threshold, 4),
        "test": {
            "roc_auc": round(float(roc_auc_score(test_y, probabilities)), 4),
            "pr_auc": round(float(average_precision_score(test_y, probabilities)), 4),
            "precision": round(float(precision_score(test_y, predictions)), 4),
            "recall": round(float(recall_score(test_y, predictions)), 4),
            "f1": round(float(f1_score(test_y, predictions)), 4),
            "f2": round(float(fbeta_score(test_y, predictions, beta=2)), 4),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        },
        "fairness_slices": {
            "gender": group_metrics(test_y, predictions, test_x["gender"]),
            "senior_citizen": group_metrics(test_y, predictions, test_x["SeniorCitizen"]),
        },
    }
    artifact = {
        "pipeline": pipeline,
        "threshold": threshold,
        "metadata": {
            "version": "1.0.0",
            "trained_at": metrics["trained_at"],
            "features": MODEL_FEATURES,
        },
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Treina o modelo de churn.")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_PATH)
    parser.add_argument("--artifact", type=Path, default=settings.model_path)
    parser.add_argument("--metrics", type=Path, default=settings.metrics_path)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    data_path = download_dataset(args.data)
    metrics = train(data_path, args.artifact, args.metrics)
    print(json.dumps(metrics["test"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
