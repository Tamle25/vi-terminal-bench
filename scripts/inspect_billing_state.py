"""Read-only recovery view, including local owner/lease and observation timestamps."""
import argparse
import datetime as dt
import json
from pathlib import Path
from billing_ledger import readonly
from reconcile_billing import status


def observe(ledger, local_state=None):
    report = status(ledger, local_state)
    report['observed_at_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    report['global_lease_policy'] = 'No timeout releases a submitted/uncertain reservation'
    if local_state:
        db = readonly(local_state)
        try:
            report['local_execution_leases'] = [dict(row) for row in db.execute('SELECT trial_id,number,phase,owner,lease_until FROM attempts ORDER BY trial_id,number')]
            report['local_request_leases'] = [dict(row) for row in db.execute('SELECT request_id,phase,owner,lease_until FROM execution_requests ORDER BY request_id')]
        finally: db.close()
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--ledger', required=True)
    p.add_argument('--local-state')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    report = observe(args.ledger, args.local_state)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
