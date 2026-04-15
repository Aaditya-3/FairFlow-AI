from __future__ import annotations

from datetime import datetime, timezone

from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from firebase_config import db, require_firestore
from local_store import save_local_audit


SAMPLE_AUDIT = {
    "model_name": "Resume Screening Model v1.2",
    "dataset_name": "TechCorp Hiring Data 2022-2023 (n=4,821)",
    "bias_score": 73,
    "demographic_parity": 0.31,
    "equalized_odds": 0.28,
    "individual_fairness": 0.64,
    "calibration_error": 0.18,
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
    "gemini_explanation": (
        "The model shows severe gender bias via proxy features, with women 31% less likely "
        "to be shortlisted for the same qualifications. This perpetuates workplace inequality, "
        "directly harming SDG 10.3 — equal opportunity for all. The organization must immediately "
        "remove zip_code and university_tier features and retrain on balanced data."
    ),
    "sdg_tag": "SDG 10.3",
    "status": "sample",
    "user_id": "guest-demo",
    "created_at": SERVER_TIMESTAMP,
}


def seed_sample_audit():
    if db is None:
        local_payload = {
            **SAMPLE_AUDIT,
            "created_at": datetime.now(timezone.utc),
        }
        save_local_audit("sample_hiring_audit", local_payload)
        return "sample_hiring_audit"

    firestore_client = require_firestore()
    firestore_client.collection("audits").document("sample_hiring_audit").set(SAMPLE_AUDIT)
    return "sample_hiring_audit"


if __name__ == "__main__":
    document_id = seed_sample_audit()
    print(f"Seeded Firestore document: {document_id}")
