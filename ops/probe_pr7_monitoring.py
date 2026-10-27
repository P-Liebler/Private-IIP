"""Private synthetic monitoring compatibility; credentials arrive through stdin only."""
import asyncio
import json
import sys

import httpx


async def main(control):
    async with httpx.AsyncClient(trust_env=False, timeout=15) as client:
        build = (await client.get('http://prometheus:9090/api/v1/status/buildinfo')).json()
        assert build['status'] == 'success' and build['data']['version'] == '3.15.1'
        target = None
        for _ in range(12):
            result = (await client.get('http://prometheus:9090/api/v1/targets')).json()
            target = next((row for row in result['data']['activeTargets'] if row['labels'].get('job') == 'private-iip-api'), None)
            if target and target['health'] == 'up':
                break
            await asyncio.sleep(5)
        assert target and target['health'] == 'up', 'PROMETHEUS_API_SCRAPE_NOT_UP'
        rules = (await client.get('http://prometheus:9090/api/v1/rules')).json()
        assert rules['status'] == 'success' and rules['data']['groups']
        health = await client.get('http://grafana:3000/api/health')
        assert health.status_code == 200 and health.json()['database'] == 'ok'
        assert health.json()['version'] == '12.4.13'
        anonymous = await client.get('http://grafana:3000/api/search')
        assert anonymous.status_code == 401
        authorized = await client.get('http://grafana:3000/api/datasources/uid/prometheus/health',
            auth=httpx.BasicAuth(control['user'], control['password']))
        assert authorized.status_code == 200 and authorized.json()['status'] == 'OK'
        print(json.dumps({'status': 'PRIVATE_SYNTHETIC_MONITORING_VERIFIED',
            'prometheus_version': build['data']['version'], 'api_scrape_up': True,
            'rule_groups_loaded': len(rules['data']['groups']), 'grafana_version': health.json()['version'],
            'grafana_anonymous_rejected': True, 'grafana_prometheus_health': 'OK',
            'production_scheduler_or_target_host_acceptance': False}))


if __name__ == '__main__':
    asyncio.run(main(json.loads(sys.stdin.readline())))
