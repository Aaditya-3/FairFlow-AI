from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

from sdg_mapping import build_sdg_mapping

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
DOMAIN_PROFILES: dict[str, dict[str, Any]] = {
    "hiring": {
        "keywords": {
            "resume",
            "candidate",
            "hired",
            "hire",
            "shortlist",
            "experience",
            "university",
        },
        "model_family": "hiring_random_forest",
    },
    "lending": {
        "keywords": {
            "loan",
            "approved",
            "credit",
            "income",
            "debt",
            "mortgage",
            "default",
        },
        "model_family": "lending_gradient_boosting",
    },
    "care_delivery": {
        "keywords": {
            "triage",
            "patient",
            "care",
            "diagnosis",
            "insurance",
            "readmission",
            "severity",
        },
        "model_family": "care_delivery_logistic_regression",
    },
}


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _infer_domain(df: pd.DataFrame, target_column: str) -> str:
    tokens = {target_column.lower()}
    for column in df.columns:
        tokens.update(part for part in column.lower().replace("-", "_").split("_") if part)

    best_domain = "hiring"
    best_score = -1
    for domain, profile in DOMAIN_PROFILES.items():
        score = len(tokens.intersection(profile["keywords"]))
        if score > best_score:
            best_domain = domain
            best_score = score
    return best_domain


def _build_domain_model(domain: str) -> tuple[Pipeline, str]:
    if domain == "lending":
        return (
            Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    ("model", GradientBoostingClassifier(random_state=42)),
                ]
            ),
            DOMAIN_PROFILES[domain]["model_family"],
        )
    if domain == "care_delivery":
        return (
            Pipeline(
                steps=[
                    ("imputer", SimpleImputer(strategy="median")),
                    (
                        "model",
                        LogisticRegression(
                            class_weight="balanced",
                            max_iter=1000,
                            solver="lbfgs",
                        ),
                    ),
                ]
            ),
            DOMAIN_PROFILES[domain]["model_family"],
        )
    return (
        Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("model", RandomForestClassifier(n_estimators=200, random_state=42)),
            ]
        ),
        DOMAIN_PROFILES["hiring"]["model_family"],
    )


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


def _coerce_remote_shap(
    remote_shap: Any,
    feature_columns: list[str],
) -> tuple[list[dict[str, float]], list[str]]:
    if isinstance(remote_shap, dict):
        rows = [
            {"feature": str(feature), "value": abs(_safe_float(value))}
            for feature, value in remote_shap.items()
            if str(feature) in feature_columns
        ]
    elif isinstance(remote_shap, list):
        rows = []
        for item in remote_shap:
            if isinstance(item, dict) and "feature" in item:
                rows.append(
                    {
                        "feature": str(item["feature"]),
                        "value": abs(_safe_float(item.get("value"))),
                    }
                )
    else:
        rows = []

    rows.sort(key=lambda item: item["value"], reverse=True)
    if not rows:
        raise ValueError("Vertex endpoint did not return SHAP feature attributions.")
    return rows[:10], [row["feature"] for row in rows[:3]]


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


def _row_label(row: pd.Series, row_index: int) -> str:
    for key in ("candidate_id", "patient_id", "applicant_id", "id", "name", "full_name"):
        if key in row and str(row[key]).strip():
            return str(row[key])
    return f"row-{row_index + 1}"


def _build_candidate_flags(
    normalized: pd.DataFrame,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    protected_binary: np.ndarray,
    sensitive_column: str,
    shap_top3: list[str],
    protected_mapping: dict[int, str],
) -> list[dict[str, Any]]:
    flagged: list[dict[str, Any]] = []
    ranked_indices = np.argsort(probabilities)
    for row_index in ranked_indices:
        if len(flagged) >= 5:
            break
        if int(predictions[row_index]) == 1 and probabilities[row_index] > 0.35:
            continue
        row = normalized.iloc[int(row_index)]
        group_value = protected_mapping.get(int(protected_binary[row_index]), "Unknown")
        reasons = [
            feature
            for feature in shap_top3
            if feature in normalized.columns and str(row.get(feature, "")).strip()
        ][:3]
        flagged.append(
            {
                "row_id": _row_label(row, int(row_index)),
                "protected_group": group_value,
                "sensitive_attribute": sensitive_column,
                "predicted_decision": int(predictions[row_index]),
                "approval_probability": round(float(probabilities[row_index]), 4),
                "primary_drivers": reasons,
                "recommendation_seed": (
                    "Review this decision with protected-attribute proxies masked "
                    "and document a human override if qualifications support it."
                ),
            }
        )
    return flagged


