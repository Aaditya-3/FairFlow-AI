from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from firebase_admin import firestore

from firebase_config import db, require_firestore
from gemini_explainer import generate_explanation
from local_store import get_local_audit, list_local_audits_for_user
from models.audit_result import AuditResult, FairnessMetrics
from vertex_pipeline import run_bias_analysis, store_audit_result


router = APIRouter()
TMP_DIR = Path("/tmp/unbiased-ai-decision")
TMP_DIR.mkdir(parents=True, exist_ok=True)


def _serialize_firestore_payload(payload: dict[str, Any], document_id: str) -> dict[str, Any]:
    created_at = payload.get("created_at")
    return {
        "audit_id": document_id,
        "user_id": payload.get("user_id", ""),
        "model_name": payload.get("model_name", ""),
        "dataset_name": payload.get("dataset_name", ""),
        "bias_score": payload.get("bias_score", 0),
        "fairness_metrics": payload.get("fairness_metrics", {}),
        "shap_values": payload.get("shap_values", []),
        "shap_top3": payload.get("shap_top3", []),
        "causal_graph_json": payload.get("causal_graph_json", {}),
        "demographic_parity": payload.get("demographic_parity", 0),
        "equalized_odds": payload.get("equalized_odds", 0),
        "individual_fairness": payload.get("individual_fairness", 0),
        "calibration_error": payload.get("calibration_error", 0),
        "gemini_explanation": payload.get("gemini_explanation", ""),
        "sdg_tag": payload.get("sdg_tag", "SDG 10.3"),
        "status": payload.get("status", "completed"),
        "created_at": created_at or datetime.now(timezone.utc),
    }


async def _persist_upload(upload_file: UploadFile, destination: Path) -> Path:
    contents = await upload_file.read()
    destination.write_bytes(contents)
    return destination


@router.post("/audit", response_model=AuditResult)
async def create_audit(
    dataset_file: UploadFile = File(...),
    model_file: UploadFile | None = File(None),
    model_name: str = Form(...),
    user_id: str = Form(...),
):
    if not dataset_file.filename or not dataset_file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dataset_file must be a CSV upload.",
        )

    dataset_path = TMP_DIR / f"{uuid4()}-{dataset_file.filename}"
    await _persist_upload(dataset_file, dataset_path)

    model_path: str | None = None
    if model_file and model_file.filename:
        artifact_path = TMP_DIR / f"{uuid4()}-{model_file.filename}"
        await _persist_upload(model_file, artifact_path)
        model_path = str(artifact_path)

    audit_result = run_bias_analysis(str(dataset_path), model_path)
    audit_result["model_name"] = model_name
    audit_result["dataset_name"] = dataset_file.filename
    audit_result["user_id"] = user_id
    audit_result["status"] = "completed"
    audit_result["sdg_tag"] = "SDG 10.3"
    audit_result["gemini_explanation"] = generate_explanation(audit_result)

    document_id = store_audit_result(user_id, audit_result)
    response_payload = {
        **audit_result,
        "audit_id": document_id,
        "created_at": datetime.now(timezone.utc),
    }
    return AuditResult(
        audit_id=response_payload["audit_id"],
        user_id=response_payload["user_id"],
        model_name=response_payload["model_name"],
        dataset_name=response_payload["dataset_name"],
        bias_score=response_payload["bias_score"],
        fairness_metrics=FairnessMetrics(**response_payload["fairness_metrics"]),
        shap_values=response_payload["shap_values"],
        shap_top3=response_payload["shap_top3"],
        causal_graph_json=response_payload["causal_graph_json"],
        demographic_parity=response_payload["demographic_parity"],
        equalized_odds=response_payload["equalized_odds"],
        individual_fairness=response_payload["individual_fairness"],
        calibration_error=response_payload["calibration_error"],
        gemini_explanation=response_payload["gemini_explanation"],
        sdg_tag=response_payload["sdg_tag"],
        status=response_payload["status"],
        created_at=response_payload["created_at"],
    )


@router.get("/audit/{audit_id}", response_model=AuditResult)
def get_audit(audit_id: str):
    if db is None:
        payload = get_local_audit(audit_id)
        if payload is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
    else:
        snapshot = require_firestore().collection("audits").document(audit_id).get()
        if not snapshot.exists:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
        payload = _serialize_firestore_payload(snapshot.to_dict() or {}, snapshot.id)

    return AuditResult(
        audit_id=payload["audit_id"],
        user_id=payload["user_id"],
        model_name=payload["model_name"],
        dataset_name=payload["dataset_name"],
        bias_score=payload["bias_score"],
        fairness_metrics=FairnessMetrics(**payload["fairness_metrics"]),
        shap_values=payload["shap_values"],
        shap_top3=payload["shap_top3"],
        causal_graph_json=payload["causal_graph_json"],
        demographic_parity=payload["demographic_parity"],
        equalized_odds=payload["equalized_odds"],
        individual_fairness=payload["individual_fairness"],
        calibration_error=payload["calibration_error"],
        gemini_explanation=payload["gemini_explanation"],
        sdg_tag=payload["sdg_tag"],
        status=payload["status"],
        created_at=payload["created_at"],
    )


@router.get("/audit/history/{user_id}")
def get_audit_history(user_id: str):
    if db is None:
        return list_local_audits_for_user(user_id, limit=20)

    docs = (
        require_firestore()
        .collection("audits")
        .where("user_id", "==", user_id)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(20)
        .stream()
    )
    history = []
    for snapshot in docs:
        history.append(_serialize_firestore_payload(snapshot.to_dict() or {}, snapshot.id))
    return history
