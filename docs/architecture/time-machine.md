# Financial Time Machine

Die Time Machine liest Archive. Sie erzeugt keine historischen Prognosen und ergänzt keinen damaligen Wissensstand mit späteren Modellen.

## STRICT_PIT

Publikations-/Known-, Observed-, Retrieved- und Created-Zeit müssen, soweit vorhanden, vor dem ausgewählten UTC-Cutoff liegen. Portfolio: P4-Ledger-Replay mit damaligen Transaktionsversionen. Preise: datierte Versionsköpfe einschließlich abgelehnter oder widersprüchlicher Beobachtungen, kein Rückfall auf ältere gute Werte. Fundamentals/Estimates: damals bekannte Versionsköpfe; spätere Restatements ersetzen frühere Ansichten nicht. Originalbytes werden vor Anzeige von Originalbelegen per SHA geprüft.

Research-, Risiko- und Recommendation-Snapshots müssen tatsächlich damals existiert haben. Prognosen benötigen zusätzlich damaligen Generated-/Information-Cutoff und damals existierende eigene Modelle; selbst ein heute mit altem Informations-Cutoff erzeugtes Ergebnis ist keine historische Prognose. Spätere Outcomes stehen in einem gesonderten Abschnitt außerhalb des damaligen Wissensstands. Private Dokumente erfordern ebenfalls damalige erste Beobachtung und Erstellung.

Legacy-P5-News-Mappings haben keinen ursprünglichen Erstellungszeitpunkt. Solche Artikel können als belegtes Artikelarchiv erscheinen, aber ihre damalige Instrumentzuordnung bleibt `HISTORICAL_AVAILABILITY_UNVERIFIED`. Aktuelle Instrumentmetadaten werden bei späterer Änderung nicht als damalige Stammdaten angezeigt.

## RECONSTRUCTED_HISTORICAL

Strikte Abschnitte bleiben unverändert. Ein gesonderter, deutlich markierter Abschnitt zeigt später importierte Preis-/Fundamentalversionen für frühere Handelstage/Berichtsperioden. Er behauptet keine ursprüngliche PIT-Verfügbarkeit. Dokumente, Estimates, Modelle, Prognosen und Empfehlungen werden nicht zurückdatiert. Keine Archivansicht schreibt Daten.

Zustände: `HISTORICAL_DATA_UNAVAILABLE`, `HISTORICAL_AVAILABILITY_UNVERIFIED`, `NOT_ARCHIVED_AT_SELECTED_DATE`, `NO HISTORICAL PREDICTION`. Spätere Importe, fehlende Originale, unbekannte Metadaten oder fehlende Snapshots bleiben sichtbare Lücken. Antworten sind begrenzt; Detailarchive haben keine unbegrenzte Vollhistoriengarantie. Historische Portfolio-Replays setzen die bereits in P4/P6 dokumentierten Daten-/Kalender-/Corporate-Action-Nachweise voraus.
