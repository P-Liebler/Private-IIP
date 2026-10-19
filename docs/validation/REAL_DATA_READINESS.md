# Real Data Readiness

Stand: 19.10.2026. PR2 ergänzt P0–P10 ohne Umnummerierung. Einstieg: `/data-operations/readiness`; API: `/api/v1/validation`.

Ein Audit bindet Universe, Instrumente, Benchmark, Zeitraum, Horizont, Währung, Availability-Modus, Features, Folds und Quellenpolitik. Es kombiniert PR1-Coverage, P6-Replay und die unveränderten P7-Gates. Fehlende Kalender und nicht geprüfte Partitionen bleiben `null`, nicht null Beobachtungen als vermeintlich geprüftes Ergebnis.

Die Coverage zählt Instrument und Benchmark gemeinsam. `validated_fx_sessions` zählt versorgte Sitzungen, einschließlich Identitätsumrechnung bei gleicher Währung; diese sind keine externen FX-Beobachtungen. Einzelberichte zeigen Währungsrichtung und fehlende Sitzungen. Synthetische Kurse sind technische Coverage, keine reale Dateneignung.

Harte Sperren bleiben getrennt: Quellenrechte, Originalnachweis, PIT-Belege, Membership/Delistings, Corporate Actions, Features, Historientiefe und OOS. Ein Qualitätsscore hebt keine Sperre auf. Reconstructed-Historie bleibt Forschung. Die Grenzen 1.000 Training, 500 OOS, 600 verschiedene OOS-Signaltage und drei Folds werden nicht abgesenkt.

Die Operator-Checklisten speichern versionierte Arbeitsnotizen für zwölf Rechte-/Betriebsaspekte. Sie verändern keine Source Registry. Niemals Geheimnisse in Notizfelder schreiben. Freigabe, Aktivierung und Review laufen weiterhin über die vorhandenen Quellenprozesse.

Pilot: 3–5 bestehende Instrumente, separater Benchmark, CHF und explizite Collections. Vorschau prüft Gates vor jedem Zugriff; Start und Wiederaufnahme verwenden PR1-Jobs. Fortschritt, Cancel/Resume, Quarantäne und Originalarchivierung bleiben bei PR1. `RAW_EVIDENCE` belegt Original-SHA und Herkunft, verändert aber weder alte Availability noch Quellenrechte. Ohne freigegebene Quellen oder rechtmäßig gelieferte Originale: `LIVE_SMOKE_BLOCKED_SOURCE_NOT_APPROVED` beziehungsweise `BLOCKED_BY_REAL_DATA`.

Aktueller tatsächlicher Befund und Audit-ID: [PR2A-Abnahme](../PR2A_REAL_DATA_ACCEPTANCE_REPORT.md). Es wurde kein realer Pilot als erfolgreich erklärt.
