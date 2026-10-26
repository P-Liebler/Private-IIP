export const sourceExplanations: Record<string, string> = {
  ECB: "Tägliche EUR-Referenzkurse für unterstützte Währungspaare. Keine Aktienkurse.",
  SNB: "Unterstützte monatliche Makro- und FX-Referenzen. Kein Ersatz für tägliche Portfolio-Wechselkurse.",
  SEC_EDGAR: "Unternehmensmeldungen und XBRL-Fundamentaldaten von US-Filern. Keine Börsenkurse.",
  OPENFIGI: "Kandidaten für ISIN-/Ticker-/FIGI-Zuordnungen. Börse und Handelswährung müssen geprüft werden; keine Kurse.",
  ALPHAVANTAGE: "Begrenzte tägliche OHLCV für ausdrücklich zugeordnete Instrumente. Kostenloser Umfang und Archivierung müssen freigegeben sein.",
  COMPANY_IR: "Einzeln geprüfte Originalberichte und Dateiverträge eines Emittenten. Kein universeller Website-Crawler.",
  NEWS_RSS: "Metadaten und Links aus einzeln freigegebenen Feeds. Kein automatisch erlaubtes Volltextarchiv.",
  YAHOO: "Gewünschte priorisierte Kursquelle. Automatischer Abruf bleibt ohne ausdrückliche passende Erlaubnis gesperrt.",
  STOOQ: "Mögliche historische Kursquelle; Nutzungs- und Speicherrechte sind noch nicht geklärt.",
  MANUAL_CSV: "Eigene zulässige Kurs-, FX- und Transaktionsdateien mit Vorschau und ausdrücklicher Übernahme.",
  MANUAL_DOCUMENTS: "Eigene Dokumente unter separater Quellen- und dokumentbezogener Speicher-/Indexfreigabe.",
  MANUAL_RESEARCH: "Manuell belegte Fundamentaldaten; keine automatisch nachgewiesene historische Verfügbarkeit.",
};
