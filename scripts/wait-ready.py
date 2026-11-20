#!/usr/bin/env python3
"""Wait for successful read-only HTTP responses, not just open TCP ports."""
import argparse
import json
import time
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('implementation', choices=['walt', 'procivis'])
args = parser.parse_args()
if args.implementation == 'walt':
    targets = [(port, '/api.json', {}) for port in (18101, 18102, 18103)]
else:
    targets = [(18104, '/api/config/v1', {'Authorization': 'Bearer ' + (ROOT / 'runtime/procivis/token').read_text()})]
for port, path, headers in targets:
    deadline = time.monotonic() + 180
    while True:
        try:
            req = urllib.request.Request(f'http://localhost:{port}{path}', headers={'Accept': 'application/json', **headers})
            with urllib.request.urlopen(req, timeout=2) as response:
                json.load(response)
            break
        except (OSError, ValueError) as error:
            if time.monotonic() >= deadline:
                raise SystemExit(f'API {port} not ready within 180 seconds; inspect compose logs locally.') from error
            time.sleep(1)
print('READY:', args.implementation)
