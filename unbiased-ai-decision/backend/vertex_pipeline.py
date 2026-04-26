from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud import aiplatform
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from bias_analyzer import analyze_bias
from firebase_config import require_firestore


def vertex_status() -> str:
    if os.getenv("VERTEX_ENDPOINT_ID") and os.getenv("VERTEX_PROJECT_ID") and os.getenv("VERTEX_REGION"):
        return "endpoint_ready"
    required = [
        os.getenv("VERTEX_PROJECT_ID"),
        os.getenv("VERTEX_REGION"),
        os.getenv("VERTEX_STAGING_BUCKET"),
    ]
    return "job_ready" if all(required) else "not_configured"


def _vertex_endpoint_resource_name() -> str | None:
    endpoint_id = os.getenv("VERTEX_ENDPOINT_ID")
    project = os.getenv("VERTEX_PROJECT_ID")
    region = os.getenv("VERTEX_REGION")
    if not endpoint_id or not project or not region:
        return None
    if endpoint_id.startswith("projects/"):
        return endpoint_id
    return f"projects/{project}/locations/{region}/endpoints/{endpoint_id}"


def _parse_vertex_prediction_item(item: Any) -> tuple[int, float, dict[str, float]]:
    if isinstance(item, (int, float, bool)):
        prediction = int(float(item) >= 0.5)
        return prediction, float(item), {}
    if not isinstance(item, dict):
        raise ValueError("Vertex endpoint returned an unsupported prediction shape.")

    probability = item.get("probability", item.get("score", item.get("positive_probability")))
    prediction = item.get("prediction", item.get("predicted_label", item.get("label")))
    if prediction is None and probability is not None:
        prediction = int(float(probability) >= 0.5)
    if probability is None:
        probability = float(prediction or 0)
    if isinstance(prediction, str):
        prediction = 1 if prediction.lower() in {"1", "true", "yes", "approved", "hire", "hired"} else 0

    shap_values = (
        item.get("shap_values")
        or item.get("feature_attributions")
        or item.get("attributions")
        or {}
    )
    return int(prediction), float(probability), shap_values


def _predict_with_vertex_endpoint(feature_frame, domain: str) -> dict[str, Any] | None:
    endpoint_name = _vertex_endpoint_resource_name()
    if endpoint_name is None:
        return None

    project = os.environ["VERTEX_PROJECT_ID"]
    region = os.environ["VERTEX_REGION"]
    aiplatform.init(project=project, location=region)
    endpoint = aiplatform.Endpoint(endpoint_name=endpoint_name)
    instances = feature_frame.astype(float).to_dict(orient="records")
    response = endpoint.predict(
        instances=instances,
        parameters={"domain": domain, "return_explanations": True},
    )

    predictions: list[int] = []
    probabilities: list[float] = []
    shap_totals: dict[str, float] = {}
    for item in response.predictions:
        prediction, probability, shap_values = _parse_vertex_prediction_item(item)
        predictions.append(prediction)
        probabilities.append(probability)
        if isinstance(shap_values, dict):
            for feature, value in shap_values.items():
                shap_totals[str(feature)] = shap_totals.get(str(feature), 0.0) + abs(float(value))

    if not predictions:
        raise ValueError("Vertex endpoint returned no predictions.")

    shap_summary = [
        {"feature": feature, "value": value / len(predictions)}
        for feature, value in shap_totals.items()
    ]
    return {
        "predictions": predictions,
        "probabilities": probabilities,
        "shap_values": shap_summary,
        "model_family": f"vertex_endpoint_{domain}",
    }


def _submit_vertex_custom_job(dataset_path: str, model_artifact_path: str | None) -> str | None:
    if vertex_status() not in {"job_ready", "endpoint_ready"}:
        return None

    if not dataset_path.startswith("gs://"):
        return None

    project = os.environ["VERTEX_PROJECT_ID"]
    region = os.environ["VERTEX_REGION"]
    staging_bucket = os.environ["VERTEX_STAGING_BUCKET"]
    image_uri = os.getenv(
        "VERTEX_TRAINING_IMAGE",
        "us-docker.pkg.dev/vertex-ai/training/scikit-learn-cpu.1-5:latest",
    )

    try:
        aiplatform.init(project=project, location=region, staging_bucket=staging_bucket)
        display_name = f"unbiased-bias-audit-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
        worker_pool_specs = [
            {
                "machine_spec": {"machine_type": "n1-standard-4"},
                "replica_count": 1,
                "container_spec": {
                    "image_uri": image_uri,
                    "command": ["python", "-c", "print('Vertex AI audit trigger received')"],
                    "args": [
                        json.dumps(
                            {
                                "dataset_path": dataset_path,
                                "model_artifact_path": model_artifact_path,
                            }
                        )
                    ],
                },
            }
        ]
        custom_job = aiplatform.CustomJob(
            display_name=display_name,
            worker_pool_specs=worker_pool_specs,
            staging_bucket=staging_bucket,
        )
        custom_job.run(sync=False)
        return custom_job.resource_name
    except Exception:
        return None


