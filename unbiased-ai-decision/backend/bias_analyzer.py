from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import brier_score_loss
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

try:
    import joblib
except Exception:
    joblib = None

try:
    import shap
except Exception:
    shap = None


LABEL_CANDIDATES = ("hired", "label", "target", "approved", "decision", "outcome")
SENSITIVE_CANDIDATES = (
    "gender",
    "sex",
    "race",
    "ethnicity",
    "age_group",
    "age",
    "insurance_status",
    "zip_code",
)
NON_FEATURE_COLUMNS = {"id", "name", "full_name", "candidate_id"}


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _pick_target_column(df: pd.DataFrame) -> str:
    lowered = {column.lower(): column for column in df.columns}
    for candidate in LABEL_CANDIDATES:
        if candidate in lowered:
            return lowered[candidate]
    raise ValueError(
        "No supported target column found. Expected one of: "
        + ", ".join(LABEL_CANDIDATES)
    )


def _pick_sensitive_column(df: pd.DataFrame, target_column: str) -> str:
    lowered = {column.lower(): column for column in df.columns}
    for candidate in SENSITIVE_CANDIDATES:
        if candidate in lowered and lowered[candidate] != target_column:
            return lowered[candidate]

    fallback_candidates = [
        column
        for column in df.columns
        if column != target_column and df[column].dtype == object and df[column].nunique(dropna=True) >= 2
    ]
    if fallback_candidates:
        return fallback_candidates[0]
    raise ValueError("No protected attribute column found for fairness analysis.")


def _coerce_binary_label(series: pd.Series) -> pd.Series:
    lowered = series.astype(str).str.strip().str.lower()
    mapped = lowered.replace(
        {
            "1": 1,
            "0": 0,
            "true": 1,
            "false": 0,
            "yes": 1,
            "no": 0,
            "approved": 1,
            "rejected": 0,
            "hire": 1,
            "hired": 1,
        }
    )
    numeric = pd.to_numeric(mapped, errors="coerce")
    if numeric.notna().sum() != len(series):
        factorized, _ = pd.factorize(lowered)
        numeric = pd.Series(factorized, index=series.index)
    return (numeric > 0).astype(int)


def _binarize_sensitive(series: pd.Series) -> tuple[np.ndarray, dict[int, str]]:
    clean = series.fillna("Unknown")
    if pd.api.types.is_numeric_dtype(clean):
        threshold = float(clean.median())
        binary = (clean.astype(float) > threshold).astype(int).to_numpy()
        mapping = {0: f"<= {threshold:.2f}", 1: f"> {threshold:.2f}"}
        return binary, mapping

    encoded = clean.astype(str).str.strip()
    top_groups = list(encoded.value_counts().index[:2])
    if len(top_groups) == 1:
        top_groups.append("Other")
    binary = encoded.apply(lambda value: 1 if value == top_groups[0] else 0).to_numpy()
    mapping = {0: top_groups[1], 1: top_groups[0]}
    return binary, mapping


def _encode_features(df: pd.DataFrame, excluded: set[str]) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    encoded = df.copy()
    encoders: dict[str, LabelEncoder] = {}
    for column in encoded.columns:
        if column in excluded:
            continue
        if encoded[column].dtype == object:
            encoder = LabelEncoder()
            encoded[column] = encoder.fit_transform(encoded[column].fillna("Unknown").astype(str))
            encoders[column] = encoder
    return encoded, encoders


def _group_stats(y_true: np.ndarray, y_pred: np.ndarray, group: np.ndarray, target_group: int) -> dict[str, float]:
    mask = group == target_group
    if mask.sum() == 0:
        return {"selection_rate": 0.0, "tpr": 0.0, "fpr": 0.0}

    group_true = y_true[mask]
    group_pred = y_pred[mask]
    positives = group_true == 1
    negatives = group_true == 0

    selection = float(np.mean(group_pred == 1))
    tpr = float(np.mean(group_pred[positives] == 1)) if positives.any() else 0.0
    fpr = float(np.mean(group_pred[negatives] == 1)) if negatives.any() else 0.0

    return {"selection_rate": selection, "tpr": tpr, "fpr": fpr}


