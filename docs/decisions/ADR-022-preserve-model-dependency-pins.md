# ADR-022: Numerische Modell-Pins und ergänzende Assistentenpakete

Datum: 2026-10-15. Status: angenommen nach tatsächlicher Restore-Prüfung.

## Befund

Der P7-Lader prüft den vollständigen Inhalt von `requirements.lock` gegen das unveränderliche Modellartefakt. Die zunächst dort ergänzten Pakete pgvector und pypdf ließen den Restore alter Modelle mit `ARTIFACT_DEPENDENCY_MISMATCH` scheitern. Ein Vergleich der ursprünglichen und erweiterten Lockfiles bestätigte: keine bestehende Paketversion wurde verändert; ausschließlich diese zwei Pakete waren ergänzt.

## Entscheidung

Die bestehenden Core-Eingabe-/Lockfiles bleiben bytegetreu im ursprünglichen Stand. Ergänzende Dokument-/Vektor-Pakete liegen in `requirements-assistant.txt` und `requirements-assistant.lock`. Alle Backendimages installieren erst den numerischen Core, anschließend die Zusatzpakete mit `--no-deps`, danach `pip check`. pgvector verwendet das bereits gepinnte NumPy; es darf keine numerische Abhängigkeit verändern.

Das Codemanifest zeichnet den ergänzenden Lockfile gesondert auf. Die vorhandene exakte Core-Dependency-Prüfung im Modelllader bleibt unverändert. Echte Änderungen am numerischen Core sperren weiterhin alte Modelle. Modellartefakte, Registry-Metadaten und archivierte Prognosen werden nicht umgeschrieben. Dies ist keine Promotion oder fachliche Neubewertung alter Modelle.

## Nachweis

Isolierter Restore muss dasselbe alte Modell mit unverändertem Artefakt- und Core-Dependency-Hash laden, dessen Dataset reproduzieren und zugleich die P10-Originale, Metadaten und Embeddings mit ihren exakten Hashes prüfen. Ein bloß erfolgreich gestarteter Container reicht nicht. Siehe abschließenden P10-Abnahmebericht.
