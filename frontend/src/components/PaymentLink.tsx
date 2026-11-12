import { useState } from "react"
import { Check, Copy, ExternalLink, Link2 } from "lucide-react"
import { call } from "../lib/api"
import { serverError } from "../lib/resource"
import { useT } from "../lib/i18n"
import { Button } from "./ui/button"

interface LinkResult {
  url: string
  amount: number
  currency_symbol?: string
  test_mode?: boolean
}

/** "Payment link" button that issues a link and shows it - the URL, the
 * amount, Copy and Open - instead of silently writing to the clipboard,
 * which gave the desk no sign anything had happened. Pass `folio` for an
 * existing folio, or `reservation` straight after booking. */
export default function PaymentLink(props: {
  folio?: string
  reservation?: string
  label?: string
  /** Float the result below the button (toolbars) instead of inline. */
  popover?: boolean
}) {
  const { t } = useT()
  const [link, setLink] = useState<LinkResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  async function create() {
    setBusy(true)
    setError(null)
    try {
      const r = props.folio
        ? await call<LinkResult>("kamra.api.folio_payment_link", { folio: props.folio })
        : await call<LinkResult>("kamra.api.reservation_payment_link", {
            reservation: props.reservation,
          })
      setLink(r)
      copy(r.url)
    } catch (e) {
      setError(serverError(e))
    } finally {
      setBusy(false)
    }
  }

  function copy(url: string) {
    navigator.clipboard?.writeText(url).then(
      () => {
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      },
      () => setCopied(false),
    )
  }

  return (
    <div className="relative flex flex-col gap-2">
      {(!link || props.popover) && (
        <Button variant="outline" disabled={busy} onClick={link ? () => setLink(null) : create}>
          <Link2 className="size-4" aria-hidden />
          {busy ? t("Creating link...") : (props.label ?? t("Payment link"))}
        </Button>
      )}
      {error && (
        <p className={"text-xs text-rose-600 " + (props.popover ? "absolute right-0 top-full z-30 mt-2 w-72 rounded-md border border-rose-200 bg-white p-2 shadow-lg" : "")}>
          {error}
        </p>
      )}
      {link && (
        <div
          className={
            "rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm " +
            (props.popover ? "absolute right-0 top-full z-30 mt-2 w-80 shadow-lg" : "")
          }
        >
          <div className="mb-1 font-medium text-emerald-900">
            {t("Payment link for {amount}", {
              amount: `${link.currency_symbol ?? ""}${Number(link.amount).toLocaleString()}`,
            })}
          </div>
          <input
            readOnly
            value={link.url}
            onFocus={(e) => e.currentTarget.select()}
            className="w-full rounded border border-emerald-200 bg-white px-2 py-1 font-mono text-xs"
          />
          <div className="mt-2 flex flex-wrap gap-2">
            <Button variant="outline" className="px-2 py-1 text-xs" onClick={() => copy(link.url)}>
              {copied ? <Check className="size-4" aria-hidden /> : <Copy className="size-4" aria-hidden />}
              {copied ? t("Copied") : t("Copy")}
            </Button>
            <Button
              variant="outline"
              className="px-2 py-1 text-xs"
              onClick={() => window.open(link.url, "_blank", "noopener")}
            >
              <ExternalLink className="size-4" aria-hidden />
              {t("Open")}
            </Button>
          </div>
          {link.test_mode && (
            <p className="mt-2 text-xs text-amber-700">
              {t("Test mode - no real money moves. Turn test mode off in Payment Gateway Settings to take live payments.")}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
