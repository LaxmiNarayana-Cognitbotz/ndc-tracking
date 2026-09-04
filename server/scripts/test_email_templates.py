"""
Script to test all email HTML templates in server/app/email_templates/.
Validates template loading, placeholder substitution, CSS injection, and outputs test results.
"""

import os
import re
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from app.helpers.email.template_renderer import render_template, TEMPLATES_DIR

# Complete mock context containing sample values for all email template placeholders
MOCK_CONTEXT = {
    "name": "Tathagat Vyas",
    "email": "tathagat.vyas@adani.com",
    "role": "Super Admin",
    "requested_at": "04-Sep-2026 10:30 AM",
    "approve_url": "https://ndc.adani.com/approve?token=sample123",
    "reject_url": "https://ndc.adani.com/reject?token=sample123",
    "login_url": "https://ndc.adani.com/login",
    "otp": "849201",
    "reset_link": "https://ndc.adani.com/reset-password?token=sample_reset_123",
    "valid_mins": "10",
    "person_number": "30213962",
    "employee_name": "Bhargav Pandya",
    "business_unit": "Solar Energy",
    "legal_employer": "Adani Green Energy Ltd",
    "location": "Ahmedabad",
    "department": "IT Operations",
    "resignation_date": "15-Aug-2026",
    "last_working_date": "31-Aug-2026",
    "days_delayed": "4",
    "assigned_date": "01-Sep-2026",
    "ndc_assigned_date": "01-Sep-2026",
    "ndc_stage": "In Progress",
    "department_name": "Human Resources",
    "pending_count": "5",
    "report_date": "04-Sep-2026",
    "total_duplicates": "2",
    "revision_start_date": "01-Sep-2026",
    "revision_completed_date": "03-Sep-2026",
    "revision_comment": "Salary recalculation adjusted for August working days.",
    "fnf_completed_date": "03-Sep-2026",
    "records_table": """
        <tr style="border-bottom:1px solid #e2e8f0;">
            <td style="padding:8px;">30213962</td>
            <td style="padding:8px;">Bhargav Pandya</td>
            <td style="padding:8px;">Adani Green Energy Ltd</td>
            <td style="padding:8px;">IT Operations</td>
            <td style="padding:8px;">31-Aug-2026</td>
        </tr>
    """,
}

OUTPUT_DIR = os.path.join(BASE_DIR, "app", "email_templates", "test_output")


def test_all_templates():
    print("=" * 80)
    print("                EMAIL TEMPLATE VALIDATION TEST SUITE")
    print("=" * 80)
    print(f"Templates Directory: {TEMPLATES_DIR}\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    template_files = sorted([f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".html")])
    if not template_files:
        print("❌ Error: No HTML template files found in templates directory.")
        sys.exit(1)

    passed_count = 0
    failed_count = 0
    results = []

    for template_file in template_files:
        filepath = os.path.join(TEMPLATES_DIR, template_file)
        raw_size = os.path.getsize(filepath)
        errors = []
        rendered_size = 0

        try:
            # 1. Render template
            rendered_html = render_template(template_file, MOCK_CONTEXT)
            rendered_size = len(rendered_html.encode("utf-8"))

            # 2. Check for remaining unhandled placeholders {{ variable }}
            unhandled_matches = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}", rendered_html)
            if unhandled_matches:
                errors.append(f"Unhandled placeholders left in HTML: {', '.join(set(unhandled_matches))}")

            # 3. Check for leftover comment tags around font_css
            if re.search(r"/\*\s*@font-face", rendered_html):
                errors.append("@font-face rule is commented out inside /* ... */")

            # 4. Check that font-family CSS is present
            if "font-family:" not in rendered_html:
                errors.append("Missing font-family CSS styling")

            # Save rendered output
            output_filepath = os.path.join(OUTPUT_DIR, template_file)
            with open(output_filepath, "w", encoding="utf-8") as f:
                f.write(rendered_html)

        except Exception as e:
            errors.append(f"Rendering exception: {str(e)}")

        if not errors:
            passed_count += 1
            status = "[PASS]"
        else:
            failed_count += 1
            status = "[FAIL]"

        results.append({
            "name": template_file,
            "status": status,
            "raw_bytes": raw_size,
            "rendered_bytes": rendered_size,
            "errors": errors
        })

    # Print Results Table
    print(f"{'Template File':<32} | {'Status':<8} | {'Template Size':<13} | {'Rendered Size':<13}")
    print("-" * 75)
    for r in results:
        print(f"{r['name']:<32} | {r['status']:<8} | {r['raw_bytes']:>10} B | {r['rendered_bytes']:>10} B")
        if r['errors']:
            for err in r['errors']:
                print(f"   └── ERROR: {err}")

    print("\n" + "=" * 80)
    print(f"Summary: {passed_count}/{len(template_files)} PASSED, {failed_count} FAILED")
    print(f"Rendered HTML samples saved to: {OUTPUT_DIR}")
    print("=" * 80 + "\n")

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    test_all_templates()
