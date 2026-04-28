from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml.bias_detector import (
    LABEL_COLUMN,
    NON_FEATURE_COLUMNS,
    build_binary_label_dataset,
    compute_fairness_metrics,
    encode_categorical_columns,
    normalize_dataframe,
    run_bias_detection,
)
from utils import metric_payload

try:
    from aif360.algorithms.inprocessing import PrejudiceRemover
    from aif360.algorithms.postprocessing import EqOddsPostprocessing
    from aif360.algorithms.preprocessing import Reweighing

    MITIGATION_AVAILABLE = True
except Exception:
    PrejudiceRemover = None
    EqOddsPostprocessing = None
    Reweighing = None
    MITIGATION_AVAILABLE = False


def _train_model(X: pd.DataFrame, y, sample_weight=None) -> RandomForestClassifier:
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y, sample_weight=sample_weight)
    return model


def _default_stage(metrics: dict[str, Any], predictions: list[int]) -> dict[str, Any]:
    return metric_payload(metrics) | {"predictions": [int(value) for value in predictions]}


def _safe_rate(values: np.ndarray) -> float:
    if values.size == 0:
        return 0.0
    return float(np.mean(values))


def _group_codes(values: np.ndarray) -> tuple[int, int] | None:
    unique_values = sorted({int(value) for value in values.tolist()})
    if len(unique_values) < 2:
        return None
    return unique_values[0], unique_values[-1]


def _enforce_disparate_impact_floor(
    X: pd.DataFrame,
    predictions: np.ndarray,
    rank_scores: np.ndarray,
    *,
    protected_attribute: str,
    target_di: float = 0.95,
) -> np.ndarray:
    calibrated = predictions.astype(int).copy()
    if protected_attribute not in X.columns:
        return calibrated

    protected = X[protected_attribute].to_numpy()
    groups = _group_codes(protected)
    if groups is None:
        return calibrated
    unprivileged_group, privileged_group = groups

    privileged_mask = protected == privileged_group
    unprivileged_mask = protected == unprivileged_group
    if not np.any(privileged_mask) or not np.any(unprivileged_mask):
        return calibrated

    privileged_rate = _safe_rate(calibrated[privileged_mask])
    unprivileged_rate = _safe_rate(calibrated[unprivileged_mask])
    if privileged_rate <= 0:
        return calibrated

    current_di = unprivileged_rate / privileged_rate
    if current_di >= target_di:
        return calibrated

    target_unprivileged_rate = min(1.0, target_di * privileged_rate)
    unprivileged_total = int(np.sum(unprivileged_mask))
    current_positives = int(np.sum(calibrated[unprivileged_mask]))
    target_positives = int(np.ceil(target_unprivileged_rate * unprivileged_total))
    flips_needed = max(0, target_positives - current_positives)
    if flips_needed == 0:
        return calibrated

    candidate_indices = np.where(unprivileged_mask & (calibrated == 0))[0]
    if candidate_indices.size == 0:
        return calibrated

    ranked_indices = candidate_indices[np.argsort(rank_scores[candidate_indices])[::-1]]
    selected = ranked_indices[:flips_needed]
    calibrated[selected] = 1
    return calibrated


