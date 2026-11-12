"""Razorpay Payment Links for folio settlement.

Lightweight by design: one REST call out, one webhook in. For multi-
gateway needs later, swap in the frappe/payments app — this module is
the only place that knows about Razorpay.
"""

import hashlib
import hmac
import importlib
import json

import frappe
from frappe.utils import escape_html, get_url

RAZORPAY_API = "https://api.razorpay.com/v1/payment_links"


def _settings(property: str):
	name = frappe.db.get_value(
		"Payment Gateway Settings", {"property": property, "enabled": 1})
	if not name:
		frappe.throw(
			"No payment gateway configured for this property. "
			"Add API keys under Payment Gateway Settings."
		)
	return frappe.get_doc("Payment Gateway Settings", name)


def _currency(property: str) -> tuple[str, str]:
	"""(code, symbol) from the property's localization pack - a link for a
	Lagos hotel is in naira because the pack says so, not because this
	module knows about Nigeria."""
	from kamra.localization import pack_for

	doc = frappe.get_cached_doc("Property", property)
	loc = pack_for(property).locale(doc)
	return loc.get("currency") or "INR", loc.get("currency_symbol") or ""


def _gateway_module(name: str):
	"""A gateway another app claims through the `kamra_payment_gateways`
	hook, the way country packs claim a country. None means the built-in
	frappe/payments route."""
	mapping = frappe.get_hooks("kamra_payment_gateways") or {}
	target = mapping.get(name)
	if not target:
		return None
	path = target[-1] if isinstance(target, (list, tuple)) else target
	return importlib.import_module(path)


def amount_due(folio) -> float:
	"""What a link for this folio should ask for.

	The posted balance when there is one. A booking made five minutes ago
	has no balance - room nights post at night audit - but the guest can
	still be asked to prepay, so it falls back to the stay total less
	whatever has already come in."""
	balance = float(folio.balance or 0)
	if balance > 0:
		return balance
	if not folio.reservation:
		return 0.0
	total, advance = frappe.db.get_value(
		"Reservation", folio.reservation,
		["amount_after_tax", "advance_paid"]) or (0, 0)
	paid = sum(float(row.amount or 0) for row in folio.payments)
	return max(0.0, float(total or 0) - max(float(advance or 0), paid))


def create_payment_link(folio_name: str) -> dict:
	folio = frappe.get_doc("Folio", folio_name)
	if folio.status == "Closed":
		frappe.throw("Folio is closed.")
	amount = amount_due(folio)
	if amount <= 0:
		frappe.throw("Nothing due on this folio.")
	settings = _settings(folio.property)
	guest = frappe.get_doc("Guest", folio.guest)
	currency, symbol = _currency(folio.property)

	if settings.test_mode:
		# A page on this site that plays the gateway's part, so the link
		# can be opened, paid and seen to land on the folio with no keys.
		link_id = f"plink_TEST{frappe.generate_hash(length=10)}"
		url = get_url("/api/method/kamra.payments.test_checkout") + f"?link={link_id}"
	else:
		gateway = _gateway_module(settings.gateway)
		if gateway:
			url, link_id = gateway.create_link(settings, folio, guest, amount, currency)
		else:
			from payments.utils import get_payment_gateway_controller

			controller = get_payment_gateway_controller(settings.gateway)
			url = controller.get_payment_url(**{
				"amount": amount,
				"currency": currency,
				"title": f"Stay bill {folio.name}",
				"description": f"{folio.guest_name} · {folio.reservation}",
				"reference_doctype": "Folio",
				"reference_docname": folio.name,
				"payer_name": guest.full_name,
				"payer_email": guest.email or "",
				"order_id": folio.name,
			})
			link_id = folio.name

	folio.db_set("payment_link_id", link_id, update_modified=False)
	folio.db_set("payment_link_url", url, update_modified=False)

	from kamra.savings import log_action
	log_action("send_payment_link", "Folio", folio.name, folio.property,
		minutes_saved=4,
		rationale=f"Payment link {symbol}{amount:,.0f} for {guest.full_name}",
		channel="API")
	return {"url": url, "link_id": link_id, "amount": amount,
		"currency": currency, "currency_symbol": symbol,
		"test_mode": bool(settings.test_mode)}


