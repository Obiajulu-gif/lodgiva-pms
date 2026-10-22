"""The write guard a restricted subscription puts on this hotel.

Run with: bench --site <hotel site> run-tests --app kamra \
    --module kamra.tests.test_access_guard
"""

import unittest
from contextlib import contextmanager

import frappe

from kamra.access_guard import BLOCKED_ON_INSERT, enforce_access_mode


@contextmanager
def access_mode(mode):
    """Pretend the control plane wrote this mode into our site config."""
    previous = frappe.conf.get("lodgiva_access_mode")
    if mode is None:
        frappe.conf.pop("lodgiva_access_mode", None)
    else:
        frappe.conf["lodgiva_access_mode"] = mode
    try:
        yield
    finally:
        if previous is None:
            frappe.conf.pop("lodgiva_access_mode", None)
        else:
            frappe.conf["lodgiva_access_mode"] = previous


def stub(doctype, is_new=True):
    """A document-shaped object the guard can inspect without a database."""
    doc = frappe.new_doc(doctype) if frappe.db.exists("DocType", doctype) else None
    if doc is None:
        raise unittest.SkipTest(f"{doctype} is not installed on this site")
    if not is_new:
        doc.name = "EXISTING-1"
        doc.__islocal = False
    return doc


class TestAccessGuard(unittest.TestCase):
    def test_full_mode_permits_everything(self):
        with access_mode("full"):
            for doctype in BLOCKED_ON_INSERT:
                with self.subTest(doctype=doctype):
                    enforce_access_mode(stub(doctype))  # must not raise

    def test_absent_config_defaults_to_full(self):
        # A site the sweep has never reached is not a site that stopped paying.
        with access_mode(None):
            enforce_access_mode(stub("Reservation"))  # must not raise

    def test_read_only_blocks_a_new_reservation(self):
        with access_mode("read_only"):
            with self.assertRaises(frappe.ValidationError) as caught:
                enforce_access_mode(stub("Reservation"))
            self.assertIn("subscription", str(caught.exception).lower())

    def test_read_only_blocks_new_revenue_documents(self):
        with access_mode("read_only"):
            for doctype in BLOCKED_ON_INSERT:
                with self.subTest(doctype=doctype):
                    with self.assertRaises(frappe.ValidationError):
                        enforce_access_mode(stub(doctype))

    def test_read_only_permits_settling_a_folio(self):
        # Folio Payment is how an in-house guest checks out. Blocking it would
        # trap guests in a hotel that cannot take their money.
        with access_mode("read_only"):
            enforce_access_mode(stub("Folio Payment"))  # must not raise

    def test_read_only_permits_updating_an_existing_document(self):
        # Checking a guest out is an update, not an insert.
        with access_mode("read_only"):
            enforce_access_mode(stub("Reservation", is_new=False))  # must not raise

    def test_read_only_permits_housekeeping(self):
        with access_mode("read_only"):
            enforce_access_mode(stub("Housekeeping Task"))  # must not raise
