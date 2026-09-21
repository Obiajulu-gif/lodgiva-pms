<p align="center">
  <img src="kamra/public/lodgiva-mark.svg" width="96" alt="Lodgiva" />
</p>

<h1 align="center">Lodgiva PMS</h1>

<p align="center">
  <b>Hotel management for Nigerian hotels</b> — front desk, tape chart, booking engine,<br/>
  VAT invoices in naira, cashiering, housekeeping and POS.
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue?style=flat-square" alt="AGPL-3.0" /></a>
  <img src="https://img.shields.io/badge/Frappe-v16-0089ff?style=flat-square" alt="Frappe v16" />
  <img src="https://img.shields.io/badge/based%20on-Kamra%20v2.6.2-0f766e?style=flat-square" alt="Based on Kamra v2.6.2" />
</p>

## About this fork

Lodgiva PMS is a **branded fork of [Kamra PMS](https://github.com/Kamra-PMS/kamra-pms)**
v2.6.2, part of [Lodgiva](https://github.com/Obiajulu-gif/lodgiva). It is
installed together with
[`lodgiva-nigeria`](https://github.com/Obiajulu-gif/lodgiva-nigeria), which
holds everything Nigerian. This fork stays deliberately close to upstream so
Kamra's releases can be merged, not rewritten.

**What this fork changes:**

- **Name and look.** Lodgiva's name and logo throughout the interface, and
  the app served at `/lodgiva` instead of `/kamra`. Every old `/kamra` link
  redirects, so bookmarks and emailed check-in links keep working.
- **Assumptions that were India-only.** Invoice wording, rupee icons, the
  guest-journey currency, and nationality/ID defaults now follow the
  property's country pack instead of assuming India.
- **Bugs found while testing.**
  - A first login on a new browser rendered screens before the hotel was
    known, so every page asked for Kamra's own demo hotel. The tape chart
    and settings crashed.
  - Public pages called a staff-only endpoint.
  - Desk actions were credited to "None".

**What it keeps:** the Python app is still named `kamra`, and so are its API
paths (`kamra.api.*`). Those are the contract that upstream updates and
integrations depend on. The AGPL licence and Kamra's copyright notices are
unchanged.

### Install

With the Lodgiva installer, on any Ubuntu server (recommended):
[`deploy/README.md`](https://github.com/Obiajulu-gif/lodgiva/blob/main/deploy/README.md).

Or into an existing Frappe v16 bench:

```bash
bench get-app payments
bench get-app https://github.com/Obiajulu-gif/lodgiva-pms --branch main
bench get-app https://github.com/Obiajulu-gif/lodgiva-nigeria --branch main
bench --site <site> install-app payments kamra lodgiva_nigeria
```

### Pulling upstream Kamra

```bash
git remote add upstream https://github.com/Kamra-PMS/kamra-pms   # once
git fetch upstream --tags
git merge v2.6.3                      # a tagged release, never develop
```

### Source and licence

Lodgiva PMS is AGPL-3.0, like Kamra. If you serve a modified version over a
network, you must offer its users the corresponding source. That's why this
repository is public, and why the booking page links to it.

---

## Upstream: Kamra PMS

> Everything below is **Kamra's own README**, kept unchanged. It describes
> Kamra: its features, demo, docs and roadmap. Links to kamrapms.com and
> demo.kamrapms.com go to Kamra, not to Lodgiva.

<p align="center">
  <a href="https://demo.kamrapms.com"><b>▶ Live demo</b></a> ·
  <a href="https://kamrapms.com/docs/"><b>Docs</b></a> ·
  <a href="#install"><b>Install</b></a> ·
  <a href="https://kamrapms.com/docs/ai-and-mcp"><b>AI / MCP</b></a> ·
  <a href="mailto:hello@kamrapms.com"><b>Contact</b></a>
</p>

> **Try it in 30 seconds → [demo.kamrapms.com](https://demo.kamrapms.com)**  
> Tap any role to sign in (credentials are on the page). Guest booking: [/book](https://demo.kamrapms.com/book) · Housekeeping app: [/kamra/hk](https://demo.kamrapms.com/kamra/hk)

**Kamra** is a full **property management system (PMS)** for hotels, resorts, and **short-term rentals / villas**. It runs on **Frappe** (the framework behind ERPNext), is **AGPL-3.0**, and is built so humans *and* AI agents share the same governed APIs — booking, check-in, folios, night audit, pricing — with deterministic money (never from an LLM).

---

## Contents

- [What's new](#whats-new)
- [Why Kamra](#why-kamra)
- [What makes it different](#what-makes-it-different)
- [Screenshots](#screenshots)
- [Short-term rentals](#short-term-rentals)
- [Features](#features)
- [Documentation & API](#documentation--api)
- [Install](#install)
- [Quickstart (development)](#quickstart-development)
- [Who it's for](#who-its-for)
- [License & contributors](#license--contributors)

---

## What's new

On **`develop`** (nightly) the product is the **2.6.2** train plus Unreleased
work. The `v2.6.2` GitHub tag is still pending — latest published release is
[v2.6.0](https://github.com/Kamra-PMS/kamra-pms/releases/tag/v2.6.0).

- **Unreleased** — System Health, property time zone, **85 MCP tools** (role +
  module gated), AI provider presets, WordPress-easy `deploy/install.sh`,
  banquet Phase 1 (send quote, guest response, Sales/Finance/HK/F&B checklists)
- **2.6.2** (in the changelog; not tagged yet) — Opera-style cashier till,
  folio ledger, cashier PIN, POS full-screen till

Notes live in [`CHANGELOG.md`](CHANGELOG.md) — this list is a pointer, not a
second release note. How we cut stables: [`RELEASING.md`](RELEASING.md).

---

## Why Kamra

Most hotel PMS software was built twenty years ago: per-room SaaS rent, locked-in data, bolt-on chatbots, and screens that need a week of training.

Kamra is the alternative we wanted:

| Pain with legacy PMS | With Kamra |
|---|---|
| Per-room / per-module pricing | **Free forever** (AGPL) — cost doesn't scale with rooms |
| Data lock-in | **You host it** — on-prem, VPS, or Frappe Cloud |
| AI as a marketing slide | **MCP tools** — Claude (or any agent) books and audits with RBAC |
| Opaque pricing & tax | **Deterministic engine** — GST / SST / VAT packs in code + CI evals |
| New-hire training hell | Front desk UI a clerk can learn the same day |

---

## What makes it different

- **Agent-ready, not agent-locked.** [MCP server](https://kamrapms.com/docs/ai-and-mcp) with **85** governed tools — role-scoped, module-gated, permission-checked, fully logged. Connect Claude; no bundled agent to trust.
- **Bring your own key.** No AI markup or model lock-in. Optional [HeyKoala](https://heykoala.ai) for voice / WhatsApp concierge.
- **Deterministic money.** Rates, tax slabs, availability, and no-overbooking guards come from code — never from a language model.
- **Full audit trail.** Every human or AI action: who, what, why.
- **Built on Frappe.** RBAC, multi-tenancy, Desk escape hatch, [frappe/payments](https://github.com/frappe/payments) gateways, ERPNext-adjacent ecosystem.

---

## Screenshots

*From the [live demo](https://demo.kamrapms.com) — open it and click around.*

| | |
|---|---|
| ![Today — front desk morning view](docs/screenshots/today.png) | ![Reservation 360](docs/screenshots/reservation-360.png) |
| **Today** — arrivals, departures, in-house, paid/due chips, room board | **Reservation 360** — billing, amend dates, check-in / out / cancel |
| ![Tape chart](docs/screenshots/tape-chart.png) | ![Reports](docs/screenshots/reports.png) |
| **Tape chart** — rooms × dates, moves & stay amendments | **Reports** — occupancy, ADR, RevPAR, flash |
| ![New booking](docs/screenshots/booking-dialog.png) | ![Guest profile](docs/screenshots/guest-profile.png) |
| **New booking** — live quote, multi-room, add-ons, cancellation policy | **Guest profile** — stay strip, merge & anonymize (DPDP) |
| ![GST invoice](docs/screenshots/invoice.png) | ![Booking Engine](docs/screenshots/booking-engine.png) |
| **Folio & tax invoice** — per-line GST, splits, payment links | **Booking engine console** — gallery, policies, FAQ, SEO |
| ![Restaurant POS](docs/screenshots/pos.png) | ![Dashboard](docs/screenshots/dashboard.png) |
| **Restaurant POS** — table map, KOT / bill print, F-keys | **Dashboard** — occupancy, revenue, chain roll-up |
| ![Laundry](docs/screenshots/laundry.png) | ![Self check-in](docs/screenshots/checkin-id.png) |
| **Laundry** — pickup → return → folio; guest self-service | **Self check-in** — ID capture, e-sign, retention policy |

**Guest-facing booking page** — date range, **Check availability**, rates, gallery, policies, pay-at-hotel:

[![Public booking page](docs/screenshots/public-booking.png)](https://demo.kamrapms.com/book)

---

## Short-term rentals

Same PMS for **villas and multi-site STR portfolios**: sellable units (room / whole-place / package), competition groups, cleaning fees & deposits, Instant or Request-to-book, and a catalog that feels like a listing site.

| | |
|---|---|
| ![STR catalog](docs/screenshots/str-catalog.png) | ![STR villas](docs/screenshots/str-villas.png) |
| **Catalog** — check-in / out + Check availability | **Places to stay** — per-villa cards & from-rates |

[![Villa listing](docs/screenshots/str-listing.png)](https://demo.kamrapms.com/book)

Live example: [demo.kamrapms.com/book](https://demo.kamrapms.com/book).

---

## Features

| Area | What you get |
|---|---|
| **Front desk** | Today board, check-in flow (GRC readiness + room suggestion), tape chart, ETA/ETD, guest profiles, blacklist |
| **Booking engine** | Direct booking + SEO console; hotels = room grid; STRs = villa catalog |
| **Short-term rentals** | Hotel vs STR property kind, sellable units, per-villa locations, Instant / Request-to-book |
| **Booking** | Multi-room / group / corporate, returning guests, add-ons, vouchers, travel agents, day-use |
| **Revenue** | Seasons, rate plans, guardrails, hurdle rates, overbooking allowance, cancellation & no-show policy in code |
| **Billing** | Folios, corporate routing, group masters, charge splits, night audit, tax invoices, GSTR-1, payment links, cashier till (FO+POS cash, PIN pad), folio ledger |
| **F&B** | POS table map, full-screen till and kitchen pass, split bills, thermal KOT, kitchen display, inventory & recipes, QR ordering, room posting |
| **Operations** | Tickets + SLA, housekeeping `/hk`, guest laundry end-to-end, lost & found, banquet / events (send quote, guest response, dept checklists) |
| **Guests** | Online pre-check-in, GRC + occupant register, **editable nationality**, ID retention modes |
| **Messaging** | WhatsApp (Meta Cloud API) — confirmations, check-in links, inbox, desk tickets |
| **Localization** | India GST, Indonesia PB1, Thailand VAT, Malaysia SST, UAE VAT — currency & locales follow the pack |
| **Platform** | Multi-property RBAC, dark mode, property time zone, System Health, AI provider presets, CSV migration (eZee / Cloudbeds presets), eval harness in CI |

---

## Documentation & API

Full manual: **[kamrapms.com/docs](https://kamrapms.com/docs/)** — quickstart, self-hosting, features, user guide, AI/MCP, FAQ.

Going live? Use the **[go-live checklist](https://kamrapms.com/docs/go-live)**.

### REST & agents

Kamra exposes **170+ REST endpoints** — the same governed layer the UI and AI use:

- [REST API reference](https://kamrapms.com/docs/api-reference)
- [Postman collection](https://kamrapms.com/docs/kamra.postman_collection.json)
- [MCP tool reference](https://kamrapms.com/docs/mcp-tools)

```bash
curl -X POST https://<your-kamra>/api/method/kamra.api.get_quote \
  -H "Authorization: token <api_key>:<api_secret>" \
  -H "Content-Type: application/json" \
  -d '{"property":"Your Property","room_type":"Your Property-DLX",
       "check_in_date":"2026-08-01","check_out_date":"2026-08-03"}'
```

In-repo: [`docs/`](docs/) · [user guide](docs/user-guide.md) · [AI & API](docs/ai-and-api.md) · [self-hosting](docs/self-hosting.md) · [dev notes](docs-dev.md) · [branding](branding/README.md)

---

## Install

**Hotels (WordPress-easy):**

```bash
curl -fsSL https://raw.githubusercontent.com/Kamra-PMS/kamra-pms/main/deploy/install.sh | bash
```

Three prompts: site domain, admin email, admin password. Pulls
`ghcr.io/kamra-pms/kamra:latest`. Then open `/kamra/setup`. Details:
[deploy/](deploy/) · [docs quickstart](https://kamrapms.com/docs/quickstart).

**Bench / Frappe Cloud:**

```bash
bench get-app payments
bench get-app kamra https://github.com/Kamra-PMS/kamra-pms --branch main
bench --site your-site install-app kamra
```

After install: product UI at **`/kamra`**, booking at **`/book`**, housekeeping at **`/hk`**. Desk remains at `/app`. Sign in as **Administrator**, open `/kamra/setup`, create your property, add staff.

| Channel | Branch / tag | Use for |
|---|---|---|
| **Stable** | `main` / `vX.Y.Z` | Production, [Frappe Cloud Marketplace](https://cloud.frappe.io/marketplace/apps/kamra), [demo](https://demo.kamrapms.com), `ghcr.io/kamra-pms/kamra:latest` |
| **Nightly** | `develop` | Previews, `ghcr.io/kamra-pms/kamra:nightly` |

Production installs should use `--branch main` (`develop` is the default GitHub branch for contributors). Releases are SemVer with a **patch-first** cadence — see [`RELEASING.md`](RELEASING.md) and [`CHANGELOG.md`](CHANGELOG.md).

---

## Quickstart (development)

```bash
bench init --frappe-branch v16.25.0 frappe-bench && cd frappe-bench
bench get-app payments
bench get-app kamra https://github.com/Kamra-PMS/kamra-pms
bench new-site kamra.localhost --admin-password admin
bench --site kamra.localhost install-app kamra
bench serve --port 8000
cd apps/kamra/frontend && npm install && npm run dev   # hot-reload UI on :5173
```

Rebuild the SPA with `npm run build` at the app root (emits `kamra/public/frontend`). Seed demo data: `bench --site … execute kamra.scripts.seed_demo.execute`. Details: [docs-dev.md](docs-dev.md).

Connect Claude (hosted MCP — no local Python):

```bash
# Kamra Agent → Connect your AI → Connect Claude, or:
claude mcp add --transport http kamra https://pms.yourhotel.com/mcp
```

---

## Who it's for

- **Hotel / villa operators** — own the software and the data; costs don't grow with room count; AI is optional, not a ransom.
- **IT & integrators** — Python (Frappe) + React, documented REST + MCP, RBAC, audit trails, CI eval suite. Fork and extend.
- **Builders of hospitality AI** — a real PMS tool surface, not a demo chatbot API.

---

## License & contributors

**AGPL-3.0** — free forever. Anyone offering Kamra as a hosted service must share modifications back.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Thanks to [@Mohammed-Muneef](https://github.com/Mohammed-Muneef) (laundry, kitchen display v2, inventory & recipes, menu import, ID-document hardening).

### Links

- **Demo:** [demo.kamrapms.com](https://demo.kamrapms.com)
- **Docs:** [kamrapms.com/docs](https://kamrapms.com/docs/)
- **Issues:** [github.com/Kamra-PMS/kamra-pms](https://github.com/Kamra-PMS/kamra-pms)
- **Email:** [hello@kamrapms.com](mailto:hello@kamrapms.com)

Built by [HeyKoala](https://heykoala.ai).

---

*Kamra means "room". The door in our logo is open on purpose.*
