"""Read-only status and explicit receipt import. Never dispatches a provider."""
import argparse
import json
from pathlib import Path
from billing_ledger import BillingLedger, readonly
from billing_executor import BillingCrash, open_local_bridge


def status(path, local_path=None):
    db = readonly(path)
    try:
        report = {'schema': 'vi-billing-status/0.1', 'origin': 'offline-fixture',
                  'currency': 'SIM_USD', 'model_calls': 0, 'secrets_read': False,
                  'pools': [json.loads(row['spec']) for row in db.execute('SELECT spec FROM pools ORDER BY id')],
                  'runs': [dict(row) for row in db.execute('SELECT * FROM runs ORDER BY pool_id,run_id')],
                  'requests': [dict(row) for row in db.execute('SELECT * FROM requests ORDER BY id')],
                  'holds': [dict(row) for row in db.execute('SELECT * FROM holds ORDER BY pool_id,id')],
                  'receipt_revisions': [dict(row) for row in db.execute('SELECT request_id,revision,sha256 FROM receipts ORDER BY request_id,revision')],
                  'event_count': db.execute('SELECT count(*) FROM events').fetchone()[0]}
    finally: db.close()
    if local_path:
        db = readonly(local_path)
        try:
            report['local_outbox'] = [dict(row) for row in db.execute('SELECT * FROM billing_outbox ORDER BY request_id')]
            report['local_overlay'] = [dict(row) for row in db.execute('SELECT * FROM billing_overlay ORDER BY request_id')]
            report['local_attempts'] = [dict(row) for row in db.execute('SELECT trial_id,number,phase,reserve_i,reserve_c,actual_i,actual_c FROM attempts ORDER BY trial_id,number')]
            report['recovery_policy'] = 'Full receipts may settle; partial trial without agent checkpoint stays uncertain; no resend'
        finally: db.close()
    return report


def import_receipt(path, envelope, raw, local_path=None, fault=False):
    if not Path(path).is_file(): raise ValueError('Existing billing ledger required')
    ledger = BillingLedger(path)
    store = None
    try:
        changed = ledger.apply_receipt(envelope, raw)
        if fault: raise BillingCrash('after_global_receipt_before_local_sync')
        synced = {}
        if local_path:
            store, bridge = open_local_bridge(local_path, ledger)
            synced = bridge.sync_all()
        return {'origin': 'offline-fixture', 'receipt_changed': changed, 'local_sync': synced,
                'model_calls': 0, 'provider_calls': 0, 'currency': 'SIM_USD'}
    finally:
        if store: store.db.close()
        ledger.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('command', choices=['status', 'import-receipt', 'cancel-reserved'])
    p.add_argument('--ledger', type=Path, required=True)
    p.add_argument('--local-state', type=Path)
    p.add_argument('--receipt', type=Path)
    p.add_argument('--raw-evidence', type=Path)
    p.add_argument('--request-id')
    p.add_argument('--output', type=Path)
    p.add_argument('--fault-after-global', action='store_true', help='Offline crash injection only')
    args = p.parse_args()
    if args.output and args.output.exists(): raise ValueError('Choose a new output path')
    if args.command == 'status':
        report = status(args.ledger, args.local_state)
    elif args.command == 'import-receipt':
        if not args.receipt or not args.raw_evidence: raise ValueError('Receipt and original raw evidence required')
        report = import_receipt(args.ledger, json.loads(args.receipt.read_text(encoding='utf-8')), args.raw_evidence.read_bytes(), args.local_state, args.fault_after_global)
    else:
        if not args.ledger.is_file() or not args.request_id: raise ValueError('Existing ledger and request ID required')
        ledger = BillingLedger(args.ledger)
        try: ledger.cancel_reserved(args.request_id)
        finally: ledger.close()
        report = {'origin': 'offline-fixture', 'cancelled_before_global_submit': args.request_id, 'model_calls': 0,
                  'note': 'Local partial task is not automatically rerun or assigned a reward'}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x', encoding='utf-8') as handle: handle.write(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    else:
        print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__': main()
