"""One property check for every Kamra API call.

Hotel staff are scoped to properties with native Frappe User Permissions on
Property. frappe.get_list and the desk (lists, reports, exports, attached
files) already honour those. Kamra's own whitelisted methods mostly read
with frappe.get_all or SQL, which do not, so a receptionist at hotel A could
point `property=` (or a reservation/folio name) at hotel B.

Rather than add a check to ~300 handlers, this runs once per request as an
auth hook - after Frappe has resolved the user from the session cookie, API
key or OAuth token, before the method runs - and refuses the call if any
argument names a property, or a document of a property, outside the user's
permitted set. A user with no Property permissions is unrestricted (owner,
group finance across all hotels), the same rule assert_property_access uses.
"""

import frappe
from frappe import _

# argument name -> doctype whose `property` field decides access
DOC_ARGS = {
	"reservation": "Reservation",
	"folio": "Folio",
	"folio_name": "Folio",
	"order": "POS Order",
	"outlet": "POS Outlet",
	"room": "Room",
	"room_type": "Room Type",
	"task": "Housekeeping Task",
	"group_booking": "Group Booking",
	"function": "Venue Booking",
	"session": "Cashier Session",
}

GUARDED_PREFIXES = ("/api/method/kamra.", "/api/v2/method/kamra.",
                    "/api/method/lodgiva_nigeria.", "/api/v2/method/lodgiva_nigeria.")


def allowed_properties(user: str | None = None) -> set[str] | None:
	"""Property names the user is limited to, or None when unrestricted."""
	user = user or frappe.session.user
	if user in ("Administrator", "Guest"):
		return None
	from frappe.core.doctype.user_permission.user_permission import get_user_permissions
	rows = get_user_permissions(user).get("Property") or []
	return {r.get("doc") for r in rows} or None


def violation(args: dict, allowed: set[str]) -> str | None:
	"""The first argument that points outside `allowed`, as a message."""
	prop = args.get("property")
	if isinstance(prop, str) and prop and prop not in allowed:
		return prop
	for key, doctype in DOC_ARGS.items():
		value = args.get(key)
		if not isinstance(value, str) or not value:
			continue
		owner = frappe.db.get_value(doctype, value, "property")
		if owner and owner not in allowed:
			return owner
	return None


def enforce():
	request = getattr(frappe.local, "request", None)
	if not request or not request.path.startswith(GUARDED_PREFIXES):
		return
	allowed = allowed_properties()
	if allowed is None:
		return
	bad = violation(frappe.local.form_dict or {}, allowed)
	if bad:
		frappe.throw(_("You don't have access to {0}.").format(bad), frappe.PermissionError)
