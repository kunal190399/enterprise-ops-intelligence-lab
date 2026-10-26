# Independent prototype — reproducible evidence

**Scope:** A new, AI-assisted portfolio demonstration with entirely fictional data. It is not a report on any real company.

## Expected validation (locally tested against bundled generator)
- Generated valid customer records: 30
- Generated valid service tickets: 300
- Generated valid billing invoices: 240
- Quarantine cases intentionally injected: 3 (duplicate customer, unknown customer on a ticket, negative invoice)
- Automation alerts in initial local demonstration: 112 review-only candidates.
- Local Python test run: seven tests passed.

Numbers above are **synthetic prototype results**, not evidence for CV claims about improvements at employers. The code and seed make them independently reproducible.

## Reproduction
```bash
python -m pip install -e '.[test]'
python scripts/generate_synthetic.py
python -m opsintel.cli build
python -m opsintel.cli report
python -m opsintel.cli alerts
pytest -q
uvicorn opsintel.api:app --host 127.0.0.1 --port 8000
```

Review the browser dashboard at http://127.0.0.1:8000 and FastAPI schema at http://127.0.0.1:8000/docs.

## What tests cover
1. Ingestion validates and quarantines intentionally invalid records.
2. Repeated ingestion yields consistent KPI outputs.
3. Aggregated reporting avoids multiplying monetary facts through ticket joins.
4. Repeated alert checks do not create duplicate alerts.
5. Source-cited local retrieval returns relevant policy material.
6. External inference is not called without an opt-in API key.
7. Local HTTP health, KPI, reporting, retrieval and alert endpoints.

## Boundaries
- Fake data, no live CRM, ERP or cloud system integration.
- Retrieval is lexical and offline, not a tested embedding-based RAG pipeline.
- Optional remote LLM functionality is unverified.
- No production IAM, RBAC, secrets management, TLS or formal privacy audit.
- Do not expose the demo server outside localhost.
- Prepared with AI assistance; review the code before claiming personal implementation expertise.
