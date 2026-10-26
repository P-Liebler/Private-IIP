"use client";

import { useId, useMemo, useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ChevronsUpDown } from "lucide-react";
import { Button, EmptyState } from "./primitives";

export type TableColumn<T> = { id: string; label: string; render: (row: T) => ReactNode; sortValue?: (row: T) => string | number | null; numeric?: boolean };
export function DataTable<T>({ label, rows, columns, rowKey, searchText, empty = "Noch keine Einträge vorhanden." }: { label: string; rows: T[]; columns: TableColumn<T>[]; rowKey: (row: T) => string; searchText?: (row: T) => string; empty?: string }) {
  const id = useId();
  const [filter, setFilter] = useState("");
  const [sort, setSort] = useState<{ id: string; descending: boolean } | null>(null);
  const shown = useMemo(() => {
    const data = rows.filter(row => !searchText || searchText(row).toLocaleLowerCase("de-CH").includes(filter.toLocaleLowerCase("de-CH")));
    const column = columns.find(c => c.id === sort?.id);
    if (column?.sortValue) data.sort((a, b) => {
      const av = column.sortValue!(a), bv = column.sortValue!(b);
      // Missing observations sort last in either direction; never coerce to zero.
      if (av === null || bv === null) return av === bv ? 0 : av === null ? 1 : -1;
      return (typeof av === "number" && typeof bv === "number" ? av - bv : String(av).localeCompare(String(bv), "de-CH", { numeric: true })) * (sort?.descending ? -1 : 1);
    });
    return data;
  }, [rows, columns, sort, searchText, filter]);
  return <section aria-label={label} className="space-y-4">
    {searchText && <label htmlFor={id} className="grid gap-2 text-sm">Einträge filtern<input id={id} type="search" value={filter} onChange={e => setFilter(e.target.value)} placeholder="Name oder Kennung…" /></label>}
    <p role="status" className="text-xs ui-muted">{shown.length} von {rows.length} Einträgen</p>
    {!shown.length ? <EmptyState title="Keine passenden Einträge" description={empty} /> : <>
      <div className="ui-table-desktop overflow-x-auto"><table className="ui-table w-full text-left text-sm"><caption className="sr-only">{label}</caption><thead><tr>{columns.map(c => <th scope="col" key={c.id} aria-sort={sort?.id === c.id ? sort.descending ? "descending" : "ascending" : undefined} className={c.numeric ? "text-right" : ""}>{c.sortValue ? <Button variant="quiet" onClick={() => setSort({ id: c.id, descending: sort?.id === c.id && !sort.descending })}>{c.label}{sort?.id !== c.id ? <ChevronsUpDown size={12} /> : sort.descending ? <ArrowDown size={12} /> : <ArrowUp size={12} />}</Button> : c.label}</th>)}</tr></thead><tbody>{shown.map(row => <tr key={rowKey(row)}>{columns.map(c => <td key={c.id} className={c.numeric ? "text-right tabular-nums" : ""}>{c.render(row)}</td>)}</tr>)}</tbody></table></div>
      <ul className="ui-table-mobile" aria-label={`${label} als Karten`}>{shown.map(row => <li key={rowKey(row)} className="ui-panel"><dl>{columns.map(c => <div key={c.id}><dt className="text-xs ui-muted">{c.label}</dt><dd className="mt-1 break-words">{c.render(row)}</dd></div>)}</dl></li>)}</ul>
    </>}
  </section>;
}
