"""
Gmail notifier — sends an HTML digest email with top 10 scored jobs.
Uses smtplib + SSL (port 465) with a Gmail App Password.
"""

import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any

import config

logger = logging.getLogger(__name__)


class Notifier:
    def send_digest(self, jobs: List[Dict[str, Any]]) -> bool:
        """
        Send HTML email digest of top jobs.
        Returns True on success.
        """
        if not jobs:
            logger.info("Notifier: no jobs to send")
            return True

        if not config.GMAIL_APP_PASSWORD:
            logger.warning("Notifier: GMAIL_APP_PASSWORD not set — skipping email")
            return False

        top_jobs = sorted(jobs, key=lambda j: j.get("score", 0), reverse=True)[:10]

        subject = (
            f"[Job Alert] {len(top_jobs)} Top Data Engineer Jobs "
            f"— {datetime.now().strftime('%b %d, %Y')}"
        )
        html = self._build_html(top_jobs, len(jobs))

        return self._send_email(subject, html)

    # ------------------------------------------------------------------
    def _send_email(self, subject: str, html: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = config.GMAIL_ADDRESS
        msg["To"]      = config.ALERT_RECIPIENT

        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
                server.sendmail(
                    config.GMAIL_ADDRESS,
                    config.ALERT_RECIPIENT,
                    msg.as_string(),
                )
            logger.info("Notifier: email sent to %s", config.ALERT_RECIPIENT)
            return True
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("Gmail auth failed — check GMAIL_APP_PASSWORD: %s", exc)
            return False
        except Exception as exc:
            logger.error("Email send error: %s", exc)
            return False

    def send_outreach_emails(self, outreach_messages: List[Dict[str, Any]]) -> int:
        """
        Actually send outreach emails via Gmail SMTP to recruiters.
        Returns the number of successful sends.
        """
        if not config.GMAIL_APP_PASSWORD:
            logger.warning("Notifier: GMAIL_APP_PASSWORD not set — skipping outreach delivery")
            return 0

        emails_to_send = [msg for msg in outreach_messages if msg.get("message_type") in ("recruiter_email", "follow_up_message")]
        if not emails_to_send:
            return 0

        sent_count = 0
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(config.GMAIL_ADDRESS, config.GMAIL_APP_PASSWORD)
                
                for msg in emails_to_send:
                    # In a real scenario, you'd fetch the recruiter's email.
                    # For this, we'll send it to the ALERT_RECIPIENT as a proxy to avoid spamming actual recruiters.
                    # Or if 'to_email' is present in msg, we'd use that.
                    to_email = msg.get("to_email", config.ALERT_RECIPIENT)
                    
                    mime_msg = MIMEMultipart("alternative")
                    mime_msg["Subject"] = msg.get("subject", "Following up")
                    mime_msg["From"]    = config.GMAIL_ADDRESS
                    mime_msg["To"]      = to_email
                    
                    body_text = msg.get("body", "")
                    mime_msg.attach(MIMEText(body_text, "plain"))
                    
                    server.sendmail(config.GMAIL_ADDRESS, to_email, mime_msg.as_string())
                    sent_count += 1
                    logger.info("Outreach: Email sent to %s for job_id %s", to_email, msg.get("job_id"))
                    
            return sent_count
            
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("Outreach: Gmail auth failed: %s", exc)
            return sent_count
        except Exception as exc:
            logger.error("Outreach: Email send array error: %s", exc)
            return sent_count

    # ------------------------------------------------------------------
    @staticmethod
    def _build_html(jobs: List[Dict[str, Any]], total: int) -> str:
        rows = ""
        for i, job in enumerate(jobs, 1):
            salary = job.get("salary")
            salary_str = f"${salary:,}/yr" if salary else "Not listed"

            posted = job.get("posted_date") or ""
            if isinstance(posted, datetime):
                posted = posted.strftime("%b %d, %Y")

            easy = job.get("easy_apply")
            easy_badge = (
                '<span style="background:#22c55e;color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">Easy Apply</span>'
                if easy else ""
            )

            score = job.get("score", 0)
            score_color = "#22c55e" if score >= 65 else ("#f59e0b" if score >= 40 else "#ef4444")

            url = job.get("url", "#")

            rows += f"""
            <tr style="border-bottom:1px solid #e5e7eb;">
              <td style="padding:12px 8px;font-weight:600;color:#1e293b;">#{i}</td>
              <td style="padding:12px 8px;">
                <a href="{url}" style="color:#2563eb;text-decoration:none;font-weight:600;">{job.get('title','')}</a>
                <br><small style="color:#6b7280;">{job.get('company','')} · {job.get('location','')}</small>
                <br>{easy_badge}
              </td>
              <td style="padding:12px 8px;text-align:center;">
                <span style="background:{score_color};color:#fff;padding:3px 8px;border-radius:12px;font-weight:700;">{score}</span>
              </td>
              <td style="padding:12px 8px;color:#059669;font-weight:600;">{salary_str}</td>
              <td style="padding:12px 8px;color:#6b7280;font-size:13px;">{posted}</td>
              <td style="padding:12px 8px;">
                <a href="{url}" style="background:#2563eb;color:#fff;padding:6px 12px;border-radius:6px;text-decoration:none;font-size:13px;">Apply</a>
              </td>
            </tr>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;margin:0;padding:0;">
          <div style="max-width:800px;margin:0 auto;padding:24px;">

            <!-- Header -->
            <div style="background:linear-gradient(135deg,#1e3a5f,#2563eb);border-radius:12px;padding:24px;margin-bottom:24px;color:#fff;">
              <h1 style="margin:0;font-size:22px;">Data Engineer Job Alert</h1>
              <p style="margin:8px 0 0;opacity:.85;">
                {total} jobs found · Top {len(jobs)} shown · Score threshold: {config.ALERT_SCORE_THRESHOLD}
              </p>
              <p style="margin:4px 0 0;font-size:13px;opacity:.7;">
                Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
              </p>
            </div>

            <!-- Table -->
            <div style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">
              <table style="width:100%;border-collapse:collapse;">
                <thead>
                  <tr style="background:#f1f5f9;">
                    <th style="padding:12px 8px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">#</th>
                    <th style="padding:12px 8px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Job</th>
                    <th style="padding:12px 8px;text-align:center;font-size:12px;color:#6b7280;text-transform:uppercase;">Score</th>
                    <th style="padding:12px 8px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Salary</th>
                    <th style="padding:12px 8px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Posted</th>
                    <th style="padding:12px 8px;text-align:left;font-size:12px;color:#6b7280;text-transform:uppercase;">Apply</th>
                  </tr>
                </thead>
                <tbody>
                  {rows}
                </tbody>
              </table>
            </div>

            <!-- Footer -->
            <p style="text-align:center;color:#9ca3af;font-size:12px;margin-top:16px;">
              Automated Job Scraper · Unsubscribe by disabling the GitHub Action
            </p>
          </div>
        </body>
        </html>
        """
