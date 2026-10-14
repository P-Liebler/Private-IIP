# Execution Time Contract

P6, version next-session-v1. Jede Signal-/Orderbeobachtung trägt signal_generated_at, information_cutoff_at, tradable_at, execution_price_type und den erst beim Fill gesetzten execution_price_timestamp. Default NEXT_OPEN; optional versionierte NEXT_CLOSE. Kein Preis aus derselben zur Entscheidung verwendeten Schlussbeobachtung.

Decision-Quantity wird ausschließlich aus signalbekanntem Close, FX, Cash und Positionslimit bestimmt. Morgen-Open ist nur realisiertes Fill-Outcome. Ein Fill erfordert timestamp strikt nach signal_generated_at, mindestens tradable_at, eine echte geöffnete Session und einen validierten positiven passenden Preis. Seine FX-Referenz wird separat zum Ausführungszeitpunkt geprüft; eine erst später bekannte Tagesrate darf keine frühere Open-Ausführung bewerten. Missing Open wird NO_FILL, niemals vorheriger Close. Verkäufe werden vor Käufen abgearbeitet; Käufe werden bei nicht ausreichendem Cash als explizite Teilfills begrenzt, kein Leverage. Auch eine Verkaufsgebühr darf kein Margin-Cash erzeugen.

Bei Exchange-Mischung entsteht das gemeinsame tägliche Signal erst nach dem spätesten verwendeten Informationscutoff. Jede Instrument-Ausführung bleibt an ihren eigenen nächsten Handelstermin gebunden. Zukünftige Labels oder Ausführungspreise gehören nicht zum Ranking-Input.

Orders außerhalb des gepinnten Bewertungsfensters werden nicht weitergetragen und als NO_FILL ausgewiesen. Ungeklärte Actions, fehlende FX oder fehlende Bewertung machen einen Run unvollständig. Synthetische Timing-Tests und Golden-Fills prüfen Same-Close-Ablehnung, Next-Open-Zulässigkeit, Kosten, Splits und Dividenden.
