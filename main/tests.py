import json
import time
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.cache import cache
from django.test import Client, RequestFactory, SimpleTestCase, override_settings

from main.form_protection import (
    ALLOW,
    HONEYPOT_FIELD,
    JS_FIELD,
    MATH_ANSWER_FIELD,
    MATH_TOKEN_FIELD,
    MAX_SUBMIT_SECONDS,
    MIN_SUBMIT_SECONDS,
    REJECT,
    SILENT_DROP,
    TIME_FIELD,
    check_form_guard,
    check_message_content,
    check_rate_limit,
    issue_math_challenge,
    issue_time_token,
)
from main.views import contact


def _valid_fields():
    return {
        'full_name': 'Ada Lovelace',
        'email': 'ada@example.com',
        'phone': '+2348001234567',
        'subject': 'product_inquiry',
        'message': 'I need a quote for a residential system.',
    }


def _math_fields():
    token, question = issue_math_challenge()
    left, right = [int(part.strip()) for part in question.split('+')]
    return {
        MATH_TOKEN_FIELD: token,
        MATH_ANSWER_FIELD: str(left + right),
        JS_FIELD: '1',
    }


def _guarded(fields=None, age=None):
    data = {**_valid_fields(), **_math_fields()}
    if fields:
        data.update(fields)
    token = issue_time_token()
    data[TIME_FIELD] = token
    if age is None:
        age = MIN_SUBMIT_SECONDS + 1
    future = time.time() + age
    return data, future


class FormGuardTests(SimpleTestCase):
    def test_honeypot_filled_is_silent_drop(self):
        data, future = _guarded({HONEYPOT_FIELD: 'https://spam.example'})
        with patch('main.form_protection.time.time', return_value=future):
            decision, _ = check_form_guard(data)
        self.assertEqual(decision, SILENT_DROP)

    def test_too_fast_is_silent_drop(self):
        data = {**_valid_fields(), **_math_fields(), TIME_FIELD: issue_time_token()}
        decision, _ = check_form_guard(data)
        self.assertEqual(decision, SILENT_DROP)

    def test_missing_js_proof_is_silent_drop(self):
        data, future = _guarded({JS_FIELD: ''})
        with patch('main.form_protection.time.time', return_value=future):
            decision, _ = check_form_guard(data)
        self.assertEqual(decision, SILENT_DROP)

    def test_wrong_math_rejects(self):
        data, future = _guarded({MATH_ANSWER_FIELD: '999'})
        with patch('main.form_protection.time.time', return_value=future):
            decision, message = check_form_guard(data)
        self.assertEqual(decision, REJECT)
        self.assertIn('check', message.lower())

    def test_valid_after_min_delay_allows(self):
        data, future = _guarded()
        with patch('main.form_protection.time.time', return_value=future):
            decision, _ = check_form_guard(data)
        self.assertEqual(decision, ALLOW)

    def test_missing_token_rejects(self):
        decision, message = check_form_guard({})
        self.assertEqual(decision, REJECT)
        self.assertIn('refresh', message.lower())

    def test_tampered_token_rejects(self):
        decision, _ = check_form_guard({TIME_FIELD: 'not-a-real-token'})
        self.assertEqual(decision, REJECT)

    def test_expired_token_rejects(self):
        token = issue_time_token()
        future = time.time() + MAX_SUBMIT_SECONDS + 30
        with patch('django.core.signing.time.time', return_value=future):
            decision, _ = check_form_guard({TIME_FIELD: token})
        self.assertEqual(decision, REJECT)


