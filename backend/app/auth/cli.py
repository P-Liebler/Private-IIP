from __future__ import annotations

import argparse
import asyncio
import getpass
import sys

from app.db.session import get_session_factory
from app.services.auth import AuthService


async def _create_user(username: str, password: str) -> None:
    async with get_session_factory()() as db:
        user = await AuthService(db).create_user(username, password)
    print(f"Created user {user.username}")


async def _reset_totp(username: str) -> None:
    async with get_session_factory()() as db:
        found = await AuthService(db).reset_totp(username)
    if not found:
        raise ValueError("User does not exist")
    print("TOTP reset; all sessions revoked")


def main() -> None:
    parser = argparse.ArgumentParser(description="Private account administration")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-user", help="Create a private account")
    create.add_argument("username", nargs="?")
    reset = commands.add_parser("reset-totp", help="Reset TOTP and revoke all sessions")
    reset.add_argument("username", nargs="?")
    args = parser.parse_args()
    username: str = args.username or input("Username: ").strip()
    try:
        if args.command == "create-user":
            password = getpass.getpass("Password (at least 12 characters): ")
            if password != getpass.getpass("Repeat password: "):
                raise ValueError("Passwords do not match")
            asyncio.run(_create_user(username, password))
        else:
            confirmation = input(f"Reset TOTP and revoke all sessions for {username}? Type RESET: ")
            if confirmation != "RESET":
                raise ValueError("Reset cancelled")
            asyncio.run(_reset_totp(username))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
