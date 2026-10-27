import os
os.environ['REFRESH_MINUTES'] = '0'
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from app import store
from app.main import app


def test_api_filters_dates_and_bounds_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(store, 'DB', tmp_path / 'test.sqlite')
    now = datetime.now(timezone.utc)
    recent = dict(id='recent',ticker='INFY',title='Results',category='results',priority=88,url='https://example.com',date=now.isoformat())
    old = {**recent, 'id':'old', 'date':(now-timedelta(days=5)).isoformat()}
    store.put('feed', {'filings':[recent,old], 'prices':[], 'updated_at':now.isoformat(), 'failures':[]})
    with TestClient(app) as client:
        assert len(client.get('/api/feed?hours=24').json()['filings']) == 1
        assert len(client.get('/api/feed?hours=168').json()['filings']) == 2
        assert client.get('/api/feed?hours=0').status_code == 422
        assert client.get('/api/feed?price=-1').status_code == 422
        assert client.post('/api/research', json={'ticker':'../../.env'}).status_code == 422
        assert len(client.get('/api/portfolio').json()['companies']) == 18
        response = client.get('/')
        assert response.status_code == 200
        assert "frame-ancestors 'none'" in response.headers['content-security-policy']
        assert client.get('/.env').status_code == 404
