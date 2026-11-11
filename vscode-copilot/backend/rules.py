"""
Offline, deterministic bucketing. No AI here — just your config rules.
Takes a list of raw email dicts and tags each with a bucket + a flag for
whether it needs an AI summary.

Buckets: need | urgent | overdue | fyi | auto
"""
import re
from datetime import datetime, timezone

import config


def _text(email):
    return f"{email.get('from','')} {email.get('subject','')} {email.get('body','')}".lower()


def _matches_any(patterns, text):
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _is_automated(email):
    hay = f"{email.get('subject','')} {email.get('from','')}"
    return _matches_any(config.AUTOMATED_PATTERNS, hay)


def _sender_hit(email, senders):
    sender = f"{email.get('from','')} {email.get('from_email','')}".lower()
    return any(s.lower() in sender for s in senders)


def _has_deadline(email):
    text = _text(email)
    return any(phrase in text for phrase in config.DEADLINE_PHRASES)


def _keyword_hit(email):
    text = _text(email)
    return any(k.lower() in text for k in config.HIGH_PRIORITY_KEYWORDS)


def _looks_like_question(email):
    subj_body = f"{email.get('subject','')} {email.get('body','')}".lower()
    return "?" in subj_body or "please" in subj_body or "can you" in subj_body


def bucket_email(email):
    """Return the bucket string for a single email."""
    # 1. Automated/tickets first — these should never pollute real priorities.
    if _is_automated(email):
        return "auto"

    # 2. Low-priority senders go straight to FYI.
    if _sender_hit(email, config.LOW_PRIORITY_SENDERS):
        return "fyi"

    high_sender = _sender_hit(email, config.HIGH_PRIORITY_SENDERS)
    high_kw = _keyword_hit(email)
    deadline = _has_deadline(email)

    # 3. Overdue beats urgent beats need.
    if deadline and ("overdue" in _text(email) or "past due" in _text(email)):
        return "overdue"
    if deadline and (high_sender or high_kw):
        return "urgent"
    if high_sender or high_kw or _looks_like_question(email):
        return "need"

    # 4. Everything else is FYI.
    return "fyi"


def enrich_with_buckets(emails):
    """
    Tag every email with its bucket, then mark the top emails (by priority
    weight) that should get an AI summary.
    """
    weight = {"overdue": 0, "urgent": 1, "need": 2, "fyi": 3, "auto": 4}

    for e in emails:
        e["bucket"] = bucket_email(e)
        e["needs_ai"] = False

    # Pick emails for AI summarizing, best priority first, but never automated
    # mail and only spend on FYI if there's budget left after the real buckets.
    ranked = sorted(emails, key=lambda e: weight.get(e["bucket"], 9))
    budget = config.MAX_AI_SUMMARIES
    # First pass: action buckets (overdue/urgent/need).
    for e in ranked:
        if budget <= 0:
            break
        if e["bucket"] in ("overdue", "urgent", "need"):
            e["needs_ai"] = True
            budget -= 1
    # Second pass: FYI gets summaries only with leftover budget.
    for e in ranked:
        if budget <= 0:
            break
        if e["bucket"] == "fyi" and not e["needs_ai"]:
            e["needs_ai"] = True
            budget -= 1

    return emails


def bucket_counts(emails):
    counts = {"need": 0, "urgent": 0, "overdue": 0, "fyi": 0, "auto": 0}
    for e in emails:
        counts[e.get("bucket", "fyi")] = counts.get(e.get("bucket", "fyi"), 0) + 1
    return counts
