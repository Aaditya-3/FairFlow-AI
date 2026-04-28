# User Test 2 - Loan Approval Workflow Session Notes

**Date:** 2024-12-03  
**Participant:** Daniel Okafor, 41, Retail Banking Data Analyst  
**Technical level:** Intermediate  
**Device:** Branch operations tablet  
**Dataset:** 1,184 loan decisions  
**Session length:** 26 minutes

## Session Goal

Daniel's task was to upload a recent branch-network loan dataset and check whether the approval model was unfairly penalizing applicants from rural communities or lower-income regions.

## Session Notes

- Daniel chose Google sign-in because he wanted the audit tied to his work account and expected to share the result with a compliance lead afterward.
- He uploaded the CSV, named the model `Loan Approval Risk Ranker v3`, and then waited 41 seconds while the system generated predictions, SHAP values, fairness metrics, and the Gemini explanation.
- During that wait, the app looked idle enough that he checked twice to confirm the upload had not stalled. The lack of visible progress reduced confidence more than the actual wait time did.
- Once the report loaded, the `68/100` severe bias score immediately signaled that this was not a marginal issue.
- The SHAP chart made the problem concrete: `income_band` and `zip_code` were the first and second drivers, which gave Daniel a defensible explanation for why rural applicants were being penalized.
- He was comfortable with the finding itself but wanted the fairness language translated into plainer business terms before sending the report to leadership.
- He shared the PDF during the session because the export was easier than rewriting the result into a separate summary for compliance.

## What Broke

- The 41-second processing period felt longer because there was no visible indication of which analysis step was running.
- The report had enough technical depth for an analyst, but not enough plain-language framing for a leadership handoff without extra explanation.

## What We Changed

- Surfaced live processing stages during audit execution so the wait state is broken into visible steps instead of a single blank pause.
- Strengthened the self-serve explanation layer with a plain-English "What does this mean?" panel and fairness metric cards that label each number as good, needs attention, or critical.
- Preserved one-tap PDF sharing so compliance handoff stays inside the report flow instead of becoming a second task.

## Quantified Outcome

In 26 minutes, Daniel processed 1,184 loan decisions and uncovered a high-severity `68/100` bias pattern. The model penalized rural applicants through the combined influence of `income_band` and `zip_code`, and he was able to hand that finding to compliance in the same session. The friction was concentrated in two places - 41 seconds of invisible processing and repeated translation of fairness jargon - and the current flow now answers both with visible audit stages, one plain-English explanation panel, and four risk-labeled metric cards that let the report stand on its own.

## Representative Quote

> "I was shocked the model penalizes rural addresses at 3x the rate of urban ones. Without this audit, we would have kept calling the model objective."

## Screenshot

![Screenshot](../../docs/screenshots/screenshot_test2_loan_bias.png)
