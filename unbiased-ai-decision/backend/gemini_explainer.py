from __future__ import annotations

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


def _fallback_explanation(bias_result: dict[str, Any]) -> str:
    top_feature = ", ".join(bias_result.get("shap_top3", [])[:1]) or "the leading proxy feature"
    severe = float(bias_result.get("bias_score", 0)) >= 60
    sdg_clause = " and directly undermines SDG 10.3" if severe else ""
    return (
        f"The audit found unfair outcomes linked most strongly to {top_feature}, which is driving the model toward unequal decisions. "
        f"This can deny qualified people fair access to jobs, loans, or care{sdg_clause}. "
        f"The single most important fix is to remove or constrain that feature and retrain the model on more balanced data."
    )


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