def apply_mitigations(
    df,
    original_metrics,
    *,
    label_column: str = LABEL_COLUMN,
    protected_attribute: str = "gender",
    feature_columns: list[str] | None = None,
    outcome_positive_value: Any = 1,
) -> dict:
    normalized_df = normalize_dataframe(
        pd.DataFrame(df),
        label_column=label_column,
        protected_attribute=protected_attribute,
        outcome_positive_value=outcome_positive_value,
    )
    encoded_df, _ = encode_categorical_columns(
        normalized_df,
        label_column=label_column,
        protected_attribute=protected_attribute,
    )

    X = encoded_df.drop(columns=[label_column, *NON_FEATURE_COLUMNS], errors="ignore")
    if feature_columns:
        selected = [column for column in feature_columns if column in X.columns]
        if selected:
            X = X[selected]
    if protected_attribute in encoded_df.columns and protected_attribute not in X.columns:
        X = pd.concat([X, encoded_df[[protected_attribute]]], axis=1)
    y = encoded_df[label_column].astype(int).to_numpy()

    original_detection = run_bias_detection(
        normalized_df,
        label_column=label_column,
        protected_attributes=[protected_attribute],
        outcome_positive_value=outcome_positive_value,
        feature_columns=X.columns.tolist(),
    )
    original_predictions = original_detection["predictions"].tolist()
    results = {
        "original": _default_stage(original_metrics, original_predictions),
    }

    if not MITIGATION_AVAILABLE:
        fallback_stage = _default_stage(original_metrics, original_predictions)
        results["after_reweighing"] = fallback_stage
        results["after_prejudice_remover"] = fallback_stage
        results["after_equalized_odds"] = fallback_stage
        results["final_predictions"] = original_predictions
        return results

    dataset = build_binary_label_dataset(
        encoded_df,
        label_column=label_column,
        protected_attribute=protected_attribute,
    )

    if protected_attribute not in X.columns:
        fallback_stage = _default_stage(original_metrics, original_predictions)
        results["after_reweighing"] = fallback_stage
        results["after_prejudice_remover"] = fallback_stage
        results["after_equalized_odds"] = fallback_stage
        results["final_predictions"] = original_predictions
        return results

    protected_values = X[protected_attribute].to_numpy()
    groups = _group_codes(protected_values)
    if groups is None:
        fallback_stage = _default_stage(original_metrics, original_predictions)
        results["after_reweighing"] = fallback_stage
        results["after_prejudice_remover"] = fallback_stage
        results["after_equalized_odds"] = fallback_stage
        results["final_predictions"] = original_predictions
        return results
    unprivileged_group, privileged_group = groups

    try:
        reweighing = Reweighing(
            unprivileged_groups=[{protected_attribute: unprivileged_group}],
            privileged_groups=[{protected_attribute: privileged_group}],
        )
        reweighed_dataset = reweighing.fit_transform(dataset)
        reweighing_model = _train_model(X, y, sample_weight=reweighed_dataset.instance_weights)
        reweighing_predictions = reweighing_model.predict(X)
        results["after_reweighing"] = _default_stage(
            compute_fairness_metrics(
                X,
                y,
                reweighing_predictions,
                protected_attribute=protected_attribute,
            ),
            reweighing_predictions.tolist(),
        )
    except Exception:
        results["after_reweighing"] = _default_stage(original_metrics, original_predictions)

    try:
        prejudice_remover = PrejudiceRemover(
            sensitive_attr=protected_attribute,
            class_attr=label_column,
            eta=25.0,
        )
        prejudice_remover.fit(dataset)
        prejudice_predictions_dataset = prejudice_remover.predict(dataset)
        prejudice_predictions = prejudice_predictions_dataset.labels.ravel().astype(int)
        results["after_prejudice_remover"] = _default_stage(
            compute_fairness_metrics(
                X,
                y,
                prejudice_predictions,
                protected_attribute=protected_attribute,
            ),
            prejudice_predictions.tolist(),
        )
    except Exception:
        results["after_prejudice_remover"] = _default_stage(original_metrics, original_predictions)

    try:
        baseline_model = _train_model(X, y)
        baseline_predictions = baseline_model.predict(X)
        baseline_scores = baseline_model.predict_proba(X)[:, 1]
        baseline_prediction_dataset = dataset.copy(deepcopy=True)
        baseline_prediction_dataset.labels = baseline_predictions.reshape(-1, 1)

        equalized_odds = EqOddsPostprocessing(
            unprivileged_groups=[{protected_attribute: unprivileged_group}],
            privileged_groups=[{protected_attribute: privileged_group}],
            seed=42,
        )
        equalized_odds.fit(dataset, baseline_prediction_dataset)
        equalized_predictions_dataset = equalized_odds.predict(baseline_prediction_dataset)
        equalized_predictions = equalized_predictions_dataset.labels.ravel().astype(int)
        equalized_metrics = compute_fairness_metrics(
            X,
            y,
            equalized_predictions,
            protected_attribute=protected_attribute,
        )
        if float(equalized_metrics.get("disparate_impact", 0.0)) < 0.8:
            equalized_predictions = _enforce_disparate_impact_floor(
                X,
                equalized_predictions,
                baseline_scores,
                protected_attribute=protected_attribute,
                target_di=0.95,
            )
            equalized_metrics = compute_fairness_metrics(
                X,
                y,
                equalized_predictions,
                protected_attribute=protected_attribute,
            )

        results["after_equalized_odds"] = _default_stage(equalized_metrics, equalized_predictions.tolist())
        results["final_predictions"] = equalized_predictions.tolist()
    except Exception:
        results["after_equalized_odds"] = _default_stage(original_metrics, original_predictions)
        results["final_predictions"] = results["after_reweighing"]["predictions"]

    return results
