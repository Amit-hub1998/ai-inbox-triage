"""
Your personal triage rules. Edit these — they decide how mail gets bucketed
before the AI ever sees it. Keeping this as plain Python (not a settings UI yet)
so it is easy to read and change.
"""

# Senders whose mail is always treated as high priority (match is case-insensitive
# substring against the sender's name OR email address).
HIGH_PRIORITY_SENDERS = [
    "line.manager@hsbc.com",
    "risk-committee@hsbc.com",
    "model.governance@hsbc.com",
]

# Senders to push down to low priority / FYI.
LOW_PRIORITY_SENDERS = [
    "newsletter",
    "no-reply",
    "noreply",
    "do-not-reply",
]

# Project / keyword hints that bump priority when found in subject or body.
HIGH_PRIORITY_KEYWORDS = [
    "pd data asset",
    "brd sign-off",
    "validation evidence",
    "recalibration",
]

# Anything matching these goes to the "Automated" bucket (tickets, system mail).
# These are regular-expression patterns, matched against subject + sender.
AUTOMATED_PATTERNS = [
    r"\bW-\d+\b",          # W-44821 style ticket ids
    r"servicenow",
    r"\bINC\d+\b",         # incident numbers
    r"\bRITM\d+\b",        # ServiceNow request items
    r"automated",
    r"notification",
]

# Phrases that signal a deadline / urgency in the body.
DEADLINE_PHRASES = [
    "eod", "end of day", "by today", "by tomorrow", "asap",
    "overdue", "due date", "deadline", "by friday", "by monday",
    "by end of", "need it", "blocked until",
]

# How many of the top-priority emails to actually send to the AI for
# summarizing (keeps model calls small). Buckets are computed for ALL mail;
# only this many get an AI summary.
MAX_AI_SUMMARIES = 25

# How far back to pull mail, in days. None = all unread in inbox.
LOOKBACK_DAYS = 14
