# Target Definitions

P6. Versionierte Targets stehen getrennt neben Feature-Snapshots im unveränderlichen Dataset. Klassifikation: Outperformance gegenüber Benchmark über 30 oder 90 Instrument-Sessions. Regression: 30-Session Excess Return und realisierte 30-Session-Volatilität; derselbe Vertrag unterstützt 90 Sessions.

Signal verwendet Schlussinformationen von Session t; Entry frühestens nächster Open t+1. End t+30 beziehungsweise t+90. Die inklusive Entry-/End-Reihe enthält exakt 30/90 Sessions. Instrument und Benchmark müssen passende vollständige Session-Beobachtungen, echte Opens, gleiche dokumentierte Basiswährung, validierte FX und Action Coverage besitzen. Kein Benchmark-Ersatz und keine Open-Schätzung.

Gross Total Return aus rohen Preisen und expliziten Actions; Target-Index reinvestiert Dividenden am Ex-Date. Native Index-Rendite wird mittels belegter Entry-/End-FX in die Basiswährung übersetzt. Outperformance = Instrument Return − Benchmark Return; Label 1 bei strikt positiver Differenz, sonst 0. Realisierte Volatilität ist Sample-Std der vollständigen Basiswährungs-Sessionrenditen × sqrt(252), inklusive erster Open→Close-Session. Fehlende Inputs setzen das jeweilige Target aus.

`signal_as_of`, `label_start`, `label_end`, `label_available_at`, Definitionsversion und exakte Inputversionen werden gespeichert. Label ist frühestens nach dem realisierten Fenster und der erforderlichen eigenen Beobachtung verfügbar. Ein historisch datierter Preis, der erst heute importiert wurde, macht kein früher verfügbares Label. Targets sind niemals Bestandteil von `features` und werden vom Strategie-Ranking nicht gelesen.
