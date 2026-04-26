from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from firebase_admin import firestore

from firebase_config import db, require_firestore
from gemini_explainer import generate_gemini_insights
from models.audit_result import AuditResult, FairnessMetrics
from vertex_pipeline import (
    create_audit_record,
    run_bias_analysis,
    store_audit_result,
    update_audit_status,
)


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
        "domain": payload.get("domain", "general"),
        "model_family": payload.get("model_family", "unknown"),
        "analysis_backend": payload.get("analysis_backend", "local"),
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
        "gemini_recommendations": payload.get("gemini_recommendations", []),
        "gemini_legal_risk": payload.get("gemini_legal_risk", ""),
        "gemini_audit_qa": payload.get("gemini_audit_qa", []),
        "candidate_flags": payload.get("candidate_flags", []),
        "counterfactuals": payload.get("counterfactuals", []),
        "sdg_tag": payload.get("sdg_tag", "SDG 10.3"),
        "sdg_mapping": payload.get("sdg_mapping", []),
        "status": payload.get("status", "completed"),
        "stage": payload.get("stage", "complete"),
        "vertex_job_name": payload.get("vertex_job_name"),
        "created_at": created_at or datetime.now(timezone.utc),
    }


def _ensure_firestore_ready() -> None:
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firestore is required for demo mode and audit history.",
        )


def _audit_response(payload: dict[str, Any]) -> AuditResult:
    return AuditResult(
        audit_id=payload.get("audit_id"),
        user_id=payload["user_id"],
        model_name=payload["model_name"],
        dataset_name=payload["dataset_name"],
        domain=payload.get("domain", "general"),
        model_family=payload.get("model_family", "unknown"),
        analysis_backend=payload.get("analysis_backend", "local"),
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
        gemini_recommendations=payload.get("gemini_recommendations", []),
        gemini_legal_risk=payload.get("gemini_legal_risk", ""),
        gemini_audit_qa=payload.get("gemini_audit_qa", []),
        candidate_flags=payload.get("candidate_flags", []),
        counterfactuals=payload.get("counterfactuals", []),
        sdg_tag=payload["sdg_tag"],
        sdg_mapping=payload.get("sdg_mapping", []),
        status=payload["status"],
        stage=payload.get("stage", "complete"),
        vertex_job_name=payload.get("vertex_job_name"),
        created_at=payload["created_at"],
    )


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
    audit_id: str | None = Form(None),
):
    _ensure_firestore_ready()
    if not dataset_file.filename or not dataset_file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dataset_file must be a CSV upload.",
        )

    document_id = create_audit_record(
        user_id,
        audit_id,
        {
            "model_name": model_name,
            "dataset_name": dataset_file.filename,
        },
    )
    dataset_path = TMP_DIR / f"{uuid4()}-{dataset_file.filename}"
    await _persist_upload(dataset_file, dataset_path)
    update_audit_status(document_id, "uploaded")

    model_path: str | None = None
    if model_file and model_file.filename:
        artifact_path = TMP_DIR / f"{uuid4()}-{model_file.filename}"
        await _persist_upload(model_file, artifact_path)
        model_path = str(artifact_path)

    def publish(stage: str, audit_status: str = "processing") -> None:
        update_audit_status(document_id, stage, audit_status)

    try:
        audit_result = run_bias_analysis(
            str(dataset_path),
            model_path,
            status_callback=publish,
        )
    except Exception as exc:
        update_audit_status(
            document_id,
            "failed",
            "failed",
            {"error": str(exc)},
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Audit analysis failed: {exc}",
        ) from exc
    audit_result["model_name"] = model_name
    audit_result["dataset_name"] = dataset_file.filename
    audit_result["user_id"] = user_id
    audit_result["status"] = "completed"
    audit_result["stage"] = "generating_gemini"
    audit_result["sdg_tag"] = "SDG 10.3"
    update_audit_status(document_id, "generating_gemini")
    gemini_insights = generate_gemini_insights(audit_result)
    audit_result["gemini_explanation"] = gemini_insights["explanation"]
    audit_result["gemini_recommendations"] = gemini_insights["recommendations"]
    audit_result["gemini_legal_risk"] = gemini_insights["legal_risk"]
    audit_result["gemini_audit_qa"] = gemini_insights["audit_qa"]
    audit_result["stage"] = "complete"

    document_id = store_audit_result(user_id, audit_result, audit_id=document_id)
    response_payload = {
        **audit_result,
        "audit_id": document_id,
        "created_at": datetime.now(timezone.utc),
    }
    return _audit_response(response_payload)


@router.get("/audit/{audit_id}", response_model=AuditResult)
def get_audit(audit_id: str):
    _ensure_firestore_ready()
    snapshot = require_firestore().collection("audits").document(audit_id).get()
    if not snapshot.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
    payload = _serialize_firestore_payload(snapshot.to_dict() or {}, snapshot.id)
    return _audit_response(payload)


@router.get("/audit/history/{user_id}")
def get_audit_history(user_id: str):
    _ensure_firestore_ready()

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
