# ADR-018: Lokale Modelle und unveränderliche Freigaben

Status: Accepted · 2026-10-14

P7 verwendet lokale CPU-Modelle auf gepinnten P6-Datasets mit zeitlichem Train/Validation/Calibration/Test-Vertrag. MLflow ist ein optionaler privater Tracking-Dienst. Datenbasierte Artefakte mit überprüften SHA-256 ersetzen unsichere fremde Pickle-Uploads.

Eine feste, versionierte Freigaberubrik und ein berechtigtes Operator-Review sind erforderlich. Synthetische/reconstructed Evidenz, unzureichende Stichproben, mangelhafte Kalibrierung und fehlende Kosten-Backtests lassen sich nicht durch einen guten Gesamtscore überstimmen. Produktionsprognosen, Abstentionen und Ergebnisversionen bleiben unveränderlich. Degradierte Modelle benötigen neue Evidenz und eine neue Modellversion; keine automatische Wiederfreigabe.

Konsequenz: technische Funktionsfähigkeit kann mit SHADOW-Modellen abgenommen werden. Ein reales validiertes V2-Produkt wird erst nach bestandenen Produktionsgates behauptet. Quantitative Modelle entscheiden, ein späterer LLM erklärt.
