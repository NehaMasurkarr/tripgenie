"""Behavioral checks using a small catalogue with known similarities."""
import copy

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics.pairwise import cosine_similarity

from backend.recommender.content_recommender import ContentBasedRecommender


def catalogue():
    return [dict(id=i, destination_name=name, state=state, region="Test", trip_types_clean=[text],
                 ideal_days=2, tfidf_text=text) for i, name, state, text in [
                     (1, "Anchor", "A", "beach ocean diving"),
                     (2, " Anchor ", "A", "beach ocean diving island"),
                     (3, "Island", "B", "beach ocean island"),
                     (4, "ISLAND", "B", "ocean island diving"),
                     (5, "Forest", "C", "forest wildlife safari"),
                     (6, "Coast", "B", "beach ocean surfing")]]


def test_scores_duplicate_exclusion_and_source_preservation():
    records = catalogue()
    original = copy.deepcopy(records)
    model = ContentBasedRecommender(records)
    results = model.recommend(1)
    assert records == original
    assert results.destination_name.str.strip().str.casefold().is_unique
    assert "anchor" not in results.destination_name.str.strip().str.casefold().tolist()
    expected = cosine_similarity(model.tfidf_matrix[0], model.tfidf_matrix).ravel()
    island = results.loc[results.destination_name.str.casefold().eq("island")].iloc[0]
    assert np.isclose(island.similarity_score, max(expected[2], expected[3]))
    assert "Forest" not in results.destination_name.tolist()  # zero overlap
    pd.testing.assert_frame_equal(results, model.recommend("anchor"))


def test_combined_score_matches_manual_cosine():
    model = ContentBasedRecommender(catalogue())
    before = model.vectorizer.vocabulary_.copy()
    results = model.recommend(1, ["wildlife", "safari"], destination_weight=0.25)
    destination = cosine_similarity(model.tfidf_matrix[0], model.tfidf_matrix).ravel()
    interest = cosine_similarity(model.vectorizer.transform(["wildlife safari"]), model.tfidf_matrix).ravel()
    for row in results.itertuples():
        assert np.isclose(row.similarity_score, 0.25 * destination[row.id - 1] + 0.75 * interest[row.id - 1])
    assert model.vectorizer.vocabulary_ == before  # queries never refit IDF


def test_unknown_interest_and_invalid_inputs():
    model = ContentBasedRecommender(catalogue())
    assert model.recommend(interests="zzzxxyyqqq").empty
    for args in [{}, {"selected_destination": 99}, {"interests": "ocean", "top_n": 0},
                 {"interests": [None]}, {"interests": "ocean", "destination_weight": 2},
                 {"selected_destination": 1, "interests": "zzzxxyyqqq"}]:
        with pytest.raises(ValueError):
            model.recommend(**args)


def test_ambiguous_name_requires_record_id():
    records = catalogue()
    records[1]["state"] = "Different location"
    model = ContentBasedRecommender(records)
    with pytest.raises(ValueError, match="ambiguous"):
        model.recommend("Anchor")
    assert not model.recommend(1).empty
