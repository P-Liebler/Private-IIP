"""Readiness must report the deliberately stopped synthetic dependency explicitly."""
import argparse
import json
from pathlib import Path
import ssl
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ca', type=Path, required=True)
    parser.add_argument('--component', choices=('database', 'minio'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    context = ssl.create_default_context(cafile=str(args.ca))
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPSHandler(context=context))
    try:
        opener.open('https://localhost:9443/api/v1/health/ready', timeout=20)
        raise AssertionError('DEPENDENCY_OUTAGE_NOT_REPORTED')
    except urllib.error.HTTPError as error:
        body = json.load(error)
        assert error.code == 503 and body['status'] == 'degraded'
        assert body['services'][args.component] == 'unavailable'
    args.output.write_text(json.dumps({'status': 'SYNTHETIC_DEPENDENCY_OUTAGE_REPORTED',
        'component': args.component, 'http_status': 503, 'strict_ca': True,
        'scope': 'READINESS_ONLY_RECOVERY_VALUATION_SEPARATE'}, indent=2))
    print('SYNTHETIC_DEPENDENCY_OUTAGE_PROBE_PASS')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('SYNTHETIC_DEPENDENCY_OUTAGE_PROBE_FAILED:' + type(error).__name__)
        raise SystemExit(1)
