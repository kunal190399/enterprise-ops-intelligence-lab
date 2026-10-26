from fastapi.testclient import TestClient
from opsintel.api import app
from opsintel.pipeline import ingest
import opsintel.api as api

def test_demo_endpoints(tmp_path,monkeypatch):
    db=tmp_path/'api.db'
    ingest(db_path=db)
    monkeypatch.setattr(api,'DB',db)
    client=TestClient(app)
    assert client.get('/health').json()['status']=='ok'
    assert client.get('/api/kpis').json()['quarantined_records']==3
    assert len(client.get('/api/customers').json())==30
    assert len(client.get('/api/revenue').json())==2
    assert 'SYNTHETIC DATA' in client.get('/').text
    res=client.post('/api/ask',json={'question':'How are SLA breaches defined?','use_llm':False})
    assert res.status_code==200
    assert res.json()['sources']
    alerts=client.post('/api/alerts').json()
    assert alerts and len(alerts)==len(client.post('/api/alerts').json())
    assert client.post('/api/ask',json={'question':'x'}).status_code==422
