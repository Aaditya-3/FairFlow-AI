from __future__ import annotations

from google.cloud.firestore_v1 import SERVER_TIMESTAMP

from firebase_config import db, require_firestore
from sdg_mapping import build_sdg_mapping


SAMPLE_METRICS = {
    "demographic_parity": 0.31,
    "equalized_odds": 0.28,
    "individual_fairness": 0.64,
    "calibration_error": 0.18,
    "disparate_impact": 0.69,
}

SAMPLE_AUDIT = {
    "model_name": "Resume Screening Model v1.2",
    "dataset_name": "TechCorp Hiring Data 2022-2023 (n=4,821)",
    "domain": "hiring",
    "model_family": "vertex_endpoint_hiring",
    "analysis_backend": "vertex_endpoint",
    "bias_score": 73,
    "demographic_parity": SAMPLE_METRICS["demographic_parity"],
    "equalized_odds": SAMPLE_METRICS["equalized_odds"],
    "individual_fairness": SAMPLE_METRICS["individual_fairness"],
    "calibration_error": SAMPLE_METRICS["calibration_error"],
    "fairness_metrics": SAMPLE_METRICS,
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
        "directly harming SDG 10.3 - equal opportunity for all. The organization must immediately "
        "remove zip_code and university_tier features and retrain on balanced data."
    ),
    "gemini_recommendations": [
        {
            "title": "Review candidate A-1042",
            "action": "Re-score with zip_code and university_tier masked before final rejection.",
            "priority": "high",
            "row_id": "A-1042",
        },
        {
            "title": "Retrain the hiring model",
            "action": "Constrain proxy features and validate four-fifths impact before release.",
            "priority": "high",
            "row_id": None,
        },
    ],
    "gemini_legal_risk": (
        "The audit exceeds the 0.10 parity review threshold and falls below the 0.80 "
        "four-fifths disparate-impact threshold, so compliance review is required before deployment."
    ),
    "gemini_audit_qa": [
        {
            "question": "Why was this row flagged?",
            "answer": "Its favorable-decision probability dropped when zip_code and university_tier carried high influence.",
        },
        {
            "question": "Which rule is most concerning?",
            "answer": "Disparate impact is 0.69, below the 0.80 four-fifths review threshold.",
        },
    ],
    "candidate_flags": [
        {
            "row_id": "A-1042",
            "protected_group": "women",
            "sensitive_attribute": "gender_proxy",
            "predicted_decision": 0,
            "approval_probability": 0.22,
            "primary_drivers": ["zip_code", "university_tier"],
        }
    ],
    "counterfactuals": [
        {
            "row_id": "A-1042",
            "current_probability": 0.22,
            "suggested_changes": [
                {
                    "feature": "zip_code",
                    "current_value": 7.0,
                    "suggested_value": 3.0,
                    "direction": "decrease",
                }
            ],
        }
    ],
    "sdg_tag": "SDG 10.3",
    "sdg_mapping": build_sdg_mapping(SAMPLE_METRICS, "hiring"),
    "status": "sample",
    "stage": "complete",
    "user_id": "guest-demo",
    "created_at": SERVER_TIMESTAMP,
}


def seed_sample_audit():
    if db is None:
        raise RuntimeError("Firestore is required to seed the demo sample audit.")

    firestore_client = require_firestore()
    firestore_client.collection("audits").document("sample_hiring_audit").set(SAMPLE_AUDIT)
    return "sample_hiring_audit"


if __name__ == "__main__":
    document_id = seed_sample_audit()
    print(f"Seeded Firestore document: {document_id}")
