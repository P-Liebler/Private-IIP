"""Bounded aggregate labels; never user IDs, questions, tools arguments or sources."""

from collections import Counter

_operations: Counter[tuple[str, str]] = Counter()
OPERATIONS = {"assistant", "retrieval", "time_machine", "brief_explanation", "scheduler"}


def observe(operation: str, available: bool) -> None:
    if operation not in OPERATIONS:
        raise ValueError("Unknown metric operation")
    _operations[(operation, "available" if available else "unavailable")] += 1


def exposition() -> list[str]:
    return [
        "# TYPE private_iip_intelligence_operations_total counter",
        *[
            f'private_iip_intelligence_operations_total{{operation="{operation}",'
            f'status="{status}"}} {count}'
            for (operation, status), count in sorted(_operations.items())
        ],
    ]