def _compute_individual_fairness(X: pd.DataFrame, predictions: np.ndarray) -> float:
    if len(X) < 2:
        return 1.0

    neighbors = min(6, len(X))
    nn = NearestNeighbors(n_neighbors=neighbors)
    nn.fit(X)
    distances, indices = nn.kneighbors(X)

    mismatches: list[float] = []
    for row_index, row_neighbors in enumerate(indices):
        for neighbor_index in row_neighbors[1:]:
            mismatches.append(abs(int(predictions[row_index]) - int(predictions[neighbor_index])))
    if not mismatches:
        return 1.0
    return round(1.0 - float(np.mean(mismatches)), 4)


def _compute_calibration_error(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    return round(float(brier_score_loss(y_true, probabilities)), 4)


def _compute_fairness_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    protected_binary: np.ndarray,
    probabilities: np.ndarray,
    encoded_features: pd.DataFrame,
) -> dict[str, Any]:
    privileged = _group_stats(y_true, y_pred, protected_binary, 1)
    unprivileged = _group_stats(y_true, y_pred, protected_binary, 0)

    privileged_selection = privileged["selection_rate"] or 1e-9
    demographic_parity = unprivileged["selection_rate"] - privileged["selection_rate"]
    equalized_odds = 0.5 * (
        (unprivileged["tpr"] - privileged["tpr"]) + (unprivileged["fpr"] - privileged["fpr"])
    )
    disparate_impact = unprivileged["selection_rate"] / privileged_selection
    individual_fairness = _compute_individual_fairness(encoded_features, y_pred)
    calibration_error = _compute_calibration_error(y_true, probabilities)

    return {
        "demographic_parity": round(float(demographic_parity), 4),
        "equalized_odds": round(float(equalized_odds), 4),
        "individual_fairness": individual_fairness,
        "calibration_error": calibration_error,
        "disparate_impact": round(float(disparate_impact), 4),
        "selection_rates": {
            "0": round(float(np.mean(y_pred[protected_binary == 0] == 1)), 4)
            if np.any(protected_binary == 0)
            else 0.0,
            "1": round(float(np.mean(y_pred[protected_binary == 1] == 1)), 4)
            if np.any(protected_binary == 1)
            else 0.0,
        },
    }


def _calculate_bias_score(metrics: dict[str, Any]) -> float:
    parity_penalty = min(1.0, abs(metrics["demographic_parity"]) / 0.5)
    odds_penalty = min(1.0, abs(metrics["equalized_odds"]) / 0.5)
    impact_penalty = min(1.0, abs(1 - metrics["disparate_impact"]))
    calibration_penalty = min(1.0, metrics["calibration_error"])
    individual_penalty = 1 - min(1.0, metrics["individual_fairness"])

    weighted = (
        0.30 * parity_penalty
        + 0.25 * odds_penalty
        + 0.20 * impact_penalty
        + 0.15 * calibration_penalty
        + 0.10 * individual_penalty
    )
    return round(float(weighted * 100), 2)


def _compute_shap_summary(model: Any, feature_frame: pd.DataFrame) -> tuple[list[dict[str, float]], list[str]]:
    try:
        if shap is None:
            raise RuntimeError("shap is not installed")
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(feature_frame)
        if isinstance(shap_values, list):
            values = np.array(shap_values[-1])
        else:
            values = np.array(shap_values)
        if values.ndim == 3:
            values = values[:, :, -1]
        mean_abs = np.abs(values).mean(axis=0)
    except Exception:
        if hasattr(model, "feature_importances_"):
            mean_abs = np.asarray(model.feature_importances_)
        else:
            mean_abs = np.zeros(feature_frame.shape[1], dtype=float)

    shap_rows = [
        {"feature": feature, "value": round(float(mean_abs[index]), 6)}
        for index, feature in enumerate(feature_frame.columns)
    ]
    shap_rows.sort(key=lambda item: item["value"], reverse=True)
    return shap_rows[:10], [row["feature"] for row in shap_rows[:3]]


