# Analystenschätzungen (P5)

`analyst_estimate_snapshots` unterstützt EPS, Revenue, Price Targets und Recommendations mit typisierter Einheit/Währung, Zielperiode, stabiler Instrument-ID, Quelle, Raw-Referenz, Beobachtungs-/Kenntnis-/Abrufzeit, Regelversion, Qualität und Ersetzungsbezug. Geld, Per-share und Rating werden nicht vermischt.

Der validierte manuelle JSON-Import benötigt MANUAL_RESEARCH mit Scope `estimates`; exakt gelieferte Bytes werden vor Parsing gespeichert. Dieselbe Raw-Version wird nicht doppelt importiert. Ein tatsächlich neu beobachteter Wert wird als neuer Snapshot archiviert, auch wenn er numerisch unverändert blieb. Änderungen überschreiben alte Werte nicht. Snapshot-Historie ist aus dem ersten wirklichen Eingang aufgebaut; `known_at=observed_at=retrieved_at` für manuelle aktuelle Beobachtungen. Die API verlangt diese Zeiten ≤ historischem Stichtag.

Keine automatische Schätzungsquelle ist derzeit freigegeben oder implementiert. Yahoo bleibt BLOCKED. Es gibt keine daraus rekonstruierte historische Konsenskurve. Forward P/E und PEG bleiben unverfügbar, bis eine zuverlässige Quelle zusätzlich den erforderlichen kompatiblen Per-share-/Zielperiodenvertrag belegt. Der lokale Assistent erzeugt keine Ersatzschätzungen.
