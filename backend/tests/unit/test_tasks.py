from app.jobs.tasks import system_ping


def test_system_ping_is_harmless_and_utc() -> None:
    result = system_ping.run()
    assert result["status"] == "ok"
    assert result["executed_at"].endswith("+00:00")
