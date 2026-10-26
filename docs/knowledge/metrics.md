# KPI definitions — synthetic demo
Paid revenue: sum of invoices whose payment_status is paid, in GBP.
Unpaid balance: sum of unpaid invoices, regardless of age.
Open tickets: tickets with status open.
SLA breach: closed tickets closed after sla_due_at, or open tickets with sla_due_at before the fixed snapshot (2026-10-25).
Customer metrics aggregate ticket and invoice facts separately to prevent multiple-child-record join fanout.
These definitions apply only to generated, fictional data.
