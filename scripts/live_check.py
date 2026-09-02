#!/usr/bin/env python3
"""Standalone live dump of the Kamereon API.

Logs in against the live Nissan API and, for every vehicle on the account,
calls every read endpoint and prints all data returned -- both the raw HTTP
response bodies (via the kamereon library's DEBUG logging) and every parsed
attribute on the Vehicle object. No Home Assistant install is required, only
`requests` and `requests_oauthlib`.

Run with the Leaf plugged in and actively charging: `chargePower` (and the
charging speed derived from it) is null when the car is not charging.

Credentials are read from environment variables:
    NISSAN_USERNAME   account email
    NISSAN_PASSWORD   account password
    NISSAN_REGION     region key, default "EU"

DEBUG logging is enabled, so the kamereon library prints every raw HTTP
response body -- including the VIN. Redact before sharing logs publicly.
"""

import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Import `kamereon` as a top-level package. The dotted path
# `custom_components.nissan_connect.kamereon` would execute the integration's
# __init__.py, which imports `homeassistant`; putting the integration directory
# on sys.path imports the library on its own instead.
_INTEGRATION_DIR = Path(__file__).resolve().parent.parent / 'custom_components' / 'nissan_connect'
sys.path.insert(0, str(_INTEGRATION_DIR))

from kamereon import NCISession  # noqa: E402


# Kamereon car-adapter resources documented by renault-api (hacf-fr) but not
# used by the bundled library. A 200 here means a viable new data source.
CANDIDATE_ENDPOINTS = [
    'pressure',              # tyre pressure, 4 wheels
    'res-state',             # vehicle state code
    'charge-history',
    'charges',
    'charge-mode',
    'charging-settings',
    'hvac-settings',
    'hvac-history',
    'hvac-sessions',
    'notification-settings',
]


def _error_detail(resp):
    """One-line error message extracted from a non-200 response body."""
    try:
        body = resp.json()
    except ValueError:
        return ' '.join(resp.text.split())[:200]
    errors = body.get('errors') if isinstance(body, dict) else None
    if errors:
        msgs = [e.get('detail') or e.get('title') or e.get('errorMessage') or ''
                for e in errors if isinstance(e, dict)]
        joined = ' | '.join(m for m in msgs if m)
        if joined:
            return joined[:200]
    return ' '.join(json.dumps(body).split())[:200]


def probe_endpoints(vehicle):
    """GET each candidate car-adapter resource; report which the car exposes.

    Read-only. Prints the HTTP status and body of every candidate. Returns a
    list of (endpoint, status, detail) tuples: status is the HTTP status code
    (or 'ERROR' on a request exception), detail is a short error message for
    any non-200 response.
    """
    base = vehicle.session.settings['car_adapter_base_url']
    headers = {'Content-Type': 'application/vnd.api+json'}
    results = []
    for endpoint in CANDIDATE_ENDPOINTS:
        url = f'{base}v1/cars/{vehicle.vin}/{endpoint}'
        try:
            resp = vehicle._get(url, headers=headers)
        except Exception as exc:
            print(f'  {endpoint:22} ERROR {exc!r}')
            results.append((endpoint, 'ERROR', repr(exc)))
            continue
        print(f'  {endpoint:22} HTTP {resp.status_code}')
        try:
            body = json.dumps(resp.json(), indent=2)
        except ValueError:
            body = resp.text
        print('\n'.join('    ' + line for line in body[:4000].splitlines()))
        detail = '' if resp.status_code == 200 else _error_detail(resp)
        results.append((endpoint, resp.status_code, detail))
    return results


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    )

    username = os.environ.get('NISSAN_USERNAME')
    password = os.environ.get('NISSAN_PASSWORD')
    region = os.environ.get('NISSAN_REGION', 'EU')

    if not username or not password:
        sys.exit('Set NISSAN_USERNAME and NISSAN_PASSWORD environment variables.')

    session = NCISession(region=region)
    session.login(username, password)

    vehicles = session.fetch_vehicles()
    print(f'\nFound {len(vehicles)} vehicle(s) on region {region}.')

    probe_results = {}
    for v in vehicles:
        print(f'\n=== {v} ===')
        # Every read endpoint, each GET-only -- no refresh_* or control calls,
        # so the physical car is never nudged. Each is wrapped individually so
        # one unsupported endpoint does not hide the rest.
        for fetch in (v.fetch_cockpit, v.fetch_location, v.fetch_battery_status,
                      v.fetch_hvac_status, v.fetch_lock_status):
            try:
                fetch()
            except Exception as exc:
                print(f'  {fetch.__name__}() failed: {exc!r}')
        print('  --- parsed Vehicle attributes ---')
        for key, value in sorted(vars(v).items()):
            print(f'  {key:30}: {value!r}')
        print('  --- endpoint probe (renault-api candidates) ---')
        probe_results[str(v)] = probe_endpoints(v)

    print('\n=== ENDPOINT PROBE SUMMARY ===')
    for vin, results in probe_results.items():
        works = [e for e, s, d in results if s == 200]
        fails = [(e, s, d) for e, s, d in results if s != 200]
        print(f'\n{vin}')
        print(f'  works ({len(works)}):')
        for e in works:
            print(f'    {e:22} HTTP 200')
        print(f'  not available ({len(fails)}):')
        for e, s, d in fails:
            label = s if s == 'ERROR' else f'HTTP {s}'
            print(f'    {e:22} {label:9} {d}')


if __name__ == '__main__':
    main()
