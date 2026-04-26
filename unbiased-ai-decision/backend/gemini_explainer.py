from __future__ import annotations

import json
import os
from typing import Any

from google import genai


PROMPT_TEMPLATE = """
You are an AI fairness expert. A bias audit has been run on an
automated decision system. Here are the results:

Bias Score: {bias_score}/100 (0=fair, 100=extremely biased)
Demographic Parity Difference: {demographic_parity}
Equalized Odds Difference: {equalized_odds}
Top 3 SHAP features driving unfair outcomes: {shap_top3}
Causal bias pathway detected: {causal_pathway}

Write exactly 3 sentences explaining:
1. What specific bias was found and in which feature
2. What real-world harm this could cause to affected groups
3. The single most important fix the organization should make

Write for a non-technical audience. Be direct. No jargon.
Reference SDG 10.3 (reduced inequalities of outcome) if bias is severe.
""".strip()

INSIGHTS_PROMPT_TEMPLATE = """
You are an AI fairness reviewer for a production audit. Return strict JSON
with these keys: explanation, recommendations, legal_risk, audit_qa.

Audit context:
- Domain: {domain}
- Bias Score: {bias_score}/100
- Demographic Parity Difference: {demographic_parity}
- Equalized Odds Difference: {equalized_odds}
- Disparate Impact: {disparate_impact}
- Top SHAP drivers: {shap_top3}
- Causal pathway: {causal_pathway}
- Flagged decision rows: {candidate_flags}
- Counterfactuals: {counterfactuals}
- SDG mapping: {sdg_mapping}

Rules:
- explanation: exactly 3 concise sentences for non-technical reviewers.
- recommendations: 3 to 5 objects with title, action, priority, row_id.
- legal_risk: one paragraph naming relevant adverse-impact thresholds.
- audit_qa: 3 objects with question and answer. Include "why was this row flagged?"
- Keep jurisdictional language general unless the audit data names a jurisdiction.
""".strip()


def _fallback_explanation(bias_result: dict[str, Any]) -> str:
    top_feature = ", ".join(bias_result.get("shap_top3", [])[:1]) or "the leading proxy feature"
    severe = float(bias_result.get("bias_score", 0)) >= 60
    sdg_clause = " and directly undermines SDG 10.3" if severe else ""
    return (
        f"The audit found unfair outcomes linked most strongly to {top_feature}, which is driving the model toward unequal decisions. "
        f"This can deny qualified people fair access to jobs, loans, or care{sdg_clause}. "
        f"The single most important fix is to remove or constrain that feature and retrain the model on more balanced data."
    )


def _fallback_recommendations(bias_result: dict[str, Any]) -> list[dict[str, Any]]:
    flags = bias_result.get("candidate_flags", [])[:3]
    recommendations: list[dict[str, Any]] = []
    for flag in flags:
        row_id = flag.get("row_id", "flagged row")
        drivers = ", ".join(flag.get("primary_drivers", []) or bias_result.get("shap_top3", []))
        recommendations.append(
            {
                "title": f"Review {row_id}",
                "action": (
                    f"Re-score this decision with {drivers or 'proxy-heavy features'} masked, "
                    "then document a human review before final action."
                ),
                "priority": "high",
                "row_id": row_id,
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "title": "Retrain with constrained proxy features",
                "action": "Remove or cap the strongest proxy drivers and compare fairness metrics before release.",
                "priority": "high",
                "row_id": None,
            }
        )
    return recommendations


def _fallback_legal_risk(bias_result: dict[str, Any]) -> str:
    metrics = bias_result.get("fairness_metrics", {})
    disparate_impact = metrics.get("disparate_impact", bias_result.get("disparate_impact", 0))
    parity = abs(float(metrics.get("demographic_parity", bias_result.get("demographic_parity", 0)) or 0))
    return (
        "This audit should be treated as elevated legal risk because the parity gap "
        f"is {parity:.3f} against a 0.100 review threshold and disparate impact is "
        f"{float(disparate_impact or 0):.3f} against the four-fifths threshold of 0.800. "
        "A compliance reviewer should validate business necessity, proxy-feature use, and appeal procedures."
    )


def _fallback_audit_qa(bias_result: dict[str, Any]) -> list[dict[str, str]]:
    top_feature = ", ".join(bias_result.get("shap_top3", [])[:2]) or "the strongest proxy drivers"
    pathway = bias_result.get("causal_pathway") or "No strong pathway detected"
    return [
        {
            "question": "Why was this row flagged?",
            "answer": f"It had a low favorable-decision probability and relied on {top_feature}.",
        },
        {
            "question": "Which fairness rule is most concerning?",
            "answer": "The report compares parity gaps to 0.10 and disparate impact to the 0.80 four-fifths threshold.",
        },
        {
            "question": "What causal pathway should reviewers inspect?",
            "answer": f"Review the pathway: {pathway}.",
        },
    ]


def _fallback_insights(bias_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "explanation": _fallback_explanation(bias_result),
        "recommendations": _fallback_recommendations(bias_result),
        "legal_risk": _fallback_legal_risk(bias_result),
        "audit_qa": _fallback_audit_qa(bias_result),
    }


def _parse_json_response(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.removeprefix("json").strip()
    try:
        decoded = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1:
            return None
        try:
            decoded = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return decoded if isinstance(decoded, dict) else None


def generate_explanation(bias_result: dict[str, Any]) -> str:
    prompt = PROMPT_TEMPLATE.format(
        bias_score=bias_result.get("bias_score", 0),
        demographic_parity=bias_result.get("demographic_parity", 0),
        equalized_odds=bias_result.get("equalized_odds", 0),
        shap_top3=", ".join(bias_result.get("shap_top3", [])),
        causal_pathway=bias_result.get("causal_pathway", "No strong pathway detected"),
    )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_explanation(bias_result)

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        text = (response.text or "").strip()
        return text or _fallback_explanation(bias_result)
    except Exception:
        return _fallback_explanation(bias_result)


def generate_gemini_insights(bias_result: dict[str, Any]) -> dict[str, Any]:
    fallback = _fallback_insights(bias_result)
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return fallback

    prompt = INSIGHTS_PROMPT_TEMPLATE.format(
        domain=bias_result.get("domain", "general"),
        bias_score=bias_result.get("bias_score", 0),
        demographic_parity=bias_result.get("demographic_parity", 0),
        equalized_odds=bias_result.get("equalized_odds", 0),
        disparate_impact=bias_result.get("disparate_impact", 0),
        shap_top3=", ".join(bias_result.get("shap_top3", [])),
        causal_pathway=bias_result.get("causal_pathway", "No strong pathway detected"),
        candidate_flags=json.dumps(bias_result.get("candidate_flags", [])[:5]),
        counterfactuals=json.dumps(bias_result.get("counterfactuals", [])[:5]),
        sdg_mapping=json.dumps(bias_result.get("sdg_mapping", [])),
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
        )
        decoded = _parse_json_response(response.text or "")
        if decoded is None:
            return fallback
        return {
            "explanation": decoded.get("explanation") or fallback["explanation"],
            "recommendations": decoded.get("recommendations") or fallback["recommendations"],
            "legal_risk": decoded.get("legal_risk") or fallback["legal_risk"],
            "audit_qa": decoded.get("audit_qa") or fallback["audit_qa"],
        }
    except Exception:
        return fallback
