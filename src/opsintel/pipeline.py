"""Ingestion, explicit validation/quarantine and unified reporting layer."""
import csv
import json
import sqlite3
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA = ROOT / "data" / "synthetic"
DEFAULT_DB = ROOT / "data" / "demo.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
 customer_id TEXT PRIMARY KEY, segment TEXT NOT NULL, region TEXT NOT NULL, account_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tickets (
 ticket_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
 priority TEXT NOT NULL, created_at TEXT NOT NULL, sla_due_at TEXT NOT NULL,
 closed_at TEXT, status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS invoices (
 invoice_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(customer_id),
 invoice_date TEXT NOT NULL, amount_gbp REAL NOT NULL, payment_status TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quarantine (
 source_file TEXT NOT NULL, row_number INTEGER NOT NULL, reason TEXT NOT NULL, raw_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS automation_alerts (
 alert_key TEXT PRIMARY KEY, category TEXT NOT NULL, subject_id TEXT NOT NULL,
 rationale TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT NOT NULL, details TEXT NOT NULL,
 occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);
DROP VIEW IF EXISTS customer_reporting;
CREATE VIEW customer_reporting AS
 SELECT c.customer_id, c.segment, c.region, c.account_status,
        COALESCE(t.ticket_count, 0) AS ticket_count,
        COALESCE(t.open_tickets, 0) AS open_tickets,
        COALESCE(t.sla_breaches, 0) AS sla_breaches,
        COALESCE(b.invoice_count, 0) AS invoice_count,
        COALESCE(b.paid_revenue_gbp, 0) AS paid_revenue_gbp,
        COALESCE(b.unpaid_balance_gbp, 0) AS unpaid_balance_gbp
 FROM customers c
 LEFT JOIN (SELECT customer_id, COUNT(*) AS ticket_count,
   SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) AS open_tickets,
   SUM(CASE WHEN (status='closed' AND closed_at > sla_due_at) OR
       (status='open' AND sla_due_at < '2026-10-25T00:00:00') THEN 1 ELSE 0 END) AS sla_breaches
   FROM tickets GROUP BY customer_id) t ON t.customer_id=c.customer_id
 LEFT JOIN (SELECT customer_id, COUNT(*) AS invoice_count,
   SUM(CASE WHEN payment_status='paid' THEN amount_gbp ELSE 0 END) AS paid_revenue_gbp,
   SUM(CASE WHEN payment_status='unpaid' THEN amount_gbp ELSE 0 END) AS unpaid_balance_gbp
   FROM invoices GROUP BY customer_id) b ON b.customer_id=c.customer_id;
"""

def connect(path=DEFAULT_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn

def date_ok(value, datetime_value=False):
    try:
        (datetime.fromisoformat if datetime_value else date.fromisoformat)(value)
        return True
    except (TypeError, ValueError):
        return False

def validate(table, row, keys, existing, customers):
    key = row[keys]
    if not key or key in existing:
        return f"missing or duplicate {keys}"
    if table == "customers":
        if not all(row.get(x) for x in ("segment", "region")) or row["account_status"] not in {"active", "paused"}:
            return "invalid customer fields"
    elif table == "tickets":
        if row["customer_id"] not in customers:
            return "unknown customer foreign key"
        if row["priority"] not in {"P1", "P2", "P3"} or row["status"] not in {"open", "closed"}:
            return "invalid status/priority"
        if not all(date_ok(row[x], True) for x in ("created_at", "sla_due_at")):
            return "invalid ticket timestamps"
        if row["status"] == "closed" and not date_ok(row["closed_at"], True):
            return "closed ticket missing timestamp"
        if row["status"] == "open" and row["closed_at"]:
            return "open ticket has closed timestamp"
        if row["closed_at"] and row["closed_at"] < row["created_at"]:
            return "closed before creation"
    elif table == "invoices":
        if row["customer_id"] not in customers:
            return "unknown customer foreign key"
        if not date_ok(row["invoice_date"]) or row["payment_status"] not in {"paid", "unpaid"}:
            return "invalid invoice fields"
        try:
            if float(row["amount_gbp"]) < 0 or float(row["amount_gbp"]) > 1e9:
                return "invalid invoice amount"
        except (ValueError, TypeError):
            return "non-numeric invoice amount"
    return None

def ingest(data_dir=DEFAULT_DATA, db_path=DEFAULT_DB):
    files = [
        ("customers", "crm_customers.csv", ["customer_id", "segment", "region", "account_status"], "customer_id"),
        ("tickets", "service_tickets.csv", ["ticket_id", "customer_id", "priority", "created_at", "sla_due_at", "closed_at", "status"], "ticket_id"),
        ("invoices", "billing_invoices.csv", ["invoice_id", "customer_id", "invoice_date", "amount_gbp", "payment_status"], "invoice_id"),
    ]
    counts = {}
    conn = connect(db_path)
    try:
        conn.executescript(SCHEMA)
        with conn:
            for table in ["tickets", "invoices", "customers", "quarantine", "automation_alerts"]:
                conn.execute(f"DELETE FROM {table}")
            customers = set()
            for table, name, cols, key in files:
                seen = set()
                valid = bad = 0
                with (Path(data_dir) / name).open(newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if set(reader.fieldnames or []) != set(cols):
                        raise ValueError(f"Unexpected CSV schema: {name}")
                    for line, row in enumerate(reader, start=2):
                        issue = validate(table, row, key, seen, customers)
                        if issue:
                            conn.execute("INSERT INTO quarantine VALUES (?,?,?,?)", (name, line, issue, json.dumps(row, sort_keys=True)))
                            bad += 1
                            continue
                        values = [row[c] for c in cols]
                        if table == "invoices": values[3] = float(values[3])
                        conn.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})", values)
                        seen.add(row[key])
                        if table == "customers": customers.add(row[key])
                        valid += 1
                counts[table] = {"accepted": valid, "quarantined": bad}
            conn.execute("INSERT INTO audit_log(event_type,details) VALUES (?,?)", ("ingest", json.dumps(counts,sort_keys=True)))
        return counts
    finally:
        conn.close()
