"""Create deterministic, explicitly SYNTHETIC telecom/IT mock data."""
import csv
from datetime import datetime, timedelta
from pathlib import Path
from random import Random

BASE = Path(__file__).resolve().parents[1] / "data" / "synthetic"
SEED = 20261026

def write(name, headers, rows):
    BASE.mkdir(parents=True, exist_ok=True)
    with (BASE / name).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, headers)
        w.writeheader()
        w.writerows(rows)

def generate():
    r = Random(SEED)
    customers = [{"customer_id": f"C{i:03d}", "segment": r.choice(["SMB","Mid-market","Enterprise"]),
                  "region": r.choice(["North","Midlands","South","Scotland"]),
                  "account_status": "active" if i % 8 else "paused"}
                 for i in range(1,31)]
    customers.append(dict(customers[0]))
    write("crm_customers.csv",["customer_id","segment","region","account_status"],customers)
    tickets = []
    start = datetime(2026,9,1)
    for i in range(1,301):
        created = start + timedelta(days=r.randrange(50),hours=r.randrange(8,18),minutes=r.randrange(60))
        priority = r.choice(["P1","P2","P3"])
        sla_hours = {"P1":4,"P2":24,"P3":72}[priority]
        due = created + timedelta(hours=sla_hours)
        is_closed = r.random() < .73
        closed_at = (created + timedelta(hours=r.randrange(1,sla_hours*2+12))).isoformat(timespec="minutes") if is_closed else ""
        tickets.append({"ticket_id":f"T{i:04d}","customer_id":r.choice(customers[:30])["customer_id"],
                        "priority":priority,"created_at":created.isoformat(timespec="minutes"),
                        "sla_due_at":due.isoformat(timespec="minutes"),"closed_at":closed_at,
                        "status":"closed" if is_closed else "open"})
    tickets.append({"ticket_id":"T9999","customer_id":"C999","priority":"P2","created_at":"2026-10-01T10:00","sla_due_at":"2026-10-02T10:00","closed_at":"","status":"open"})
    write("service_tickets.csv",["ticket_id","customer_id","priority","created_at","sla_due_at","closed_at","status"],tickets)
    invoices = []
    for i in range(1,241):
        dt = start + timedelta(days=r.randrange(50))
        amount = round(r.uniform(80,2800),2)
        paid = r.random() < .78
        invoices.append({"invoice_id":f"I{i:04d}","customer_id":r.choice(customers[:30])["customer_id"],
                         "invoice_date":dt.date().isoformat(),"amount_gbp":f"{amount:.2f}",
                         "payment_status":"paid" if paid else "unpaid"})
    invoices.append({"invoice_id":"I9999","customer_id":"C003","invoice_date":"2026-10-01","amount_gbp":"-100","payment_status":"paid"})
    write("billing_invoices.csv",["invoice_id","customer_id","invoice_date","amount_gbp","payment_status"],invoices)
    return {"seed":SEED,"valid_customers":30,"valid_tickets":300,"valid_invoices":240,"intentionally_invalid_records":3}

if __name__ == "__main__":
    print(generate())
