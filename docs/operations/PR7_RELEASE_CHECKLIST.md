# PR7 – getrennte Freigabecheckliste

Stand 27.10.2026. **NOT_RELEASED / SECURITY_NOT_APPROVED**.

- [x] Ausgangscommit und beide tatsächlichen Remotefehler geprüft; origin/main erneut unverändert.
- [x] Begrenzte offizielle DB-Beschaffung und validierter Cache; frischer Download am 27.10.
- [x] Supporting-Patches und getrennte historische Lockarchive; numerische Core-Pins unverändert.
- [x] 306 Backend-/67 Hosttests, Ruff/Format/Mypy, Frontend-Lint/Typecheck/Standalone-Build.
- [x] Vollständiger neuer Browserlauf29/29 ohne Skips; Normalmodus und Rollen danach geprüft.
- [x] Alle 14 exakten Images mit aktueller27.10.-DB gescannt und alle 14 SBOMs formal validiert.
- [x] Allgemeines wiederaufnehmbares Migrationstool,683 Originaleinträge/323 DB-Referenzen und unveränderte Quelle.
- [x] Separate Versionen-/Delete-Marker-Probe; Auth-/Policy-/Retention-/gRPC-Probes und echte Appadapter.
- [x] MLflow, native RAG/Erklärung, optionaler LLM-Ausfall und private Monitoringkompatibilität.
- [x] DB-/Storage-Readinessausfall und Golden-Recovery; falsche Credentials/widerrufene Session abgewiesen.
- [x] Vollständiger Zielrestore1381 Hashes, alte Archive/separate PR6-Hashes, Legacyprüfung und Cleanup.
- [x] Expliziter alter Goldenstichtag und heutige STALE_PRICE-Sperre; kein künstliches Auffrischen.
- [x] Gezielte Tests der reparierten primären Aktionen und dokumentierte kalte/warme Messgrenzen.
- [ ] Verbleibende Critical-/High-Befunde, native Build-/Advisorygrenzen, CSP und vollständige Expositionsentscheidung schließen.
- [ ] Vollständige Fehlerraum-/Rechte-/Recoveryabnahme aller PARTIAL-Seiten über den belegten Testumfang hinaus.
- [ ] Unabhängige Anfängerperson: PENDING_USER_TEST.
- [ ] Quellenoperator, echte kleine Liveabnahme und spätere Aktualisierung: BLOCKED.
- [ ] Reale Brokeroriginale, eigener echter Pilotaccount und belegter CHF-/Auszugsabgleich.
- [ ] Zielhost/VPN/OS-Client-CA, unabhängiger Backupzeitplan und Schlüsselrecovery.
- [ ] Separate Security-/Operatorfreigabe eines unveränderlichen Deploymanifests.
- [ ] Nach autorisiertem Push vollständige neue Remote-CI.

Jeder geänderte Build braucht eigene passende Belege. Source-, Modell-, Strategie-,
Host- und Securitygates bleiben unabhängig. Lokale QA und C:-Backups erteilen
keine Produktions-, Quellen- oder Finanzfreigabe.
