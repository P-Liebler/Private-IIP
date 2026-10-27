"""Verify the disposable PR7 HTTPS app without saving cookies or answer bodies."""
import argparse
from copy import copy
import http.cookiejar
import json
import os
from pathlib import Path
import ssl
import time
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ca', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--assistant', choices=('native', 'unavailable'))
    args = parser.parse_args()
    fixture = json.loads(args.fixture.read_text())
    assert fixture['username'].startswith('restore_')
    password = os.environ['RESTORE_TEST_PASSWORD']
    origin = 'https://localhost:9443'
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(
        context=ssl.create_default_context(cafile=str(args.ca))), urllib.request.HTTPCookieProcessor(jar))

    def request(path, data=None):
        print('HTTPS_PROBE_REQUEST', 'POST' if data is not None else 'GET', path, flush=True)
        try:
            return opener.open(urllib.request.Request(origin + path,
                data=json.dumps(data).encode() if data is not None else None,
                headers={'Origin': origin, 'Content-Type': 'application/json'}), timeout=180)
        except urllib.error.HTTPError as error:
            print('HTTPS_PROBE_RESPONSE', path, error.code)
            raise
        except urllib.error.URLError as error:
            print('HTTPS_PROBE_TRANSPORT', path, type(error.reason).__name__,
                  getattr(error.reason, 'errno', None), flush=True)
            raise

    with request('/login') as response:
        assert response.status == 200 and b'Anmelden' in response.read()
        policy = response.headers.get('Content-Security-Policy', '')
        assert "object-src 'none'" in policy and "frame-ancestors 'none'" in policy
        assert response.headers.get('X-Frame-Options') == 'DENY'
    try:
        request('/api/v1/auth/login', {'username': fixture['username'], 'password': password + 'invalid'})
        raise AssertionError('INVALID_CREDENTIALS_ACCEPTED')
    except urllib.error.HTTPError as error:
        assert error.code == 401
    with request('/api/v1/auth/login', {'username': fixture['username'], 'password': password}) as response:
        assert json.load(response)['status'] == 'authenticated'
        cookie = response.headers.get('Set-Cookie', '')
        assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    with request(f"/api/v1/portfolios/{fixture['portfolio_id']}/valuation") as response:
        valuation = json.load(response)
        from decimal import Decimal
        assert valuation['status'] == 'COMPLETE' and Decimal(valuation['total_value_base']) == Decimal('10180')
    try:
        request('/internal/metrics')
        raise AssertionError('INTERNAL_METRICS_EXPOSED')
    except urllib.error.HTTPError as error:
        assert error.code == 404
    result = {'status': 'SYNTHETIC_HTTPS_APP_VERIFIED', 'strict_ca': True,
        'secure_httponly_cookie': True, 'golden_chf': '10180', 'internal_metrics_blocked': True,
        'csp_unsafe_inline_present': "'unsafe-inline'" in policy,
        'client_os_ca_acceptance': False, 'security_approval': False}
    if args.assistant:
        with request('/api/v1/assistant/conversations', {'title': 'SYNTHETIC PR7 native runtime'}) as response:
            conversation = json.load(response)['id']
        started = time.monotonic()
        first_ms, done, errors, types, model_events = None, False, [], [], []
        with request(f'/api/v1/assistant/conversations/{conversation}/messages', {
            'question': 'Erkläre den Datenstand meines Portfolios mit den vorhandenen Belegen.',
            'portfolio_id': fixture['portfolio_id'], 'instrument_id': fixture['instrument_id']}) as response:
            for line in response:
                if not line.startswith(b'data: '):
                    continue
                event = json.loads(line[6:])
                first_ms = first_ms if first_ms is not None else (time.monotonic() - started) * 1000
                types.append(event['type'])
                if event['type'] == 'model':
                    model_events.append({key: event[key] for key in ('status', 'reason') if key in event})
                if event['type'] == 'error':
                    errors.append(event.get('code'))
                if event['type'] == 'done':
                    done = True
        with request(f'/api/v1/assistant/conversations/{conversation}/messages') as response:
            messages = json.load(response)
        assistants = [m for m in messages if m['role'] == 'ASSISTANT']
        assert done and not errors and len(assistants) == 1
        answer = assistants[0]
        print('HTTPS_ASSISTANT_RESULT', json.dumps({
            'status': answer['status'], 'model_version': answer['model_version'],
            'model_events': model_events, 'done_receipt': done}), flush=True)
        result['assistant'] = {'scope': args.assistant, 'first_event_ms': first_ms,
            'total_ms': (time.monotonic() - started) * 1000, 'types': sorted(set(types)),
            'archived_status': answer['status'], 'model_version': answer['model_version'],
            'model_events': model_events, 'native_answer_available': answer['status'] == 'AVAILABLE',
            'done_receipt': done, 'financial_answer_body_published': False,
            'selection_contract': answer['evidence'].get('selection_contract')}
    old_cookies = [copy(cookie) for cookie in jar]
    with request('/api/v1/auth/logout', {}) as response:
        assert response.status in (200, 204)
    for cookie in old_cookies:
        jar.set_cookie(cookie)
    try:
        request(f"/api/v1/portfolios/{fixture['portfolio_id']}/valuation")
        raise AssertionError('REVOKED_SESSION_ACCEPTED')
    except urllib.error.HTTPError as error:
        assert error.code == 401
    jar.clear()
    result['invalid_credentials_rejected'] = True
    result['revoked_session_rejected'] = True
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    if args.assistant == 'unavailable':
        assert answer['status'] == 'LLM_UNAVAILABLE'
    elif args.assistant == 'native':
        assert answer['status'] == 'AVAILABLE'
        assert answer['model_version'].startswith('ollama/0.40.11:')
        assert result['assistant']['selection_contract'] == 'PR7_COMPACT_LABEL_SELECTION_V1'
        assert not any(event.get('status') == 'UNAVAILABLE' for event in model_events)
    print('SYNTHETIC_HTTPS_APP_PROBE_PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('SYNTHETIC_HTTPS_APP_PROBE_FAILED:' + type(error).__name__)
        raise SystemExit(1)
