#!/usr/bin/env python3
"""Wait for JSON APIs and, for Procivis, the packaged Swagger UI assets."""
import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('implementation', choices=['walt', 'procivis'])
args = parser.parse_args()
if args.implementation == 'walt':
    targets = [(port, '/api.json', {}, None) for port in (18101, 18102, 18103)]
else:
    targets = [
        (18104, '/api/config/v1', {'Authorization': 'Bearer ' + (ROOT / 'runtime/procivis/token').read_text()}, None),
        (18104, '/api-docs/openapi.json', {}, None),
        (18104, '/swagger-ui/index.html', {}, b'swagger-ui'),
        (18104, '/swagger-ui/swagger-ui.css', {}, b'.swagger-ui'),
        (18104, '/swagger-ui/swagger-ui-bundle.js', {}, b'SwaggerUIBundle'),
        (18104, '/swagger-ui/swagger-ui-standalone-preset.js', {}, b'SwaggerUIStandalonePreset'),
        (18104, '/swagger-ui/swagger-initializer.js', {}, b'SwaggerUIBundle'),
    ]
for port, path, headers, marker in targets:
    deadline = time.monotonic() + 180
    while True:
        try:
            accept = 'application/json' if marker is None else '*/*'
            req = urllib.request.Request(f'http://localhost:{port}{path}', headers={'Accept': accept, **headers})
            with urllib.request.urlopen(req, timeout=2) as response:
                if marker is None:
                    json.load(response)
                elif marker not in response.read():
                    raise ValueError('Expected Swagger asset content was not returned.')
            break
        except (OSError, ValueError) as error:
            if isinstance(error, urllib.error.HTTPError):
                error.close()
            if time.monotonic() >= deadline:
                raise SystemExit(f'http://localhost:{port}{path} not ready within 180 seconds; inspect compose logs locally.') from error
            time.sleep(1)
print('READY:', args.implementation)
