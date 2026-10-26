"""All tests use temporary databases and deterministic mock data."""
import pytest
from opsintel.pipeline import ingest, connect
from opsintel.intelligence import kpis, customer_reporting, create_alerts, retrieve, answer

@pytest.fixture
def demo_db(tmp_path):
    return tmp_path / 'test.db'

def test_ingestion_quarantines_invalid_source_rows(demo_db):
    from scripts.generate_synthetic import generate
    generate()
    counts = ingest(db_path=demo_db)
    assert counts == {'customers':{'accepted':30,'quarantined':1}, 'tickets':{'accepted':300,'quarantined':1}, 'invoices':{'accepted':240,'quarantined':1}}
    with connect(demo_db) as c:
        reasons = {r['reason'] for r in c.execute('SELECT reason FROM quarantine')}
        assert reasons == {'missing or duplicate customer_id','unknown customer foreign key','invalid invoice amount'}

def test_reingestion_is_idempotent(demo_db):
    ingest(db_path=demo_db)
    first = kpis(demo_db)
    ingest(db_path=demo_db)
    assert first == kpis(demo_db)
    with connect(demo_db) as c:
        assert c.execute('SELECT COUNT(*) FROM tickets').fetchone()[0] == 300
        assert c.execute('SELECT COUNT(*) FROM quarantine').fetchone()[0] == 3

def test_reporting_avoids_fact_fanout(demo_db):
    ingest(db_path=demo_db)
    rows = customer_reporting(demo_db)
    assert len(rows) == 30
    with connect(demo_db) as c:
        invoice_sum = c.execute("SELECT ROUND(SUM(amount_gbp),2) FROM invoices WHERE payment_status='paid'").fetchone()[0]
        view_sum = c.execute('SELECT ROUND(SUM(paid_revenue_gbp),2) FROM customer_reporting').fetchone()[0]
        assert invoice_sum == pytest.approx(view_sum,abs=1e-6)
        assert sum(x['ticket_count'] for x in rows) == 300

def test_alerts_are_review_only_and_idempotent(demo_db):
    ingest(db_path=demo_db)
    a = create_alerts(demo_db)
    b = create_alerts(demo_db)
    assert len(a)==len(b)>0
    assert [x['alert_key'] for x in a] == [x['alert_key'] for x in b]
    assert {x['category'] for x in a} == {'overdue_sla','overdue_invoice'}

def test_retrieval_has_traceable_document_sources(demo_db):
    snippets = retrieve('What is the SLA breach definition?')
    assert snippets and all(x['source'].startswith('docs/knowledge/') for x in snippets)
    assert answer('Explain SLA breaches',demo_db)['mode']=='retrieval_only'
    assert answer('unrelatedqwertyspelling',demo_db)['mode']=='no_evidence'

def test_no_unapproved_llm_calls_without_credentials(monkeypatch,demo_db):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    assert answer('How are SLA breaches defined?',demo_db,use_llm=True)['mode']=='configuration_required'
