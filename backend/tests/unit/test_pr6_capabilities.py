import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import Response

from app.api.auth import capabilities


def test_capabilities_do_not_infer_permissions_from_other_operator_roles():
    settings = SimpleNamespace(
        data_operator_usernames=["data-user"],
        ml_operator_usernames=["model-user"],
        operations_operator_usernames=["host-user"],
    )
    response = Response()
    with patch("app.api.auth.get_settings", return_value=settings):
        result = asyncio.run(
            capabilities(response, SimpleNamespace(user=SimpleNamespace(username="data-user")))
        )
    assert result == {
        "data_operator": True,
        "ml_operator": False,
        "operations_operator": False,
    }
    assert response.headers["Cache-Control"] == "no-store"


def test_regular_user_has_no_operator_visibility():
    settings = SimpleNamespace(
        data_operator_usernames=[], ml_operator_usernames=[], operations_operator_usernames=[]
    )
    with patch("app.api.auth.get_settings", return_value=settings):
        result = asyncio.run(
            capabilities(Response(), SimpleNamespace(user=SimpleNamespace(username="reader")))
        )
    assert result and not any(result.values())
