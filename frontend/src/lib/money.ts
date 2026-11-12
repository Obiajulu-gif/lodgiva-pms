/*  Currency and tax vocabulary, from the property's localization pack. Loaded
    once per session; the defaults below are only what shows for the few
    hundred ms before the pack answers, so they are Lodgiva's home market
    rather than Kamra's - an Indian flash on a Lagos front desk reads as a
    bug, and on the very first paint there is nothing cached to correct it.
    The last resolved locale is kept in localStorage so screens render with
    the right symbol immediately on reload, before the network answers. */

import { call, getCurrentProperty } from "./api"

interface Locale {
  currency_symbol: string
  locale: string
  currency: string
  tax_label: string
  tax_id_label: string
  tax_rates: number[]
}

let cache: Locale = {
  currency_symbol: "₦",
  locale: "en-NG",
  currency: "NGN",
  tax_label: "VAT",
  tax_id_label: "TIN",
  tax_rates: [0, 7.5],
}

try {
  const saved = JSON.parse(localStorage.getItem("kamra_locale") || "")
  if (saved && saved.currency_symbol) cache = { ...cache, ...saved }
} catch {
  /* first run - the defaults above stand until the pack resolves */
}

function remember() {
  try {
    localStorage.setItem("kamra_locale", JSON.stringify(cache))
  } catch {
    /* private mode */
  }
}

export function loadLocale(): Promise<Locale> {
  return call<Locale>("kamra.api.property_locale", {
    property: getCurrentProperty(),
  })
    .then((l) => {
      cache = { ...cache, ...l }
      remember()
      return cache
    })
    .catch(() => cache)
}

/** Public pages carry `ui_locale` in their payload - adopt it directly. */
export function adoptUiLocale(ui?: { currency_symbol?: string; locale?: string } | null) {
  if (!ui) return
  cache = {
    ...cache,
    // "" is a valid symbol (generic pack shows bare numbers)
    currency_symbol: ui.currency_symbol ?? cache.currency_symbol,
    locale: ui.locale || cache.locale,
  }
  remember()
}

export const locale = () => cache
/** The property's currency symbol, e.g. "₹" or "Rp". */
export const cur = () => cache.currency_symbol
/** The number-formatting locale, e.g. "en-IN" (lakhs) or "id-ID". */
export const moneyLocale = () => cache.locale
export const fmtMoney = (n: unknown) =>
  cache.currency_symbol +
  Number(n ?? 0).toLocaleString(cache.locale, { maximumFractionDigits: 2 })
export const taxRates = () => cache.tax_rates
export const taxLabel = () => cache.tax_label
/** India splits GST into CGST + SGST halves on every bill; nobody else does. */
export const splitsGst = () => cache.currency === "INR"
/** What the country calls a tax registration number, e.g. "TIN", "GSTIN". */
export const taxIdLabel = () => cache.tax_id_label
