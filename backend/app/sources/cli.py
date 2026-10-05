from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import UTC, datetime, time

from app.db.session import get_session_factory
from app.services.sources import SourceService


def parse_review_date(value: str | None) -> datetime | None:
    return datetime.combine(datetime.fromisoformat(value).date(), time.min, UTC) if value else None


async def execute(args: argparse.Namespace) -> None:
    async with get_session_factory()() as db:
        service = SourceService(db)
        if args.command == "list":
            for source in await service.list():
                print(
                    f"{source.slug:12} gate={source.gate_status:8} "
                    f"enabled={source.enabled} trust={source.trust_level} "
                    f"reviewed={source.checked_at} next={source.next_review_at}"
                )
        elif args.command == "review":
            source = await service.review(
                args.slug,
                status=args.status,
                terms_url=args.terms_url,
                scope=args.scope,
                allowed_uses=args.use or [],
                decision_note=args.note,
                decision_by=args.reviewer,
                next_review_at=parse_review_date(args.next_review),
                rate_limit_per_minute=args.rate_limit_per_minute,
            )
            print(f"Reviewed {source.slug}: {source.gate_status}; enabled={source.enabled}")
        elif args.command == "enable":
            source = await service.enable(args.slug)
            print(f"Enabled {source.slug}")
        else:
            source = await service.disable(args.slug)
            print(f"Disabled {source.slug}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Admin-only data source registry")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    review = commands.add_parser("review")
    review.add_argument("slug")
    review.add_argument("--status", required=True, choices=["APPROVED", "BLOCKED", "UNKNOWN"])
    review.add_argument("--terms-url")
    review.add_argument("--scope", required=True)
    review.add_argument("--use", action="append", help="Allowed use, e.g. mapping")
    review.add_argument("--note", required=True)
    review.add_argument("--reviewer", required=True)
    review.add_argument("--next-review", help="YYYY-MM-DD, required for external approval")
    review.add_argument("--rate-limit-per-minute", type=int)
    for command in ("enable", "disable"):
        item = commands.add_parser(command)
        item.add_argument("slug")
    args = parser.parse_args()
    try:
        asyncio.run(execute(args))
    except Exception as error:
        # Avoid printing provider credentials or request bodies in admin errors.
        print(f"Source operation failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
