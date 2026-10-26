"use client";

import { api } from "@/lib/api";
import { Button, ConfirmationDialog } from "@/components/ui/primitives";

export function DocumentRemovalButton({ id, onRemoved }: { id: string; onRemoved: () => Promise<void> }) {
  return <ConfirmationDialog title="Dokument aus Bibliothek und Suche entfernen?" description={<><p>Das Dokument wird aus Ihrer aktiven Bibliothek und aus neuen Such- und Assistentenabrufen entfernt. Auch ein historischer Suchstichtag hebt diese Entfernung nicht auf.</p><p className="mt-3">Das unveränderliche Original, frühere Belege und das Entfernungsprotokoll bleiben im Audit erhalten. Dies ist keine physische Löschung aller gespeicherten Bytes.</p></>} trigger={<Button variant="danger">Aus Bibliothek entfernen</Button>} onConfirm={async () => { await api(`/research-documents/${id}`, { method: "DELETE" }); await onRemoved(); }} />;
}
