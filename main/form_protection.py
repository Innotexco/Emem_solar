"""Spam guards for the public contact form.

Layers:
- honeypot
- signed time-trap
- JS interaction proof (empty in HTML; set only after a real input event)
- signed math challenge
- content / language / URL filters
- per-IP and per-email rate limits
"""

from __future__ import annotations

import logging
import random
import re
import time

from django.core import signing
from django.core.cache import cache

logger = logging.getLogger(__name__)

HONEYPOT_FIELD = 'company_url'
TIME_FIELD = 'form_loaded'
JS_FIELD = 'form_js'
MATH_TOKEN_FIELD = 'form_math_token'
MATH_ANSWER_FIELD = 'form_math'

_SALT = 'emem-contact-form-time-trap'
_MATH_SALT = 'emem-contact-form-math'

MIN_SUBMIT_SECONDS = 4
MAX_SUBMIT_SECONDS = 60 * 60 * 2

ALLOW = 'allow'
SILENT_DROP = 'silent_drop'
REJECT = 'reject'

ALLOWED_SUBJECTS = {
    'residential_quote',
    'commercial_quote',
    'technical_support',
    'find_distributor',
    'product_inquiry',
    'warranty',
    'other',
}

# Burst / hourly / daily caps. LocMem is per-process; still stops floods.
RATE_IP_BURST = (1, 25)
RATE_IP_HOUR = (5, 60 * 60)
RATE_EMAIL_DAY = (3, 60 * 60 * 24)

MIN_MESSAGE_CHARS = 15

_URL_RE = re.compile(
    r'(https?://|www\.|t\.me/|bit\.ly/|tinyurl\.|goo\.gl/'
    r'|\.ru\b|\.cn\b|\.xyz\b)',
    re.I,
)
_HTML_RE = re.compile(r'<a\s|\[url\s*=|href\s*=', re.I)
_CYRILLIC_RE = re.compile(r'[\u0400-\u04FF]')
_CJK_RE = re.compile(r'[\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]')
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]{2,}$')

_SPAM_PHRASES = (
    'backlink',
    'guest post',
    'link building',
    'link insertion',
    'seo service',
    'seo package',
    'rank your website',
    'rank your site',
    'increase your ranking',
    'website traffic',
    'buy followers',
    'crypto investment',
    'forex trading',
    'binary option',
    'casino bonus',
    'adult content',
    'onlyfans',
    'viagra',
    'cialis',
    'loan offer',
    'dear sir/madam',
    'dear sir or madam',
    'we can promote',
    'digital marketing agency',
)

_DISPOSABLE_DOMAINS = {
    'mailinator.com',
    'guerrillamail.com',
    'guerrillamail.net',
    'sharklasers.com',
    'grr.la',
    'yopmail.com',
    'tempmail.com',
    'temp-mail.org',
    '10minutemail.com',
    'trashmail.com',
    'discard.email',
    'getnada.com',
    'nada.ltd',
    'mailnesia.com',
    'moakt.com',
    'throwaway.email',
}


def issue_time_token() -> str:
    return signing.dumps({'issued': time.time()}, salt=_SALT)


def issue_math_challenge() -> tuple[str, str]:
    a = random.randint(3, 12)
    b = random.randint(3, 12)
    token = signing.dumps({'a': a, 'b': b}, salt=_MATH_SALT)
    return token, f'{a} + {b}'


def challenge_payload() -> dict:
    math_token, math_question = issue_math_challenge()
    return {
        TIME_FIELD: issue_time_token(),
        'math_token': math_token,
        'math_question': math_question,
    }


def client_ip(request) -> str:
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return (request.META.get('REMOTE_ADDR') or '').strip()


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


def _math_status(token: str, answer: str) -> str:
    if not token or not str(answer).strip():
        return 'missing'
    try:
        data = signing.loads(token, salt=_MATH_SALT, max_age=MAX_SUBMIT_SECONDS)
    except (signing.SignatureExpired, signing.BadSignature):
        return 'invalid'
    try:
        expected = int(data['a']) + int(data['b'])
        given = int(str(answer).strip())
    except (KeyError, TypeError, ValueError):
        return 'wrong'
    return 'ok' if given == expected else 'wrong'