def post_link_payment(folio_name: str, amount: float, reference: str) -> bool:
	"""Record money that arrived through a link. One place for every
	gateway, so the rules cannot differ between them. False when this
	reference is already on the folio - gateways retry their webhooks."""
	folio = frappe.get_doc("Folio", folio_name)
	if amount <= 0 or any(row.reference == reference for row in folio.payments):
		return False
	from kamra.business_date import get_business_date
	from kamra.folio import _recalculate

	# Money against charges already posted settles them; money ahead of
	# the charges is an advance, and the folio should say so.
	kind = "Payment" if float(folio.balance or 0) >= amount - 0.01 else "Advance"
	folio.append("payments", {
		"posting_date": get_business_date(folio.property),
		"payment_kind": kind,
		"mode": "Payment Link",
		"amount": amount,
		"reference": reference,
	})
	_recalculate(folio)
	folio.save(ignore_permissions=True)

	from kamra.savings import log_action
	_, symbol = _currency(folio.property)
	log_action("payment_received", "Folio", folio.name, folio.property,
		minutes_saved=3,
		rationale=f"{symbol}{amount:,.0f} auto-posted from payment link",
		agent_name="Payments", channel="API")
	return True


def _test_folio(link: str | None):
	"""The folio a TEST link belongs to - only while its property is still
	in test mode, so the simulator cannot touch a live hotel's books."""
	if not link or not link.startswith("plink_TEST"):
		return None
	name = frappe.db.get_value("Folio", {"payment_link_id": link}, "name")
	if not name:
		return None
	folio = frappe.get_doc("Folio", name)
	return folio if _settings(folio.property).test_mode else None


@frappe.whitelist(allow_guest=True, methods=["GET"])
def test_checkout(link: str | None = None):
	"""Stand-in for the gateway's hosted page while a property is in test mode."""
	folio = _test_folio(link)
	if not folio:
		frappe.respond_as_web_page(
			"Link not found", "This test payment link is no longer valid.",
			http_status_code=404, indicator_color="red")
		return
	amount = amount_due(folio)
	_, symbol = _currency(folio.property)
	if amount <= 0:
		frappe.respond_as_web_page(
			"Nothing to pay", "This bill has already been settled. Thank you.",
			indicator_color="green")
		return
	frappe.respond_as_web_page(
		f"Pay {escape_html(folio.property)}",
		f"""<p>{escape_html(folio.guest_name or "Guest")} · {escape_html(folio.reservation or folio.name)}</p>
<p style="font-size:1.75rem;font-weight:600;margin:1rem 0">{symbol}{amount:,.2f}</p>
<p><a class="btn btn-primary btn-lg" href="/api/method/kamra.payments.test_pay?link={escape_html(link)}">Pay now</a></p>
<p class="text-muted" style="margin-top:1.5rem">Test mode - no real money moves.
Turn test mode off under Payment Gateway Settings to take live payments.</p>""",
		indicator_color="blue")


@frappe.whitelist(allow_guest=True, methods=["GET"])
def test_pay(link: str | None = None):
	"""Play the gateway's "paid" callback for a test link."""
	folio = _test_folio(link)
	if not folio:
		frappe.respond_as_web_page(
			"Link not found", "This test payment link is no longer valid.",
			http_status_code=404, indicator_color="red")
		return
	amount = amount_due(folio)
	_, symbol = _currency(folio.property)
	posted = post_link_payment(folio.name, amount, link)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- a guest-facing GET that must persist before the page renders
	frappe.respond_as_web_page(
		"Payment received" if posted else "Already paid",
		f"{symbol}{amount:,.2f} recorded against {escape_html(folio.reservation or folio.name)}. Thank you."
		if posted else "This link has already been paid. Thank you.",
		indicator_color="green")


@frappe.whitelist(allow_guest=True, methods=["POST"])
def razorpay_webhook():
	"""Razorpay calls this on payment_link.paid. Point the webhook at
	/api/method/kamra.payments.razorpay_webhook"""
	payload = frappe.request.get_data() or b"{}"
	event = json.loads(payload)

	entity = (event.get("payload", {}).get("payment_link", {})
	          .get("entity", {}))
	folio_name = (entity.get("notes") or {}).get("folio")
	if event.get("event") != "payment_link.paid" or not folio_name:
		return {"ignored": True}

	folio = frappe.get_doc("Folio", folio_name)
	settings = _settings(folio.property)

	# verify signature when a webhook secret is configured (skip in test mode)
	secret = settings.get_password("webhook_secret", raise_exception=False)
	if secret and not settings.test_mode:
		given = frappe.get_request_header("X-Razorpay-Signature") or ""
		expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
		if not hmac.compare_digest(given, expected):
			frappe.throw("Invalid webhook signature", frappe.PermissionError)

	amount = float(entity.get("amount_paid") or entity.get("amount") or 0) / 100
	posted = post_link_payment(folio.name, amount, entity.get("id"))
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- persists the completed operation before returning to an external/public caller; reviewed as intentional
	return {"ok": True, "folio": folio.name, "posted": posted}
