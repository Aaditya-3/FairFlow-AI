from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any


STORE_PATH = Path(__file__).resolve().parent / ".demo_store" / "audits.json"
STORE_LOCK = Lock()

_DEFAULT_SAMPLE_AUDIT = {
    "user_id": "guest-demo",
    "model_name": "Resume Screening Model v1.2",
    "dataset_name": "TechCorp Hiring Data 2022-2023 (n=4,821)",
    "bias_score": 73,
    "fairness_metrics": {
        "demographic_parity": 0.31,
        "equalized_odds": 0.28,
        "individual_fairness": 0.64,
        "calibration_error": 0.18,
        "disparate_impact": 0.69,
    },
    "shap_values": [
        {"feature": "gender_proxy", "value": 0.412},
        {"feature": "zip_code", "value": 0.307},
        {"feature": "university_tier", "value": 0.266},
    ],
    "shap_top3": ["gender_proxy", "zip_code", "university_tier"],
    "causal_graph_json": {
        "nodes": [
            {"id": "gender_proxy"},
            {"id": "zip_code"},
            {"id": "university_tier"},
            {"id": "hired"},
        ],
        "edges": [
            {"source": "gender_proxy", "target": "zip_code", "weight": 0.33},
            {"source": "zip_code", "target": "hired", "weight": 0.28},
        ],
    },
    "causal_pathway": "gender_proxy -> zip_code -> hired",
    "demographic_parity": 0.31,
    "equalized_odds": 0.28,
    "individual_fairness": 0.64,
    "calibration_error": 0.18,
    "gemini_explanation": (
        "The model shows severe gender bias via proxy features, with women 31% less likely "
        "to be shortlisted for the same qualifications. This perpetuates workplace inequality "
        "and directly undermines SDG 10.3. The organization should remove proxy-heavy inputs "
        "such as zip code and retrain on more balanced data."
    ),
    "sdg_tag": "SDG 10.3",
    "status": "sample",
    "created_at": None,
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_store_dir() -> None:
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    return value


def _read_store() -> dict[str, Any]:
    _ensure_store_dir()
    if not STORE_PATH.exists():
        return {"audits": {}}

    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"audits": {}}


def _write_store(payload: dict[str, Any]) -> None:
    _ensure_store_dir()
    STORE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_sample_audit() -> dict[str, Any]:
    payload = _serialize_value(_DEFAULT_SAMPLE_AUDIT)
    payload["created_at"] = _utcnow_iso()
    return payload


def _ensure_sample_audit(data: dict[str, Any]) -> bool:
    audits = data.setdefault("audits", {})
    if "sample_hiring_audit" in audits:
        return False

    audits["sample_hiring_audit"] = _build_sample_audit()
    return True


def seed_local_sample_audit() -> str:
    with STORE_LOCK:
        data = _read_store()
        changed = _ensure_sample_audit(data)
        if changed:
            _write_store(data)
    return "sample_hiring_audit"


def save_local_audit(document_id: str, payload: dict[str, Any]) -> str:
    with STORE_LOCK:
        data = _read_store()
        _ensure_sample_audit(data)

        record = _serialize_value(payload)
        if not record.get("created_at"):
            record["created_at"] = _utcnow_iso()

        data.setdefault("audits", {})[document_id] = record
        _write_store(data)
    return document_id


def get_local_audit(document_id: str) -> dict[str, Any] | None:
    with STORE_LOCK:
        data = _read_store()
        changed = _ensure_sample_audit(data)
        if changed:
            _write_store(data)
        record = data.get("audits", {}).get(document_id)
        if record is None:
            return None
        return {
            "audit_id": document_id,
            **record,
        }


def _parse_created_at(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.fromtimestamp(0, tz=timezone.utc)


def list_local_audits_for_user(user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    with STORE_LOCK:
        data = _read_store()
        changed = _ensure_sample_audit(data)
        if changed:
            _write_store(data)

        audits = []
        for document_id, payload in data.get("audits", {}).items():
            if payload.get("user_id") != user_id:
                continue
            audits.append(
                {
                    "audit_id": document_id,
                    **payload,
                }
            )

    audits.sort(key=lambda item: _parse_created_at(item.get("created_at")), reverse=True)
    return audits[:limit]


def local_storage_status() -> dict[str, Any]:
    return {
        "storage": "file",
        "path": str(STORE_PATH),
    }
