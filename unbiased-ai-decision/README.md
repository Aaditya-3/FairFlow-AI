# Unbiased AI Decision

AI fairness auditing for automated decisions in hiring, lending, and care delivery.

![SDG 10](https://img.shields.io/badge/SDG%2010-Reduced%20Inequalities-009EDB?style=for-the-badge)
![Firebase](https://img.shields.io/badge/Firebase-FFCA28?style=for-the-badge&logo=firebase&logoColor=black)
![Vertex AI](https://img.shields.io/badge/Vertex%20AI-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75FF?style=for-the-badge&logo=googlebard&logoColor=white)
![Flutter](https://img.shields.io/badge/Flutter-02569B?style=for-the-badge&logo=flutter&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![SHAP](https://img.shields.io/badge/SHAP-Explainability-EF4444?style=for-the-badge)
![Causal AI](https://img.shields.io/badge/Causal%20AI-Enabled-111827?style=for-the-badge)

## SDG Target 10.3

Primary alignment: **SDG 10 - Reduced Inequalities**  
Target 10.3: **Ensure equal opportunity and reduce inequalities of outcome, including by eliminating discriminatory practices**

## Evidence Checklist

- Google tech integration: Firebase Auth, Firestore, Vertex AI, and Gemini integration are implemented in `backend/` and `flutter-app/`
- Flutter mobile app: the product is a Flutter mobile/web app in [`flutter-app/`](flutter-app)
- Demo-ready guest mode: the app supports Firebase anonymous sign-in first and now falls back to a local guest session plus local sample audit if demo Firebase services are unavailable
- 3 documented user tests: see [`user-tests/test_1_recruiter_tool.md`](user-tests/test_1_recruiter_tool.md), [`user-tests/test_2_loan_model.md`](user-tests/test_2_loan_model.md), and [`user-tests/test_3_medical_triage.md`](user-tests/test_3_medical_triage.md)
- SDG target cited by number: SDG 10.3 is surfaced in the UI, backend payloads, and documentation
- Community impact story: see [`IMPACT_STORY.md`](IMPACT_STORY.md)
- Problem statement video: the script is included in [`video_script.md`](video_script.md)
- Docker reproducibility: see [`docker/docker-compose.yml`](docker/docker-compose.yml)
- Deployment scaffold: Cloud Run deployment commands are included below
- Technical depth: SHAP, fairness metrics, causal graph generation, and Gemini plain-language summaries are all present

## Demo Modes

### Local demo

- Backend: `http://localhost:8080`
- Flutter web: `http://localhost:3000`
- Health check: `http://localhost:8080/health`

Local demo behavior:

- If Firebase and Firestore are configured, guest/demo mode uses Firebase anonymous auth plus Firestore sample data
- If Firebase demo services are unavailable, the app can still enter guest mode and the backend falls back to a local file-backed audit store for the sample audit and new uploads

### Deployed demo

This repository includes deployment scaffolding, but it does **not** ship with a published Cloud Run URL by default. After deployment, replace the placeholder URL in your project materials with the real deployed target.

## Why this project stands out

- Mobile-first accessibility through Flutter for phone, tablet, and web use
- Plain-language Gemini explanations for non-technical decision-makers
- SHAP feature impact and causal pathway analysis for technical reviewers
- SDG 10.3 framing for impact and policy alignment
- User-test evidence across hiring, lending, and medical triage workflows

## Architecture

```text
          +----------------------+
          | Flutter Mobile / Web |
          | Google / Guest Auth  |
          +----------+-----------+
                     |
                     v
             +-------+--------+
             | FastAPI Backend |
             | /audit /health  |
             +-------+--------+
                     |
     +---------------+-----------------+
     |                                 |
     v                                 v
+----+----------------+       +--------+---------+
| Gemini 1.5 Flash    |       | Vertex AI Job    |
| plain-language      |       | orchestration    |
| explanation         |       | + local analyzer |
+----+----------------+       +--------+---------+
     |                                 |
     +---------------+-----------------+
                     |
                     v
              +------+------+ 
              | Firestore   |
              | or local    |
              | demo store  |
              +-------------+
```

## Repository layout

```text
unbiased-ai-decision/
|-- backend/
|-- flutter-app/
|-- user-tests/
|-- docker/
|-- .env.example
|-- video_script.md
|-- IMPACT_STORY.md
`-- README.md
```

## Local setup

1. Clone the repository.
2. Copy `.env.example` to `.env`.
3. Fill in Firebase, Vertex AI, and Gemini values if you want the full Google-backed experience.
4. Start the app:

```bash
cd docker
docker compose up --build
```

5. Open the app at `http://localhost:3000`.
6. Open the backend health endpoint at `http://localhost:8080/health` to confirm service status.
7. Use `Try as Guest - no sign-up needed` from the login screen.

Optional sample seeding:

```bash
python backend/seed_sample_audit.py
```

The sample seed is useful for Firestore-backed demos. The local fallback store will auto-provide a sample audit even if Firestore is not configured.

## Environment variables

See [`.env.example`](.env.example) for the full set. The main groups are:

- Firebase service account and web app config
- Gemini API key
- Vertex AI project, region, and staging bucket
- Flutter backend base URL

## Backend API

- `GET /`
- `GET /health`
- `POST /audit`
- `GET /audit/{audit_id}`
- `GET /audit/history/{user_id}`
- `POST /auth/verify`
- `GET /auth/me`

## Cloud Run deployment

```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/unbiased-ai
gcloud run deploy unbiased-ai \
  --image gcr.io/PROJECT_ID/unbiased-ai \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=...,FIREBASE_...=...
```

After deployment, update:

- `FLUTTER_API_BASE_URL`
- your shared demo link
- any README or submission materials that still contain placeholders

## User test evidence

- [User Test 1 - Recruiter workflow](user-tests/test_1_recruiter_tool.md)
- [User Test 2 - Loan approval workflow](user-tests/test_2_loan_model.md)
- [User Test 3 - Medical triage workflow](user-tests/test_3_medical_triage.md)

## Impact and video assets

- [Community impact story](IMPACT_STORY.md)
- [Problem statement video script](video_script.md)

## Roadmap

- CI/CD bias gates for model release approval
- Multi-language support for policy and compliance teams
- Government API integrations for regulated decision audits
- Real-time fairness monitoring dashboards
