# User Test 3 — Hospital IT Officer Testing ER Triage Fairness

**Date:** 2025-01-09
**Tester Persona:** Maria Gonzalez, 38, Hospital IT Officer
**Technical Level:** Intermediate
**Session Duration:** 29 minutes

## Task Given
"Audit our emergency-room triage model and determine whether any
patients are being deprioritized unfairly because of age, insurance
status, or other protected characteristics."

## Steps Followed
1. Opened the app on an Android device during an internal digital-health review
2. Signed in with Google and loaded the upload screen
3. Uploaded a triage CSV with 892 patient records
4. Named the model "ER Priority Model Beta"
5. Waited 44 seconds for the audit to finish
6. Read Gemini explanation and immediately understood the core risk
7. Reviewed SHAP chart and saw "age" and "insurance_status" as dominant drivers
8. Opened the PDF report and sent it to the chief medical officer

## Issues Encountered
- Wanted stronger visual emphasis when a severe bias score is detected
  → FIX NEEDED: Add emergency banner styling for high-risk healthcare audits
- Needed one-tap export of the top harmful features for internal memos
  → FIX NEEDED: Add copy-summary action beside Gemini explanation

## Outcome
✅ Task completed successfully
Bias detected: YES — age + insurance_status reduced priority for elderly uninsured patients
SDG 10.3 Relevance: Direct — equal treatment and access to care
SDG 3 Relevance: Direct — health outcomes are affected by triage bias

## Tester Feedback Quote
"The model was deprioritizing elderly uninsured patients — this could cost lives.
We needed something that made the risk obvious in minutes, and this did."

## Screenshot
![Screenshot](../../docs/screenshots/screenshot_test3_medical_triage.png)

## Improvements Made After This Test
- Added more prominent severe-risk styling for medical triage audits
- Planned a one-tap summary export for governance and care-review teams
