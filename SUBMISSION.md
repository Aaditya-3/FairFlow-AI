# 🌍 FairFlow AI — Google Solution Challenge 2026 Submission

FairFlow AI is a fairness-auditing platform built to help organizations detect discriminatory patterns in hiring, lending, and healthcare decision systems before those systems harm real people. It combines explainable AI, mobile-first reporting, and Google Cloud services so non-technical reviewers can move from a CSV upload to an actionable fairness report in minutes.

## 🧭 What Judges Should Review First

This repository contains two connected components that serve different roles in the submission:

- `unbiased-ai-decision/` is the **primary Google Solution Challenge submission**. It is the Flutter mobile/web experience that uses Firebase Auth, Firestore, Gemini 1.5 Flash, Vertex AI, and Cloud Run to deliver a polished, Google-native fairness auditing workflow.
- `backend/` + `frontend/` at the repository root are the **advanced FairFlow auditing engine**. This stack powers deeper ML analysis, including SHAP explanations, AIF360 and Fairlearn metrics, counterfactual reasoning, WASM precheck support, differential privacy PDF reporting, and governance-oriented inspection tools.

The Flutter submission exists so judges can evaluate the end-user experience that best fits Solution Challenge criteria: accessible, mobile-friendly, and tightly integrated with Google technologies. The advanced engine exists because fairness work also needs rigorous technical depth, reproducibility, and model-agnostic analysis for practitioners.

## 🚀 Demo In 3 Steps

1. Configure the primary submission by copying `unbiased-ai-decision/.env.example` to `unbiased-ai-decision/.env` and filling the Firebase, Gemini, and optional Vertex AI values.
2. Start the submission stack with Docker Compose:

```bash
cd unbiased-ai-decision/docker
docker compose up --build
```

3. Open `http://localhost:3000`, sign in with Google or use guest mode, then review `http://localhost:8080/health` to confirm backend service status.

## 🔗 Live Links

- Live demo URL: `[PLACEHOLDER — fill in after Cloud Run deploy]`
- Demo video: `[PLACEHOLDER — fill in YouTube URL]`

## ☁️ Google Technology Stack

- Firebase Auth for Google sign-in and guest access
- Firestore for audit history and live progress state
- Vertex AI for model packaging, deployment, and scalable inference
- Gemini 1.5 Flash for plain-language fairness explanation, legal risk summaries, and remediation guidance
- Cloud Run for deployable, scale-to-zero backend delivery

## 🎯 SDG Alignment

| SDG Target | Why it fits FairFlow |
| --- | --- |
| SDG 10.3 | Detects discriminatory outcomes and highlights where decision systems reduce equal opportunity. |
| SDG 8.5 | Helps hiring and lending teams identify unfair barriers to employment and economic participation. |
| SDG 16.b | Produces evidence that supports non-discriminatory governance, review, and policy enforcement. |

## 🧪 User Test Evidence

- [User Test 1 — Recruiter workflow](unbiased-ai-decision/user-tests/test_1_recruiter_tool.md)
- [User Test 2 — Loan approval workflow](unbiased-ai-decision/user-tests/test_2_loan_model.md)
- [User Test 3 — Medical triage workflow](unbiased-ai-decision/user-tests/test_3_medical_triage.md)
- [Community impact story](unbiased-ai-decision/IMPACT_STORY.md)
- [Competitive analysis](docs/competitive-analysis.md)

## ✅ Why This Submission Is Distinct

FairFlow is not just a fairness library wrapped in a dashboard. It is a practical, end-to-end operating surface for AI accountability: mobile-first Flutter delivery, Gemini-generated explanations for non-technical teams, causal pathway visualization, browser-side WASM precheck, differential privacy PDF exports, and multi-jurisdiction legal risk framing across EU, US, and India contexts.

That combination matters for real deployment. Teams do not only need a metric; they need a tool they can run, understand, share, and act on under time pressure. FairFlow was designed to meet that operational reality while staying rooted in the Google stack that makes Solution Challenge submissions scalable and credible.
