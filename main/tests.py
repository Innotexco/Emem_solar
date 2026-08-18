import json
import time
from unittest.mock import patch

from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import Client, RequestFactory, SimpleTestCase, override_settings

from main.form_protection import (
    ALLOW,
    HONEYPOT_FIELD,
    MAX_SUBMIT_SECONDS,
    MIN_SUBMIT_SECONDS,
    REJECT,
    SILENT_DROP,
    TIME_FIELD,
    check_form_guard,
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


class FormGuardTests(SimpleTestCase):
    def test_honeypot_filled_is_silent_drop(self):
        token = issue_time_token()
        future = time.time() + MIN_SUBMIT_SECONDS + 1
        with patch('main.form_protection.time.time', return_value=future):
            decision, _ = check_form_guard({
                HONEYPOT_FIELD: 'https://spam.example',
                TIME_FIELD: token,
            })
        self.assertEqual(decision, SILENT_DROP)

    def test_too_fast_is_silent_drop(self):
        decision, _ = check_form_guard({TIME_FIELD: issue_time_token()})
        self.assertEqual(decision, SILENT_DROP)

    def test_valid_after_min_delay_allows(self):
        token = issue_time_token()
        future = time.time() + MIN_SUBMIT_SECONDS + 0.2
        with patch('main.form_protection.time.time', return_value=future):
            decision, _ = check_form_guard({TIME_FIELD: token})
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


def _attach_messages(request):
    request.session = {}
    request._messages = FallbackStorage(request)
    return request


class ContactViewGuardTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _ajax_post(self, data):
        request = self.factory.post(
            '/contact/',
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        return _attach_messages(request)

    def test_get_includes_time_token(self):
        request = _attach_messages(self.factory.get('/contact/'))
        response = contact(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="form_loaded"')
        self.assertContains(response, 'name="company_url"')
        self.assertContains(response, 'csrfmiddlewaretoken')

    @patch('main.views.EmailMessage')
    def test_honeypot_does_not_send_email(self, email_cls):
        token = issue_time_token()
        future = time.time() + MIN_SUBMIT_SECONDS + 1
        data = {**_valid_fields(), TIME_FIELD: token, HONEYPOT_FIELD: 'http://bot.test'}
        with patch('main.form_protection.time.time', return_value=future):
            response = contact(self._ajax_post(data))
        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload['ok'])
        email_cls.return_value.send.assert_not_called()

    @patch('main.views.EmailMessage')
    def test_instant_submit_does_not_send_email(self, email_cls):
        data = {**_valid_fields(), TIME_FIELD: issue_time_token()}
        response = contact(self._ajax_post(data))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content)['ok'])
        email_cls.return_value.send.assert_not_called()

    @patch('main.views.EmailMessage')
    def test_valid_timed_submit_sends_email(self, email_cls):
        token = issue_time_token()
        future = time.time() + MIN_SUBMIT_SECONDS + 1
        data = {**_valid_fields(), TIME_FIELD: token}
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
