import numpy as np
from backend.evaluation import ndcg, run_evaluation


def test_ndcg_known_orderings():
    assert ndcg([1, 1, 0], [1, 1, 0]) == 1
    assert ndcg([0, 0], [1, 1]) == 0
    assert 0 < ndcg([0, 1], [1, 0]) < 1
    assert ndcg([0, 0], [0, 0]) == 0


def test_catalogue_evaluation_invariants():
    retrieval, preferences, summary = run_evaluation()
    assert summary['destination_profiles'] == 93
    assert summary['masked_interest_queries'] == 20
    assert preferences.duplicate_count.eq(0).all() and preferences.self_count.eq(0).all()
    assert preferences.returned_count.eq(5).all()
    assert np.isfinite(preferences.ndcg_at_5).all()
    assert preferences.ndcg_at_5.between(0, 1).all()
    assert retrieval.precision_at_5.between(0, 1).all()
    assert set(retrieval.method) == {'masked_content','full_content','popularity','seeded_random'}
    assert all(0 <= value <= 1 for value in summary['catalogue_coverage'].values())
