# User Test 1 - Recruiter Workflow Session Notes

**Date:** 2024-11-15  
**Participant:** Priya Sharma, 34, HR Manager at a mid-size tech firm  
**Technical level:** Non-technical  
**Device:** Android phone  
**Dataset:** 347 hiring decisions from the previous 6 months  
**Session length:** 22 minutes

## Session Goal

Priya's task was simple: upload a recent hiring CSV and decide whether the screening model was disadvantaging candidates through demographic or proxy features.

## Session Notes

- Priya entered through guest mode on Android, opened the sample audit first, and only then felt comfortable uploading real data. The sample lowered the fear of "breaking something" before the real test started.
- She uploaded her own CSV and then waited 38 seconds for the audit to finish. During that gap, she paused and asked whether the app was still running because nothing on screen explained what step the system was on.
- The first screen she trusted was the bias score summary. Once she saw `61/100` and "Moderate Risk," she kept reading instead of backing out.
- The fairness metrics section slowed her down. She understood that something was wrong, but she needed facilitator help to interpret what "Equalized Odds" meant and whether the number was acceptable.
- The SHAP chart created the breakthrough moment. As soon as `zip_code` appeared as the top driver, she connected it to a class and race proxy in the recruiting funnel.
- She exported the PDF before the session ended because she wanted something she could send directly to leadership without recreating the finding in email.

## What Broke

- The 38-second processing window looked idle on mobile, which made the audit feel unreliable right before the key insight appeared.
- The fairness metric labels sounded technical enough that Priya needed translation even though she already understood the hiring risk once the proxy feature surfaced.

## What We Changed

- Added a live audit-status timeline on the upload screen so processing is visible from `uploading` through `complete` instead of feeling frozen.
- Reworked the fairness metrics area into four risk-labeled cards with plain-language descriptions so non-technical reviewers can tell what is healthy, elevated, or critical without outside help.
- Kept the report handoff lightweight with one-tap PDF sharing so the insight can move directly from the audit screen to manager review.

## Quantified Outcome

In a 22-minute session on a 347-row hiring dataset, Priya surfaced two concrete usability blockers: one 38-second "is this stuck?" moment and one terminology blocker in the metrics section. The audit still produced a usable business finding in-session - a `61/100` bias score with `zip_code` as the top driver - and the resulting iteration converted both blockers into product behavior: one visible status timeline and four plain-language metric cards, reducing the need for facilitator translation at the exact point where insight should happen.

## Representative Quote

> "I never knew our tool was using zip code as a signal. That explains so much. This is exactly what I needed to show my leadership team why we need to change the system."

## Screenshot

![Screenshot](../../docs/screenshots/screenshot_test1_report_screen.png)
