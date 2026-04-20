import os
import smtplib
from email.message import EmailMessage


def send_email_sync(to_email: str, subject: str, body: str) -> None:
    """
    Sends email via SMTP if SMTP_HOST / SMTP_USER / SMTP_PASSWORD are set;
    otherwise logs to stdout (demo / local dev).
    """
    host = os.getenv("SMTP_HOST", "").strip()
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASSWORD", "").strip()
    from_addr = os.getenv("FROM_EMAIL", "blog-api@localhost")

    if not host or not user:
        print(f"\n--- [Blog API email demo] ---\nTo: {to_email}\nSubject: {subject}\n\n{body}\n---\n")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_email
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
