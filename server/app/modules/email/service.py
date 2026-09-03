"""Email service – sends the NDC Delayed Cases reminder email via SMTP."""

from fastapi import HTTPException
import asyncio
import io
import logging
import os
import smtplib
import zipfile
from datetime import date, datetime, timedelta
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fastapi import BackgroundTasks
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.helpers.ff.sharepoint_service import SharePointService, get_httpx_client
from app.models.email_recipient import EmailRecipient
from app.models.ndc_approval import NdcApproval
from app.models.ndc_record import NdcRecord
from app.models.rm_email_configuration import RmEmailConfiguration
from app.modules.common.service import CommonService
from app.utils.pdf_utils import trim_pdf_to_max_pages
from config.database import BASE_DIR, async_session

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────


class EmailService:
    @staticmethod
    def _parse_recipients(recipient) -> list[str]:
        """Normalize string (comma/semicolon separated) or iterable of emails into a list of unique, stripped email strings."""
        if not recipient:
            return []
        recipients_list: list[str] = []
        if isinstance(recipient, str):
            items = recipient.replace(";", ",").split(",")
        elif isinstance(recipient, (list, tuple, set)):
            items = []
            for item in recipient:
                if isinstance(item, str):
                    items.extend(item.replace(";", ",").split(","))
                elif item:
                    items.append(str(item))
        else:
            items = [str(recipient)]

        for addr in items:
            clean = addr.strip()
            if clean and clean not in recipients_list:
                recipients_list.append(clean)
        return recipients_list

    @staticmethod
    def _fmt_date(d) -> str:
        """Format a date or date-string as '01-Jun-2026'."""
        try:
            if d is None:
                return "—"
            if isinstance(d, (date, datetime)):
                return d.strftime("%d-%b-%Y")
            try:
                return datetime.strptime(str(d), "%Y-%m-%d").strftime("%d-%b-%Y")
            except Exception:
                return str(d)
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in _fmt_date: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    def _days_delayed(last_working_date) -> int:
        """Return how many calendar days have passed since last_working_date."""
        try:
            if last_working_date is None:
                return 0
            if isinstance(last_working_date, (date, datetime)):
                lwd = last_working_date if isinstance(last_working_date, date) else last_working_date.date()
            else:
                try:
                    lwd = datetime.strptime(str(last_working_date), "%Y-%m-%d").date()
                except Exception:
                    return 0
            diff = (date.today() - lwd).days
            return max(0, diff)
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in _days_delayed: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    # ── HTML template builder ─────────────────────────────────────────────────────

    @staticmethod
    def _build_html(records: list[dict], reminder_type: str = "ndc_delayed") -> str:
        """Build the full HTML email body for the delayed-cases reminder."""

        try:
            row_html = ""
            for rec in records:
                days = rec.get("days_delayed", 0)
                if reminder_type == "fnf_open":
                    status_td = '<td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;"><span style="color:#0b3d91;font-weight:600;">Open</span></td>'
                elif reminder_type == "fnf_revision":
                    status_td = '<td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;"><span style="background-color:#ffe5e5;color:#d62828;padding:4px 10px;border-radius:12px;font-weight:600;display:inline-block;">Revision Required</span></td>'
                elif reminder_type == "fnf_paid":
                    status_td = '<td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;"><span style="background-color:#fef3c7;color:#b45309;padding:4px 10px;border-radius:12px;font-weight:600;display:inline-block;">F&amp;F Paid (DMS Pending)</span></td>'
                else:
                    status_td = f'<td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;"><span style="background-color:#ffe5e5;color:#d62828;padding:4px 10px;border-radius:12px;font-weight:600;display:inline-block;">{days} Days</span></td>'

                row_html += f"""
                <tr>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.get('person_number', '')}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.get('employee_name', '')}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.get('department', '—')}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{EmailService._fmt_date(rec.get('last_working_date'))}</td>
                  {status_td}
                </tr>"""

            if reminder_type == "fnf_open":
                title = "F&F Open Cases Report"
                intro = f"Please find below the list of the F&F open cases identified as of today ({EmailService._fmt_date(date.today())})."
                col_5 = "F&F Status"
                outro = "Please review these records and take the necessary actions."
            elif reminder_type == "fnf_revision":
                title = "F&F Revision Required Cases Report"
                intro = f"Please find below the list of the F&F revision required cases identified as of today ({EmailService._fmt_date(date.today())})."
                col_5 = "F&F Status"
                outro = "Please review these records and take the necessary actions."
            elif reminder_type == "fnf_delayed":
                title = "F&F Delayed Cases Report"
                intro = f"Please find below the list of the F&F delayed cases identified as of today ({EmailService._fmt_date(date.today())})."
                col_5 = "Days Delayed"
                outro = "Kindly review and expedite the pending actions to ensure timely closure."
            elif reminder_type == "fnf_paid":
                title = "F&F Paid (Not in DMS) — DMS Upload Pending"
                intro = f"Please find below the list of F&F paid employees whose DMS document upload is still pending as of today ({EmailService._fmt_date(date.today())})."
                col_5 = "F&F Status"
                outro = "Kindly upload the DMS documents for these employees at the earliest to close the settlement loop."
            else:
                title = "NDC Delayed Cases Report"
                intro = f"Please find below the top delayed NDC cases identified as of {EmailService._fmt_date(date.today())}."
                col_5 = "Days Delayed"
                outro = "Kindly review and expedite the pending actions to ensure timely closure."

            html = f"""<!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="x-apple-disable-message-reformatting">
        <style>
          body {{ margin: 0; padding: 0; background-color: #f5f7fb; font-family: Arial, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
          table {{ border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
          .wrapper {{ width: 100% !important; background-color: #f5f7fb; padding: 20px 10px; }}
          .container {{ width: 100% !important; max-width: 800px !important; margin: 0 auto; background-color: #ffffff; border-radius: 10px; border: 1px solid #e5e7eb; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.08); }}
          .table-responsive {{ width: 100% !important; overflow-x: auto !important; -webkit-overflow-scrolling: touch; margin-top: 15px; }}
          @media only screen and (max-width: 600px) {{
            .wrapper {{ padding: 10px 4px !important; }}
            .header {{ padding: 18px 16px !important; }}
            .header h2 {{ font-size: 18px !important; line-height: 1.3 !important; }}
            .content {{ padding: 16px 12px !important; font-size: 13px !important; }}
            .footer {{ padding: 16px 12px !important; font-size: 11.5px !important; }}
            th, td {{ padding: 8px 6px !important; font-size: 12px !important; }}
          }}
        </style>
        </head>
        <body style="background-color:#f5f7fb;font-family:Arial,sans-serif;margin:0;padding:0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" bgcolor="#f5f7fb" class="wrapper" style="background-color:#f5f7fb;width:100%;padding:20px 10px;">
          <tr>
            <td align="center">
              <table class="container" width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;max-width:800px;margin:0 auto;background-color:#ffffff;border-radius:10px;border:1px solid #e5e7eb;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);border-collapse:separate;">
                <tr>
                  <td class="header" bgcolor="#0b3d91" style="background-color:#0b3d91;padding:25px 35px;color:white;">
                    <h2 style="margin:0;font-family:Arial,sans-serif;font-size:22px;color:#ffffff;font-weight:bold;">{title}</h2>
                  </td>
                </tr>
                <tr>
                  <td class="content" style="padding:30px;color:#333333;font-family:Arial,sans-serif;font-size:14px;line-height:1.7;">
                    <p style="margin:0 0 16px 0;">Hello Team,</p>
                    <p style="margin:0 0 16px 0;">
                      {intro}
                    </p>
                    <div class="table-responsive" style="width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:15px;">
                      <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;min-width:480px;">
                        <thead>
                          <tr bgcolor="#eef3fb" style="background-color:#eef3fb;">
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Employee ID</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Name</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Department</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Pending Since</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">{col_5}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {row_html}
                        </tbody>
                      </table>
                    </div>
                    <p style="margin:20px 0 0 0;font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#333333;">
                      {outro}
                    </p>
                  </td>
                </tr>
                <tr>
                  <td class="footer" bgcolor="#fafafa" style="padding:25px 30px;background-color:#fafafa;color:#666666;border-top:1px solid #ececec;font-family:Arial,sans-serif;font-size:12.5px;line-height:1.5;">
                    Regards,<br>
                    <b style="color:#333333;">Team HR</b>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
        </body>
        </html>"""
            return html
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in _build_html: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    # ── main send function ────────────────────────────────────────────────────────

    @staticmethod
    async def send_delayed_reminder(
        records: list[dict], recipient: str | None = None, reminder_type: str = "ndc_delayed"
    ) -> dict:
        """
        Send the NDC delayed-cases reminder email with all delayed records.

        Args:
            records: Top-N delayed records (dicts with keys: person_number,
                     employee_name, department, last_working_date, days_delayed).
            recipient: Optional custom recipient email.
            reminder_type: Type of reminder ("ndc_delayed", "fnf_open", "fnf_revision").

        Returns:
            {"success": bool, "message": str}
        """
        try:
            # Check if email notifications are enabled
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications are disabled (EMAIL_NOTIFICATION=%s). Skipping delayed reminder email.", os.getenv("EMAIL_NOTIFICATION"))
                return {"success": True, "message": "Email notifications are disabled. Email not sent."}

            smtp_host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            recipients_list = EmailService._parse_recipients(recipient)
            if not recipients_list:
                recipients_list = EmailService._parse_recipients(os.getenv("EMAIL_RECIPIENT", ""))

            if not smtp_from:
                msg = "SMTP_FROM not configured"
                logger.error(msg)
                return {"success": False, "message": msg}

            if not recipients_list:
                msg = "Recipient email not configured or provided"
                logger.error(msg)
                return {"success": False, "message": msg}

            html_body = EmailService._build_html(records, reminder_type=reminder_type)

            if reminder_type == "fnf_open":
                subj_title = "F&F Open Cases Reminder"
                subject_line = f"{subj_title} – {len(records)} Records ({EmailService._fmt_date(date.today())})"
            elif reminder_type == "fnf_revision":
                subj_title = "F&F Revision Required Cases Reminder"
                subject_line = f"{subj_title} – {len(records)} Records ({EmailService._fmt_date(date.today())})"
            elif reminder_type == "fnf_delayed":
                subj_title = "F&F Delayed Cases Reminder"
                subject_line = f"{subj_title} – {len(records)} Records ({EmailService._fmt_date(date.today())})"
            elif reminder_type == "fnf_paid":
                subj_title = "F&F Paid — DMS Upload Pending"
                subject_line = f"{subj_title} – {len(records)} Records ({EmailService._fmt_date(date.today())})"
            else:
                subj_title = "NDC Delayed Cases Reminder"
                subject_line = f"Reminder: Top Delayed NDC Cases ({EmailService._fmt_date(date.today())})"

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject_line
            msg["From"] = smtp_from
            msg["To"] = ", ".join(recipients_list)

            # CC recipient for F&F / GCC HR reminder types
            envelope_recipients = list(recipients_list)
            if reminder_type in ("fnf_open", "fnf_revision", "fnf_delayed", "fnf_paid"):
                cc_recipient = os.getenv("FNF_EMAIL_CC") or os.getenv("EMAIL_CC", "")
                if cc_recipient:
                    msg["Cc"] = cc_recipient
                    envelope_recipients.append(cc_recipient)

            msg.attach(MIMEText(html_body, "html"))

            try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as server:
                    server.ehlo()
                    if "starttls" in server.esmtp_features:
                        server.starttls()
                        server.ehlo()
                    if smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, envelope_recipients, msg.as_string())

                logger.info("%s sent to %s (CC: %s, %d records)", subj_title, ", ".join(recipients_list), msg.get("Cc", "None"), len(records))
                return {
                    "success": True,
                    "message": f"Reminder email sent to {', '.join(recipients_list)} with {len(records)} records.",
                }
            except Exception as e:
                logger.exception("Failed to send reminder email: %s", e)
                return {"success": False, "message": f"Email failed: {e}"}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_delayed_reminder: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def send_fnf_details_email(email_to: str, record: dict) -> dict:
        """
        Send the F&F details of an employee to a specific email address,
        attaching the F&F document file if available.
        """

        try:
            # Check if email notifications are enabled
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications are disabled (EMAIL_NOTIFICATION=%s). Skipping F&F details email to %s.", os.getenv("EMAIL_NOTIFICATION"), email_to)
                return {"success": True, "message": "Email notifications are disabled. Email not sent."}

            smtp_host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            if not smtp_from:
                msg = "SMTP_FROM not configured"
                logger.error(msg)
                return {"success": False, "message": msg}

            # Build simple, professional HTML template
            html_body = f"""<!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="x-apple-disable-message-reformatting">
        <style>
          body {{ margin: 0; padding: 0; background-color: #f8fafc; font-family: Arial, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
          table {{ border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
          .wrapper {{ width: 100% !important; background-color: #f8fafc; padding: 20px 10px; }}
          .container {{ width: 100% !important; max-width: 560px !important; margin: 0 auto; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; border-top: 4px solid #0f766e; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); }}
          .table-responsive {{ width: 100% !important; overflow-x: auto !important; -webkit-overflow-scrolling: touch; margin: 20px 0; }}
          @media only screen and (max-width: 600px) {{
            .wrapper {{ padding: 10px 4px !important; }}
            .content {{ padding: 20px 14px !important; font-size: 13px !important; }}
            .footer {{ padding: 16px 14px !important; font-size: 11.5px !important; }}
            .details-table td {{ padding: 8px 6px !important; font-size: 12px !important; }}
          }}
        </style>
        </head>
        <body style="background-color:#f8fafc;font-family:Arial,sans-serif;margin:0;padding:0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" bgcolor="#f8fafc" class="wrapper" style="background-color:#f8fafc;width:100%;padding:20px 10px;">
          <tr>
            <td align="center">
              <table class="container" width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;max-width:560px;margin:0 auto;background-color:#ffffff;border-radius:8px;border:1px solid #e2e8f0;border-top:4px solid #0f766e;overflow:hidden;box-shadow:0 4px 6px -1px rgba(0, 0, 0, 0.05);border-collapse:separate;">
                <tr>
                  <td class="content" style="padding:32px 24px;color:#334155;font-family:Arial,sans-serif;font-size:14px;line-height:1.6;">
                    <h2 style="color:#0f766e;font-size:18px;font-weight:600;margin-top:0;margin-bottom:20px;border-bottom:1px solid #e2e8f0;padding-bottom:10px;font-family:Arial,sans-serif;">Full &amp; Final Settlement Details</h2>
                    <p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#475569;font-family:Arial,sans-serif;">Dear {record.get('employee_name') or 'Team'},</p>
                    <p style="margin:0 0 16px;font-size:14px;line-height:1.6;color:#475569;font-family:Arial,sans-serif;">Please find attached your Full &amp; Final Settlement documents for your reference.</p>
                
                    <div class="table-responsive" style="width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin:20px 0;">
                      <table class="details-table" width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;">
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">Employee Name:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">{record.get('employee_name')}</td>
                        </tr>
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">Person Number:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">{record.get('person_number')}</td>
                        </tr>
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">Department:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">{record.get('department')}</td>
                        </tr>
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">Resignation Date:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">{EmailService._fmt_date(record.get('resignation_date'))}</td>
                        </tr>
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">Last Working Date:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">{EmailService._fmt_date(record.get('last_working_date'))}</td>
                        </tr>
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">F&amp;F Status:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">{record.get('fnf_status')}</td>
                        </tr>
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">Completed Date:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">{EmailService._fmt_date(record.get('fnf_completed_date'))}</td>
                        </tr>
                        <tr>
                          <td class="label" style="padding:10px 12px;border-bottom:none;font-weight:600;color:#64748b;width:38%;font-family:Arial,sans-serif;font-size:13.5px;">Document Count:</td>
                          <td class="value" style="padding:10px 12px;border-bottom:none;color:#0f172a;font-weight:500;font-family:Arial,sans-serif;font-size:13.5px;">ACTUAL_DOCUMENT_COUNT_PLACEHOLDER</td>
                        </tr>
                      </table>
                    </div>
                
                    <p style="margin:20px 0 0;font-size:14px;line-height:1.6;color:#475569;font-family:Arial,sans-serif;">
                      Kindly review the details and inform us if you notice any discrepancy or have any queries.<br>
                      Wishing you success in your future endeavors.
                    </p>
                  </td>
                </tr>
                <tr>
                  <td class="footer" bgcolor="#f8fafc" style="background-color:#f8fafc;padding:20px 24px;border-top:1px solid #e2e8f0;font-family:Arial,sans-serif;font-size:12.5px;color:#64748b;line-height:1.5;">
                    Regards,<br>
                    <strong style="color:#475569;">Team HR</strong>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
        </body>
        </html>"""

            # Build MIMEMultipart message
            msg = MIMEMultipart("mixed")
            msg["Subject"] = f"F&F Settlement Details – {record.get('employee_name')} ({record.get('person_number')})"
            msg["From"] = smtp_from
            msg["To"] = email_to
        
            # CC recipient for F&F emails (manual and automated)
            cc_recipient = os.getenv("FNF_EMAIL_CC") or os.getenv("EMAIL_CC", "")
            if cc_recipient:
                msg["Cc"] = cc_recipient

            # Build list of envelope recipients for SMTP sendmail
            recipients = [email_to]
            if cc_recipient:
                recipients.append(cc_recipient)
        
            # Attach F&F document(s) from SharePoint or local folder as fallback
            attached_from_sharepoint = False
            actual_document_count = 0
            person_number = record.get("person_number")
        
            if person_number:
                logger.info("Attempting to attach F&F document(s) from SharePoint for person: %s", person_number)
                sharepoint_service = SharePointService()
                async with get_httpx_client() as client:
                    try:
                        # 1. Resolve site ID
                        site_id = await sharepoint_service.get_site_id(client)
                    
                        # 2. Resolve drive ID and folder path
                        drive_id, folder_path = await sharepoint_service.get_drive_details(client, site_id)
                    
                        # 3. Locate folder and list files
                        files, resolved_folder = await sharepoint_service.get_person_folder_files(
                            client, site_id, drive_id, folder_path, person_number
                        )
                    
                        if files:
                            actual_document_count = len(files)
                            if len(files) == 1:
                                # Single file attachment
                                file_item = files[0]
                                name = file_item.get("name", "document.pdf")
                                download_url = file_item.get("@microsoft.graph.downloadUrl")
                                if download_url:
                                    logger.info("Downloading file '%s' from SharePoint for email attachment.", name)
                                    res = await client.get(download_url)
                                    if res.status_code == 200:
                                        trimmed_content = trim_pdf_to_max_pages(res.content, max_pages=2, filename=name)
                                        attachment = MIMEApplication(trimmed_content)
                                        attachment.add_header('Content-Disposition', 'attachment', filename=name)
                                        msg.attach(attachment)
                                        logger.info("Successfully attached SharePoint file '%s' to email.", name)
                                        attached_from_sharepoint = True
                            else:
                                # Multiple files: ZIP them in-memory and attach
                                logger.info("Multiple files (%d) found in SharePoint. Zipping for email attachment...", len(files))
                            
                                zip_buffer = io.BytesIO()
                                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                                    for file_item in files:
                                        name = file_item.get("name", "document.pdf")
                                        download_url = file_item.get("@microsoft.graph.downloadUrl")
                                        if download_url:
                                            logger.info("Downloading '%s' from SharePoint for email ZIP attachment...", name)
                                            res = await client.get(download_url)
                                            if res.status_code == 200:
                                                trimmed_content = trim_pdf_to_max_pages(res.content, max_pages=2, filename=name)
                                                zip_file.writestr(name, trimmed_content)
                                            
                                zip_buffer.seek(0)
                                zip_data = zip_buffer.read()
                                if zip_data:
                                    zip_filename = f"{person_number}_documents.zip"
                                    attachment = MIMEApplication(zip_data)
                                    attachment.add_header('Content-Disposition', 'attachment', filename=zip_filename)
                                    msg.attach(attachment)
                                    logger.info("Successfully attached SharePoint ZIP archive '%s' to email.", zip_filename)
                                    attached_from_sharepoint = True
                        else:
                            logger.info("No SharePoint documents found for person: %s", person_number)
                    except Exception as e:
                        logger.error("Failed to retrieve SharePoint attachments for email: %s", str(e))

            # Fallback to local uploads folder if nothing was attached from SharePoint
            if not attached_from_sharepoint:
                fnf_doc_name = record.get("fnf_document")
                if fnf_doc_name:
                    file_path = BASE_DIR / "uploads" / fnf_doc_name
                    if file_path.exists():
                        actual_document_count = 1
                        with open(file_path, "rb") as f:
                            file_bytes = f.read()
                        trimmed_content = trim_pdf_to_max_pages(file_bytes, max_pages=2, filename=fnf_doc_name)
                        attachment = MIMEApplication(trimmed_content)
                        attachment.add_header('Content-Disposition', 'attachment', filename=fnf_doc_name)
                        msg.attach(attachment)
                        logger.info("Attached F&F document from local server fallback: %s", fnf_doc_name)

            # Now that we know the exact number of attached files, replace the placeholder and attach body
            html_body = html_body.replace("ACTUAL_DOCUMENT_COUNT_PLACEHOLDER", str(actual_document_count))
            body_part = MIMEText(html_body, "html")
            msg.attach(body_part)

            try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=60) as server:
                    server.ehlo()
                    if "starttls" in server.esmtp_features:
                        server.starttls()
                        server.ehlo()
                    if smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, recipients, msg.as_string())

                logger.info("F&F details email sent to %s (CC: %s) for %s", email_to, cc_recipient, record.get('employee_name'))
                return {
                    "success": True,
                    "message": f"Email sent successfully to {email_to}.",
                }
            except Exception as e:
                logger.exception("Failed to send F&F details email: %s", e)
                return {"success": False, "message": f"Failed to send email: {e}"}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_fnf_details_email: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def send_fnf_email_service(record_id: int, email_to: str, db: AsyncSession, background_tasks: BackgroundTasks = None) -> dict:
        """Prepare and send the F&F details email for a specific record."""
        try:
            result = await db.execute(
                select(NdcRecord).where(NdcRecord.id == record_id)
            )
            record = result.scalar_one_or_none()
            if not record:
                return {"success": False, "message": "Record not found", "status_code": 404}

            # Fetch record approvals
            approvals_res = await db.execute(
                select(NdcApproval).where(NdcApproval.ndc_record_id == record.id)
            )
            record_approvals = approvals_res.scalars().all()

            stage_key_map = {
                "RM Approval": "rm",
                "IT Approval": "it",
                "ABEX Approval": "abex",
                "Telecom Approval": "telecom",
                "Store Approval": "store",
                "Safety Approval": "safety",
                "Administration Approval": "administration",
                "Security Approval": "security",
                "HR Approval": "hr",
                "GCC HR Approval": "gcc_hr",
                "Final ABEX Approval": "final_abex",
                "Business Specific Approval": "business_specific",
                "Legatrix Approval": "legatrix",
            }

            # Check if an F&F document file exists on the server in the uploads folder
            fnf_doc_name = ""
            for ext in [".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".xls"]:
                possible_file = f"{record.person_number}{ext}"
                possible_path = BASE_DIR / "uploads" / possible_file
                if possible_path.exists():
                    fnf_doc_name = possible_file
                    break

            # Block sending if no document is found in DB (SharePoint) or locally
            has_doc = record.fnf_document_count and record.fnf_document_count > 0
            if not has_doc and not fnf_doc_name:
                return {"success": False, "message": "No F&F document found for this employee. Email not triggered.", "status_code": 400}

            # Base record fields
            record_dict = {
                "person_number": str(record.person_number),
                "employee_name": record.employee_name or "",
                "department": record.department or record.department_reporting_name or "—",
                "resignation_date": record.resignation_date,
                "last_working_date": record.last_working_date,
                "fnf_status": CommonService._derive_fnf_status(record),
                "fnf_completed_date": record.fnf_completed_date,
                "fnf_document_count": record.fnf_document_count,
                "fnf_document": fnf_doc_name,
            }

            # Initialize approvals with default
            for prefix in stage_key_map.values():
                record_dict[f"{prefix}_approval_status"] = "Not Applicable"
                record_dict[f"{prefix}_approval_date"] = ""

            # Populate approvals
            for approval in record_approvals:
                prefix = stage_key_map.get(approval.stage_name)
                if prefix:
                    status_mapped = ""
                    if approval.status == "PENDING":
                        status_mapped = "Pending"
                    elif approval.status == "IN_PROGRESS":
                        status_mapped = "In Progress"
                    elif approval.status == "COMPLETED":
                        status_mapped = "Completed"
                    elif approval.status == "NOT_APPLICABLE":
                        status_mapped = "Not Applicable"
                    else:
                        status_mapped = approval.status.capitalize() if approval.status else "Not Applicable"

                    record_dict[f"{prefix}_approval_status"] = status_mapped
                    record_dict[f"{prefix}_approval_date"] = (
                        approval.stage_completed_at.strftime("%Y-%m-%d")
                        if approval.stage_completed_at
                        else ""
                    )

            # Mark email sent flags in DB
            record.is_fnf_email_sent = True
            if getattr(record, "is_fnf_revision", False):
                record.is_fnf_revision_email_sent = True
            await db.commit()

            if background_tasks:
                # Run the email sending task in the background so the API returns instantly
                background_tasks.add_task(EmailService.send_fnf_details_email, email_to.strip(), record_dict)
                return {"success": True, "message": f"Email queued to be sent to {email_to} shortly."}
            else:
                # Fallback to synchronous wait if no background_tasks provided
                outcome = await EmailService.send_fnf_details_email(
                    email_to=email_to.strip(),
                    record=record_dict
                )
                return outcome
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_fnf_email_service: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    def send_fnf_revision_comment_email(record, comment: str, recipient) -> bool:
        """Send an instant email to F&F Team when a record is marked Revision Required with a comment."""
        try:
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications disabled. Skipping instant F&F revision comment email.")
                return False

            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            recipients_list = EmailService._parse_recipients(recipient)
            if not recipients_list:
                env_fallback = os.getenv("FNF_EMAIL_RECIPIENT") or os.getenv("EMAIL_RECIPIENT")
                if env_fallback:
                    recipients_list = EmailService._parse_recipients(env_fallback)

            if not smtp_from:
                logger.error("SMTP_FROM not configured for F&F revision comment email")
                return False

            if not recipients_list:
                logger.warning(
                    f"F&F Team email recipient is not configured in database or environment. "
                    f"Skipping instant revision comment email for {getattr(record, 'employee_name', 'Employee')} ({getattr(record, 'person_number', 'N/A')})."
                )
                return False

            lwd = EmailService._fmt_date(record.last_working_date)
            today_str = EmailService._fmt_date(date.today())
            escaped_comment = (comment or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")

            subject = f"F&F Revision Required – {record.employee_name} ({record.person_number})"

            html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="background-color:#f5f7fb;font-family:Arial,sans-serif;margin:0;padding:0;">
<table width="100%" border="0" cellspacing="0" cellpadding="0" bgcolor="#f5f7fb" style="background-color:#f5f7fb;width:100%;padding:20px 10px;">
  <tr>
    <td align="center">
      <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;max-width:700px;margin:0 auto;background-color:#ffffff;border-radius:10px;border:1px solid #e5e7eb;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);border-collapse:separate;">
        <tr>
          <td bgcolor="#0b3d91" style="background-color:#0b3d91;color:white;padding:25px 35px;">
            <h2 style="margin:0;font-family:Arial,sans-serif;font-size:22px;color:#ffffff;font-weight:bold;">F&amp;F Revision Required – Action Needed</h2>
          </td>
        </tr>
        <tr>
          <td style="padding:30px;color:#333333;font-family:Arial,sans-serif;font-size:14px;line-height:1.7;">
            <p style="margin:0 0 16px 0;">Dear Team,</p>
            <p style="margin:0 0 16px 0;">The following F&amp;F record has been marked as <b>Revision Required</b> on {today_str}:</p>
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;margin-bottom:20px;">
              <thead>
                <tr bgcolor="#eef3fb" style="background-color:#eef3fb;">
                  <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Employee ID</th>
                  <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Name</th>
                  <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Department</th>
                  <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Last Working Date</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{record.person_number}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{record.employee_name}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{record.department or '—'}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{lwd}</td>
                </tr>
              </tbody>
            </table>
            <div style="background-color:#fffbeb;border-left:4px solid #f59e0b;padding:16px 20px;border-radius:0 6px 6px 0;margin-bottom:20px;">
              <p style="margin:0 0 8px 0;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#92400e;">Revision Comment</p>
              <p style="margin:0;font-family:Arial,sans-serif;font-size:13.5px;color:#78350f;line-height:1.6;font-style:italic;">"{escaped_comment}"</p>
            </div>
            <p style="margin:0;font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#333333;">Kindly review and take the necessary actions at the earliest.</p>
          </td>
        </tr>
        <tr>
          <td bgcolor="#fafafa" style="padding:25px 30px;background-color:#fafafa;color:#666666;border-top:1px solid #ececec;font-family:Arial,sans-serif;font-size:12.5px;line-height:1.5;">
            Regards,<br>
            <b style="color:#333333;">Team HR</b>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = ", ".join(recipients_list)

            # CC recipient for F&F Team revision comment email
            envelope_recipients = list(recipients_list)
            cc_recipient = os.getenv("FNF_EMAIL_CC") or os.getenv("EMAIL_CC", "")
            if cc_recipient:
                msg["Cc"] = cc_recipient
                envelope_recipients.append(cc_recipient)

            msg.attach(MIMEText(html_body, "html"))

            try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                    server.ehlo()
                    if "starttls" in server.esmtp_features:
                        server.starttls()
                        server.ehlo()
                    if smtp_user and smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, envelope_recipients, msg.as_string())
                logger.info(f"Successfully sent F&F revision comment email for {record.person_number} to {', '.join(recipients_list)} (CC: {msg.get('Cc', 'None')})")
                return True
            except Exception as smtp_err:
                logger.error(f"SMTP error sending F&F revision comment email: {smtp_err}")
                return False
        except Exception as e:
            logger.error(f"Error in send_fnf_revision_comment_email: {e}", exc_info=True)
            return False


    @staticmethod
    def send_notification_email(records, recipient, stage_name, manager_name=None, is_tomorrow=False):
        """Format the records as HTML and send via SMTP."""
        try:
            # Check if email notifications are enabled
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications are disabled (EMAIL_NOTIFICATION=%s). Skipping %s notification email to %s.", os.getenv("EMAIL_NOTIFICATION"), stage_name, recipient)
                return False

            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            if not smtp_from:
                logger.error("SMTP_FROM not configured in env")
                return False

            if not records:
                return False

            row_html = ""
            for rec in records:
                lwd = EmailService._fmt_date(rec.last_working_date)
                row_html += f"""
                <tr>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.person_number}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.employee_name}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.department or '—'}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{lwd}</td>
                </tr>"""

            greeting = f"Dear {manager_name}," if manager_name and "Conflict Redirected" not in manager_name else "Dear Team,"
            warning_html = ""
            if manager_name and "Conflict Redirected" in manager_name:
                clean_name = manager_name.replace(" (Conflict Redirected)", "")
                warning_html = f"""
                <p style="color: #d9534f; font-family: Arial, sans-serif; font-size: 14px; font-weight: bold; background-color: #fdf7f7; border: 1px solid #d9534f; padding: 12px; border-radius: 5px; margin-bottom: 15px; margin-top: 0;">
                  Warning: This report has been redirected to HR because there are multiple conflicting email configurations for manager '{clean_name}' in the system.
                </p>
                """

            clean_dept = stage_name.replace(" Approval", "").replace(" Approvals", "").replace(" Report", "").strip()

            if is_tomorrow:
                tomorrow_str = EmailService._fmt_date(date.today() + timedelta(days=1))
                intro_paragraph = f"""
                <p style="margin: 0 0 16px 0;">The following records are currently pending at the <b>{clean_dept} Approval</b> stage and require your attention:</p>
                <div style="background-color:#fff7e6;padding:14px 16px;margin:0 0 16px 0;border-left:4px solid #ffb020;font-family:Arial,sans-serif;font-size:13.5px;color:#666666;line-height:1.5;">
                  <b>Note:</b> The employees listed below have their Last Working Date scheduled for tomorrow ({tomorrow_str}).
                </div>
                """
                subject = f"Action Required: Pending {clean_dept} Approvals (Due Tomorrow)"
                header_title = f"Pending {clean_dept} Approval Records"
                outro = "Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."
            else:
                if clean_dept in ("F&F Team", "F&F Open"):
                    intro_paragraph = "<p style=\"margin: 0 0 16px 0;\">The following users are currently on the <b>F&F Open</b> list and require your attention:</p>"
                    subject = "F&F Open List Report - Action Required"
                    header_title = "F&F Open List Records"
                    outro = "Kindly review the above records and complete the necessary actions at the earliest to avoid delays in the process."
                elif clean_dept in ("F&F Revision Required", "F&F Revision"):
                    intro_paragraph = "<p style=\"margin: 0 0 16px 0;\">The following users currently require <b>F&F Revision</b> and require your attention:</p>"
                    subject = "F&F Revision Required - Action Required"
                    header_title = "F&F Revision Required Records"
                    outro = "Kindly review the above records and complete the necessary actions at the earliest to avoid delays in the process."
                else:
                    intro_paragraph = f"<p style=\"margin: 0 0 16px 0;\">The following records are currently pending at the <b>{clean_dept} Approval</b> stage and require your attention:</p>"
                    subject = f"Action Required: Pending {clean_dept} Approvals"
                    header_title = f"Pending {clean_dept} Approval Records"
                    outro = "Kindly review the above records and complete the necessary approvals at the earliest to avoid delays in the NDC process."

            html_body = f"""<!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="x-apple-disable-message-reformatting">
        <style>
          body {{ margin: 0; padding: 0; background-color: #f5f7fb; font-family: Arial, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
          table {{ border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
          .wrapper {{ width: 100% !important; background-color: #f5f7fb; padding: 20px 10px; }}
          .container {{ width: 100% !important; max-width: 800px !important; margin: 0 auto; background-color: #ffffff; border-radius: 10px; border: 1px solid #e5e7eb; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.08); }}
          .table-responsive {{ width: 100% !important; overflow-x: auto !important; -webkit-overflow-scrolling: touch; margin-top: 15px; }}
          @media only screen and (max-width: 600px) {{
            .wrapper {{ padding: 10px 4px !important; }}
            .header {{ padding: 18px 16px !important; }}
            .header h2 {{ font-size: 18px !important; line-height: 1.3 !important; }}
            .content {{ padding: 16px 12px !important; font-size: 13px !important; }}
            th, td {{ padding: 8px 6px !important; font-size: 12px !important; }}
          }}
        </style>
        </head>
        <body style="background-color:#f5f7fb;font-family:Arial,sans-serif;margin:0;padding:0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" bgcolor="#f5f7fb" class="wrapper" style="background-color:#f5f7fb;width:100%;padding:20px 10px;">
          <tr>
            <td align="center">
              <table class="container" width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;max-width:800px;margin:0 auto;background-color:#ffffff;border-radius:10px;border:1px solid #e5e7eb;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);border-collapse:separate;">
                <tr>
                  <td class="header" bgcolor="#0b3d91" style="background-color:#0b3d91;color:white;padding:25px 35px;">
                    <h2 style="margin:0;font-family:Arial,sans-serif;font-size:22px;color:#ffffff;font-weight:bold;">{header_title}</h2>
                  </td>
                </tr>
                <tr>
                  <td class="content" style="padding:30px;color:#333333;font-family:Arial,sans-serif;font-size:14px;line-height:1.7;">
                    <p style="margin:0 0 16px 0;">{greeting}</p>
                    {warning_html}
                    {intro_paragraph}
                    <div class="table-responsive" style="width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:15px;">
                      <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;min-width:420px;">
                        <thead>
                          <tr bgcolor="#eef3fb" style="background-color:#eef3fb;">
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Employee ID</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Name</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Department</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:1px solid #ececec;">Last Working Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {row_html}
                        </tbody>
                      </table>
                    </div>
                    <p style="margin:20px 0 0 0;font-family:Arial,sans-serif;font-size:14px;line-height:1.6;color:#333333;">
                      {outro}
                    </p>
                  </td>
                </tr>
                <tr>
                  <td class="footer" bgcolor="#fafafa" style="padding:25px 30px;background-color:#fafafa;color:#666666;border-top:1px solid #ececec;font-family:Arial,sans-serif;font-size:12.5px;line-height:1.5;">
                    Regards,<br>
                    <b style="color:#333333;">Team HR</b>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
        </body>
        </html>"""

            recipients_list = EmailService._parse_recipients(recipient)
            if not recipients_list:
                logger.error(f"Recipient not configured for {stage_name} email")
                return False

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = smtp_from
            msg["To"] = ", ".join(recipients_list)

            # CC recipient for GCC HR and F&F Team daily notifications
            envelope_recipients = list(recipients_list)
            clean_dept_lower = clean_dept.lower()
            if clean_dept_lower in ("gcc hr", "f&f team", "f&f open", "f&f revision required", "f&f revision", "fnf team", "fnf"):
                cc_recipient = os.getenv("FNF_EMAIL_CC") or os.getenv("EMAIL_CC", "")
                if cc_recipient:
                    msg["Cc"] = cc_recipient
                    envelope_recipients.append(cc_recipient)

            msg.attach(MIMEText(html_body, "html"))

            try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                    server.ehlo()
                    if "starttls" in server.esmtp_features:
                        server.starttls()
                        server.ehlo()
                    if smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, envelope_recipients, msg.as_string())
                logger.info(f"Successfully sent {stage_name} email with {len(records)} records to {', '.join(recipients_list)} (CC: {msg.get('Cc', 'None')}).")
                return True
            except Exception as e:
                logger.error(f"Failed to send {stage_name} email to {', '.join(recipients_list)}: {e}")
                return False
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_notification_email: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    def send_duplicate_managers_report(records, recipient):
        """Format the conflicting/duplicate RM records as HTML and send to HR."""
        try:
            # Check if email notifications are enabled
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications are disabled (EMAIL_NOTIFICATION=%s). Skipping duplicate managers report email to %s.", os.getenv("EMAIL_NOTIFICATION"), recipient)
                return False

            smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            if not smtp_user:
                logger.error("SMTP_USER not configured in env")
                return False

            if not records:
                return False

            row_html = ""
            for rm_name, rec in records:
                lwd = EmailService._fmt_date(rec.last_working_date)
                row_html += f"""
                <tr>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;color:#d9534f;border-bottom:1px solid #ececec;">{rm_name}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.person_number}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.employee_name}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{rec.department or '—'}</td>
                  <td style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;color:#333333;border-bottom:1px solid #ececec;">{lwd}</td>
                </tr>"""

            html_body = f"""<!DOCTYPE html>
        <html>
        <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta name="x-apple-disable-message-reformatting">
        <style>
          body {{ margin: 0; padding: 0; background-color: #f5f7fb; font-family: Arial, sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
          table {{ border-collapse: collapse; mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
          .wrapper {{ width: 100% !important; background-color: #f5f7fb; padding: 20px 10px; }}
          .container {{ width: 100% !important; max-width: 800px !important; margin: 0 auto; background-color: #ffffff; border-radius: 10px; border: 1px solid #e5e7eb; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.08); }}
          .table-responsive {{ width: 100% !important; overflow-x: auto !important; -webkit-overflow-scrolling: touch; margin-top: 15px; }}
          @media only screen and (max-width: 600px) {{
            .wrapper {{ padding: 10px 4px !important; }}
            .header {{ padding: 18px 16px !important; }}
            .header h2 {{ font-size: 18px !important; line-height: 1.3 !important; }}
            .content {{ padding: 16px 12px !important; font-size: 13px !important; }}
            th, td {{ padding: 8px 6px !important; font-size: 12px !important; }}
          }}
        </style>
        </head>
        <body style="background-color:#f5f7fb;font-family:Arial,sans-serif;margin:0;padding:0;">
        <table width="100%" border="0" cellspacing="0" cellpadding="0" bgcolor="#f5f7fb" class="wrapper" style="background-color:#f5f7fb;width:100%;padding:20px 10px;">
          <tr>
            <td align="center">
              <table class="container" width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;max-width:800px;margin:0 auto;background-color:#ffffff;border-radius:10px;border:1px solid #e5e7eb;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,.08);border-collapse:separate;">
                <tr>
                  <td class="header" bgcolor="#d9534f" style="background-color:#d9534f;color:white;padding:25px 35px;">
                    <h2 style="margin:0;font-family:Arial,sans-serif;font-size:22px;font-weight:bold;color:#ffffff;">Conflicting RM Configurations - Redirected Approvals Report</h2>
                  </td>
                </tr>
                <tr>
                  <td class="content" style="padding:30px;color:#333333;font-family:Arial,sans-serif;font-size:14px;line-height:1.7;">
                    <p style="margin:0 0 16px 0;">Dear Team,</p>
                    <p style="color: #d9534f; font-weight: bold; background-color: #fdf7f7; border: 1px solid #d9534f; padding: 12px; border-radius: 5px; margin-bottom: 15px; margin-top:0;">
                      Warning: The following pending RM approvals have been redirected to HR because their Reporting Managers have multiple conflicting email configurations in the system. Please resolve these duplicates in the <b>rm_email_configuration</b> database table.
                    </p>
                    <div class="table-responsive" style="width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;margin-top:15px;">
                      <table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;min-width:480px;">
                        <thead>
                          <tr bgcolor="#fdf7f7" style="background-color:#fdf7f7;">
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:2px solid #d9534f;">Reporting Manager</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:2px solid #d9534f;">Employee ID</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:2px solid #d9534f;">Name</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:2px solid #d9534f;">Department</th>
                            <th style="padding:12px 14px;font-family:Arial,sans-serif;font-size:13px;font-weight:bold;text-align:left;color:#333333;border-bottom:2px solid #d9534f;">Last Working Date</th>
                          </tr>
                        </thead>
                        <tbody>
                          {row_html}
                        </tbody>
                      </table>
                    </div>
                    <p style="margin:20px 0 0 0;">Please review these records and take the necessary actions.</p>
                  </td>
                </tr>
                <tr>
                  <td class="footer" bgcolor="#fafafa" style="padding:25px 30px;background-color:#fafafa;color:#666666;border-top:1px solid #ececec;font-family:Arial,sans-serif;font-size:12.5px;line-height:1.5;">
                    Regards,<br>
                    <b style="color:#333333;">Team HR</b>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
        </body>
        </html>"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Redirected RM Approvals Report (Conflicting Manager Configurations) - Action Required"
            msg["From"] = smtp_from
            msg["To"] = recipient
            msg.attach(MIMEText(html_body, "html"))

            try:
                with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                    server.ehlo()
                    if "starttls" in server.esmtp_features:
                        server.starttls()
                        server.ehlo()
                    if smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.sendmail(smtp_from, [recipient], msg.as_string())
                logger.info(f"Successfully sent consolidated duplicate RM report with {len(records)} records to HR ({recipient}).")
                return True
            except Exception as e:
                logger.error(f"Failed to send consolidated duplicate RM report to HR ({recipient}): {e}")
                return False
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_duplicate_managers_report: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def fetch_all_data():
        """Fetch all active NDC records and their approval stages from the database, handling schema differences if needed."""
        try:
            async with async_session() as session:
                # Check if 'approver_name' column exists in database to avoid ProgrammingError on old schemas
                has_approver_name_col = False
                try:
                    col_check = await session.execute(text(
                        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='ndc_records' AND column_name='approver_name')"
                    ))
                    has_approver_name_col = col_check.scalar()
                except Exception as e:
                    logger.warning(f"Could not check for approver_name column presence: {e}")

                query = select(NdcRecord, NdcApproval).join(NdcApproval, NdcRecord.id == NdcApproval.ndc_record_id)
                if not has_approver_name_col and hasattr(NdcRecord, "approver_name"):
                    query = query.options(defer(NdcRecord.approver_name))
                
                result = await session.execute(query)
                rows = result.all()
            
                # Group by record
                records_map = {}
                for rec, app in rows:
                    if rec.id not in records_map:
                        records_map[rec.id] = {
                            "record": rec,
                            "approvals": {},
                            "db_approvals": []
                        }
                    records_map[rec.id]["db_approvals"].append(app)
                
                    # Use lower case for consistent matching
                    stage = app.stage_name.strip().lower()
                    status = app.status.strip().lower() if app.status else ""
                
                    # Handle GCC HR vs HR carefully
                    if "gcc hr" in stage:
                        key = "gcc hr"
                    elif "hr" in stage:
                        key = "hr"
                    elif "rm" in stage:
                        key = "rm"
                    elif "telecom" in stage:
                        key = "telecom"
                    elif "administration" in stage or "admin" in stage:
                        key = "administration"
                    elif "it" in stage:
                        key = "it"
                    elif "safety" in stage:
                        key = "safety"
                    elif "security" in stage:
                        key = "security"
                    elif "final abex" in stage:
                        key = "final abex"
                    elif "abex" in stage:
                        key = "abex"
                    elif "store" in stage:
                        key = "store"
                    elif "business specific" in stage:
                        key = "business specific"
                    elif "legatrix" in stage:
                        key = "legatrix"
                    else:
                        key = stage
                    
                    records_map[rec.id]["approvals"][key] = status
                
                return records_map
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in fetch_all_data: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def run_10am_job():
        """Daily 10:00 AM Email Job to send all pending approval updates."""
        try:
            # Check if email notifications are enabled
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications are disabled (EMAIL_NOTIFICATION=%s). Skipping 10:00 AM email job entirely.", os.getenv("EMAIL_NOTIFICATION"))
                return

            logger.info("Starting consolidated 10:00 AM email job...")
            records_map = await EmailService.fetch_all_data()
        
            # Fetch department email recipients and RM configs
            dept_email_map = {}
            rm_configs_by_name = {}  # key: rm_name (lower) -> list of emails
        
            async with async_session() as session:
                try:
                    dept_res = await session.execute(select(EmailRecipient))
                    for rec in dept_res.scalars().all():
                        if rec.department and rec.email:
                            dept_key = rec.department.strip().lower()
                            parsed_emails = EmailService._parse_recipients(rec.email)
                            if dept_key not in dept_email_map:
                                dept_email_map[dept_key] = []
                            for e in parsed_emails:
                                if e not in dept_email_map[dept_key]:
                                    dept_email_map[dept_key].append(e)
                except Exception as e:
                    logger.warning(f"Could not fetch department email recipients: {e}")
                
                try:
                    rm_configs_res = await session.execute(select(RmEmailConfiguration))
                    for cfg in rm_configs_res.scalars().all():
                        if cfg.rm_name and cfg.email:
                            name_key = cfg.rm_name.strip().lower()
                            email_val = cfg.email.strip()
                            if name_key not in rm_configs_by_name:
                                rm_configs_by_name[name_key] = []
                            rm_configs_by_name[name_key].append(email_val)
                except Exception as e:
                    logger.warning(f"Could not fetch RM email configurations: {e}")
                
            rm_groups = {}  # key: (rm_name, rm_email) -> value: list of NdcRecord
            duplicate_rm_records = []  # list of (rm_name, rec)
            fnf_revision_records = []  # list of NdcRecord for F&F Revision Required (sent only once)
            fnf_paid_records = []  # list of NdcRecord for F&F Paid (Not in DMS)
        
            departments = [
                ("HR", dept_email_map.get("hr")),
                ("Telecom", dept_email_map.get("telecom")),
                ("Administration", dept_email_map.get("administration")),
                ("GCC HR", dept_email_map.get("gcc hr")),
                ("Abex", dept_email_map.get("abex")),
                ("Store", dept_email_map.get("store")),
                ("Safety", dept_email_map.get("safety")),
                ("Final Abex", dept_email_map.get("final abex")),
                ("Business Specific", dept_email_map.get("business specific")),
                ("Legatrix", dept_email_map.get("legatrix")),
                ("F&F Team", dept_email_map.get("f&f team")),
            ]
        
            emails_to_send = {dep: [] for dep, _ in departments}
        
            for rec_id, data in records_map.items():
                rec = data["record"]
                approvals = data["approvals"]
                db_approvals = data.get("db_approvals", [])
            
                # 1. Group for RM department separately (only if Pending)
                if approvals.get("rm", "") == "pending":
                    rm_name = getattr(rec, "approver_name", None)
                    if not rm_name:
                        for app in db_approvals:
                            if app.stage_name.strip().lower() == "rm":
                                rm_name = app.approver_name
                                break
                
                    if rm_name:
                        rm_name = rm_name.strip()
                    else:
                        rm_name = "Unknown Manager"
                    
                    has_conflict = False
                    rm_email = None
                
                    if rm_name and rm_name != "Unknown Manager":
                        normalized_rm = rm_name.lower()
                        if normalized_rm in rm_configs_by_name:
                            emails = rm_configs_by_name[normalized_rm]
                            if len(emails) > 1:
                                has_conflict = True
                            elif len(emails) == 1:
                                rm_email = emails[0]
                
                    default_rm_email = dept_email_map.get("rm")
                
                    if has_conflict:
                        duplicate_rm_records.append((rm_name, rec))
                    else:
                        target_email = rm_email or default_rm_email
                        if not target_email:
                            logger.info(f"Skipping notification for RM '{rm_name}': no email configuration or default RM email found.")
                            continue
                        key = (rm_name, target_email)
                        if key not in rm_groups:
                            rm_groups[key] = []
                        rm_groups[key].append(rec)
                
                # 2. Build for other departments
                for dept_name, recipient in departments:
                    dept_key = dept_name.lower()
                    current_status = approvals.get(dept_key, "")
                
                    # Specific rule for GCC HR
                    if dept_name == "GCC HR":
                        req_depts = ["rm", "it", "telecom", "safety", "administration", "security", "hr"]
                        all_completed = True
                        for req_d in req_depts:
                            if approvals.get(req_d, "") != "completed":
                                all_completed = False
                                break
                    
                        if current_status == "pending" and all_completed:
                            emails_to_send[dept_name].append(rec)
                    elif dept_name == "F&F Team":
                        # Specific rule for F&F Team (F&F Open list)
                        is_eligible = rec.ndc_stage == "NDC Completed" and approvals.get("gcc hr") == "completed"
                        is_fnf_open = (
                            is_eligible
                            and (not rec.is_fnf_completed)
                            and (not rec.is_fnf_revision)
                            and (not getattr(rec, "is_fnf_paid", False))
                            and (not getattr(rec, "is_fnf_closed", False))
                        )
                        if is_fnf_open:
                            emails_to_send[dept_name].append(rec)
                    else:
                        if current_status == "pending":
                            emails_to_send[dept_name].append(rec)

                # Collect F&F Paid records (where payment done but DMS pending — neither completed nor closed)
                is_fnf_paid = getattr(rec, "is_fnf_paid", False)
                is_fnf_completed = getattr(rec, "is_fnf_completed", False)
                is_fnf_closed = getattr(rec, "is_fnf_closed", False)
                if is_fnf_paid and not is_fnf_completed and not is_fnf_closed:
                    fnf_paid_records.append(rec)

                # Collect new F&F Revision Required records (to send only once to F&F Team)
                is_fnf_revision = getattr(rec, "is_fnf_revision", False)
                is_fnf_revision_email_sent = getattr(rec, "is_fnf_revision_email_sent", False)
                if is_fnf_revision and not is_fnf_revision_email_sent:
                    fnf_revision_records.append(rec)
                            
            # Send RM emails in batches
            rm_group_items = list(rm_groups.items())
            total_rm_emails = len(rm_group_items)
        
            success_count = 0
            failure_count = 0
        
            if total_rm_emails > 0:
                BATCH_SIZE = int(os.getenv("EMAIL_BATCH_SIZE", "10"))
                BATCH_DELAY = int(os.getenv("EMAIL_BATCH_DELAY_SECONDS", "30"))
            
                logger.info(f"Starting RM email send. Total unique RMs: {total_rm_emails}. Batch size: {BATCH_SIZE}. Batch delay: {BATCH_DELAY}s.")
            
                for i in range(0, total_rm_emails, BATCH_SIZE):
                    batch = rm_group_items[i:i + BATCH_SIZE]
                    logger.info(f"Sending RM email batch {i // BATCH_SIZE + 1} (emails {i+1} to {min(i + BATCH_SIZE, total_rm_emails)} of {total_rm_emails})...")
                
                    for (rm_name, rm_email), recs in batch:
                        try:
                            success = EmailService.send_notification_email(recs, rm_email, "RM", manager_name=rm_name)
                            if success:
                                success_count += 1
                            else:
                                failure_count += 1
                        except Exception as e:
                            logger.error(f"Failed to send email to RM '{rm_name}' ({rm_email}): {e}")
                            failure_count += 1
                        await asyncio.sleep(2)
                
                    if i + BATCH_SIZE < total_rm_emails:
                        logger.info(f"Waiting for {BATCH_DELAY} seconds before next batch...")
                        await asyncio.sleep(BATCH_DELAY)
                    
                logger.info(f"RM Email Job Completed. Success: {success_count}, Failure: {failure_count}")
            else:
                logger.info("No pending RM records. Skipping RM emails.")
            
            # Send duplicate/conflicting RM records report to HR
            if duplicate_rm_records:
                hr_email = dept_email_map.get("hr")
                if hr_email:
                    EmailService.send_duplicate_managers_report(duplicate_rm_records, hr_email)
                else:
                    logger.warning("Conflicting RM records found, but HR email is not configured in database.")
                await asyncio.sleep(2)
            
            # Send other department emails
            for dept_name, recipient in departments:
                if not recipient:
                    logger.info(f"Skipping {dept_name} daily notification: recipient email is not configured.")
                    continue
                
                records_for_dept = emails_to_send[dept_name]
                if records_for_dept:
                    EmailService.send_notification_email(records_for_dept, recipient, dept_name)
                else:
                    logger.info(f"No pending records for {dept_name}. Skipping email.")

            # Send daily 10:00 AM F&F Paid (Not in DMS) reminder to F&F Team
            if fnf_paid_records:
                ff_recipient_list = dept_email_map.get("f&f team")
                ff_recipient = ", ".join(ff_recipient_list) if ff_recipient_list else os.getenv("EMAIL_RECIPIENT", "")
                if ff_recipient:
                    logger.info(f"Sending daily 10:00 AM F&F Paid reminder with {len(fnf_paid_records)} records to {ff_recipient}...")
                    paid_payload = [
                        {
                            "id": r.id,
                            "person_number": str(r.person_number) if r.person_number else "",
                            "employee_name": r.employee_name or "",
                            "department": r.department or "—",
                            "last_working_date": (
                                r.last_working_date.strftime("%Y-%m-%d")
                                if r.last_working_date
                                else ""
                            ),
                            "days_delayed": EmailService._days_delayed(r.last_working_date),
                        }
                        for r in fnf_paid_records
                    ]
                    paid_payload.sort(key=lambda x: x["last_working_date"] or "", reverse=True)
                    try:
                        res = await EmailService.send_delayed_reminder(
                            paid_payload,
                            recipient=ff_recipient,
                            reminder_type="fnf_paid",
                        )
                        if res.get("success"):
                            logger.info("Successfully sent daily 10:00 AM F&F Paid reminder email.")
                        else:
                            logger.error(f"Failed to send daily 10:00 AM F&F Paid reminder: {res.get('message')}")
                    except Exception as e:
                        logger.error(f"Error sending daily 10:00 AM F&F Paid reminder email: {e}")
                else:
                    logger.warning("F&F Team email recipient not configured. Skipping daily 10:00 AM F&F Paid reminder email.")

            # NOTE: Daily F&F Revision Required email is disabled.
            # Revision emails are now sent instantly when admin marks "Needs Revision" with a comment.
            # if fnf_revision_records:
            #     ff_recipient = dept_email_map.get("f&f team")
            #     if not ff_recipient:
            #         ff_recipient = os.getenv("EMAIL_RECIPIENT", "")
            #     
            #     if ff_recipient:
            #         logger.info(f"Sending daily F&F Revision Required email with {len(fnf_revision_records)} records to {ff_recipient}...")
            #         loop = asyncio.get_event_loop()
            #         success = await loop.run_in_executor(
            #             None,
            #             EmailService.send_notification_email,
            #             fnf_revision_records,
            #             ff_recipient,
            #             "F&F Revision Required"
            #         )
            #         if success:
            #             # Mark as email sent in database
            #             async with async_session() as session:
            #                 for r in fnf_revision_records:
            #                     stmt = select(NdcRecord).where(NdcRecord.id == r.id)
            #                     db_res = await session.execute(stmt)
            #                     db_rec = db_res.scalar_one_or_none()
            #                     if db_rec:
            #                         db_rec.is_fnf_revision_email_sent = True
            #                 await session.commit()
            #             logger.info("Successfully sent daily F&F Revision Required email and updated is_fnf_revision_email_sent flags in DB.")
            #     else:
            #         logger.warning("F&F Team email recipient not configured. Skipping daily F&F Revision Required email.")
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in run_10am_job: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def get_pending_records_for_tomorrow(stage_keyword: str):
        """Fetch NdcRecord instances where the specified stage is pending and last_working_date is tomorrow."""
        try:
            target_date = date.today() + timedelta(days=1)
        
            async with async_session() as session:
                query = (
                    select(NdcRecord)
                    .join(NdcApproval, NdcRecord.id == NdcApproval.ndc_record_id)
                    .where(
                        NdcApproval.stage_name.ilike(f"%{stage_keyword}%"),
                        NdcApproval.status.ilike("PENDING"),
                        NdcRecord.last_working_date == target_date
                    )
                    .distinct()
                )
                result = await session.execute(query)
                records = result.scalars().unique().all()
            
                # Ensure strict uniqueness by person_number
                unique_records = []
                seen_person_numbers = set()
                for r in records:
                    if r.person_number not in seen_person_numbers:
                        seen_person_numbers.add(r.person_number)
                        unique_records.append(r)
                    
                return unique_records
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in get_pending_records_for_tomorrow: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def process_stage_for_tomorrow(keyword: str, recipient: str, stage_name: str):
        try:
            if not recipient:
                logger.info(f"Skipping {stage_name} tomorrow notification: recipient email is not configured.")
                return
            
            logger.info(f"Fetching pending {stage_name} records for tomorrow...")
            records = await EmailService.get_pending_records_for_tomorrow(keyword)
        
            if not records:
                logger.info(f"No pending {stage_name} records found for tomorrow. Email not sent.")
                return
            
            logger.info(f"Found {len(records)} pending {stage_name} records for tomorrow. Sending email to {recipient}...")
            EmailService.send_notification_email(records, recipient, stage_name, is_tomorrow=True)
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in process_stage_for_tomorrow: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def run_tomorrow_alert_job():
        """Tomorrow Alert Job specifically for IT & Security pending actions."""
        try:
            # Check if email notifications are enabled
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications are disabled (EMAIL_NOTIFICATION=%s). Skipping tomorrow alert job entirely.", os.getenv("EMAIL_NOTIFICATION"))
                return

            logger.info("Starting Tomorrow Alerts (IT & Security) email job...")
            dept_email_map = {}
            async with async_session() as session:
                try:
                    res = await session.execute(select(EmailRecipient))
                    for rec in res.scalars().all():
                        if rec.department and rec.email:
                            dept_email_map[rec.department.strip().lower()] = rec.email.strip()
                except Exception as e:
                    logger.warning(f"Could not fetch department email recipients: {e}")

            # 1. Process IT Approvals for tomorrow
            await EmailService.process_stage_for_tomorrow(
                keyword="IT", 
                recipient=dept_email_map.get("it"), 
                stage_name="IT"
            )
        
            # 2. Process Security Approvals for tomorrow
            await EmailService.process_stage_for_tomorrow(
                keyword="Security", 
                recipient=dept_email_map.get("security"), 
                stage_name="Security"
            )
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in run_tomorrow_alert_job: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def send_auto_fnf_emails(db: AsyncSession):
        """
        Scan for records where is_fnf_completed is True and is_fnf_email_sent is False.
        Check if a document exists (locally or on SharePoint).
        If a document exists, find the employee's email address from the employee_email_master
        and automatically send the F&F details email, updating is_fnf_email_sent to True.
        """
        try:
            # Check if email notifications are enabled
            if os.getenv("EMAIL_NOTIFICATION", "on").lower() not in ("on", "true", "1", "yes"):
                logger.info("Email notifications are disabled (EMAIL_NOTIFICATION=%s). Skipping auto F&F email sending.", os.getenv("EMAIL_NOTIFICATION"))
                return

            logger.info("Auto F&F Email Sender: Starting check...")
        
            # 1. Fetch eligible records
            try:
                stmt = select(NdcRecord).where(
                    NdcRecord.is_fnf_completed == True,
                    NdcRecord.is_fnf_email_sent == False
                )
                res = await db.execute(stmt)
                records = res.scalars().all()
            except Exception as e:
                logger.error("Auto F&F Email Sender: Failed to query eligible records: %s", str(e))
                return

            if not records:
                logger.info("Auto F&F Email Sender: No unsent completed F&F records found.")
                return

            logger.info("Auto F&F Email Sender: Found %d record(s) to process.", len(records))

            # Import locally inside function to avoid circular imports
            from app.models.employee_email_master import EmployeeEmailMaster

            for record in records:
                person_number = record.person_number
                if not person_number:
                    continue

                # 2. Check if a document exists (using the new fast DB column)
                has_doc = record.fnf_document_count and record.fnf_document_count > 0

                # Check local uploads folder as a fallback if DB says 0
                if not has_doc:
                    for ext in [".pdf", ".png", ".jpg", ".jpeg", ".docx", ".xlsx", ".xls"]:
                        possible_file = f"{person_number}{ext}"
                        possible_path = BASE_DIR / "uploads" / possible_file
                        if possible_path.exists():
                            has_doc = True
                            break

                if not has_doc:
                    logger.info("Auto F&F Email Sender: No F&F document found yet for employee %s (%s). Skipping.", record.employee_name, person_number)
                    continue

                # 3. Get employee email from master table
                try:
                    # Cast person_number to int because NdcRecord stores it as string, 
                    # but EmployeeEmailMaster stores it as BigInteger!
                    pn_int = int(person_number)
                    stmt_email = select(EmployeeEmailMaster.email).where(EmployeeEmailMaster.person_number == pn_int)
                    res_email = await db.execute(stmt_email)
                    emp_email = res_email.scalar_one_or_none()
                except Exception as e:
                    logger.error("Auto F&F Email Sender: Failed to look up email for %s: %s", person_number, str(e))
                    continue

                if not emp_email:
                    continue

                # 4. Send F&F details email
                logger.info("Auto F&F Email Sender: Sending F&F email to %s for %s (%s)...", emp_email, record.employee_name, person_number)
                try:
                    outcome = await EmailService.send_fnf_email_service(record.id, emp_email, db)
                    if outcome.get("success"):
                        record.is_fnf_email_sent = True
                        await db.commit()
                        logger.info("Auto F&F Email Sender: Successfully sent email and updated record for employee %s (%s).", record.employee_name, person_number)
                    else:
                        logger.error("Auto F&F Email Sender: Failed to send F&F details email for employee %s (%s): %s", record.employee_name, person_number, outcome.get("message"))
                except Exception as e:
                    logger.exception("Auto F&F Email Sender: Exception occurred while processing %s: %s", person_number, str(e))
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_auto_fnf_emails: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


    @staticmethod
    async def send_password_reset_email(to_email: str, reset_link: str) -> dict:
        """Send a password reset email to the specified recipient."""
        try:
            smtp_host = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER") or os.getenv("SMTP_USERNAME", "")
            smtp_password = os.getenv("SMTP_PASSWORD", "")
            smtp_from = os.getenv("SMTP_FROM", smtp_user)

            if not smtp_user:
                msg = "SMTP user not configured"
                logger.warning(msg)
                return {"success": False, "message": msg}

            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1.0">
              <meta name="x-apple-disable-message-reformatting">
              <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 15px 10px; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
                .card {{ max-width: 540px; width: 100%; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }}
                .header {{ background-color: #003b70; color: #ffffff; padding: 24px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 20px; font-weight: 600; letter-spacing: 0.5px; }}
                .body {{ padding: 32px 24px; color: #334155; line-height: 1.6; font-size: 14px; }}
                .btn-container {{ text-align: center; margin: 28px 0; }}
                .btn {{ display: inline-block; background-color: #003b70; color: #ffffff !important; padding: 12px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .footer {{ background-color: #f8fafc; padding: 16px 24px; border-top: 1px solid #f1f5f9; text-align: center; font-size: 12px; color: #64748b; }}
                .warning {{ background-color: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px; font-size: 13px; color: #92400e; border-radius: 0 4px 4px 0; margin-top: 20px; }}
                @media only screen and (max-width: 600px) {{
                  body {{ padding: 10px 5px !important; }}
                  .header {{ padding: 18px 16px !important; }}
                  .body {{ padding: 20px 16px !important; font-size: 13px !important; }}
                  .btn {{ padding: 10px 20px !important; font-size: 13px !important; }}
                }}
              </style>
            </head>
            <body>
              <div class="card">
                <div class="header">
                  <h1>Adani HR NDC Tracking</h1>
                </div>
                <div class="body">
                  <p>Dear Team,</p>
                  <p>We received a request to reset your password for your <strong>Adani HR NDC Tracking</strong> account.</p>
                  <p>Click the button below to set a new password:</p>
                  <div class="btn-container">
                    <a href="{reset_link}" class="btn" target="_blank">Reset Password</a>
                  </div>
                  <p>Or copy and paste this link into your browser:</p>
                  <p style="word-break: break-all; font-size: 12px; color: #003b70;"><a href="{reset_link}">{reset_link}</a></p>
                  <div class="warning">
                    ⏳ This password reset link is valid for <strong>30 minutes</strong>. If you did not request this, please ignore this email.
                  </div>
                  <p style="margin-top: 20px; font-size: 14px; color: #475569;">
                    Regards,<br>
                    <strong>Team HR</strong>
                  </p>
                </div>
                <div class="footer">
                  &copy; {datetime.now().year} Adani HR NDC Tracking Platform. All rights reserved.
                </div>
              </div>
            </body>
            </html>
            """

            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Password Reset Request – Adani HR NDC Tracking"
            msg["From"] = smtp_from
            msg["To"] = to_email
            msg.attach(MIMEText(html_content, "html"))

            try:
                def _send():
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                        server.ehlo()
                        if "starttls" in server.esmtp_features:
                            server.starttls()
                            server.ehlo()
                        if smtp_password:
                            server.login(smtp_user, smtp_password)
                        server.sendmail(smtp_from, [to_email], msg.as_string())

                await asyncio.to_thread(_send)
                logger.info("Password reset email sent successfully to %s", to_email)
                return {"success": True, "message": "Email sent"}
            except Exception as e:
                logger.error("Failed to send password reset email to %s: %s", to_email, str(e))
                return {"success": False, "message": str(e)}
        except HTTPException:
            raise
        except Exception as e:
            import logging; logging.error(f'Error in send_password_reset_email: {e}', exc_info=True)
            import fastapi
            raise fastapi.HTTPException(status_code=500, detail='An internal server error occurred.')


