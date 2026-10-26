"""Local demonstration API: never deploy publicly without security review."""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from .pipeline import DEFAULT_DB
from .intelligence import kpis, customer_reporting, invoice_buckets, create_alerts, answer

app = FastAPI(title="Enterprise Ops Intelligence Lab",version="0.1.0",description="Synthetic-data-only independent prototype")
DB = Path(os.environ.get('OPSINTEL_DB',str(DEFAULT_DB)))
HOME = Path(__file__).resolve().parents[2] / 'static' / 'index.html'

class AskRequest(BaseModel):
    question: str = Field(min_length=3,max_length=500)
    use_llm: bool = False

@app.get('/',response_class=HTMLResponse)
def home():
    return HOME.read_text(encoding='utf-8')

@app.get('/health')
def health():
    return {'status':'ok','scope':'local synthetic demo'}

@app.get('/api/kpis')
def api_kpis():
    try: return kpis(DB)
    except Exception as e: raise HTTPException(503, 'Run ingestion to initialise the demo database') from e

@app.get('/api/customers')
def api_customers():
    try: return customer_reporting(DB)
    except Exception as e: raise HTTPException(503, 'Demo database not initialised') from e

@app.get('/api/revenue')
def api_revenue():
    try: return invoice_buckets(DB)
    except Exception as e: raise HTTPException(503, 'Demo database not initialised') from e

@app.post('/api/alerts')
def api_alerts():
    try: return create_alerts(DB)
    except Exception as e: raise HTTPException(503, 'Demo database not initialised') from e

@app.post('/api/ask')
def api_ask(req:AskRequest):
    try: return answer(req.question, DB, use_llm=req.use_llm)
    except ImportError as e: raise HTTPException(400, 'Install [llm] extra to enable LLM') from e
