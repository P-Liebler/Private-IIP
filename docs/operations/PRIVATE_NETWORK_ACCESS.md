# Privater Netzwerkzugang

Nur Caddy veröffentlicht 80/443 auf VPN_BIND_ADDRESS; Default ist 127.0.0.1. Produktionsvorprüfung verwirft Loopback als fehlende Ziel-VPN-Konfiguration sowie Wildcards, öffentliche, Multicast- und Link-local-Adressen. Die Adresse allein beweist keine VPN-Isolation: Interface, Routing und Firewall müssen auf dem wirklichen Host geprüft werden.

PostgreSQL, Valkey, API, MinIO, MLflow und Ollama erhalten keine Hostports. Prometheus 9090/Grafana 3001 binden 127.0.0.1 und bleiben administrativ, gegebenenfalls über einen authentifizierten SSH-Tunnel. Docker-Netze sind keine Berechtigung für andere lokale Administratoren.

Operatorprüfung: mit aktivem VPN privaten DNS-Namen auflösen, HTTPS öffnen, IPv4-/IPv6-Bindings mit `Get-NetTCPConnection`/`ss -lntp` und Docker-Portansicht vergleichen. Danach VPN ausschalten und von einem getrennten Client sowohl Namen als auch direkte Adressen testen: kein Zugriff auf App oder interne Dienste. Auch LAN-Nachbarn und IPv6 prüfen. DNS-Auflösung allein ist kein Nachweis erreichbarer oder unerreichbarer Dienste.

Firewallregeln nur nach ausdrücklicher Operatorfreigabe ändern, mit erhaltenem administrativem Rückweg. Docker kann Linux-Firewallpfade anders als normale Hostprozesse nutzen. Docker dokumentiert, dass vor Engine 28.0.0 auch veröffentlichte Loopback-Ports von L2-Nachbarn erreichbar sein konnten: [Port publishing](https://docs.docker.com/engine/network/port-publishing/), geprüft 19.10.2026. Deshalb fordert Preflight Engine >=28. Windows Docker Desktop/WSL2 und Linux müssen jeweils am tatsächlichen Host von außen geprüft werden. Lokale Compose-Tests schließen dieses Gate nicht.