class ContentFilterTests(SimpleTestCase):
    def test_url_in_message_is_silent_drop(self):
        decision, _ = check_message_content(
            'Ada', 'ada@example.com', '+2348001234567', 'product_inquiry',
            'Please visit https://spam.example/offer',
        )
        self.assertEqual(decision, SILENT_DROP)

    def test_cyrillic_is_silent_drop(self):
        decision, _ = check_message_content(
            'Иван', 'ada@example.com', '+2348001234567', 'other',
            'Здравствуйте, хотим предложить SEO',
        )
        self.assertEqual(decision, SILENT_DROP)

    def test_spam_phrase_is_silent_drop(self):
        decision, _ = check_message_content(
            'Mark', 'mark@example.com', '+2348001234567', 'other',
            'We can help with link building for your pages.',
        )
        self.assertEqual(decision, SILENT_DROP)

    def test_bad_subject_rejects(self):
        decision, _ = check_message_content(
            'Ada', 'ada@example.com', '+2348001234567', 'not-a-subject',
            'I need a quote for a residential system.',
        )
        self.assertEqual(decision, REJECT)

    def test_short_phone_rejects(self):
        decision, _ = check_message_content(
            'Ada', 'ada@example.com', '123', 'product_inquiry',
            'I need a quote for a residential system.',
        )
        self.assertEqual(decision, REJECT)

    def test_genuine_quote_allows(self):
        decision, _ = check_message_content(**{
            'full_name': 'Ada Lovelace',
            'email': 'ada@example.com',
            'phone': '+2348001234567',
            'subject': 'product_inquiry',
            'message': 'I need a quote for a residential system.',
        })
        self.assertEqual(decision, ALLOW)


class RateLimitTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_second_burst_is_blocked(self):
        self.assertTrue(check_rate_limit('1.2.3.4', 'a@example.com'))
        self.assertFalse(check_rate_limit('1.2.3.4', 'a@example.com'))

    def test_other_ip_is_independent(self):
        self.assertTrue(check_rate_limit('1.2.3.4', 'a@example.com'))
        self.assertTrue(check_rate_limit('9.9.9.9', 'b@example.com'))


def _attach_messages(request):
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class ContactViewGuardTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()

    def _ajax_post(self, data, ip='203.0.113.10'):
        request = self.factory.post(
            '/contact/',
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
            REMOTE_ADDR=ip,
        )
        return _attach_messages(request)

    def test_get_includes_protection_fields(self):
        request = _attach_messages(self.factory.get('/contact/'))
        response = contact(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="form_loaded"')
        self.assertContains(response, 'name="company_url"')
        self.assertContains(response, 'name="form_js"')
        self.assertContains(response, 'name="form_math"')
        self.assertContains(response, 'csrfmiddlewaretoken')

    @patch('main.views.EmailMessage')
    def test_honeypot_does_not_send_email(self, email_cls):
        data, future = _guarded({HONEYPOT_FIELD: 'http://bot.test'})
        with patch('main.form_protection.time.time', return_value=future):
            response = contact(self._ajax_post(data))
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload['ok'])
        email_cls.return_value.send.assert_not_called()

    @patch('main.views.EmailMessage')
    def test_instant_submit_does_not_send_email(self, email_cls):
        data = {**_valid_fields(), **_math_fields(), TIME_FIELD: issue_time_token()}
        response = contact(self._ajax_post(data))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['ok'])
        email_cls.return_value.send.assert_not_called()

    @patch('main.views.EmailMessage')
    def test_url_spam_does_not_send_email(self, email_cls):
        data, future = _guarded({
            'message': 'Great site, see https://cheap-backlinks.example',
        })
        with patch('main.form_protection.time.time', return_value=future):
            response = contact(self._ajax_post(data))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['ok'])
        email_cls.return_value.send.assert_not_called()

    @patch('main.views.EmailMessage')
    def test_valid_timed_submit_sends_email(self, email_cls):
        data, future = _guarded()
        with patch('main.form_protection.time.time', return_value=future):
            response = contact(self._ajax_post(data))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['ok'])
        self.assertEqual(email_cls.return_value.send.call_count, 2)


@override_settings(SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies')
class ContactCsrfTests(SimpleTestCase):
    def test_post_without_csrf_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post('/contact/', _valid_fields())
        self.assertEqual(response.status_code, 403)
