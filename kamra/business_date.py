"""Front-office business date.

Opera advances the business date only after night audit, so a 01:00 charge
still posts to yesterday until the audit rolls the day. Every money and
revenue posting should use get_business_date(property), not nowdate()."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from frappe.utils import add_days, nowdate

import frappe


def get_business_date(property: str) -> str:
	"""Current business date for a property; falls back to calendar today."""
	if not property:
		return nowdate()
	bd = frappe.db.get_value("Property", property, "business_date")
	return str(bd) if bd else nowdate()


def ensure_business_date(property: str) -> str:
	"""Seed business_date if blank, then return it."""
	bd = frappe.db.get_value("Property", property, "business_date")
	if not bd:
		bd = nowdate()
		frappe.db.set_value("Property", property, "business_date", bd,
		                    update_modified=False)
	return str(bd)


def property_today(property: str | None = None) -> str:
	"""Calendar date in the hotel's OWN timezone.

	Not nowdate(): that answers in the site's timezone, and a hotel in
	Lagos on a site set to Asia/Kolkata would roll its day five and a half
	hours early - closing the books while the restaurant is still open.
	"""
	tz_name = None
	if property:
		tz_name = frappe.db.get_value("Property", property, "timezone")
	tz_name = tz_name or frappe.db.get_single_value(
		"System Settings", "time_zone")
	try:
		return datetime.now(ZoneInfo(tz_name)).date().isoformat()
	except Exception:
		# An unknown or blank zone must not stop the audit.
		return nowdate()


def advance_business_date(property: str, from_date: str | None = None) -> str:
	"""Roll the business date forward by one day after a successful night audit."""
	current = from_date or get_business_date(property)
	nxt = add_days(current, 1)
	frappe.db.set_value("Property", property, "business_date", nxt,
	                    update_modified=False)
	return str(nxt)
