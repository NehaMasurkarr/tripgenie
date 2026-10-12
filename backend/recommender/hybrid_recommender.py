"""Explainable metadata/content hybrid; no collaborative filtering or Flask state."""
from numbers import Real
import re

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .content_recommender import ContentBasedRecommender, destination_key, normalize_text


DEFAULT_WEIGHTS = {"content": 0.30, "popularity": 0.10, "interests": 0.20,
                   "budget": 0.15, "season": 0.15, "duration": 0.10}
SEASONS = {"winter", "summer", "spring", "autumn", "monsoon", "post monsoon"}
INTEREST_ALIASES = {"cultural": "culture", "waterfall": "waterfalls",
                    "short treks": "short trek", "backpacker": "backpacking"}
TIERS = {"budget": "budget_category", "mid-range": "mid_range_category", "luxury": "luxury_category"}


def positive_number(value, name):
    if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number.")
    return float(value)


def season_matches(labels, season):
    """Conservative phrase matching, without treating post-monsoon as monsoon.

    Conditional prose remains a heuristic signal, not verified travel guidance.
    Avoid matches take precedence over best-season matches in scoring.
    """
    for label in labels:
        text = normalize_text(label)
        if season == "monsoon":
            text = re.sub(r"\b(?:post|pre) monsoon\b", "", text)
        if re.search(r"\b" + re.escape(season) + r"\b", text):
            return True
    return False


