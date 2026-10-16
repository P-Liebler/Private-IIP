# Historische Finanzdaten

Stand 2026-10-16. P6 bleibt der normative Verfügbarkeitsvertrag. PR1 führt keine konkurrierende PIT-Klassifikation ein.

| Fachlicher Begriff | Bestehende Evidenz | Bedeutung |
| --- | --- | --- |
| PUBLIC_HISTORICAL | VERIFIED_PUBLIC_TIMESTAMP / VERIFIED_SOURCE_DOCUMENT | Dokumentierter öffentlicher Zeitpunkt; eigener Review-Zeitpunkt bleibt separat |
| LOCAL_ARCHIVED | LOCAL_FIRST_OBSERVATION | Wirklicher Empfang und Archivierung; nicht rückdatierbar |
| RECONSTRUCTED_HISTORICAL | P6 RECONSTRUCTED_HISTORICAL-Modus | Späterer historischer Import, keine damals betriebene App suggerieren |
| UNVERIFIED | UNVERIFIED / USER_ASSERTED ohne ausreichenden Beleg | Kein Strict-PIT-Nachweis |

Beobachtungstag, ursprüngliche Veröffentlichung, tatsächlicher lokaler Empfang und Review-Datum unterscheiden. Ein 2026 importierter Kurs von 2021 ist nicht 2021 lokal archiviert. Ein heute geladener SNB-Cube liefert keinen historischen Publikationszeitpunkt jeder Beobachtung. Monatliche Referenz-FX bleiben Makrodaten, keine täglichen Bewertungskurse. Makroversionen erhalten Frequenz, Quellserie, belegtes Release-Datum oder null und Revisionsart; fehlende Originalvintages bleiben rekonstruiert.

Raw-Antworten vor Parsing archivieren. Gleiche Beobachtungen erzeugen keine unnötigen kanonischen Versionen; Korrekturen hängen Versionen an. Rohpreise, Adjusted-Referenzen und Total-Return-Berechnungen trennen. Raw Close plus explizite Actions verhindert Doppelzählung. Fehlendes Open bleibt NO_FILL. Keine Nullrenditen für Kurslücken.

Coverage beruht auf P6-Kalendern, Sitzungsschluss inklusive Frühschluss und Publikationspuffer, tatsächlichen Versionen und zeitgerechten Prüfbelegen. `STRICT_PIT_READY` verlangt zusätzlich historischen FX- und Membership-Nachweis. Dieser Datenstatus ist keine Modellfreigabe. Dataset-/Modell-/Prediction-/Recommendation-Archive bleiben gepinnt und unverändert; neue Daten ändern nur neue Berechnungen. Reale Prognosen beginnen mit realem Modellbetrieb, nicht mit dem Anfang eines Backfills.

Heute aktive Instrumente sind kein historisches Universe. Inception, Delisting, Identifierintervalle, entfernte Mitglieder und vollständige Universe-Evidenz prüfen. OpenFIGI inklusive unlisted unterstützt Identität, ersetzt diese Belege aber nicht.
