"""Read-only catalogue, filtering, and recommendation response shaping."""
import json
import re
from pathlib import Path

from backend.recommender.content_recommender import ContentBasedRecommender, destination_key, normalize_text
from backend.recommender.hybrid_recommender import HybridRecommender, DEFAULT_WEIGHTS, SEASONS, TIERS, season_matches


def display_text(value):
    """Remove opaque inline source tokens from display text; retain source records."""
    return re.sub(r"\[web:\d+\]", "", value).strip() if isinstance(value, str) else value


class CatalogueService:
    def __init__(self, path):
        self.records = json.loads(Path(path).read_text(encoding="utf-8"))
        self.by_id = {row["id"]: row for row in self.records}
        self.content = ContentBasedRecommender(self.records)
        self.hybrid = HybridRecommender(self.content)

    def get(self, destination_id):
        if destination_id not in self.by_id:
            raise LookupError("Destination not found.")
        return self.by_id[destination_id]

    def summary(self, row, tier="budget"):
        prefix = TIERS[tier]
        return {"id": row["id"], "name": row["destination_name"].strip(), "state": row["state"],
                "region": row["region"], "description": display_text(row["unique_experiences"]),
                "interests": row["trip_types_clean"], "best_seasons": row["best_seasons"],
                "accessibility": row["accessibility"], "popularity": row["popularity_score"],
                "duration": {"minimum": row["minimum_days"], "ideal": row["ideal_days"], "maximum": row["maximum_days"]},
                "daily_cost": {"low": row[f"{prefix}.total_daily_low"], "high": row[f"{prefix}.total_daily_high"],
                               "currency": "INR", "tier": tier},
                "attractions": row["primary_attractions"], "activities": row["activities_available"],
                "coordinates": {"latitude": row["coordinates.latitude"], "longitude": row["coordinates.longitude"]},
                "duplicate_review": row["duplicate_destination_flag"]}

    def detail(self, destination_id):
        row = self.get(destination_id)
        return self.summary(row) | {key: display_text(row[key]) for key in ["food_scene", "safety_notes", "special_considerations",
                "permits_required", "permits_details", "suggested_itinerary", "last_updated", "data_sources", "avoid_seasons"]}

    def options(self):
        return {"states": sorted({r["state"] for r in self.records}), "regions": sorted({r["region"] for r in self.records}),
                "interests": sorted({t for r in self.records for t in r["trip_types_clean"]}),
                "seasons": sorted(SEASONS), "budget_tiers": list(TIERS), "default_weights": DEFAULT_WEIGHTS,
                "record_count": len(self.records), "destination_count": len({destination_key(r["destination_name"]) for r in self.records})}

    @staticmethod
    def matches(row, filters):
        for key in ["state", "region"]:
            if filters.get(key) and destination_key(row[key]) != destination_key(filters[key]):
                return False
        if filters.get("q"):
            query = normalize_text(filters["q"])
            if query not in normalize_text(" ".join([row["destination_name"], row["state"], row["unique_experiences"]])):
                return False
        if filters.get("interest") and normalize_text(filters["interest"]) not in row["trip_types_clean"]:
            return False
        prefix = TIERS[filters.get("budget_tier", "budget")]
        budget = filters.get("max_daily_budget")
        endpoint = filters.get("budget_endpoint", "high")
        if budget is not None and (row[f"{prefix}.total_daily_{endpoint}"] is None or row[f"{prefix}.total_daily_{endpoint}"] > budget):
            return False
        if filters.get("season") and not (season_matches(row["best_seasons_clean"], filters["season"]) and
                                            not season_matches(row["avoid_seasons_clean"], filters["season"])):
            return False
        if filters.get("days") is not None and not row["minimum_days"] <= filters["days"] <= row["maximum_days"]:
            return False
        return True

    def discover(self, filters):
        rows = sorted((r for r in self.records if self.matches(r, filters)), key=lambda r: (-r["popularity_score"], r["id"]))
        seen, unique = set(), []
        for row in rows:
            key = destination_key(row["destination_name"])
            if key not in seen:
                seen.add(key)
                unique.append(row)
        return unique

    def recommend(self, preferences):
        params = dict(preferences)
        model = params.pop("model", "hybrid")
        state, region = params.pop("state", None), params.pop("region", None)
        top_n = params.pop("top_n", 5)
        # Filter source variants before ranking/deduplication; do not lose an eligible variant.
        eligibility = {"state": state, "region": region}
        if model == "content" and params.get("strict_filters"):
            eligibility |= {"budget_endpoint": "low", "max_daily_budget": params.get("daily_budget"), "season": params.get("season"),
                            "days": params.get("trip_days"), "budget_tier": params.get("budget_tier", "budget")}
        candidate_ids = [r["id"] for r in self.records if self.matches(r, eligibility)]
        if model == "hybrid":
            ranked = self.hybrid.recommend(**params, top_n=len(self.records), candidate_ids=candidate_ids)
        else:
            ranked = self.content.recommend(selected_destination=params.get("selected_destination"),
                                            interests=params.get("interests"), top_n=len(self.records), candidate_ids=candidate_ids)
        recommendations = []
        for scored in ranked.to_dict(orient="records"):
            row = self.get(scored["id"])
            breakdown = ({k: {"score": scored[f"{k}_score"], "weight": scored[f"{k}_weight"],
                               "contribution": scored[f"{k}_contribution"]} for k in DEFAULT_WEIGHTS}
                         if model == "hybrid" else {"content": {"score": scored["similarity_score"], "weight": 1.0,
                                                                  "contribution": scored["similarity_score"]}})
            recommendations.append({"destination": self.summary(row, params.get("budget_tier", "budget")),
                "score": scored["hybrid_score" if model == "hybrid" else "similarity_score"], "breakdown": breakdown})
            if len(recommendations) == top_n:
                break
        return recommendations
