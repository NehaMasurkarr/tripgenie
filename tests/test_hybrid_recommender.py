import numpy as np
import pandas as pd
import pytest
from sklearn.metrics.pairwise import cosine_similarity

from backend.recommender.content_recommender import ContentBasedRecommender
from backend.recommender.hybrid_recommender import DEFAULT_WEIGHTS, HybridRecommender, season_matches


def make_model():
    rows = []
    for id_, name, text, popularity, tags, best, avoid in [
        (1, "Anchor", "beach ocean island", 4, ["beach"], ["winter"], []),
        (2, "Island", "beach ocean diving", 10, ["beach", "diving"], ["winter"], []),
        (3, " ISLAND ", "beach island surfing", 7, ["beach"], ["winter"], ["peak winter"]),
        (4, "Forest", "forest wildlife safari", 6, ["wildlife"], ["post monsoon"], [])]:
        row = dict(id=id_, destination_name=name, state="Test", region="Test", tfidf_text=text,
                   trip_types_clean=tags, popularity_score=popularity, minimum_days=2, ideal_days=3,
                   maximum_days=5, best_seasons_clean=best, avoid_seasons_clean=avoid)
        for tier in ["budget_category", "mid_range_category", "luxury_category"]:
            row[f"{tier}.total_daily_low"] = 100
            row[f"{tier}.total_daily_high"] = 200
        rows.append(row)
    return HybridRecommender(ContentBasedRecommender(rows))


def test_component_arithmetic_and_duplicate_exclusion():
    model = make_model()
    results = model.recommend(selected_destination=1, interests=["beach"], daily_budget=100,
                              season="winter", trip_days=6)
    assert results.destination_name.str.strip().str.casefold().is_unique
    assert "anchor" not in results.destination_name.str.casefold().tolist()
    row = results.loc[results.id.eq(2)].iloc[0]
    assert row.budget_score == 0.5
    assert row.duration_score == 0.5
    assert row.popularity_score == 1
    assert row.interests_score == 1 and row.season_score == 1
    destination = cosine_similarity(model.content.tfidf_matrix[0], model.content.tfidf_matrix).ravel()
    interests = cosine_similarity(model.content.vectorizer.transform(["beach"]), model.content.tfidf_matrix).ravel()
    assert np.isclose(row.content_score, (destination[1] + interests[1]) / 2)
    assert np.isclose(row.hybrid_score, sum(row[f"{k}_score"] * w for k, w in DEFAULT_WEIGHTS.items()))


def test_only_active_weights_count_and_override_changes_ranking():
    model = make_model()
    results = model.recommend()
    assert results.popularity_weight.eq(1).all()
    assert results.iloc[0].id == 2
    weights = {k: 0 for k in DEFAULT_WEIGHTS} | {"interests": 1}
    wildlife = model.recommend(interests=["wildlife"], weights=weights)
    assert wildlife.id.tolist() == [4]
    assert wildlife.iloc[0].hybrid_score == 1
    pd.testing.assert_frame_equal(wildlife, model.recommend(interests=["wildlife"], weights=weights))


def test_season_avoid_precedence_and_strict_filters():
    model = make_model()
    assert not season_matches(["post monsoon", "pre monsoon"], "monsoon")
    assert season_matches(["post-monsoon"], "post monsoon")
    assert season_matches(["early winter"], "winter")
    strict = model.recommend(season="winter", daily_budget=100, trip_days=3, strict_filters=True)
    assert set(strict.id) == {1, 2}
    assert strict.season_score.eq(1).all()
    assert model.recommend(daily_budget=99, strict_filters=True).empty
    assert model.recommend(trip_days=6, strict_filters=True).empty


def test_missing_budget_is_not_affordable_and_interest_oov_is_explicit():
    model = make_model()
    model.catalogue.loc[model.catalogue.id.eq(4), "budget_category.total_daily_high"] = np.nan
    weights = {k: 0 for k in DEFAULT_WEIGHTS} | {"budget": 1}
    results = model.recommend(daily_budget=100, weights=weights)
    assert 4 not in results.id.tolist()
    oov = model.recommend(interests=["zzzxxyyqqq"])
    assert oov.content_score.eq(0).all() and oov.interests_score.eq(0).all()
    assert len(oov) > 0  # popularity still active, as documented


@pytest.mark.parametrize("arguments", [
    {"weights": {k: 0 for k in DEFAULT_WEIGHTS}}, {"weights": {"content": -1}},
    {"weights": {"content": float("nan")}}, {"weights": {"bogus": 1}},
    {"weights": {"content": "high"}}, {"daily_budget": 0}, {"daily_budget": "3000"},
    {"trip_days": -1}, {"season": "january"}, {"interests": "beach"},
    {"interests": [""]}, {"top_n": 0}, {"budget_tier": "cheap"}, {"strict_filters": "yes"}])
def test_invalid_preferences_rejected(arguments):
    with pytest.raises(ValueError):
        make_model().recommend(**arguments)
