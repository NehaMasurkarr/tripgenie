"""Small explicit schema validators shared by API endpoints."""
from numbers import Real
import math

from backend.recommender.hybrid_recommender import SEASONS, TIERS, DEFAULT_WEIGHTS
from backend.recommender.content_recommender import normalize_text


class ValidationError(ValueError):
    pass


def number(value, name, minimum, maximum, integer=False):
    valid_type = isinstance(value, int) if integer else isinstance(value, Real)
    if isinstance(value, bool) or not valid_type or not math.isfinite(value) or not minimum <= value <= maximum:
        kind = "integer" if integer else "number"
        raise ValidationError(f"{name} must be a {kind} between {minimum} and {maximum}.")
    return value


def text(value, name, limit=120):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValidationError(f"{name} must be nonempty text of at most {limit} characters.")
    return value.strip()


def interest_list(value):
    if not isinstance(value, list) or len(value) > 20:
        raise ValidationError("interests must be a list of at most 20 phrases.")
    return [text(v, "interest", 60) for v in value]


def validate_preferences(body):
    allowed = {"model", "selected_destination", "interests", "daily_budget", "budget_tier", "season",
               "trip_days", "weights", "top_n", "strict_filters", "state", "region"}
    if set(body) - allowed:
        raise ValidationError(f"Unknown fields: {', '.join(sorted(set(body) - allowed))}.")
    result = dict(body)
    if not isinstance(result.get("model", "hybrid"), str) or result.get("model", "hybrid") not in {"content", "hybrid"}:
        raise ValidationError("model must be content or hybrid.")
    for key, minimum, maximum, integer in [("daily_budget", 1, 1_000_000, False),
                                            ("trip_days", 0.5, 30, False), ("top_n", 1, 20, True)]:
        if key in result:
            number(result[key], key, minimum, maximum, integer)
    if "selected_destination" in result:
        selected = result["selected_destination"]
        if isinstance(selected, str):
            result["selected_destination"] = text(selected, "selected_destination")
        else:
            number(selected, "selected_destination", 1, 1_000_000, True)
    if "interests" in result:
        result["interests"] = interest_list(result["interests"])
    if "strict_filters" in result and not isinstance(result["strict_filters"], bool):
        raise ValidationError("strict_filters must be boolean.")
    for key in ["state", "region"]:
        if key in result:
            result[key] = text(result[key], key)
    if "budget_tier" in result and (not isinstance(result["budget_tier"], str) or result["budget_tier"] not in TIERS):
        raise ValidationError("budget_tier must be budget, mid-range, or luxury.")
    if "season" in result:
        season = normalize_text(text(result["season"], "season"))
        result["season"] = "autumn" if season == "fall" else season
        if result["season"] not in SEASONS:
            raise ValidationError(f"season must be one of {', '.join(sorted(SEASONS))}.")
    if "weights" in result:
        weights = result["weights"]
        if not isinstance(weights, dict) or set(weights) - set(DEFAULT_WEIGHTS):
            raise ValidationError("weights must be an object of known hybrid component names.")
        for key, value in weights.items():
            number(value, f"weights.{key}", 0, 100, False)
        if result.get("model") == "content":
            raise ValidationError("weights apply only to the hybrid model.")
    return result