def run_bias_analysis(
    dataset_path: str,
    model_artifact_path: str | None = None,
    status_callback: Any | None = None,
) -> dict[str, Any]:
    require_endpoint = os.getenv("REQUIRE_VERTEX_ENDPOINT", "false").lower() == "true"

    def provider(feature_frame, domain: str):
        try:
            return _predict_with_vertex_endpoint(feature_frame, domain)
        except Exception:
            if require_endpoint:
                raise
            return None

    result = analyze_bias(
        dataset_path,
        model_artifact_path,
        status_callback=status_callback,
        prediction_provider=provider,
    )
    result["vertex_job_name"] = _submit_vertex_custom_job(dataset_path, model_artifact_path)
    return result


def create_audit_record(user_id: str, audit_id: str | None, payload: dict[str, Any]) -> str:
    firestore_client = require_firestore()
    document_id = audit_id or str(uuid4())
    firestore_client.collection("audits").document(document_id).set(
        {
            "user_id": user_id,
            "status": "processing",
            "stage": "uploading",
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
            **payload,
        },
        merge=True,
    )
    return document_id


def update_audit_status(
    audit_id: str,
    stage: str,
    status: str = "processing",
    extra: dict[str, Any] | None = None,
) -> None:
    firestore_client = require_firestore()
    firestore_client.collection("audits").document(audit_id).set(
        {
            "status": status,
            "stage": stage,
            "updated_at": SERVER_TIMESTAMP,
            **(extra or {}),
        },
        merge=True,
    )


def store_audit_result(user_id: str, result_dict: dict[str, Any], audit_id: str | None = None) -> str:
    payload = {
        "user_id": user_id,
        "model_name": result_dict.get("model_name", "Unnamed Model"),
        "dataset_name": result_dict.get("dataset_name", "uploaded_dataset.csv"),
        "domain": result_dict.get("domain", "general"),
        "model_family": result_dict.get("model_family", "unknown"),
        "analysis_backend": result_dict.get("analysis_backend", "local"),
        "bias_score": result_dict.get("bias_score", 0),
        "fairness_metrics": result_dict.get("fairness_metrics", {}),
        "shap_values": result_dict.get("shap_values", []),
        "shap_top3": result_dict.get("shap_top3", []),
        "causal_graph_json": result_dict.get("causal_graph_json", {}),
        "causal_pathway": result_dict.get("causal_pathway", ""),
        "demographic_parity": result_dict.get("demographic_parity", 0),
        "equalized_odds": result_dict.get("equalized_odds", 0),
        "individual_fairness": result_dict.get("individual_fairness", 0),
        "calibration_error": result_dict.get("calibration_error", 0),
        "sdg_tag": "SDG 10.3",
        "sdg_mapping": result_dict.get("sdg_mapping", []),
        "gemini_explanation": result_dict.get("gemini_explanation", ""),
        "gemini_recommendations": result_dict.get("gemini_recommendations", []),
        "gemini_legal_risk": result_dict.get("gemini_legal_risk", ""),
        "gemini_audit_qa": result_dict.get("gemini_audit_qa", []),
        "candidate_flags": result_dict.get("candidate_flags", []),
        "counterfactuals": result_dict.get("counterfactuals", []),
        "status": result_dict.get("status", "completed"),
        "stage": result_dict.get("stage", "complete"),
        "vertex_job_name": result_dict.get("vertex_job_name"),
    }

    firestore_client = require_firestore()
    collection = firestore_client.collection("audits")
    document_reference = collection.document(audit_id) if audit_id else collection.document()
    document_reference.set(
        {
            **payload,
            "created_at": SERVER_TIMESTAMP,
            "updated_at": SERVER_TIMESTAMP,
        }
        if audit_id is None
        else {
            **payload,
            "updated_at": SERVER_TIMESTAMP,
        },
        merge=bool(audit_id),
    )
    return document_reference.id
