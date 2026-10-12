"""Deterministic trip drafts grounded in catalogue attractions and activities."""
from backend.recommender.content_recommender import normalize_text
from backend.recommender.hybrid_recommender import TIERS


def build_itinerary(row, days, budget_tier="budget", interests=None):
    phrases = [normalize_text(t) for t in (interests or [])]

    def ordered(values):
        # Stable ordering and exact item deduplication; never invent places.
        values = list(dict.fromkeys(values))
        return sorted(values, key=lambda v: -sum(p in normalize_text(v) for p in phrases))

    attractions = ordered(row["primary_attractions"])
    activities = ordered(row["activities_available"])
    plan = [{"day": d + 1, "title": "Explore at your own pace", "attractions": [], "activities": []} for d in range(days)]
    for field, items, capacity in [("attractions", attractions, 2), ("activities", activities, 1)]:
        for index, item in enumerate(items[:days * capacity]):
            plan[index % days][field].append(item)
    for day in plan:
        if day["attractions"]:
            day["title"] = day["attractions"][0]
    prefix = TIERS[budget_tier]
    low, high = row[f"{prefix}.total_daily_low"], row[f"{prefix}.total_daily_high"]
    warnings = ["A catalogue-based draft: ordering is not route-optimized. Confirm opening hours, transport, permits, and current prices.",
                "Cost ranges are daily catalogue estimates multiplied by days; per-person assumptions and long-distance travel costs are not verified."]
    if not row["minimum_days"] <= days <= row["maximum_days"]:
        warnings.append("Requested days are outside the catalogue's recommended duration range.")
    return {"destination_id": row["id"], "destination_name": row["destination_name"].strip(), "days": plan,
            "estimated_cost": {"low": low * days if low is not None else None,
                               "high": high * days if high is not None else None, "currency": "INR", "tier": budget_tier},
            "source_itinerary": row["suggested_itinerary"], "warnings": warnings,
            "considerations": row["special_considerations"], "permits": row["permits_details"]}
