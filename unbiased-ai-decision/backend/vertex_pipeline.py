from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from google.cloud import aiplatform
from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from bias_analyzer import analyze_bias
from firebase_config import db, require_firestore
from local_store import save_local_audit


def vertex_status() -> str:
    required = [
        os.getenv("VERTEX_PROJECT_ID"),
        os.getenv("VERTEX_REGION"),
        os.getenv("VERTEX_STAGING_BUCKET"),
    ]
    return "ready" if all(required) else "not_configured"


def _submit_vertex_custom_job(dataset_path: str, model_artifact_path: str | None) -> str | None:
    if vertex_status() != "ready":
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


def run_bias_analysis(dataset_path: str, model_artifact_path: str | None = None) -> dict[str, Any]:
    local_result = analyze_bias(dataset_path, model_artifact_path)
    local_result["vertex_job_name"] = _submit_vertex_custom_job(dataset_path, model_artifact_path)
    return local_result


def store_audit_result(user_id: str, result_dict: dict[str, Any]) -> str:
    payload = {
        "user_id": user_id,
        "model_name": result_dict.get("model_name", "Unnamed Model"),
        "dataset_name": result_dict.get("dataset_name", "uploaded_dataset.csv"),
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
        "gemini_explanation": result_dict.get("gemini_explanation", ""),
        "status": result_dict.get("status", "completed"),
        "vertex_job_name": result_dict.get("vertex_job_name"),
    }

    if db is None:
        document_id = f"local-{uuid4()}"
        payload["created_at"] = datetime.now(timezone.utc)
        return save_local_audit(document_id, payload)

    firestore_client = require_firestore()
    collection = firestore_client.collection("audits")
    document_reference = collection.document()
    document_reference.set(
        {
            **payload,
            "created_at": SERVER_TIMESTAMP,
        }
    )
    return document_reference.id
