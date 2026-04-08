from __future__ import annotations

from statistics import median


DEFAULT_WEIGHTS = {
    "speed": 10.0,
    "chat": 20.0,
    "instruction": 10.0,
    "code": 20.0,
    "tool": 15.0,
    "long_context": 15.0,
    "vision": 10.0,
}


def redistribute_vision_weight(weights: dict[str, float]) -> dict[str, float]:
    vision = weights["vision"]
    remaining_total = 100.0 - vision
    out: dict[str, float] = {}
    for key, value in weights.items():
        if key == "vision":
            continue
        out[key] = value * 100.0 / remaining_total
    return out


def median_or_single(values: list[float]) -> float:
    return values[0] if len(values) == 1 else float(median(values))


def compute_overall_score(
    dimension_scores: dict[str, float],
    is_vision_capable: bool,
    weights: dict[str, float] | None = None,
) -> float:
    weights = weights or DEFAULT_WEIGHTS
    effective = weights if is_vision_capable else redistribute_vision_weight(weights)
    total = 0.0
    for key, weight in effective.items():
        total += dimension_scores.get(key, 0.0) * (weight / 100.0)
    return round(total, 2)
