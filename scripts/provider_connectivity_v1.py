"""One-shot OpenAI Responses connectivity, independent of benchmark/fixture ledgers.

No SDK, proxy, redirects or automatic retries. A durable claim consumes the one
attempt even on crash or credential failure. Never delete state to retry a run.
"""
import argparse
from contextlib import closing
import datetime as dt
from decimal import Decimal
import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import ssl

from scoped_credentials import credential_scope, sanitize, sanitized_error


MODEL = 'gpt-5.4-mini-2026-03-17'
RUN = 'stage9-openai-connectivity-001'
SOURCES = ['configs/stage9-connectivity.json', 'scripts/provider_connectivity_v1.py',
           'scripts/scoped_credentials.py', 'scripts/credential_artifacts.py']


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def validate(spec):
    req = spec['request']
    expected = {'model': MODEL, 'input': 'Chỉ trả lời đúng một dòng: Kết nối tiếng Việt thành công.',
                'max_output_tokens': 128, 'reasoning': {'effort': 'none'},
                'service_tier': 'default', 'store': False, 'stream': False, 'tools': []}
    if (spec['schema'] != 'vi-provider-connectivity/1' or spec['run_id'] != RUN
            or spec['scope'] != 'provider-connectivity' or spec['provider'] != 'openai'
            or spec['currency'] != 'USD' or spec['max_requests'] != 1
            or spec['timeout_seconds'] != 30 or spec['input_token_reserve'] != 4096
            or req != expected or len(req['input'].encode('utf-8')) > 512):
        raise ValueError('UNSUPPORTED_EFFECTIVE_CONFIG')
    prices = spec['pricing']
    if [prices[k] for k in ['input', 'cached_input', 'output']] != ['0.75', '0.075', '4.50']:
        raise ValueError('UNSUPPORTED_PRICE')
    cap, reserve = Decimal(spec['cap_usd']), Decimal(spec['reservation_usd'])
    upper = (Decimal(4096) * Decimal(prices['input']) + Decimal(128) * Decimal(prices['output'])) / 1000000
    if not (cap.is_finite() and reserve.is_finite() and upper <= reserve <= cap <= Decimal('2')):
        raise ValueError('BUDGET_DENIED')


def gate_inputs(repo, manifest):
    return all(digest(repo / name) == expected for name, expected in manifest['source_sha256'].items()) and set(manifest['source_sha256']) == set(SOURCES)


def claim(db, spec, manifest):
    db.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, manifest TEXT NOT NULL, state TEXT NOT NULL, reserve TEXT NOT NULL, result TEXT)')
    db.commit()
    # One fixed run identity, not an operator-supplied ID which could reset budget.
    with db:
        db.execute('INSERT INTO runs VALUES (?, ?, ?, ?, NULL)',
                   (RUN, json.dumps(manifest, sort_keys=True), 'reserved', spec['reservation_usd']))


def cost(spec, body):
    """Observed token-price estimate, never an authoritative provider invoice."""
    usage = body.get('usage')
    if not isinstance(usage, dict) or body.get('model') != MODEL or body.get('service_tier') != 'default':
        return None
    i, o = usage.get('input_tokens'), usage.get('output_tokens')
    details = usage.get('input_tokens_details')
    c = details.get('cached_tokens') if isinstance(details, dict) else None
    if any(type(n) is not int or n < 0 for n in [i, o, c]) or c > i:
        return None
    if i > spec['input_token_reserve'] or o > spec['request']['max_output_tokens']:
        return None
    if details.get('cache_write_tokens', 0) != 0:
        return None  # Different pricing contract: retain reservation.
    prices = spec['pricing']
    return str((Decimal(i-c)*Decimal(prices['input']) + Decimal(c)*Decimal(prices['cached_input']) + Decimal(o)*Decimal(prices['output'])) / 1000000)


def request_once(key, spec):
    # Fixed HTTPS origin and path. http.client neither follows redirects nor retries
    # a request; it does not consume proxy/base-URL environment overrides.
    connection = http.client.HTTPSConnection('api.openai.com', timeout=spec['timeout_seconds'], context=ssl.create_default_context())
    try:
        connection.request('POST', '/v1/responses',
                           body=json.dumps(spec['request'], ensure_ascii=False).encode('utf-8'),
                           headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json',
                                    'X-Client-Request-Id': RUN})
        response = connection.getresponse()
        raw = response.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError('RESPONSE_SIZE_LIMIT')
        body = json.loads(raw)
        if not isinstance(body, dict):
            raise ValueError('INVALID_RESPONSE')
        # Drop request echoes and arbitrary headers. Exact-key sanitize happens in lease.
        allowed = ['id', 'model', 'status', 'service_tier', 'usage', 'output', 'error', 'incomplete_details']
        return {'http_status': response.status, 'provider_request_id': response.getheader('x-request-id'),
                'response': {k: body[k] for k in allowed if k in body}}
    finally:
        connection.close()


