"""CLI: python -m opsintel.cli build|report|alerts"""
import argparse
import json
from .pipeline import ingest
from .intelligence import kpis, create_alerts

def main():
    p = argparse.ArgumentParser(description="Synthetic enterprise BI portfolio demo")
    p.add_argument('command', choices=['build','report','alerts'])
    p.add_argument('--db', default=None)
    args = p.parse_args()
    if args.command == 'build':
        result = ingest(**({'db_path':args.db} if args.db else {}))
    elif args.command == 'report':
        result = kpis(args.db)
    else:
        result = {"alert_count":len(create_alerts(args.db))}
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__ == '__main__':
    main()