def _build_causal_graph(
    feature_frame: pd.DataFrame,
    protected_series: np.ndarray,
    target_column: str,
    sensitive_column: str,
    shap_top3: list[str],
) -> tuple[dict[str, Any], str]:
    nodes = [{"id": sensitive_column}, {"id": target_column}]
    edges: list[dict[str, Any]] = [{"source": sensitive_column, "target": target_column, "weight": 0.0}]

    pathway = "No strong causal proxy pathway detected."
    protected_numeric = protected_series.astype(float)

    for feature in shap_top3:
        if feature not in feature_frame.columns:
            continue
        correlation = abs(np.corrcoef(feature_frame[feature].astype(float), protected_numeric)[0, 1])
        if np.isnan(correlation):
            correlation = 0.0
        nodes.append({"id": feature})
        edges.append({"source": sensitive_column, "target": feature, "weight": round(float(correlation), 4)})
        edges.append({"source": feature, "target": target_column, "weight": round(float(max(correlation, 0.1)), 4)})
        if correlation >= 0.1 and pathway == "No strong causal proxy pathway detected.":
            pathway = f"{sensitive_column} -> {feature} -> {target_column}"

    deduped_nodes = list({node["id"]: node for node in nodes}.values())
    return {"nodes": deduped_nodes, "edges": edges}, pathway


def _load_model(model_artifact_path: str | None):
    if not model_artifact_path:
        return None

    artifact_path = Path(model_artifact_path)
    if not artifact_path.exists():
        return None

    if joblib is None:
        return None

    try:
        return joblib.load(artifact_path)
    except Exception:
        return None


def analyze_bias(dataset_path: str, model_artifact_path: str | None = None) -> dict[str, Any]:
    dataframe = pd.read_csv(dataset_path)
    dataframe.columns = [column.strip() for column in dataframe.columns]

    target_column = _pick_target_column(dataframe)
    sensitive_column = _pick_sensitive_column(dataframe, target_column)

    normalized = dataframe.copy()
    for column in normalized.columns:
        if normalized[column].dtype == object:
            normalized[column] = normalized[column].fillna("Unknown").astype(str).str.strip()
        else:
            normalized[column] = normalized[column].fillna(0)

    normalized[target_column] = _coerce_binary_label(normalized[target_column])
    protected_binary, protected_mapping = _binarize_sensitive(normalized[sensitive_column])

    excluded = {target_column, *NON_FEATURE_COLUMNS}
    encoded, encoders = _encode_features(normalized, excluded)
    feature_columns = [column for column in encoded.columns if column not in excluded]
    feature_frame = encoded[feature_columns]
    labels = normalized[target_column].to_numpy(dtype=int)

    loaded_model = _load_model(model_artifact_path)
    if loaded_model is None:
        model = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
            ]
        )
        model.fit(feature_frame, labels)
    else:
        model = loaded_model

    predictions = np.asarray(model.predict(feature_frame)).astype(int)
    if hasattr(model, "predict_proba"):
        probabilities = np.asarray(model.predict_proba(feature_frame))[:, -1]
    else:
        probabilities = predictions.astype(float)

    shap_values, shap_top3 = _compute_shap_summary(model, feature_frame)
    causal_graph_json, causal_pathway = _build_causal_graph(
        feature_frame,
        protected_binary,
        target_column,
        sensitive_column,
        shap_top3,
    )
    fairness_metrics = _compute_fairness_metrics(
        labels,
        predictions,
        protected_binary,
        probabilities,
        feature_frame,
    )
    bias_score = _calculate_bias_score(fairness_metrics)

    return {
        "bias_score": bias_score,
        "fairness_metrics": fairness_metrics,
        "shap_values": shap_values,
        "shap_top3": shap_top3,
        "causal_graph_json": causal_graph_json,
        "causal_pathway": causal_pathway,
        "demographic_parity": fairness_metrics["demographic_parity"],
        "equalized_odds": fairness_metrics["equalized_odds"],
        "individual_fairness": fairness_metrics["individual_fairness"],
        "calibration_error": fairness_metrics["calibration_error"],
        "disparate_impact": fairness_metrics["disparate_impact"],
        "sensitive_attribute": sensitive_column,
        "sensitive_groups": protected_mapping,
        "target_column": target_column,
        "dataset_name": Path(dataset_path).name,
        "model_loaded_from_artifact": bool(model_artifact_path and loaded_model is not None),
        "row_count": int(len(normalized)),
        "column_count": int(len(normalized.columns)),
        "encoders": encoders,
    }
