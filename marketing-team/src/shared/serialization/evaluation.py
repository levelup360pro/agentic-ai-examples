from typing import Any, Dict

def critique_to_payload(critique: Any, *, include_weights: bool = False) -> Dict[str, Any]:
    # critique is a Critique Pydantic instance; duck-typed to avoid tight coupling
    payload = {
        "average_score": getattr(critique, "average_score", None),
        "meets_threshold": (getattr(critique, "meets_threshold", None) or 0),
        "reasoning": getattr(critique, "reasoning", "") or "",
        "violations": getattr(critique, "violations", []) or [],
        "scores": getattr(critique, "scores", {}),  # {"brand_voice":..., "structure":..., "accuracy":...}
    }
    if include_weights:
        payload["weights"] = getattr(critique, "weights", {}) or {}
    return payload