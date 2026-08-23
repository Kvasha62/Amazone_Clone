# ────────────────────────────────────────────────────────────────────────
# apps/payments/tests/test_webhook_security.py — HMAC-SHA256 webhook auth.
#
# ПРОВЕРЯЕТ:
#   1. Valid signature → webhook accepted
#   2. Missing signature → rejected (403)
#   3. Invalid signature → rejected (403)
#   4. Signature from another payload → rejected (403)
#   5. Modified request body → rejected (403)
#   6. Valid signature + succeeded → payment flow works
#   7. Unsigned succeeded → payment NOT transitioned
#   8. Wrong secret → rejected (403)
# ────────────────────────────────────────────────────────────────────────

import hashlib
import hmac
import json

from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from apps.orders.tests.factories import create_test_order, create_test_user
from apps.payments.models import Payment
from apps.payments.tests.factories import create_test_payment


WEBHOOK_SECRET = 'test-webhook-secret-key-32bytes!!'


def _sign_body(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    """Compute HMAC-SHA256 signature for a raw request body."""
    return hmac.new(
        secret.encode('utf-8'),
        body,
        hashlib.sha256,
    ).hexdigest()


def _json_bytes(data: dict) -> bytes:
    """Serialize data to JSON bytes (deterministic)."""
    return json.dumps(data).encode('utf-8')


class WebhookHMACSignatureTests(TestCase):
    """HMAC-SHA256 signature verification for payment webhooks."""

    def setUp(self):
        self.user = create_test_user()
        self.order = create_test_order(self.user)
        self.payment = create_test_payment(
            self.order, self.user, status='processing',
        )
        self.client = APIClient()
        self.url = reverse('payments:payment-webhook')

    def _webhook_data(self, **overrides):
        """Build default webhook payload."""
        data = {
            'external_id': self.payment.external_id,
            'event_type': 'payment.succeeded',
            'status': 'succeeded',
        }
        data.update(overrides)
        return data

    def _post_signed(self, data, secret=WEBHOOK_SECRET):
        """POST webhook with correct HMAC signature over JSON body."""
        body = _json_bytes(data)
        sig = _sign_body(body, secret)
        return self.client.post(
            self.url,
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )

    # ── 1. Valid signature → accepted ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_valid_signature_accepted(self):
        """Valid HMAC-SHA256 signature → webhook accepted (200)."""
        data = self._webhook_data()
        resp = self._post_signed(data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ── 2. Missing signature → rejected ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_missing_signature_rejected(self):
        """Missing X-Webhook-Signature → 403."""
        data = self._webhook_data()
        resp = self.client.post(
            self.url,
            data=_json_bytes(data),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── 3. Invalid signature → rejected ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_invalid_signature_rejected(self):
        """Invalid HMAC signature → 403."""
        data = self._webhook_data()
        resp = self.client.post(
            self.url,
            data=_json_bytes(data),
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE='invalid_signature_value',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── 4. Signature from another payload → rejected ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_signature_from_another_payload_rejected(self):
        """Signature computed from different payload → 403."""
        other_body = _json_bytes({'foo': 'bar'})
        wrong_sig = _sign_body(other_body)
        data = self._webhook_data()
        resp = self.client.post(
            self.url,
            data=_json_bytes(data),
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=wrong_sig,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── 5. Modified request body → rejected ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_modified_body_rejected(self):
        """Valid signature for original body, but body changed → 403."""
        data = self._webhook_data()
        sig = _sign_body(_json_bytes(data))
        modified_data = data.copy()
        modified_data['status'] = 'failed'
        resp = self.client.post(
            self.url,
            data=_json_bytes(modified_data),
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── 6. Valid signature + succeeded → payment flow works ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_valid_signature_succeeded_transitions_payment(self):
        """Valid signature + status=succeeded → payment becomes SUCCEEDED."""
        data = self._webhook_data(status='succeeded')
        resp = self._post_signed(data)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['status'], 'succeeded')
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'succeeded')

    # ── 7. Unsigned succeeded → payment NOT transitioned ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_unsigned_succeeded_does_not_transition_payment(self):
        """Unsigned webhook with status=succeeded → payment stays PROCESSING."""
        data = self._webhook_data(status='succeeded')
        resp = self.client.post(
            self.url,
            data=_json_bytes(data),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'processing')

    # ── 8. Wrong secret → rejected ──

    @override_settings(PAYMENT_WEBHOOK_SECRET=WEBHOOK_SECRET)
    def test_wrong_secret_rejected(self):
        """Signature computed with wrong secret → 403."""
        data = self._webhook_data()
        body = _json_bytes(data)
        wrong_sig = _sign_body(body, 'wrong-secret-key!!!!!!!!!!!')
        resp = self.client.post(
            self.url,
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=wrong_sig,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ── No secret configured → rejected ──

    @override_settings(PAYMENT_WEBHOOK_SECRET='')
    def test_no_secret_configured_rejected(self):
        """No PAYMENT_WEBHOOK_SECRET → all webhooks rejected (403)."""
        data = self._webhook_data()
        body = _json_bytes(data)
        sig = _sign_body(body, 'some-secret')
        resp = self.client.post(
            self.url,
            data=body,
            content_type='application/json',
            HTTP_X_WEBHOOK_SIGNATURE=sig,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
