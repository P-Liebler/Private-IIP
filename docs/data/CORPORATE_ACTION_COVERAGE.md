# Corporate-Action-Coverage

Stand 2026-10-16. Nachweis erfolgt je Instrument, Ereignistyp und Intervall. Ein importiertes Ereignis und eine leere Ergebnisliste sind keine Vollständigkeitsbestätigung.

1. Original aus einer für `action_coverage` genehmigten Quelle unverändert archivieren.
2. Vollständige historische Ereignisliste mit Quelle/Fundstelle und Datumsdefinitionen prüfen.
3. Unabhängigen Cross-Check und konkrete Vollständigkeitsmethode dokumentieren.
4. Aktuelle kanonische Versions-IDs des Intervalls und der geprüften Typen abgleichen.
5. Berechtigter Daten-Operator erstellt einen neuen `ActionCoverageReview`. Keine automatische oder globale Freigabe.

`POST /api/v1/data-operations/action-coverage/reviews` verlangt exakten Raw-Beleg, Zeitraum, Typen, Versionsliste, History-Referenz, Cross-Check, Methode und Begründung. Split-only-Reviews erfüllen das Total-Return-Gate nicht. P6 benötigt mindestens SPLIT und DIVIDEND; weitergehende Ereignisse brauchen fachlich unterstützte Berechnung. Eine neue/korrigierte Action macht den bisherigen Versionsnachweis unzureichend. Alte Review- und Ergebnisversionen bleiben erhalten.

Der manuelle Action-Vertrag unterstützt SPLIT, REVERSE_SPLIT, DIVIDEND, TICKER_CHANGE und DELISTING. SPECIAL_DIVIDEND wird als Cash-Dividende berechnet und behält die Sonderklassifikation im unveränderlichen `event_details`. Zähler/Nenner sind prüfbar; widersprüchliche Split-Faktoren werden verworfen. Record-/Payment-Daten und Datum als Ex-/Wirksamkeitstag bleiben typbezogen. Spins, Fusionen und Aktientausche werden nicht zu Splits umgedeutet, sondern abgewiesen. Fremdwährungsdividenden ohne akzeptierten Währungsvertrag bleiben gesperrt.

Nach gültigem Nachweis dürfen neue P6-/Research-/Risiko-/Backtest-Berechnungen mit ihren eigenen Gates entstehen. Keine rückwirkende Veränderung früherer Snapshots. Für echte Instrumente ist in PR1 keine vollständige Action-Historie pauschal bestätigt worden.
