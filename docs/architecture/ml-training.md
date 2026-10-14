# P7: Training-Vertrag

Normativ: Masterplan 85–103, 157–158. Die lokale Pipeline verwendet ausschließlich gepinnte P6-Datasets. Mehrjährige Fenster entstehen durch `p7-pinned-window-composition-v1`: zwei bis acht originale, chronologisch angrenzende Fenster, höchstens 30'000 Beobachtungen und 16 Kalenderjahre. Universe, Benchmark, Currency, Datenmodus, Kalender, Features, Targets, Code und Dependencies müssen übereinstimmen. Verschachtelte Komposition, Lücken, Überlappungen und widersprüchliche Versionshashes sind gesperrt. Replay überprüft jedes originale Fenster und den zusammengesetzten Content-Hash; keine Neuabfrage von Marktquellen.

`P7DataReadinessService` prüft Originalbytes und Versionshashes sowie Zugehörigkeit, Cutoffs und Werte der Feature-Snapshots. Fehlende finanzielle Pflichtfeatures bleiben unzulässig. `INSUFFICIENT_HISTORY`, `DATA_QUALITY_FAILED`, `RECONSTRUCTED_RESEARCH_ONLY` und `STRICT_PIT_ELIGIBLE` sind getrennt. Synthetische Beobachtungen prüfen den technischen Vertrag, niemals reale Produktionsbelege.

Sechs CPU-Modelle: Logistic Regression, Linear Regression, LightGBM und XGBoost als Classifier/Regressor. NumPy, SciPy und scikit-learn sind gepinnt; XGBoost verwendet die CPU-Distribution. Maximale Baumzahl 150, Tiefe 3, ein numerischer Thread. Modelltyp, Target, Pflichtfeatures, Seed, Fold-Fenster und unveränderte Promotion-Regeln werden vor Start gespeichert.

Skalierung, optionale Median-Imputation und Entfernen konstanter Features lernen ausschließlich TRAIN. Missing-Flags bleiben erhalten; Pflichtfeatures werden nicht imputiert. Eine deterministische Suche über drei Komplexitätsstufen nutzt einen zusätzlichen chronologischen, gepurgten Holdout innerhalb TRAIN. Außenfenster beeinflussen weder Auswahl noch Transformation. Fehlender innerer Holdout bedeutet dokumentierten Default.

Die API stellt begrenzte Jobs in die separate Celery-Queue `ml`. Der optionale Worker läuft mit einer Prozesskonkurrenz, zwei CPUs, 2 GiB und einem Task pro Kindprozess. Roh-Exceptions werden nicht ausgegeben. Ohne ausreichende Fold-Partitionen scheitert Training mit `INSUFFICIENT_PARTITION_HISTORY`.

End-to-End-Abnahme derzeit in Arbeit; keine Phasen- oder Produktionsfreigabe.