class HybridRecommender:
    """Reuse an already fitted ContentBasedRecommender for personalized ranking."""

    def __init__(self, content_recommender):
        if not isinstance(content_recommender, ContentBasedRecommender):
            raise ValueError("Supply a fitted ContentBasedRecommender.")
        self.content = content_recommender
        self.catalogue = content_recommender.catalogue
        required = {"popularity_score", "minimum_days", "maximum_days", "best_seasons_clean", "avoid_seasons_clean"}
        required |= {f"{prefix}.total_daily_{end}" for prefix in TIERS.values() for end in ["low", "high"]}
        if not required.issubset(self.catalogue.columns):
            raise ValueError(f"Missing hybrid fields: {sorted(required - set(self.catalogue.columns))}")
        for field in ["best_seasons_clean", "avoid_seasons_clean", "trip_types_clean"]:
            if not self.catalogue[field].map(lambda v: isinstance(v, list) and all(isinstance(t, str) for t in v)).all():
                raise ValueError(f"{field} must contain lists of strings.")
        self._names = self.catalogue.destination_name.map(destination_key)

    @classmethod
    def from_json(cls, path):
        return cls(ContentBasedRecommender.from_json(path))

    def recommend(self, selected_destination=None, interests=None, daily_budget=None,
                  budget_tier="budget", season=None, trip_days=None, weights=None,
                  top_n=5, strict_filters=False):
        """Rank catalogue entries with bounded component scores and contributions.

        daily_budget is in dataset units per day for the requested tier.
        Missing preferences deactivate their components; active weights normalize
        to sum to one. Unrecognized interest terms produce zero interest/content
        matches; other requested preferences and popularity can still rank entries.
        strict_filters enforces budget lower endpoint, duration range, and positive
        season match with no avoid-season match. Otherwise all are soft signals.
        """
        if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
            raise ValueError("top_n must be a positive integer.")
        if not isinstance(strict_filters, bool):
            raise ValueError("strict_filters must be boolean.")
        if budget_tier not in TIERS:
            raise ValueError(f"budget_tier must be one of {list(TIERS)}.")
        daily_budget = positive_number(daily_budget, "daily_budget") if daily_budget is not None else None
        trip_days = positive_number(trip_days, "trip_days") if trip_days is not None else None
        if interests is None:
            interest_tags = []
        elif isinstance(interests, (list, tuple)) and all(isinstance(v, str) and normalize_text(v) for v in interests):
            interest_tags = list(dict.fromkeys(INTEREST_ALIASES.get(normalize_text(v), normalize_text(v)) for v in interests))
        else:
            raise ValueError("interests must be a list/tuple of nonempty interest phrases.")
        if season is not None:
            if not isinstance(season, str):
                raise ValueError("season must be a supported season string.")
            season = normalize_text(season)
            if season == "fall":
                season = "autumn"
            if season not in SEASONS:
                raise ValueError(f"Supported seasons: {sorted(SEASONS)}.")
        configured = DEFAULT_WEIGHTS.copy()
        if weights is not None:
            if not isinstance(weights, dict) or set(weights) - set(DEFAULT_WEIGHTS):
                raise ValueError(f"weights must map known components: {list(DEFAULT_WEIGHTS)}.")
            configured.update(weights)
        for key, value in configured.items():
            if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value) or value < 0:
                raise ValueError(f"Weight {key} must be finite and nonnegative.")
        active = {"content": selected_destination is not None or bool(interest_tags), "popularity": True,
                  "interests": bool(interest_tags), "budget": daily_budget is not None,
                  "season": season is not None, "duration": trip_days is not None}
        total_weight = sum(configured[k] for k in configured if active[k])
        if total_weight <= 0:
            raise ValueError("At least one active component needs a positive weight.")
        effective = {k: configured[k] / total_weight if active[k] else 0.0 for k in configured}
        result = self.catalogue[["id", "destination_name", "state", "region", "trip_types_clean",
                                 "popularity_score", "minimum_days", "ideal_days", "maximum_days",
                                 "best_seasons_clean", "avoid_seasons_clean"]].copy().rename(columns={"popularity_score": "popularity_rating"})
        component = {k: np.zeros(len(result)) for k in DEFAULT_WEIGHTS}
        excluded_name = None
        content_signals = []
        if selected_destination is not None:
            position = self.content._destination_position(selected_destination)
            excluded_name = self._names.iloc[position]
            content_signals.append(cosine_similarity(self.content.tfidf_matrix[position], self.content.tfidf_matrix).ravel())
        if interest_tags:
            query_vector = self.content.vectorizer.transform([" ".join(interest_tags)])
            content_signals.append(cosine_similarity(query_vector, self.content.tfidf_matrix).ravel())
            requested = set(interest_tags)
            component["interests"] = self.catalogue.trip_types_clean.map(lambda tags: len(requested & set(tags)) / len(requested)).to_numpy()
        if content_signals:
            component["content"] = np.mean(content_signals, axis=0)
        popularity = pd.to_numeric(self.catalogue.popularity_score, errors="coerce")
        known = popularity.dropna()
        if len(known):
            span = known.max() - known.min()
            component["popularity"] = ((popularity - known.min()) / span).fillna(0).to_numpy() if span else popularity.notna().astype(float).to_numpy()
        prefix = TIERS[budget_tier]
        low = pd.to_numeric(self.catalogue[f"{prefix}.total_daily_low"], errors="coerce")
        high = pd.to_numeric(self.catalogue[f"{prefix}.total_daily_high"], errors="coerce")
        result["daily_cost_low"] = low
        result["daily_cost_high"] = high
        eligible = pd.Series(True, index=result.index)
        if daily_budget is not None:
            valid_cost = low.notna() & high.notna() & low.ge(0) & high.ge(low) & high.gt(0)
            component["budget"] = (daily_budget / high.where(valid_cost)).clip(0, 1).fillna(0).to_numpy()
            if strict_filters:
                eligible &= valid_cost & low.le(daily_budget)
        if season is not None:
            best = self.catalogue.best_seasons_clean.map(lambda labels: season_matches(labels, season))
            avoid = self.catalogue.avoid_seasons_clean.map(lambda labels: season_matches(labels, season))
            component["season"] = (best & ~avoid).astype(float).to_numpy()
            if strict_filters:
                eligible &= best & ~avoid
        if trip_days is not None:
            ideal = pd.to_numeric(self.catalogue.ideal_days, errors="coerce")
            component["duration"] = (np.minimum(ideal, trip_days) / np.maximum(ideal, trip_days)).where(ideal.gt(0), 0).fillna(0).to_numpy()
            if strict_filters:
                eligible &= pd.to_numeric(self.catalogue.minimum_days, errors="coerce").le(trip_days)
                eligible &= pd.to_numeric(self.catalogue.maximum_days, errors="coerce").ge(trip_days)
        for key in DEFAULT_WEIGHTS:
            result[f"{key}_score"] = np.clip(component[key], 0, 1)
            result[f"{key}_weight"] = effective[key]
            result[f"{key}_contribution"] = result[f"{key}_score"] * effective[key]
        result["hybrid_score"] = result[[f"{key}_contribution" for key in DEFAULT_WEIGHTS]].sum(axis=1)
        result["_name_key"] = self._names
        if excluded_name is not None:
            eligible &= self._names.ne(excluded_name)
        return (result.loc[eligible & result.hybrid_score.gt(0)]
                .sort_values(["hybrid_score", "id"], ascending=[False, True], kind="stable")
                .drop_duplicates("_name_key").head(top_n).drop(columns="_name_key").reset_index(drop=True))
