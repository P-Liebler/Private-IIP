# PR8D – echter Portfolio-Pilot

Stand: 27.10.2026. **REAL_PORTFOLIO_PENDING_ORIGINALS_AND_SECURITY_APPROVAL**. Es wurden keine privaten Originale bereitgestellt und keine unabhängige Testperson benannt. Kein synthetischer Test wird als reale Depot- oder Anfängerabnahme gewertet.

Der [technische Core-Nachweis](PR8E_CORE_ACCEPTANCE_REPORT.md) ist mit 306 Backend-, 82 Host- und 30 Browserfällen sowie isoliertem Restore von 1383 Dateihashes abgeschlossen. Er belegt die lokalen synthetischen Abläufe, während die folgenden echten Nachweise ausstehen. Der Zielhost ist laut bestehender Nutzerantwort noch nicht verfügbar; die lokale Vorbereitung verlangt keine erneute Host- oder Instrumentenabfrage.

## Aufnahme vor dem Pilot

1. Security- und Hostfreigabe des exakten Kandidaten sowie geschützten eigenen Pilotaccount nachweisen. Vorher keine sensiblen Originale aufnehmen.
2. Originale privat, außerhalb von Git/Actions ablegen: Transaktionshistorie einschließlich Gebühren/Steuern/FX, Konto-/Währungszuordnung, Depotauszug mit Stichtag/Zeitzone, unverwechselbare ISIN/Listing/MIC/Handelswährung, Splits und Dividenden. Rechte am Upload und an zulässigen Kurs-/FX-Originalen dokumentieren.
3. Eigene Accounts je Broker-/Währungskonto anlegen. Keine synthetischen E2E-Fixtures in diesen Account übernehmen. Zuordnungen vor Commit vollständig prüfen.

## Durchlauf und Protokoll

| Schritt | Tatsächlicher Nachweis | Aktuell |
| --- | --- | --- |
| Originale importieren | Raw-ID/Hash, Mapping-Preview, Commit-/Wiederholungsbeleg | AUSSTEHEND |
| Stückzahlen | Auszug ↔ Ledgerposition je Listing und Konto | AUSSTEHEND |
| Cash | Je Währung, einschließlich negativer Salden | AUSSTEHEND |
| Gebühren/Steuern/Käufe/Verkäufe | Originalposten ↔ Buchung, korrigierte/voidierte Version erhalten | AUSSTEHEND |
| Dividenden/Splits | Effektiv-/Zahltage, Faktor und Coverage, keine Doppelbuchung | AUSSTEHEND |
| Kurse und FX | Datum, Währung, Provenienz und Freshness; Broker-Ausführungskurse getrennt von Referenzkursen | AUSSTEHEND |
| CHF-Abgleich | Gemeinsamer Bewertungsstichtag, Stück-/Cash-/Kurs-/FX-Differenzen getrennt, belegter Rest | AUSSTEHEND |
| Korrekturen | Neue nachvollziehbare Version, kein künstlicher Ausgleichsposten | AUSSTEHEND |

Unbekannte Werte bleiben unbekannt. Unterschiedliche Kurszeitpunkte, Broker-FX-Spreads und aufgelaufene Gebühren dürfen nur mit Beleg als Differenzgrund angegeben werden. Ohne Erklärung bleibt der betroffene Abgleich offen.

## Unabhängige Anfängerabnahme

Das bestehende [PR7-Protokoll](ux/PR7_BEGINNER_TEST.md) bleibt vorbereitet, nicht durchgeführt. Eine tatsächlich verfügbare Person soll ohne Einführung Portfolioanlage, Import, Positionsanzeige, Kursproblem, Korrektur, Quellenprüfung und Einstellungen versuchen. Beobachter protokolliert tatsächliche Hürden, Hilfestellungen und Abbrüche. Erst daraus werden konkrete gravierende UX-Blocker abgeleitet. Browserautomation ist kein Ersatz für diese Person.

Nächste Operatoraktion: nach Sicherheits-/Hostfreigabe eigene Originale privat bereitstellen und eine Testperson mit Termin benennen. Dafür werden hier weder Daten erfunden noch erneut bestimmte ISIN vom Nutzer verlangt.
