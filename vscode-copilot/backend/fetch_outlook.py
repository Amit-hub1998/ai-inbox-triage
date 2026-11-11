"""
Step 1: pull mail from Outlook via COM and write data/emails.json.

Windows + classic Outlook desktop only. Reads your inbox, does NOT mark
anything as read, applies the offline bucketing rules, and writes the result
for the VS Code extension (the AI brain) to pick up.

Run:  python fetch_outlook.py
"""
import json
import os
import sys
from datetime import datetime, timedelta

import config
import rules

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
EMAILS_PATH = os.path.join(DATA_DIR, "emails.json")

OL_FOLDER_INBOX = 6  # olFolderInbox
MAIL_ITEM_CLASS = 43  # olMail


def _clean(value, limit=None):
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").strip()
    return text[:limit] if limit else text


def fetch_emails():
    try:
        import win32com.client
        from pywintypes import com_error
    except ImportError:
        print("Missing pywin32. Install with: python -m pip install pywin32",
              file=sys.stderr)
        sys.exit(1)

    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        inbox = namespace.GetDefaultFolder(OL_FOLDER_INBOX)
        items = inbox.Items
        items.Sort("[ReceivedTime]", True)  # newest first
    except com_error as error:
        print(f"Outlook COM error: {error}", file=sys.stderr)
        print("Check that classic Outlook is installed and a mail profile is configured.",
              file=sys.stderr)
        sys.exit(1)

    cutoff = None
    if config.LOOKBACK_DAYS:
        cutoff = datetime.now() - timedelta(days=config.LOOKBACK_DAYS)

    emails = []
    for message in items:
        try:
            if getattr(message, "Class", None) != MAIL_ITEM_CLASS:
                continue

            received = getattr(message, "ReceivedTime", None)
            if cutoff and received is not None:
                # COM datetime -> naive python datetime for comparison
                try:
                    received_dt = datetime(received.year, received.month, received.day,
                                           received.hour, received.minute, received.second)
                    if received_dt < cutoff:
                        break  # sorted newest-first, so we can stop
                except Exception:
                    pass

            sender_email = ""
            try:
                sender_email = _clean(message.SenderEmailAddress)
            except Exception:
                pass

            emails.append({
                "id": _clean(getattr(message, "EntryID", "")),
                "from": _clean(getattr(message, "SenderName", "")),
                "from_email": sender_email,
                "subject": _clean(getattr(message, "Subject", "(no subject)")),
                "received": _clean(received),
                "unread": bool(getattr(message, "UnRead", False)),
                "importance": int(getattr(message, "Importance", 1)),
                "body": _clean(getattr(message, "Body", ""), limit=2000),
            })
        except Exception as exc:
            print(f"Skipped one message: {exc}", file=sys.stderr)
            continue

    return emails


def main():
    emails = fetch_emails()
    emails = rules.enrich_with_buckets(emails)

    os.makedirs(DATA_DIR, exist_ok=True)
    payload = {
        "fetched_at": datetime.now().isoformat(timespec="seconds"),
        "total": len(emails),
        "counts": rules.bucket_counts(emails),
        "emails": emails,
    }
    with open(EMAILS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(emails)} emails to {os.path.abspath(EMAILS_PATH)}")
    print(f"Buckets: {payload['counts']}")
    ai_count = sum(1 for e in emails if e.get("needs_ai"))
    print(f"{ai_count} flagged for AI summary. Next: run the VS Code extension.")


if __name__ == "__main__":
    main()