def execute(repo, spec, manifest, db_path, transport=None):
    validate(spec)
    if not gate_inputs(repo, manifest):
        raise ValueError('SOURCE_DRIFT')
    if manifest['spec_sha256'] != digest(repo / 'configs/stage9-connectivity.json'):
        raise ValueError('SPEC_DRIFT')
    # Prevent callers from supplying a different in-memory spec than frozen on disk.
    if spec != json.loads((repo / 'configs/stage9-connectivity.json').read_text(encoding='utf-8')):
        raise ValueError('SPEC_DRIFT')
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as db:
        claim(db, spec, manifest)  # Unique identity blocks concurrent/repeated execution.

        def live_gate():
            row = db.execute('SELECT state FROM runs WHERE id=?', (RUN,)).fetchone()
            return row == ('reserved',) and gate_inputs(repo, manifest)

        result = {'schema': 'vi-provider-receipt/1', 'run_id': RUN, 'scope': 'provider-connectivity',
                  'currency': 'USD', 'cap_usd': spec['cap_usd'], 'reserved_usd': spec['reservation_usd'],
                  'client_request_id': RUN, 'request_attempts': 0, 'token_price_estimate_usd': None,
                  'authoritative_invoice_usd': None, 'benchmark_trials': 0, 'recorded_at_utc': now(),
                  'manifest': manifest}
        try:
            with credential_scope(mode='runtime', target='model-api-client', gate=live_gate,
                                  dotenv_path=repo / '.env', environment={}) as lease:
                key = lease.sdk_key()
                # Commit uncertain submission BEFORE entering a potentially billable sink.
                with db:
                    db.execute('UPDATE runs SET state=? WHERE id=?', ('submitted', RUN))
                result['request_attempts'] = 1
                try:
                    observed = (transport or request_once)(key, spec)
                    result.update(lease.sanitize(observed))
                except Exception as exc:
                    result['transport_error'] = sanitized_error(exc)
                finally:
                    key = None
        except Exception as exc:
            result['credential_or_gate_error'] = sanitized_error(exc)
        body = result.get('response', {})
        result['token_price_estimate_usd'] = cost(spec, body)
        result['connectivity_passed'] = (result.get('http_status') == 200 and body.get('status') == 'completed'
                                         and body.get('model') == MODEL and bool(result.get('provider_request_id')))
        known = result['token_price_estimate_usd'] is not None
        result['accounting_state'] = 'token_estimate_recorded_not_invoiced' if known else 'unknown_cost_reservation_held'
        result['exposure_held_usd'] = spec['reservation_usd']  # Retain until invoice reconciliation.
        result = sanitize(result)
        with db:
            db.execute('UPDATE runs SET state=?, result=? WHERE id=?',
                       ('observed' if result['request_attempts'] else 'pre_dispatch_failed', json.dumps(result, ensure_ascii=False), RUN))
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--export', action='store_true', help='Export existing receipt without sending')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    spec = json.loads((repo / 'configs/stage9-connectivity.json').read_text(encoding='utf-8'))
    validate(spec)
    if not args.execute and not args.export:
        print('Preview only; max requests 1; cap USD 2; no credential read')
        return
    db_path = repo / 'jobs/stage9-connectivity/ledger.sqlite3'
    if args.execute and args.export:
        raise ValueError('CHOOSE_EXECUTE_OR_EXPORT')
    if args.export:
        # Read-only export cannot create missing state or submit a request.
        with closing(sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True)) as db:
            row = db.execute('SELECT result FROM runs WHERE id=?', (RUN,)).fetchone()
        if not row or not row[0]:
            raise ValueError('UNRECONCILED_SUBMISSION_DO_NOT_RETRY')
        result = json.loads(row[0])
    else:
        manifest = json.loads((repo / 'reports/stage9-frozen-inputs.json').read_text(encoding='utf-8'))
        result = execute(repo, spec, manifest, db_path)
    write_new(repo / 'reports/provider-connectivity-stage9.json', result)
    print(json.dumps({k: result.get(k) for k in ['run_id', 'http_status', 'request_attempts', 'connectivity_passed', 'token_price_estimate_usd', 'accounting_state']}))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps(sanitized_error(exc)))
        raise SystemExit(1) from None
