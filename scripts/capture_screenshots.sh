#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCREENSHOT_DIR="$ROOT_DIR/docs/screenshots"
export ROOT_DIR

mkdir -p "$SCREENSHOT_DIR"

cat <<'EOF'
Manual screenshot capture checklist

1. Run the primary Flutter submission and open the relevant completed audit screens.
2. Capture these three screenshots manually:
   - screenshot_test1_report_screen.png
   - screenshot_test2_loan_bias.png
   - screenshot_test3_medical_triage.png
3. Save the images into docs/screenshots/ using the exact filenames above.

This script also updates the user test markdown files so they point at the expected screenshot paths.
EOF

python3 - <<'PY'
import os
from pathlib import Path

root = Path(os.environ["ROOT_DIR"])
updates = {
    root / "unbiased-ai-decision/user-tests/test_1_recruiter_tool.md": "![Screenshot](../../docs/screenshots/screenshot_test1_report_screen.png)",
    root / "unbiased-ai-decision/user-tests/test_2_loan_model.md": "![Screenshot](../../docs/screenshots/screenshot_test2_loan_bias.png)",
    root / "unbiased-ai-decision/user-tests/test_3_medical_triage.md": "![Screenshot](../../docs/screenshots/screenshot_test3_medical_triage.png)",
}

for path, image_markdown in updates.items():
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "## Screenshot Placeholder\n[screenshot_test1_report_screen.png]",
        f"## Screenshot\n{image_markdown}",
    )
    text = text.replace(
        "## Screenshot Placeholder\n[screenshot_test2_loan_report.png]",
        f"## Screenshot\n{image_markdown}",
    )
    text = text.replace(
        "## Screenshot Placeholder\n[screenshot_test3_medical_report.png]",
        f"## Screenshot\n{image_markdown}",
    )
    path.write_text(text, encoding="utf-8")
PY

printf '\nUpdated markdown image paths. Add the actual screenshot files to:\n%s\n' "$SCREENSHOT_DIR"
