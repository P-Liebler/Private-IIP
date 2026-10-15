"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, API_BASE } from "@/lib/api";
import { field, PortfolioSelect, Result } from "@/components/intelligence";

type Conversation = { id: string; title: string };
type Message = { id: string; role: string; content: string; status: string; model_version: string | null; evidence: { citations?: Citation[] } };
type Citation = { document_id: string; chunk_id: string; title: string; url: string; published_at: string | null; content_hash: string };
export default function AssistantPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversation, setConversation] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [portfolio, setPortfolio] = useState("");
  const [instrument, setInstrument] = useState("");
  const [question, setQuestion] = useState("");
  const [text, setText] = useState("");
  const [progress, setProgress] = useState("");
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [runtime, setRuntime] = useState<unknown>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(() => {
    api<Conversation[]>("/assistant/conversations").then(setConversations).catch(e => setError(String(e)));
    api("/assistant/status").then(setRuntime).catch(e => setError(String(e)));
    return () => controller.current?.abort();
  }, []);
  useEffect(() => {
    if (!conversation) return;
    let current = true;
    api<Message[]>(`/assistant/conversations/${conversation}/messages`).then(r => { if (current) setMessages(r); }).catch(e => { if (current) setError(String(e)); });
    return () => { current = false; };
  }, [conversation]);
  async function create() {
    try { const row = await api<Conversation>("/assistant/conversations", { method: "POST", body: JSON.stringify({ title: "Neue Analyse" }) }); setConversations(r => [row, ...r]); setMessages([]); setConversation(row.id); setText(""); } catch (e) { setError(String(e)); }
  }
  async function remove() {
    try { await api(`/assistant/conversations/${conversation}`, { method: "DELETE" }); setConversations(r => r.filter(c => c.id !== conversation)); setMessages([]); setConversation(""); setText(""); setCitations([]); } catch (e) { setError(String(e)); }
  }
  async function ask() {
    setBusy(true); setError(""); setText(""); setCitations([]);
    const abort = new AbortController(); controller.current = abort;
    try {
      const response = await fetch(`${API_BASE}/assistant/conversations/${conversation}/messages`, { method: "POST", credentials: "include", cache: "no-store", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question, portfolio_id: portfolio || null, instrument_id: instrument || null }), signal: abort.signal });
      if (!response.ok) throw new Error((await response.json()).error?.message ?? "Analyse fehlgeschlagen");
      if (!response.body) throw new Error("Kein Antwortstrom");
      const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = "";
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let split: number;
        while ((split = buffer.indexOf("\n\n")) >= 0) {
          const frame = buffer.slice(0, split); buffer = buffer.slice(split + 2);
          if (!frame.startsWith("data: ")) continue;
          const event = JSON.parse(frame.slice(6));
          if (event.type === "text") setText(t => t + event.delta);
          else if (event.type === "done") { setCitations(event.citations); setProgress(`${event.status} · ${event.model_version ?? "Strukturierte Daten ohne LLM"}`); }
          else if (event.type === "error") throw new Error(event.message + " · " + event.code);
          else setProgress(`${event.type} · ${event.name ?? ""} · ${event.status}`);
        }
      }
      setMessages(await api<Message[]>(`/assistant/conversations/${conversation}/messages`));
      setText(""); setQuestion("");
    } catch (e) { if (abort.signal.aborted) setProgress("Abgebrochen"); else setError(String(e)); }
    finally { setBusy(false); controller.current = null; }
  }
  return <main className="space-y-5 py-8"><h1 className="text-2xl">Lokaler Assistent</h1><p>Quantitative Dienste liefern Fakten. Das lokale Modell waehlt belegte Inhalte zur Erklaerung. Keine Handelsausfuehrung.</p><Link className="text-emerald-400" href="/documents">Dokumente und Quellen verwalten</Link><details><summary>Lokaler Modellstatus</summary><Result value={runtime} /></details>
    {error && <p role="alert" className="text-rose-400">{error}</p>}<div className="flex gap-3"><select aria-label="Unterhaltung" className={field} disabled={busy} value={conversation} onChange={e => { setMessages([]); setConversation(e.target.value); setText(""); setCitations([]); }}><option value="">Unterhaltung waehlen</option>{conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select><button className={field} disabled={busy} onClick={create}>Neue Unterhaltung</button><button className={field} disabled={!conversation || busy} onClick={remove}>Unterhaltung loeschen</button></div>
    <PortfolioSelect value={portfolio} onChange={setPortfolio} /><label className="block">Instrument-ID <input className={field} aria-label="Instrument-ID" value={instrument} onChange={e => setInstrument(e.target.value)} /></label>
    <section aria-label="Nachrichten" className="space-y-4">{messages.map(m => <article key={m.id} className="rounded border border-zinc-800 p-4"><h2>{m.role} · {m.status}</h2><p className="whitespace-pre-wrap">{m.content}</p>{m.model_version && <p className="text-xs">{m.model_version}</p>}{m.evidence.citations?.map(c => <p key={c.chunk_id}><a className="text-emerald-400" target="_blank" rel="noreferrer" href={`${new URL(API_BASE).origin}${c.url}`}>{c.title}</a> - {c.chunk_id} - {c.content_hash}</p>)}{m.role === "ASSISTANT" && <details><summary>Fakten, Werkzeuge und Quellen</summary><Result value={m.evidence} /></details>}</article>)}{text && <p className="whitespace-pre-wrap">{text}</p>}</section>
    <label className="block">Frage<textarea aria-label="Frage" className={`${field} block w-full`} maxLength={2000} value={question} onChange={e => setQuestion(e.target.value)} /></label><button className={field} disabled={!conversation || !question || busy} onClick={ask}>Analyse starten</button> <button className={field} disabled={!busy} onClick={() => controller.current?.abort()}>Abbrechen</button><p role="status">{progress}</p>
    <ul>{citations.map(c => <li key={c.chunk_id}><a className="text-emerald-400" target="_blank" rel="noreferrer" href={`${new URL(API_BASE).origin}${c.url}`}>{c.title}</a> · {c.published_at ?? "Publikationsdatum unbekannt"} · {c.chunk_id} · {c.content_hash}</li>)}</ul><p className="text-sm text-zinc-400">Gespeicherte Unterhaltungen werden nach der konfigurierten Aufbewahrungsfrist geloescht. Keine Passwoerter oder Zugangsdaten eingeben.</p></main>;
}
