"""Bounded actual Prometheus scrape check, run inside the isolated QA API."""
import json
import time
import urllib.error
import urllib.request

deadline = time.monotonic() + 50
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen('http://prometheus:9090/api/v1/targets', timeout=5) as response:
            value = json.load(response)
        if any(target['health'] == 'up' and target.get('labels', {}).get('job') == 'private-iip-api'
               for target in value['data']['activeTargets']):
            print('ACTUAL_CORE_PROMETHEUS_TARGET_UP')
            break
    except (OSError, ValueError, KeyError):
        pass
    time.sleep(2)
else:
    raise SystemExit('CORE_PROMETHEUS_TARGET_NOT_UP')