def _build_counterfactuals(
    feature_frame: pd.DataFrame,
    normalized: pd.DataFrame,
    predictions: np.ndarray,
    probabilities: np.ndarray,
    shap_top3: list[str],
) -> list[dict[str, Any]]:
    counterfactuals: list[dict[str, Any]] = []
    negative_indices = [index for index, prediction in enumerate(predictions) if int(prediction) == 0]
    for row_index in negative_indices[:5]:
        row = normalized.iloc[row_index]
        changes = []
        for feature in shap_top3:
            if feature not in feature_frame.columns:
                continue
            series = feature_frame[feature].astype(float)
            current_value = float(feature_frame.iloc[row_index][feature])
            median_value = float(series.median())
            if current_value == median_value:
                continue
            changes.append(
                {
                    "feature": feature,
                    "current_value": current_value,
                    "suggested_value": median_value,
                    "direction": "increase" if median_value > current_value else "decrease",
                }
            )
            if len(changes) == 2:
                break
        if not changes:
            continue
        counterfactuals.append(
            {
                "row_id": _row_label(row, row_index),
                "current_probability": round(float(probabilities[row_index]), 4),
                "suggested_changes": changes,
            }
        )
    return counterfactuals


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


def analyze_bias(
    dataset_path: str,
    model_artifact_path: str | None = None,
    status_callback: Any | None = None,
    prediction_provider: Any | None = None,
) -> dict[str, Any]:
    def publish(stage: str, status: str = "processing") -> None:
        if status_callback is not None:
            status_callback(stage, status)

    dataframe = pd.read_csv(dataset_path)
    dataframe.columns = [column.strip() for column in dataframe.columns]

    target_column = _pick_target_column(dataframe)
    sensitive_column = _pick_sensitive_column(dataframe, target_column)
    domain = _infer_domain(dataframe, target_column)
    publish("preparing_features")

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

    remote_prediction = None
    if prediction_provider is not None:
        publish("calling_vertex_endpoint")
        remote_prediction = prediction_provider(feature_frame, domain)

    loaded_model = None if remote_prediction else _load_model(model_artifact_path)
    if remote_prediction:
        predictions = np.asarray(remote_prediction["predictions"]).astype(int)
        probabilities = np.asarray(remote_prediction["probabilities"]).astype(float)
        shap_values, shap_top3 = _coerce_remote_shap(
            remote_prediction.get("shap_values"),
            feature_columns,
        )
        model_family = remote_prediction.get("model_family", "vertex_endpoint_model")
        analysis_backend = "vertex_endpoint"
    elif loaded_model is None:
        model, model_family = _build_domain_model(domain)
        publish(f"training_{domain}_model")
        model.fit(feature_frame, labels)
        publish("running_predictions")
        predictions = np.asarray(model.predict(feature_frame)).astype(int)
        if hasattr(model, "predict_proba"):
            probabilities = np.asarray(model.predict_proba(feature_frame))[:, -1]
        else:
            probabilities = predictions.astype(float)
        publish("generating_shap")
        shap_values, shap_top3 = _compute_shap_summary(model, feature_frame)
        analysis_backend = "local_domain_model"
    else:
        model = loaded_model
        model_family = "uploaded_model_artifact"
        publish("running_predictions")
        predictions = np.asarray(model.predict(feature_frame)).astype(int)
        if hasattr(model, "predict_proba"):
            probabilities = np.asarray(model.predict_proba(feature_frame))[:, -1]
        else:
            probabilities = predictions.astype(float)
        publish("generating_shap")
        shap_values, shap_top3 = _compute_shap_summary(model, feature_frame)
        analysis_backend = "uploaded_artifact"
    publish("building_causal_graph")
    causal_graph_json, causal_pathway = _build_causal_graph(
        feature_frame,
        protected_binary,
        target_column,
        sensitive_column,
        shap_top3,
    )
    publish("computing_fairness_metrics")
    fairness_metrics = _compute_fairness_metrics(
        labels,
        predictions,
        protected_binary,
        probabilities,
        feature_frame,
    )
    bias_score = _calculate_bias_score(fairness_metrics)
    candidate_flags = _build_candidate_flags(
        normalized,
        predictions,
        probabilities,
        protected_binary,
        sensitive_column,
        shap_top3,
        protected_mapping,
    )
    counterfactuals = _build_counterfactuals(
        feature_frame,
        normalized,
        predictions,
        probabilities,
        shap_top3,
    )

    return {
        "domain": domain,
        "model_family": model_family,
        "analysis_backend": analysis_backend,
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
        "candidate_flags": candidate_flags,
        "counterfactuals": counterfactuals,
        "sdg_mapping": build_sdg_mapping(fairness_metrics, domain),
        "row_count": int(len(normalized)),
        "column_count": int(len(normalized.columns)),
        "encoders": encoders,
    }
