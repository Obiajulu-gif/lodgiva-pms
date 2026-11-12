import { useCallback, useEffect, useState } from "react"
import { useNavigate, useOutletContext } from "react-router-dom"
import { AlertTriangle, CheckCircle2, Clock } from "lucide-react"
import { call } from "../lib/api"
import { serverError } from "../lib/resource"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { cur, moneyLocale } from "../lib/money"
import { useT } from "../lib/i18n"
import type { ShellContext } from "../AppShell"

// Group dashboard: every property the user may access, side by side.
// Backed by kamra.group - the same numbers as each property's own reports.

const n0 = (n: unknown) =>
  Number(n ?? 0).toLocaleString(moneyLocale(), { maximumFractionDigits: 0 })
const money = (n: unknown) => `${cur()}${n0(n)}`
const today = () => new Date().toISOString().slice(0, 10)
const monthStart = () => today().slice(0, 8) + "01"

type Tab = "portfolio" | "close" | "finance"

interface PortRow {
  property: string; property_name: string; rooms: number; out_of_service: number
  room_nights_sold: number; occupancy_pct: number; room_revenue: number; adr: number
  revpar: number; arrivals: number; departures: number; business_date: string; provisional: boolean
}
interface Portfolio { rows: PortRow[]; totals: Omit<PortRow, "property" | "property_name" | "business_date"> & { properties: number } }
interface Blocker { kind: string; count: number; text: string; link: string }
interface CloseRow {
  property: string; property_name: string; business_date: string; today: string; days_behind: number
  status: "Ready" | "Blocked" | "Behind"; open_cashiers: number; blockers: Blocker[]
  last_audit: { name: string; business_date: string; status: string } | null
  provisional: { collections: number }
}
interface FinRow {
  property: string; property_name: string
  tenders: Record<"cash" | "bank_transfer" | "pos_terminal" | "paystack" | "other", number>
  collected: number; refunds: number; outstanding_folios: number; outstanding: number
  unmatched_payments: number; unmatched_amount: number; variance_total: number
  cashier_variances: { name: string; user: string; business_date: string; variance: number }[]
  provisional: boolean; links: Record<string, string>
}
interface Finance { rows: FinRow[]; totals: Omit<FinRow, "property" | "property_name" | "links" | "cashier_variances" | "provisional"> }

const STATUS_TONE: Record<CloseRow["status"], string> = {
  Ready: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Blocked: "bg-amber-50 text-amber-700 border-amber-200",
  Behind: "bg-rose-50 text-rose-700 border-rose-200",
}

