# User Test 3 - Medical Triage Workflow Session Notes

**Date:** 2025-01-09  
**Participant:** Maria Gonzalez, 38, Hospital IT Officer  
**Technical level:** Intermediate  
**Device:** Android phone  
**Dataset:** 892 triage records  
**Session length:** 29 minutes

## Session Goal

Maria's task was to audit an emergency-room triage model and determine whether patients were being deprioritized unfairly because of age, insurance status, or other protected characteristics.

## Session Notes

- Maria ran the session on Android during an internal digital-health review, uploaded the triage CSV, and labeled the model `ER Priority Model Beta` so the report would be recognizable when forwarded internally.
- The full audit took 44 seconds. She accepted the wait, but wanted the report to communicate urgency much more aggressively once a severe result appeared because healthcare reviewers should not need to read every paragraph before understanding the risk level.
- The Gemini explanation gave her the first clear read on the problem. She understood the patient-safety implication before touching the deeper charts.
- The SHAP chart then made the issue defensible: `age` and `insurance_status` were the dominant drivers, which aligned with the exact fairness concern the hospital team wanted to test.
- Maria could share the PDF immediately, but she still wanted the most harmful features surfaced more prominently so they could be quoted in internal care-review memos without extra interpretation.
- She sent the report to the chief medical officer during the session because the finding was serious enough to escalate immediately.

## What Broke

- A severe healthcare bias finding did not feel visually urgent enough at first glance; the team wanted the high-risk state to be unmistakable before anyone parsed the details.
- Sharing the full report was easy, but extracting the top harmful factors for internal review still depended on a human summarizing the result.

## What We Changed

- Elevated the high-risk state in the report summary with explicit severity labeling, stronger color treatment, and a bias gauge so dangerous audits read as urgent on first view.
- Exposed PDF sharing in two places - the app bar and the sticky footer - so escalation can happen from the same screen without hunting for the action.
- Added a dedicated legal-risk and audit Q&A section so governance conversations do not have to start from raw metrics alone.

## Quantified Outcome

In a 29-minute session on 892 triage records, Maria escalated a concrete patient-safety risk in the same sitting: `age` and `insurance_status` surfaced as the dominant drivers behind unfair deprioritization of elderly uninsured patients. The session exposed two healthcare-specific gaps - insufficient urgency in the severe-risk state and too much manual work when handing findings upward - and the current report now answers with repeated risk signaling in the summary flow plus two visible PDF-share entry points for faster escalation.

## Representative Quote

> "The model was deprioritizing elderly uninsured patients - this could cost lives. We needed something that made the risk obvious in minutes, and this did."

## Screenshot

![Screenshot](../../docs/screenshots/screenshot_test3_medical_triage.png)
