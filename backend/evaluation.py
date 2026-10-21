"""Reproducible weak-label retrieval and preference-agreement evaluation.

Run from the repository root: python -m backend.evaluation --output docs/evaluation
No user feedback is synthesized; every target comes from catalogue metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time

import numpy as np
import pandas as pd

from backend.recommender.content_recommender import ContentBasedRecommender, destination_key, normalize_text
from backend.recommender.hybrid_recommender import HybridRecommender, SEASONS, season_matches

ROOT = Path(__file__).resolve().parents[1]


def ndcg(gains, ideal):
    def dcg(values):
        values = np.asarray(values, dtype=float)
        return float(np.sum((2 ** values - 1) / np.log2(np.arange(len(values)) + 2)))
    denominator = dcg(ideal)
    return dcg(gains) / denominator if denominator else 0.0


def run_evaluation(path=ROOT / 'data/processed/india_tourism_processed.json', seed=42):
    records = json.loads(Path(path).read_text())
    catalogue = pd.DataFrame(records)
    keys = catalogue.destination_name.map(destination_key)
    representatives = catalogue.assign(key=keys).sort_values(['popularity_score', 'id'], ascending=[False, True]).drop_duplicates('key')
    full = ContentBasedRecommender(records)
    hybrid = HybridRecommender(full)
    lookup = {r['id']: r for r in records}
    rng = np.random.default_rng(seed)
    # Remove direct labels, place names, and geography from the masked text corpus.
    descriptive_fields = ['primary_attractions_clean', 'activities_available_clean', 'unique_experiences',
                          'hidden_gems_clean', 'local_culture', 'food_scene']
    def parts(value):
        return ' '.join(value) if isinstance(value, list) else str(value or '')
    masked_records = [dict(r, tfidf_text=normalize_text(' '.join(parts(r[f]) for f in descriptive_fields))) for r in records]
    masked = ContentBasedRecommender(masked_records)
    group_tags = {key: set(t for tags in group.trip_types_clean for t in tags)
                  for key, group in catalogue.assign(key=keys).groupby('key')}
    labels = sorted(t for t in {t for tags in group_tags.values() for t in tags}
                    if sum(t in tags for tags in group_tags.values()) >= 5)
    retrieval_rows = []
    for tag in labels:
        relevant = {key for key, tags in group_tags.items() if tag in tags}
        random_ids = representatives.iloc[rng.choice(len(representatives), 5, replace=False)].id.tolist()
        candidates = {
            'masked_content': masked.recommend(interests=[tag]).id.tolist(),
            'full_content': full.recommend(interests=[tag]).id.tolist(),
            'popularity': representatives.head(5).id.tolist(), 'seeded_random': random_ids}
        for method, ids in candidates.items():
            hits = [int(destination_key(lookup[id_]['destination_name']) in relevant) for id_ in ids]
            average_precision = sum(hit * sum(hits[:i + 1]) / (i + 1) for i, hit in enumerate(hits)) / min(5, len(relevant))
            retrieval_rows.append({'query_tag': tag, 'method': method, 'relevant_destinations': len(relevant),
                'returned_count': len(ids), 'precision_at_5': sum(hits) / 5, 'recall_at_5': sum(hits) / len(relevant),
                'ap_at_5': average_precision, 'ndcg_at_5': ndcg(hits, [1] * min(5, len(relevant)))})
    preference_rows, served = [], {method: set() for method in ['content', 'hybrid', 'popularity']}
    for query in representatives.itertuples():
        source = lookup[query.id]
        interests = source['trip_types_clean'][:2]
        best = [s for s in sorted(SEASONS) if season_matches(source['best_seasons_clean'], s)
                and not season_matches(source['avoid_seasons_clean'], s)]
        profile = {'selected_destination': source['id'], 'interests': interests,
                   'daily_budget': source['budget_category.daily_midpoint'], 'trip_days': source['ideal_days']}
        if best:
            profile['season'] = best[0]
        def relevance(row):
            criteria = {
                'interest_coverage': len(set(interests) & set(row['trip_types_clean'])) / len(interests),
                'budget_upper_fit': float(row['budget_category.total_daily_high'] <= profile['daily_budget']),
                'duration_range_fit': float(row['minimum_days'] <= profile['trip_days'] <= row['maximum_days'])}
            if 'season' in profile:
                criteria['season_fit'] = float(season_matches(row['best_seasons_clean'], profile['season']) and
                                              not season_matches(row['avoid_seasons_clean'], profile['season']))
            return criteria
        pool = [r for r in records if destination_key(r['destination_name']) != query.key]
        ideal_by_name = {}
        for row in pool:
            key = destination_key(row['destination_name'])
            gain = np.mean(list(relevance(row).values()))
            ideal_by_name[key] = max(ideal_by_name.get(key, 0), gain)
        ideal = sorted(ideal_by_name.values(), reverse=True)[:5]
        for method in served:
            started = time.perf_counter()
            if method == 'hybrid':
                ranked = hybrid.recommend(**profile)
                ids = ranked.id.tolist()
            elif method == 'content':
                ids = full.recommend(selected_destination=source['id'], interests=interests).id.tolist()
            else:
                ids = representatives.loc[representatives.key.ne(query.key)].head(5).id.tolist()
            elapsed = (time.perf_counter() - started) * 1000
            rows = [lookup[id_] for id_ in ids]
            metrics = pd.DataFrame([relevance(r) for r in rows])
            gains = metrics.mean(axis=1).tolist()
            names = [destination_key(r['destination_name']) for r in rows]
            served[method].update(names)
            preference_rows.append({'query_id': source['id'], 'query_name': source['destination_name'], 'method': method,
                'returned_count': len(rows), 'latency_ms': elapsed, 'ndcg_at_5': ndcg(gains, ideal),
                'preference_agreement': float(np.mean(gains)), 'region_diversity': len({r['region'] for r in rows}) / 5,
                'duplicate_count': len(names) - len(set(names)), 'self_count': sum(name == query.key for name in names),
                **metrics.mean().to_dict()})
    retrieval = pd.DataFrame(retrieval_rows)
    preferences = pd.DataFrame(preference_rows)
    summary = {
        'seed': seed, 'source_sha256': hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        'destination_profiles': len(representatives), 'masked_interest_queries': len(labels),
        'retrieval_means': retrieval.groupby('method')[['precision_at_5', 'recall_at_5', 'ap_at_5', 'ndcg_at_5']].mean().to_dict(orient='index'),
        'preference_means': preferences.groupby('method')[['ndcg_at_5', 'preference_agreement', 'interest_coverage',
            'budget_upper_fit', 'season_fit', 'duration_range_fit', 'region_diversity', 'duplicate_count', 'self_count']].mean().to_dict(orient='index'),
        'catalogue_coverage': {method: len(names) / len(representatives) for method, names in served.items()},
        'latency_ms': {method: {'p50': float(group.latency_ms.quantile(.5)), 'p95': float(group.latency_ms.quantile(.95))}
                       for method, group in preferences.groupby('method')},
        'limitations': ['Metadata-derived weak labels, not user relevance judgments.',
            'Full-content labels and hybrid interest matching include target tags: preference agreement is not independent accuracy.',
            'Masked content excludes explicit trip tags, names, and geography but descriptive wording may still reveal the labels.',
            'Synthetic profiles derive from source metadata; no user ratings or interaction data are invented.',
            'Latency is local sequential warm-model timing, not a production load benchmark.']}
    assert preferences.duplicate_count.eq(0).all() and preferences.self_count.eq(0).all()
    assert preferences.ndcg_at_5.between(0, 1 + 1e-9).all()
    return retrieval, preferences, summary


def save_report(retrieval, preferences, summary, output):
    import matplotlib.pyplot as plt
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    retrieval.to_csv(output / 'retrieval.csv', index=False)
    preferences.to_csv(output / 'preferences.csv', index=False)
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, allow_nan=False) + '\n')
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    retrieval.groupby('method')[['precision_at_5', 'ndcg_at_5']].mean().plot.bar(ax=axes[0], rot=20)
    preferences.groupby('method')[['ndcg_at_5', 'preference_agreement']].mean().plot.bar(ax=axes[1], rot=0)
    for ax, title in zip(axes, ['Weak-label interest retrieval', 'Catalogue-derived preference agreement']):
        ax.set(title=title, ylabel='Score', xlabel='Method', ylim=(0, 1.05))
    fig.tight_layout()
    fig.savefig(output / 'comparison.png', dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    preferences.groupby('method')[['interest_coverage', 'budget_upper_fit', 'season_fit', 'duration_range_fit']].mean().plot.bar(ax=axes[0], rot=0)
    pd.Series(summary['catalogue_coverage']).plot.bar(ax=axes[1], rot=0, color='#0072b2')
    axes[0].set(title='Preference-specific agreement', ylabel='Fraction', xlabel='Method', ylim=(0, 1.05))
    axes[1].set(title='Destination coverage across profile queries', ylabel='Fraction of unique names served', xlabel='Method', ylim=(0, 1.05))
    fig.tight_layout()
    fig.savefig(output / 'coverage.png', dpi=150)
    plt.close(fig)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='docs/evaluation')
    args = parser.parse_args()
    result = run_evaluation()
    save_report(*result, args.output)
    print(json.dumps(result[2], indent=2))
