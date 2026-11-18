"""The per-request property check (kamra.property_guard).

Run with: bench --site <hotel site> run-tests --app kamra \
    --module kamra.tests.test_property_guard
"""

import unittest
from unittest.mock import patch

from kamra.property_guard import DOC_ARGS, violation

ALLOWED = {"Hotel A"}
OWNERS = {("Reservation", "RES-A"): "Hotel A", ("Reservation", "RES-B"): "Hotel B",
          ("Folio", "FOL-B"): "Hotel B", ("POS Order", "ORD-B"): "Hotel B"}


def fake_get_value(doctype, name, field):
	assert field == "property"
	return OWNERS.get((doctype, name))


class TestPropertyGuard(unittest.TestCase):
	def check(self, **args):
		with patch("frappe.db.get_value", side_effect=fake_get_value):
			return violation(args, ALLOWED)

	def test_own_property_passes(self):
		self.assertIsNone(self.check(property="Hotel A", reservation="RES-A"))

	def test_other_property_argument_refused(self):
		self.assertEqual(self.check(property="Hotel B"), "Hotel B")

	def test_document_of_other_property_refused(self):
		self.assertEqual(self.check(reservation="RES-B"), "Hotel B")
		self.assertEqual(self.check(folio="FOL-B"), "Hotel B")
		self.assertEqual(self.check(order="ORD-B"), "Hotel B")

	def test_own_property_cannot_smuggle_other_document(self):
		self.assertEqual(self.check(property="Hotel A", folio="FOL-B"), "Hotel B")

	def test_unknown_document_left_to_handler(self):
		self.assertIsNone(self.check(reservation="NOPE"))

	def test_non_string_arguments_ignored(self):
		self.assertIsNone(self.check(property=None, reservation=["RES-B"]))

	def test_every_mapped_doctype_has_property(self):
		import frappe
		for doctype in set(DOC_ARGS.values()):
			self.assertTrue(frappe.get_meta(doctype).has_field("property"), doctype)
