from uuid import UUID

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from agent.memory_store import store_memory
from database import get_db
from domain_config import PRESET_DOMAIN_TEMPLATES
from ml.causal_tcav import run_causal_tcav_analysis
from models import Audit, User
from routers.auth import get_current_user
from schemas import DeepInspectionResponse
from utils import rebuild_audit_rows


router = APIRouter()


def _audit_domain_config(audit: Audit) -> dict:
    default_config = PRESET_DOMAIN_TEMPLATES["hiring"].model_dump(mode="json")
    return audit.domain_config or default_config


def _get_audit_for_user(db: Session, audit_id: UUID, user_id) -> Audit:
    audit = (
        db.query(Audit)
        .options(joinedload(Audit.candidates))
        .filter(Audit.id == audit_id, Audit.user_id == user_id)
        .first()
    )
    if not audit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found.")
    return audit


@router.post("/inspection/deep/{audit_id}", response_model=DeepInspectionResponse)
def run_deep_inspection(
    audit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    audit = _get_audit_for_user(db, audit_id, current_user.id)
    if not audit.candidates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Deep inspection requires at least one candidate record.",
        )

    domain_config = _audit_domain_config(audit)
    protected_priority = domain_config.get("protected_attributes", ["gender", "ethnicity"])
    outcome_column = domain_config.get("outcome_column", "hired")

    dataframe = pd.DataFrame(rebuild_audit_rows(list(audit.candidates)))
    resolved_outcome_column = outcome_column if outcome_column in dataframe.columns else "hired"
    inspection = run_causal_tcav_analysis(
        dataframe,
        outcome_column=resolved_outcome_column,
        protected_priority=protected_priority,
    )
    top_proxy = inspection["proxy_findings"][0]["feature"] if inspection["proxy_findings"] else "none"

    store_memory(
        db,
        user_id=current_user.id,
        audit=audit,
        stage="deep_inspection",
        metadata={
            "top_proxy": top_proxy,
            "tcav_concepts": ",".join(concept["concept"] for concept in inspection["tcav_concepts"][:3]),
            "engine": inspection["engine"],
        },
    )
    db.commit()

    return {
        "audit_id": audit.id,
        **inspection,
    }
