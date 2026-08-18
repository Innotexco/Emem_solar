"""Honeypot + signed time-trap helpers for public contact forms."""

from __future__ import annotations

import time

from django.core import signing

HONEYPOT_FIELD = 'company_url'
TIME_FIELD = 'form_loaded'
_SALT = 'emem-contact-form-time-trap'

# Humans need a few seconds; bots typically POST immediately.
MIN_SUBMIT_SECONDS = 3
# Allow a tab to sit open, but expire stale tokens.
MAX_SUBMIT_SECONDS = 60 * 60 * 2

ALLOW = 'allow'
SILENT_DROP = 'silent_drop'
REJECT = 'reject'


def issue_time_token() -> str:
    return signing.dumps({'issued': time.time()}, salt=_SALT)


def _time_token_status(token: str) -> str:
    if not token:
        return 'missing'
    try:
        data = signing.loads(token, salt=_SALT, max_age=MAX_SUBMIT_SECONDS)
    except signing.SignatureExpired:
        return 'expired'
    except signing.BadSignature:
        return 'invalid'

    try:
        issued = float(data.get('issued', 0))
    except (TypeError, ValueError):
        return 'invalid'

    if time.time() - issued < MIN_SUBMIT_SECONDS:
        return 'too_fast'
    return 'ok'


def check_form_guard(post) -> tuple[str, str]:
    """Return (decision, user-facing message).

    Honeypot hits and instant submits look like success to the client
    so bots do not keep retrying.
    """
    honeypot = (post.get(HONEYPOT_FIELD) or '').strip()
    if honeypot:
        return SILENT_DROP, ''

    status = _time_token_status((post.get(TIME_FIELD) or '').strip())
    if status == 'too_fast':
        return SILENT_DROP, ''
    if status in {'missing', 'expired', 'invalid'}:
        return REJECT, 'Please refresh the page and try again.'
    return ALLOW, ''
