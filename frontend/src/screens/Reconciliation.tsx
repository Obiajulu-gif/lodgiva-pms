import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Download, Upload } from "lucide-react"
import { call, getCurrentProperty } from "../lib/api"
import { serverError } from "../lib/resource"
import { Button } from "../components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card"
import { cur, moneyLocale } from "../lib/money"
import { useT } from "../lib/i18n"

// Reconciliation queue (lodgiva_nigeria.reconcile): bank transfers, POS slips
// and Paystack settlements matched to folios, with manual resolution.

const money = (n: unknown) =>
  `${cur()}${Number(n ?? 0).toLocaleString(moneyLocale(), { maximumFractionDigits: 0 })}`
const SOURCES = ["Bank Transfer", "POS Terminal", "Paystack"] as const

interface Line {
  name: string; source: string; reference: string; amount: number; currency: string | null
  received_on: string; status: string; folio: string | null; payer: string | null
  narration: string | null; match_note: string | null
  resolved_by: string | null; resolution_note: string | null
}

export default function Reconciliation() {
  const { t } = useT()
  const property = getCurrentProperty()
  const [status, setStatus] = useState("")
  const [rows, setRows] = useState<Line[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [source, setSource] = useState<string>(SOURCES[0])
  const [csv, setCsv] = useState("")
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))

  const load = useCallback(() => {
    setError(null)
    call<Line[]>("lodgiva_nigeria.reconcile.queue", { property, ...(status ? { status } : {}) })
      .then(setRows).catch((e) => setError(serverError(e)))
  }, [property, status])
  useEffect(load, [load])

  const ingest = () => {
    call<{ added: number; skipped: number; Matched: number; Suggested: number; Unmatched: number }>(
      "lodgiva_nigeria.reconcile.ingest", { property, source, rows: csv })
      .then((r) => {
        setNotice(t("{a} added ({m} matched, {s} suggested, {u} unmatched), {k} skipped",
          { a: r.added, m: r.Matched, s: r.Suggested, u: r.Unmatched, k: r.skipped }))
        setCsv(""); load()
      }).catch((e) => setError(serverError(e)))
  }

  const resolve = (line: Line, action: "post" | "match" | "ignore") => {
    const folio = action === "ignore" ? null : window.prompt(t("Folio"), line.folio ?? "")
    if (action !== "ignore" && !folio) return
    const note = window.prompt(t("Note for the record (required)"))
    if (!note) return
    call("lodgiva_nigeria.reconcile.resolve", { name: line.name, action, note, ...(folio ? { folio } : {}) })
      .then(load).catch((e) => setError(serverError(e)))
  }

  const exportUrl = `/api/method/lodgiva_nigeria.reconcile.export?property=${encodeURIComponent(property)}&date=${date}`

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-zinc-900">{t("Reconciliation")}</h1>
          <p className="text-xs text-zinc-500">{t("Money seen at the bank, the POS terminal or Paystack, matched to folios.")}</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <input type="date" aria-label={t("Export date")} value={date} onChange={(e) => setDate(e.target.value)}
            className="rounded-md border border-zinc-300 bg-white px-2 py-1.5" />
          <a href={exportUrl} className="inline-flex items-center gap-1 rounded-md border border-zinc-300 bg-white px-3 py-1.5 font-medium hover:bg-zinc-50">
            <Download className="size-4" />{t("Daily export")}
          </a>
        </div>
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
      {notice && <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">{notice}</div>}

      <Card>
        <CardHeader><CardTitle>{t("Load a statement")}</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex flex-wrap gap-2">
            <select aria-label={t("Source")} value={source} onChange={(e) => setSource(e.target.value)}
              className="rounded-md border border-zinc-300 bg-white px-2 py-1.5">
              {SOURCES.map((s) => <option key={s}>{s}</option>)}
            </select>
            <Button onClick={ingest} disabled={!csv.trim()}><Upload className="size-4" />{t("Add lines")}</Button>
          </div>
          <textarea aria-label={t("CSV lines")} value={csv} onChange={(e) => setCsv(e.target.value)} rows={4}
            placeholder={"reference,amount,date,payer,narration\nTRF123,45000,2026-11-12,Ada Obi,RES-2026-00012 balance"}
            className="w-full rounded-md border border-zinc-300 p-2 font-mono text-xs" />
        </CardContent>
      </Card>

      <div className="flex w-fit rounded-lg border border-zinc-200 bg-white p-0.5 text-sm">
        {[["", t("Needs action")], ["Matched", t("Matched")], ["Resolved", t("Resolved")], ["Ignored", t("Ignored")]].map(([k, label]) => (
          <button key={k} onClick={() => setStatus(k)}
            className={"rounded-md px-3 py-1.5 font-medium " + (status === k ? "bg-brand-600 text-white" : "text-zinc-600")}>{label}</button>
        ))}
      </div>

      <Card>
        <CardContent className="overflow-x-auto pt-4">
          {rows && rows.length === 0 && <p className="text-sm text-zinc-500">{t("Nothing here.")}</p>}
          {rows && rows.length > 0 && (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-200 text-left text-xs font-medium uppercase tracking-wider text-zinc-500">
                  <th className="py-2 pr-3">{t("Received")}</th><th className="py-2 pr-3">{t("Source")}</th>
                  <th className="py-2 pr-3">{t("Reference")}</th><th className="py-2 pr-3 text-right">{t("Amount")}</th>
                  <th className="py-2 pr-3">{t("Folio")}</th><th className="py-2 pr-3">{t("Status")}</th><th className="py-2" />
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100">
                {rows.map((r) => (
                  <tr key={r.name} className="align-top">
                    <td className="py-2 pr-3 whitespace-nowrap">{r.received_on}</td>
                    <td className="py-2 pr-3">{t(r.source)}</td>
                    <td className="py-2 pr-3"><div className="font-mono text-xs">{r.reference}</div><div className="text-xs text-zinc-500">{r.payer} {r.narration}</div></td>
                    <td className="py-2 pr-3 text-right tabular-nums">{money(r.amount)}{r.currency ? ` ${r.currency}` : ""}</td>
                    <td className="py-2 pr-3">{r.folio ? <Link className="text-brand-700 hover:underline" to={`/billing/${r.folio}`}>{r.folio}</Link> : "-"}</td>
                    <td className="py-2 pr-3"><div className="font-medium">{t(r.status)}</div><div className="text-xs text-zinc-500">{r.match_note}{r.resolved_by ? ` · ${r.resolved_by}: ${r.resolution_note}` : ""}</div></td>
                    <td className="py-2 whitespace-nowrap text-right">
                      {(r.status === "Unmatched" || r.status === "Suggested") && (
                        <span className="inline-flex gap-1">
                          <Button variant="outline" onClick={() => resolve(r, "post")}>{t("Post")}</Button>
                          <Button variant="outline" onClick={() => resolve(r, "match")}>{t("Match")}</Button>
                          <Button variant="ghost" onClick={() => resolve(r, "ignore")}>{t("Ignore")}</Button>
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
