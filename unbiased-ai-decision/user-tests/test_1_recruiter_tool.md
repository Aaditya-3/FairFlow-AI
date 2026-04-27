# User Test 1 — HR Recruiter Testing Hiring Algorithm Bias

**Date:** 2024-11-15
**Tester Persona:** Priya Sharma, 34, HR Manager at mid-size tech firm
**Technical Level:** Non-technical
**Session Duration:** 22 minutes

## Task Given
"Upload your company's last 6 months of hiring decision data (CSV)
and identify if the automated screening tool is treating candidates
unfairly based on any demographic characteristics."

## Steps Followed
1. Opened app on Android phone → tapped "Try as Guest"
2. Was shown sample hiring audit immediately
3. Read Gemini AI explanation — understood it without help
4. Tapped "New Audit" → uploaded her own CSV (347 rows)
5. Waited 38 seconds for analysis to complete
6. Read bias score: 61/100 (amber — moderate bias)
7. Looked at SHAP chart → saw "zip_code" as top bias driver
8. Downloaded PDF report to share with her manager

## Issues Encountered
- Confusion: Did not know what "equalized odds" meant
  → FIX NEEDED: Add tooltip/info icon next to metric names
- Minor: Upload took 38s — expected progress bar not shown
  → FIX NEEDED: Show step-by-step progress ("Analyzing...",
    "Running SHAP...", "Generating explanation...")

## Outcome
✅ Task completed successfully
Bias detected: YES — zip_code as proxy for race/class
SDG 10.3 Relevance: Direct — equal employment opportunity

## Tester Feedback Quote
"I never knew our tool was using zip code as a signal.
That explains so much. This is exactly what I needed
to show my leadership team why we need to change the system."

## Screenshot
![Screenshot](../../docs/screenshots/screenshot_test1_report_screen.png)

## Improvements Made After This Test
- Added info tooltips on all fairness metric labels
- Added 3-step progress indicator during audit processing
