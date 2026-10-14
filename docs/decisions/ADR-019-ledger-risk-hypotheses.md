# ADR-019: Ledger-Risiko und gespeicherte Hypothesen

Status: Accepted · 2026-10-14

P8 berechnet tatsächliche Portfoliorenditen aus dem P4-Ledger und validierten P3/P6-Marktinputs. Cashflows werden täglich neutralisiert und auf explizite Referenzsitzungen zusammengeführt. Kurslücken an offenen Tagen werden nicht aufgefüllt. Snapshot-Inhalte und kanonische/Raw-Provenienz werden eingefroren.

Szenarien trennen Positions-, FX-, Beta- und Parameterhypothesen. What-if verwendet kopierte Bestände mit expliziten Kosten; der reale Ledger wird nie verändert. Aktuelle Exposure kann verfügbar sein, während historische Risikokennzahlen fehlen. Pro-forma-Performance ist gekennzeichnet.

Konsequenz: P8 ist unabhängig von einem P7-Produktionsmodell, MLflow und LLM nutzbar. Seine technische Abnahme ersetzt weder den Nachweis vollständiger realer Historie noch die ausstehende Freigabe der Zielinstallation. P9/P10 sind nicht Bestandteil dieser Entscheidung.
