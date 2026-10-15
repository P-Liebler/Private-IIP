from decimal import Decimal
from typing import Any

from app.recommendations.contracts import WEIGHTS

D = Decimal


def score(components: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(k for k in WEIGHTS if k != "momentum" and components.get(k) is None)
    if missing:
        return {"score": None, "components": {}, "missing_inputs": missing}
    result, total = {}, D(0)
    for name, weight in WEIGHTS.items():
        value = components.get(name)
        if value is None:
            result[name] = {"status": "OPTIONAL_UNAVAILABLE", "value": None, "weight": weight}
            continue
        number = D(str(value))
        if not number.is_finite():
            raise ValueError("Non-finite scoring input")
        number = max(D(0), min(D(100), number))
        contribution = number * D(weight)
        result[name] = {
            "status": "AVAILABLE",
            "value": str(number),
            "weight": weight,
            "contribution": str(contribution),
        }
        total += contribution
    return {"score": str(total), "components": result, "missing_inputs": []}
