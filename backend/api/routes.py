"""Versioned REST endpoints with consistent JSON envelopes."""
from flask import Blueprint, current_app, jsonify, request
from werkzeug.exceptions import UnsupportedMediaType

from backend.api.validation import ValidationError, interest_list, number, text, validate_preferences
from backend.services.itinerary import build_itinerary
from backend.recommender.hybrid_recommender import TIERS

api = Blueprint("api", __name__, url_prefix="/api/v1")


def service():
    return current_app.extensions["catalogue"]


def success(data, **meta):
    return jsonify({"data": data, "meta": meta})


def json_body():
    if not request.is_json:
        raise UnsupportedMediaType("Send a JSON body with Content-Type: application/json.")
    body = request.get_json()
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object.")
    return body


@api.get("/options")
def options():
    return success(service().options())


@api.get("/destinations")
def destinations():
    allowed = {"q", "state", "region", "interest", "season", "max_daily_budget", "budget_tier", "days", "page", "limit"}
    if set(request.args) - allowed:
        raise ValidationError("Unknown destination filter parameter.")
    if any(len(request.args.getlist(k)) != 1 for k in request.args):
        raise ValidationError("Filter parameters must not repeat.")
    filters = dict(request.args)
    for key in ["q", "state", "region", "interest"]:
        if key in filters:
            filters[key] = text(filters[key], key)
    for key, maximum in [("max_daily_budget", 1_000_000), ("days", 30), ("page", 1000), ("limit", 100)]:
        if key in filters:
            try:
                value = int(filters[key]) if key in {"page", "limit"} else float(filters[key])
            except ValueError:
                raise ValidationError(f"{key} must be numeric.") from None
            filters[key] = number(value, key, 0.5 if key == "days" else 1, maximum, key in {"page", "limit"})
    normalized = validate_preferences({k: v for k, v in filters.items() if k in {"season", "budget_tier"}})
    filters.update(normalized)
    page, limit = filters.pop("page", 1), filters.pop("limit", 12)
    rows = service().discover(filters)
    offset = (page - 1) * limit
    return success([service().summary(row, filters.get("budget_tier", "budget")) for row in rows[offset:offset + limit]],
                   total=len(rows), page=page, limit=limit)


@api.get("/destinations/<int:destination_id>")
def detail(destination_id):
    return success(service().detail(destination_id))


@api.post("/recommendations")
def recommendations():
    preferences = validate_preferences(json_body())
    rows = service().recommend(preferences)
    warnings = ["Scores express catalogue preference matching, not verified suitability or user satisfaction."]
    if preferences.get("interests"):
        recognized = service().content.vectorizer.transform([" ".join(preferences["interests"])])
        if recognized.nnz == 0:
            warnings.append("Interest terms were not recognized; other active preferences may determine hybrid results.")
    return success(rows, model=preferences.get("model", "hybrid"), count=len(rows), warnings=warnings)


@api.post("/itineraries")
def itineraries():
    body = json_body()
    allowed = {"destination_id", "days", "budget_tier", "interests"}
    if set(body) - allowed or not {"destination_id", "days"}.issubset(body):
        raise ValidationError("Supply destination_id and days, with optional budget_tier and interests.")
    destination_id = number(body["destination_id"], "destination_id", 1, 1_000_000, True)
    days = number(body["days"], "days", 1, 14, True)
    tier = body.get("budget_tier", "budget")
    if not isinstance(tier, str) or tier not in TIERS:
        raise ValidationError("budget_tier must be budget, mid-range, or luxury.")
    interests = interest_list(body.get("interests", []))
    return success(build_itinerary(service().get(destination_id), days, tier, interests))