def _rate_hit(key: str, limit: int, ttl: int) -> bool:
    """Return True if this hit exceeds the limit."""
    added = cache.add(key, 1, ttl)
    if added:
        return False
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, ttl)
        return False
    return count > limit


def check_rate_limit(ip: str, email: str) -> bool:
    """Return True when the request is within limits."""
    ip = ip or 'unknown'
    email = (email or '').strip().lower() or 'unknown'
    checks = [
        (f'contact:ip-burst:{ip}', *RATE_IP_BURST),
        (f'contact:ip-hour:{ip}', *RATE_IP_HOUR),
        (f'contact:email-day:{email}', *RATE_EMAIL_DAY),
    ]
    return not any(_rate_hit(key, limit, ttl) for key, limit, ttl in checks)


def check_message_content(full_name, email, phone, subject, message) -> tuple[str, str]:
    """Return (decision, user-facing message) for field contents."""
    subject = (subject or '').strip()
    if subject not in ALLOWED_SUBJECTS:
        return REJECT, 'Please select a valid subject.'

    email = (email or '').strip()
    if not _EMAIL_RE.match(email):
        return REJECT, 'Please enter a valid email address.'
    domain = email.rsplit('@', 1)[-1].lower()
    if domain in _DISPOSABLE_DOMAINS:
        return SILENT_DROP, ''

    digits = re.sub(r'\D', '', phone or '')
    if len(digits) < 8 or len(digits) > 16:
        return REJECT, 'Please enter a valid phone number.'

    text = (message or '').strip()
    if len(text) < MIN_MESSAGE_CHARS:
        return REJECT, 'Please add a bit more detail so we can help.'

    blob = ' '.join([full_name or '', email, phone or '', text])
    if _URL_RE.search(blob) or _HTML_RE.search(blob):
        return SILENT_DROP, ''
    if _CYRILLIC_RE.search(blob) or _CJK_RE.search(blob):
        return SILENT_DROP, ''

    low = blob.lower()
    if any(phrase in low for phrase in _SPAM_PHRASES):
        return SILENT_DROP, ''

    return ALLOW, ''


def check_form_guard(post, request=None) -> tuple[str, str]:
    """Return (decision, user-facing message).

    Honeypot hits, missing JS proof, and instant submits look like
    success so bots do not keep retrying.
    """
    honeypot = (post.get(HONEYPOT_FIELD) or '').strip()
    if honeypot:
        logger.warning('contact drop honeypot ip=%s', _safe_ip(request))
        return SILENT_DROP, ''

    status = _time_token_status((post.get(TIME_FIELD) or '').strip())
    if status == 'too_fast':
        logger.warning('contact drop too_fast ip=%s', _safe_ip(request))
        return SILENT_DROP, ''
    if status in {'missing', 'expired', 'invalid'}:
        return REJECT, 'Please refresh the page and try again.'

    if (post.get(JS_FIELD) or '').strip() != '1':
        logger.warning('contact drop no_js ip=%s', _safe_ip(request))
        return SILENT_DROP, ''

    math_status = _math_status(
        (post.get(MATH_TOKEN_FIELD) or '').strip(),
        post.get(MATH_ANSWER_FIELD) or '',
    )
    if math_status != 'ok':
        return REJECT, 'Please answer the quick check question.'

    if request is not None:
        email = (post.get('email') or '').strip()
        if not check_rate_limit(client_ip(request), email):
            logger.warning('contact drop rate_limit ip=%s', _safe_ip(request))
            return REJECT, 'Too many attempts. Please wait a few minutes and try again.'

    return ALLOW, ''


def _safe_ip(request) -> str:
    if request is None:
        return '-'
    return client_ip(request) or '-'
