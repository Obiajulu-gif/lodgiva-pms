"""WhatsApp: staging recipient allowlist, webhook signature, receipt ordering.

Run with: bench --site <hotel site> run-tests --app kamra \
    --module kamra.tests.test_whatsapp_guards
"""

import hashlib
import hmac
import unittest
from unittest.mock import MagicMock, patch

import frappe

from kamra import whatsapp as wa


class TestRecipientGuard(unittest.TestCase):
	def blocked(self, allow, to):
		with patch.dict(frappe.local.conf, {"lodgiva_whatsapp_test_recipients": allow}):
			return wa._blocked_recipient(to)

	def test_no_allowlist_sends_to_anyone(self):
		with patch.dict(frappe.local.conf, {}, clear=False):
			frappe.local.conf.pop("lodgiva_whatsapp_test_recipients", None)
			self.assertIsNone(wa._blocked_recipient("+2348030000001"))

	def test_allowlisted_number_in_any_format(self):
		self.assertIsNone(self.blocked("+234 803 000 0009", "2348030000009"))

	def test_everyone_else_is_blocked_and_meta_never_called(self):
		self.assertTrue(self.blocked(["+2348030000009"], "+2348039999999"))
		with patch.dict(frappe.local.conf, {"lodgiva_whatsapp_test_recipients": "+2348030000009"}), \
				patch.object(wa, "_post_graph") as graph:
			ok, _ = wa._send(MagicMock(), "+2348039999999", {})
			self.assertFalse(ok)
			graph.assert_not_called()


class TestSignature(unittest.TestCase):
	def conn(self, secret):
		c = MagicMock()
		c.meta.has_field.return_value = True
		c.get_password.return_value = secret
		return c

	def test_valid_and_forged(self):
		body = b'{"entry": []}'
		good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
		self.assertTrue(wa.signature_ok(self.conn("s3cret"), body, good))
		self.assertFalse(wa.signature_ok(self.conn("s3cret"), body, "sha256=" + "0" * 64))
		self.assertFalse(wa.signature_ok(self.conn("s3cret"), body + b" ", good))

	def test_connection_without_secret_is_trusted(self):
		self.assertTrue(wa.signature_ok(self.conn(None), b"{}", ""))


class TestReceiptOrder(unittest.TestCase):
	def test_read_never_goes_back_to_delivered(self):
		self.assertLess(wa.STATUS_RANK["Delivered"], wa.STATUS_RANK["Read"])
		row = frappe._dict(name="WAM-1", status="Read")
		with patch("frappe.db.get_value", return_value=row), patch("frappe.db.set_value") as setv:
			wa._apply_status({"id": "wamid.1", "status": "delivered"})
			setv.assert_not_called()
			wa._apply_status({"id": "wamid.1", "status": "failed", "errors": [{"title": "Undeliverable"}]})
			setv.assert_called_once()