export default function Group() {
  const { t } = useT()
  const nav = useNavigate()
  const { switchProperty } = useOutletContext<ShellContext>()
  const [tab, setTab] = useState<Tab>("portfolio")
  const [from, setFrom] = useState(monthStart())
  const [to, setTo] = useState(today())
  const [only, setOnly] = useState("")
  const [props, setProps] = useState<{ name: string; property_name: string }[]>([])
  const [port, setPort] = useState<Portfolio | null>(null)
  const [close, setClose] = useState<{ rows: CloseRow[]; summary: Record<string, number> } | null>(null)
  const [fin, setFin] = useState<Finance | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    call<{ name: string; property_name: string }[]>("kamra.api.my_properties").then(setProps).catch(() => {})
  }, [])

  const load = useCallback(() => {
    setError(null)
    const args = { from_date: from, to_date: to, ...(only ? { property: only } : {}) }
    const fail = (e: unknown) => setError(serverError(e))
    if (tab === "portfolio") call<Portfolio>("kamra.group.portfolio", args).then(setPort).catch(fail)
    if (tab === "close") call<typeof close>("kamra.group.daily_close", only ? { property: only } : {}).then(setClose).catch(fail)
    if (tab === "finance") call<Finance>("kamra.group.finance", args).then(setFin).catch(fail)
  }, [tab, from, to, only])
  useEffect(load, [load])

  // Drill into one hotel: make it the current property, then open the screen.
  const open = (property: string, link: string) => {
    switchProperty(property)
    nav(link)
  }

  const th = "py-2 pr-3 text-right"
  const td = "py-2 pr-3 text-right tabular-nums"
  const Prov = ({ on }: { on: boolean }) =>
    on ? <span className="ml-1 rounded bg-amber-100 px-1 text-[10px] font-medium text-amber-700" title={t("Not through night audit yet - can still change")}>{t("provisional")}</span> : null

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">{t("Group Dashboard")}</h1>
          <p className="text-xs text-zinc-500">{t("Every property you can access. Click a hotel to open its own screens.")}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <select aria-label={t("Property")} value={only} onChange={(e) => setOnly(e.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-2 py-1.5">
            <option value="">{t("All properties")}</option>
            {props.map((p) => <option key={p.name} value={p.name}>{p.property_name}</option>)}
          </select>
          {tab !== "close" && (
            <>
              <input type="date" aria-label={t("From")} value={from} max={to} onChange={(e) => setFrom(e.target.value)}
                className="rounded-md border border-zinc-300 bg-white px-2 py-1.5" />
              <input type="date" aria-label={t("To")} value={to} min={from} onChange={(e) => setTo(e.target.value)}
                className="rounded-md border border-zinc-300 bg-white px-2 py-1.5" />
            </>
          )}
        </div>
      </div>

      <div role="tablist" className="flex w-fit rounded-lg border border-zinc-200 bg-white p-0.5 text-sm">
        {([["portfolio", t("All Properties")], ["close", t("Daily Close")], ["finance", t("Finance")]] as const).map(([k, label]) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={"rounded-md px-3 py-1.5 font-medium " + (tab === k ? "bg-brand-600 text-white" : "text-zinc-600")}>
            {label}
          </button>
        ))}
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}

      {tab === "portfolio" && port && (
        <Card>
          <CardHeader><CardTitle>{t("All Properties")} · {from} – {to}</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  <th className="py-2 pr-3">{t("Property")}</th>
                  <th className={th}>{t("Occ %")}</th><th className={th}>{t("Room revenue")}</th>
                  <th className={th}>{t("ADR")}</th><th className={th}>{t("RevPAR")}</th>
                  <th className={th}>{t("Arr")}</th><th className={th}>{t("Dep")}</th>
                  <th className="py-2 text-right">{t("Out of service")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {port.rows.map((r) => (
                  <tr key={r.property}>
                    <td className="py-2 pr-3">
                      <button className="font-medium text-brand-700 underline-offset-2 hover:underline" onClick={() => open(r.property, "/dashboard")}>
                        {r.property_name}
                      </button>
                      <Prov on={r.provisional} />
                    </td>
                    <td className={td}>{r.occupancy_pct}%</td><td className={td}>{money(r.room_revenue)}</td>
                    <td className={td}>{money(r.adr)}</td><td className={td}>{money(r.revpar)}</td>
                    <td className={td}>{r.arrivals}</td><td className={td}>{r.departures}</td>
                    <td className="py-2 text-right tabular-nums">{r.out_of_service} / {r.rooms}</td>
                  </tr>
                ))}
                <tr className="border-t-2 border-zinc-300 font-semibold">
                  <td className="py-2 pr-3">{t("Total")} ({port.totals.properties})<Prov on={port.totals.provisional} /></td>
                  <td className={td}>{port.totals.occupancy_pct}%</td><td className={td}>{money(port.totals.room_revenue)}</td>
                  <td className={td}>{money(port.totals.adr)}</td><td className={td}>{money(port.totals.revpar)}</td>
                  <td className={td}>{port.totals.arrivals}</td><td className={td}>{port.totals.departures}</td>
                  <td className="py-2 text-right tabular-nums">{port.totals.out_of_service} / {port.totals.rooms}</td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {tab === "close" && close && (
        <div className="space-y-3">
          <p className="text-sm text-zinc-600">
            {t("{a} ready · {b} blocked · {c} behind", { a: close.summary.Ready ?? 0, b: close.summary.Blocked ?? 0, c: close.summary.Behind ?? 0 })}
          </p>
          {close.rows.map((r) => (
            <Card key={r.property}>
              <CardContent className="space-y-2 pt-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <button className="font-semibold text-brand-700 hover:underline" onClick={() => open(r.property, "/dashboard")}>{r.property_name}</button>
                  <span className={"inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium " + STATUS_TONE[r.status]}>
                    {r.status === "Ready" ? <CheckCircle2 className="size-3.5" /> : r.status === "Blocked" ? <AlertTriangle className="size-3.5" /> : <Clock className="size-3.5" />}
                    {t(r.status)}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
                  <div><div className="text-xs text-zinc-500">{t("Business date")}</div><div className="font-medium">{r.business_date}{r.days_behind ? ` (${t("{n} days behind", { n: r.days_behind })})` : ""}</div></div>
                  <div><div className="text-xs text-zinc-500">{t("Open cashiers")}</div><div className="font-medium">{r.open_cashiers}</div></div>
                  <div><div className="text-xs text-zinc-500">{t("Last audit")}</div><div className="font-medium">{r.last_audit ? `${r.last_audit.business_date} · ${r.last_audit.status}` : t("never")}</div></div>
                  <div><div className="text-xs text-zinc-500">{t("Collections")}<Prov on /></div><div className="font-medium">{money(r.provisional.collections)}</div></div>
                </div>
                {r.blockers.length > 0 && (
                  <ul className="space-y-1 text-sm">
                    {r.blockers.map((b) => (
                      <li key={b.kind} className="flex items-center justify-between gap-2 rounded-md bg-amber-50 px-2 py-1">
                        <span>{b.count} · {t(b.text)}</span>
                        <button className="shrink-0 text-xs font-medium text-brand-700 hover:underline" onClick={() => open(r.property, b.link)}>{t("Resolve")} →</button>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {tab === "finance" && fin && (
        <Card>
          <CardHeader><CardTitle>{t("Finance")} · {from} – {to}</CardTitle></CardHeader>
          <CardContent className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  <th className="py-2 pr-3">{t("Property")}</th>
                  <th className={th}>{t("Cash")}</th><th className={th}>{t("Bank transfer")}</th>
                  <th className={th}>{t("POS terminal")}</th><th className={th}>{t("Paystack")}</th>
                  <th className={th}>{t("Refunds")}</th><th className={th}>{t("Outstanding")}</th>
                  <th className={th}>{t("Unmatched")}</th><th className="py-2 text-right">{t("Cash variance")}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {fin.rows.map((r) => (
                  <tr key={r.property}>
                    <td className="py-2 pr-3">
                      <button className="font-medium text-brand-700 hover:underline" onClick={() => open(r.property, r.links.report)}>{r.property_name}</button>
                      <Prov on={r.provisional} />
                    </td>
                    {(["cash", "bank_transfer", "pos_terminal", "paystack"] as const).map((k) => (
                      <td key={k} className={td}><button className="hover:underline" onClick={() => open(r.property, r.links.transactions)}>{money(r.tenders[k])}</button></td>
                    ))}
                    <td className={td}>{money(r.refunds)}</td>
                    <td className={td}><button className="hover:underline" onClick={() => open(r.property, r.links.outstanding)}>{money(r.outstanding)} ({r.outstanding_folios})</button></td>
                    <td className={td}><button className={"hover:underline " + (r.unmatched_payments ? "text-amber-700" : "")} onClick={() => open(r.property, r.links.unmatched)}>{r.unmatched_payments} · {money(r.unmatched_amount)}</button></td>
                    <td className="py-2 text-right tabular-nums"><button className={"hover:underline " + (r.variance_total ? "text-rose-700" : "")} onClick={() => open(r.property, r.links.variances)}>{money(r.variance_total)}</button></td>
                  </tr>
                ))}
                <tr className="border-t-2 border-zinc-300 font-semibold">
                  <td className="py-2 pr-3">{t("Total")}</td>
                  {(["cash", "bank_transfer", "pos_terminal", "paystack"] as const).map((k) => <td key={k} className={td}>{money(fin.totals.tenders[k])}</td>)}
                  <td className={td}>{money(fin.totals.refunds)}</td>
                  <td className={td}>{money(fin.totals.outstanding)} ({fin.totals.outstanding_folios})</td>
                  <td className={td}>{fin.totals.unmatched_payments} · {money(fin.totals.unmatched_amount)}</td>
                  <td className="py-2 text-right tabular-nums">{money(fin.totals.variance_total)}</td>
                </tr>
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
