"use client";

import { useEffect, useRef, useState } from "react";
import { Info, X } from "lucide-react";

export function notify(message: string) {
  if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent("iip:notice", { detail: message }));
}
export function ToastRegion() {
  const [items, setItems] = useState<{ id: number; message: string }[]>([]);
  const next = useRef(0); const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  useEffect(() => {
    const listener = (event: Event) => {
      const id = ++next.current; const message = (event as CustomEvent<string>).detail;
      setItems(old => [...old.slice(-2), { id, message }]);
      timers.current.push(setTimeout(() => setItems(old => old.filter(i => i.id !== id)), 6500));
    };
    window.addEventListener("iip:notice", listener);
    const timeouts = timers.current;
    return () => { window.removeEventListener("iip:notice", listener); timeouts.forEach(clearTimeout); };
  }, []);
  return <div className="ui-toasts" aria-live="polite" aria-atomic="false">{items.map(i => <div className="ui-toast" key={i.id}><Info size={18} className="shrink-0" aria-hidden="true" /><p className="text-sm">{i.message}</p><button className="ui-icon-button ui-button-quiet !min-h-6 !w-6 !p-0" aria-label="Hinweis schließen" onClick={() => setItems(old => old.filter(x => x.id !== i.id))}><X size={14} /></button></div>)}</div>;
}
