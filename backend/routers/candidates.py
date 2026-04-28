import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from uuid import UUID

from database import get_db
from domain_config import PRESET_DOMAIN_TEMPLATES
from ml.bias_detector import run_bias_detection
from ml.counterfactual import generate_counterfactual
from models import Audit, Candidate, User
from routers.auth import get_current_user
from schemas import CounterfactualRequest, CounterfactualResponse
from utils import rebuild_audit_rows, serialize_candidate, to_serializable


router = APIRouter()


def _audit_domain_config(audit: Audit) -> dict:
    default_config = PRESET_DOMAIN_TEMPLATES["hiring"].model_dump(mode="json")
    return audit.domain_config or default_config


def _get_authorized_audit(db: Session, audit_id: UUID, user_id) -> Audit:
    audit = (
        db.query(Audit)
        .options(joinedload(Audit.candidates))
        .filter(Audit.id == audit_id, Audit.user_id == user_id)
        .first()
    )
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
    return audit


@router.get("/candidates/{audit_id}")
def get_candidates(
    audit_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str = Query(default=""),
    bias_status: str = Query(default="all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    audit = _get_authorized_audit(db, audit_id, current_user.id)

    query = db.query(Candidate).filter(Candidate.audit_id == audit.id)
    if search:
        query = query.filter(Candidate.name.ilike(f"%{search.strip()}%"))
    if bias_status == "flagged":
        query = query.filter(Candidate.bias_flagged.is_(True))
    elif bias_status == "clean":
        query = query.filter(Candidate.bias_flagged.is_(False))

    total = query.count()
    candidates = (
        query.order_by(Candidate.name.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [serialize_candidate(candidate) for candidate in candidates],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


@router.get("/explain/{candidate_id}")
def get_candidate_explanation(
    candidate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    candidate = (
        db.query(Candidate)
        .join(Audit, Candidate.audit_id == Audit.id)
        .filter(Candidate.id == candidate_id, Audit.user_id == current_user.id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")
    return candidate.shap_values or {}


@router.post("/counterfactual", response_model=CounterfactualResponse)
def run_counterfactual(
    payload: CounterfactualRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    candidate = (
        db.query(Candidate)
        .join(Audit, Candidate.audit_id == Audit.id)
        .filter(Candidate.id == payload.candidate_id, Audit.user_id == current_user.id)
        .first()
    )
    if not candidate:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

    audit = _get_authorized_audit(db, candidate.audit_id, current_user.id)
    ordered_candidates = list(audit.candidates)
    candidate_index = next(
        (index for index, item in enumerate(ordered_candidates) if item.id == candidate.id),
        None,
    )
    if candidate_index is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate record is inconsistent.")

    domain_config = _audit_domain_config(audit)
    protected_attributes = domain_config.get("protected_attributes", ["gender"])
    feature_columns = domain_config.get("feature_columns") or None
    outcome_positive_value = domain_config.get("outcome_positive_value", 1)
    outcome_column = domain_config.get("outcome_column", "hired")

    reconstructed_df = pd.DataFrame(rebuild_audit_rows(ordered_candidates))
    resolved_outcome_column = outcome_column if outcome_column in reconstructed_df.columns else "hired"
    detection_result = run_bias_detection(
        reconstructed_df,
        label_column=resolved_outcome_column,
        protected_attributes=protected_attributes,
        outcome_positive_value=outcome_positive_value,
        feature_columns=feature_columns,
    )
    counterfactual = generate_counterfactual(
        detection_result["model"],
        reconstructed_df.iloc[candidate_index].to_dict(),
        detection_result["label_encoders"],
        detection_result["majority_values"],
        label_column=resolved_outcome_column,
        protected_attributes=protected_attributes,
        model_feature_names=detection_result.get("feature_names", []),
    )

    candidate.counterfactual_result = to_serializable(counterfactual)
    candidate.bias_flagged = bool(
        counterfactual["bias_detected"] or ((candidate.shap_values or {}).get("proxy_flags") or [])
    )
    db.commit()

    return {
        "candidate_id": candidate.id,
        **counterfactual,
    }
