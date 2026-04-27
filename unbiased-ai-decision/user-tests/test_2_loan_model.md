# User Test 2 — Bank Analyst Testing Loan Approval Bias

**Date:** 2024-12-03
**Tester Persona:** Daniel Okafor, 41, Retail Banking Data Analyst
**Technical Level:** Intermediate
**Session Duration:** 26 minutes

## Task Given
"Upload the latest loan approval dataset for our branch network and
check whether the model is unfairly penalizing applicants from rural
communities or lower-income regions."

## Steps Followed
1. Opened the Flutter web app on a branch operations tablet
2. Signed in with Google and landed on the home dashboard
3. Uploaded a CSV export of 1,184 loan decisions
4. Added the model name "Loan Approval Risk Ranker v3"
5. Waited 41 seconds while SHAP, fairness metrics, and Gemini explanation loaded
6. Reviewed bias score: 68/100 (red — severe bias)
7. Inspected the SHAP chart and saw "income_band" and "zip_code" ranked first and second
8. Shared the report PDF with the compliance lead

## Issues Encountered
- Needed clearer feedback during upload because the app looked idle
  → FIX NEEDED: Add explicit progress states and completion toast
- Wanted a glossary for fairness terms before presenting to leadership
  → FIX NEEDED: Add plain-language metric help drawer

## Outcome
✅ Task completed successfully
Bias detected: YES — income + zip code combination penalized rural applicants
SDG 10.3 Relevance: Direct — equal financial opportunity regardless of geography

## Tester Feedback Quote
"I was shocked the model penalizes rural addresses at 3x the rate of urban ones.
Without this audit, we would have kept calling the model objective."

## Screenshot
![Screenshot](../../docs/screenshots/screenshot_test2_loan_bias.png)

## Improvements Made After This Test
- Added clearer audit progress messaging during model execution
- Prioritized glossary support for fairness metrics on report screens
