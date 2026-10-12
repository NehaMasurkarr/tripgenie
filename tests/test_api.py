import hashlib
import json
from pathlib import Path

import pytest

from backend.app import create_app


@pytest.fixture(scope="module")
def app():
    return create_app({"TESTING": True, "LOG_LEVEL": "ERROR"})


@pytest.fixture
def client(app):
    return app.test_client()


def test_discovery_detail_and_options(client):
    assert client.get('/health').json['catalogue_records'] == 100
    options = client.get('/api/v1/options').json['data']
    assert options['destination_count'] == 93
    assert 'beach' in options['interests']
    response = client.get('/api/v1/destinations?limit=100')
    assert response.status_code == 200
    rows = response.json['data']
    assert len(rows) == response.json['meta']['total'] == 93
    assert len({r['name'].casefold() for r in rows}) == 93
    detail = client.get('/api/v1/destinations/1').json['data']
    assert detail['name'] == 'Goa' and detail['suggested_itinerary']
    assert client.get('/api/v1/destinations/999').status_code == 404
    assert client.get('/api/v1/destinations?page=100').json['data'] == []


def test_filters_are_applied_before_pagination(client):
    data = client.get('/api/v1/destinations?state=Goa&interest=beach&max_daily_budget=4000&season=winter&days=3').json
    assert data['data']
    for row in data['data']:
        assert row['state'] == 'Goa' and 'beach' in row['interests']
        assert row['daily_cost']['high'] <= 4000
        assert row['duration']['minimum'] <= 3 <= row['duration']['maximum']
    assert all('goa' in (r['name'] + ' ' + r['state'] + ' ' + r['description']).lower()
               for r in client.get('/api/v1/destinations?q=Goa').json['data'])


def test_personalization_and_score_breakdown(client):
    profile = dict(selected_destination=1, interests=['beach'], daily_budget=3000, season='winter', trip_days=3)
    response = client.post('/api/v1/recommendations', json=profile)
    assert response.status_code == 200
    rows = response.json['data']
    assert len(rows) == 5 and not any(r['destination']['name'] == 'Goa' for r in rows)
    assert len({r['destination']['name'].casefold() for r in rows}) == len(rows)
    assert [r['score'] for r in rows] == sorted([r['score'] for r in rows], reverse=True)
    for row in rows:
        assert row['score'] == pytest.approx(sum(v['contribution'] for v in row['breakdown'].values()))
        assert sum(v['weight'] for v in row['breakdown'].values()) == pytest.approx(1)
    assert client.post('/api/v1/recommendations', json=profile).json == response.json
    content = client.post('/api/v1/recommendations', json={'model': 'content', 'interests': ['wildlife'], 'state': 'Karnataka'})
    assert content.status_code == 200 and content.json['data']
    assert all(r['destination']['state'] == 'Karnataka' for r in content.json['data'])
    strict = client.post('/api/v1/recommendations', json={'daily_budget': 1, 'strict_filters': True})
    assert strict.status_code == 200 and strict.json['data'] == []


def test_itinerary_is_grounded_unique_and_costed(client, app):
    source = app.extensions['catalogue'].get(1)
    response = client.post('/api/v1/itineraries', json={'destination_id': 1, 'days': 3, 'interests': ['beach']})
    assert response.status_code == 200
    plan = response.json['data']
    attractions = [a for d in plan['days'] for a in d['attractions']]
    activities = [a for d in plan['days'] for a in d['activities']]
    assert len(plan['days']) == 3 and len(set(attractions)) == len(attractions)
    assert set(attractions) <= set(source['primary_attractions'])
    assert set(activities) <= set(source['activities_available'])
    assert plan['estimated_cost']['low'] == 3 * source['budget_category.total_daily_low']
    assert plan['source_itinerary'] == source['suggested_itinerary']
    assert plan['warnings']
    assert client.post('/api/v1/itineraries', json={'destination_id': 999, 'days': 3}).status_code == 404


@pytest.mark.parametrize('body', [[], None, {'model': []}, {'budget_tier': []}, {'selected_destination': True},
    {'daily_budget': '1000'}, {'daily_budget': -1}, {'trip_days': True}, {'season': 'january'}, {'top_n': 100},
    {'interests': [None]}, {'weights': {'unknown': 1}}, {'weights': {'content': True}}, {'extra': 'x'},
    {'weights': {k: 0 for k in ['content','popularity','interests','budget','season','duration']}},
    {'model': 'content', 'weights': {'content': 1}}, {'model': 'content'}])
def test_invalid_recommendations_return_json_400(client, body):
    response = client.post('/api/v1/recommendations', data=json.dumps(body), content_type='application/json')
    assert response.status_code == 400
    assert response.json['error']['message'] and response.json['error']['request_id']


@pytest.mark.parametrize('query', ['days=NaN', 'limit=1.5', 'limit=101', 'unknown=yes', 'season=January', 'state=A&state=B'])
def test_invalid_queries(client, query):
    assert client.get('/api/v1/destinations?' + query).status_code == 400


def test_http_errors_cors_and_no_internal_error_leak(client, app, monkeypatch):
    assert client.post('/api/v1/recommendations', data='{}').status_code == 415
    assert client.post('/api/v1/recommendations', data='{', content_type='application/json').status_code == 400
    assert client.get('/does-not-exist').status_code == 404
    assert client.put('/api/v1/options').status_code == 405
    assert client.post('/api/v1/recommendations', json={'interests': ['x' * 17000]}).status_code == 413
    preflight = client.options('/api/v1/recommendations', headers={'Origin':'http://localhost:5173', 'Access-Control-Request-Method':'POST'})
    assert preflight.headers['Access-Control-Allow-Origin'] == 'http://localhost:5173'
    assert 'Access-Control-Allow-Origin' not in client.get('/health', headers={'Origin':'https://untrusted.example'}).headers
    monkeypatch.setattr(app.extensions['catalogue'], 'options', lambda: (_ for _ in ()).throw(RuntimeError('private details')))
    failure = client.get('/api/v1/options')
    assert failure.status_code == 500 and 'private details' not in failure.get_data(as_text=True)


@pytest.mark.parametrize('body', [{'destination_id':1,'days':0}, {'destination_id':True,'days':3},
                                 {'destination_id':1,'days':2.5}, {'destination_id':1,'days':15}, {}])
def test_invalid_itinerary(client, body):
    assert client.post('/api/v1/itineraries', json=body).status_code == 400


def test_requests_do_not_modify_dataset_files(client):
    paths = list(Path('data').rglob('*.json'))
    hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    client.post('/api/v1/recommendations', json={'interests':['beach']})
    client.post('/api/v1/itineraries', json={'destination_id':1, 'days':3})
    assert hashes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
