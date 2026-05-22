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


if __name__ == '__main__':
    main()
