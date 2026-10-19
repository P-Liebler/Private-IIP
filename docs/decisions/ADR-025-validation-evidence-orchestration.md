# ADR-025 – PR2-Prüfevidenz um bestehende quantitative Dienste

2026-10-16 · Angenommen für PR2.

PR1-Collector-Jobs, P6-Datasets/Execution, P7-Training/Registry/Predictions und P9-Backtests bleiben die einzigen fachlichen Ausführungspfade. PR2 koordiniert sie mit einer append-only Tabelle `validation_records` für typisierte Audit-, Pilot-, Originalbeleg-, Protokoll-, Auswertungs- und Forward-Verknüpfungen. API-Schemata und Services bestimmen die zulässigen Inhalte; es gibt keinen beliebigen JSON-Schreibendpunkt. Parent-Links, Ownership, SHA-256 und Update-Trigger schützen die Evidenz. Bestehende gepinnte Zeilen erhalten keine neuen Spalten; ADR-024 bleibt unverändert gültig.

Reale Herkunft benötigt einen geprüften Original-/Rechtebezug; USER_ARCHIVE allein ist kein Real-Datenbeweis. Herkunftsreviews ersetzen keine P6-Verfügbarkeitsreviews und aktivieren keine Quelle. Quelle/Use müssen sowohl zur expliziten Policy als auch zu den gepinnten Eingaben passen.

Experimente registrieren Horizonte, Ziele, Fenster, Parameter, Kosten, Metriken und feste bestehende Gates vor OOS. Verwendete oder reservierte finale Fenster dürfen nicht still wieder als unangetastet gelten. P7 erzeugt die Modelle; PR2 erzeugt keine zweite Trainingspipeline. Neue FX-Kosten werden in derselben P6-Engine berechnet, Altanfragen behalten ihren bisherigen Default von null expliziten FX-Gebühren. Alte Resultate werden nicht neu geschrieben.

Forward-Research verwendet bestehende immutable Predictions/Outcomes mit FORWARD_ARCHIVED_SHADOW und experimentellem Status. Derselbe aktuelle Membership-/Feature-/Artefakt-/Kalibrierungs-/Intervallpfad bleibt bindend. Keine Rückdatierung, keine Produktionsfreigabe. Scheduling erfordert globale Konfiguration und eine explizite Operatorpolicy; standardmäßig aus. Korrekturen hängen Outcomes an. Source-, Modell-, Strategie- und Homelab-Gates bleiben getrennt.
