"""Shared HTTP and fixture helpers. Crypto is only for adversarial test inputs."""
import base64
import hashlib
import json
from pathlib import Path
import time
import urllib.error
import urllib.request
import urllib.parse

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT / 'fixtures/training-completion.json').read_text())
CASES = json.loads((ROOT / 'fixtures/cases.json').read_text())


def b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip('=')


def unb64(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def compact(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False)


def new_key():
    key = ec.generate_private_key(ec.SECP256R1()).private_numbers()
    return {'kty': 'EC', 'crv': 'P-256',
            'x': b64(key.public_numbers.x.to_bytes(32, 'big')),
            'y': b64(key.public_numbers.y.to_bytes(32, 'big')),
            'd': b64(key.private_value.to_bytes(32, 'big'))}


def public_key(key):
    return {k: key[k] for k in ('kty', 'crv', 'x', 'y')}


def did_jwk(key):
    return 'did:jwk:' + b64(compact(public_key(key)).encode())


def sign_jwt(payload, key, typ='kb+jwt', extra_header=None):
    message = b64(compact({'alg': 'ES256', 'typ': typ, **(extra_header or {})}).encode()) + '.' + b64(compact(payload).encode())
    signer = ec.derive_private_key(int.from_bytes(unb64(key['d']), 'big'), ec.SECP256R1())
    r, s = utils.decode_dss_signature(signer.sign(message.encode(), ec.ECDSA(hashes.SHA256())))
    return message + '.' + b64(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))


class ApiError(Exception):
    def __init__(self, status, body):
        self.status, self.body = status, body
        # Do not echo response bodies: they can contain tokens and private keys.
        super().__init__(f'HTTP {status}; response available to the runner')


def request(url, data=None, *, method=None, headers=None, form=False):
    if form:
        body = urllib.parse.urlencode(data).encode()
    else:
        body = compact(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method,
          headers={'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded' if form else 'application/json', **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as error:
        raise ApiError(error.code, error.read().decode()) from None


def unpack(sdjwt):
    parts = sdjwt.split('~')
    issuer = json.loads(unb64(parts[0].split('.')[1]))
    disclosures = [json.loads(unb64(x)) for x in parts[1:-1] if x]
    return issuer, disclosures


def mutate_presentation(token, case_id, holder):
    """Keep issuer signature; re-sign KB so only the intended condition changes."""
    parts = token.split('~')
    kb = json.loads(unb64(parts[-1].split('.')[1]))
    if case_id == 'tampered-claim':
        for i in range(1, len(parts) - 1):
            value = json.loads(unb64(parts[i]))
            if value[1] == 'courseId':
                value[2] = 'SEC-999'
                parts[i] = b64(compact(value).encode())
    elif case_id == 'missing-required-claim':
        parts = [parts[0], *[x for x in parts[1:-1] if json.loads(unb64(x))[1] != 'name'], parts[-1]]
    elif case_id == 'wrong-nonce':
        kb['nonce'] = 'different-' + kb['nonce']
    elif case_id == 'wrong-audience':
        kb['aud'] = 'https://other-verifier.example'
    elif case_id == 'missing-key-binding':
        return '~'.join(parts[:-1]) + '~'
    unsigned = '~'.join(parts[:-1]) + '~'
    kb['sd_hash'] = b64(hashlib.sha256(unsigned.encode()).digest())
    return unsigned + sign_jwt(kb, new_key() if case_id == 'wrong-holder-key' else holder)


def business_check(issuer, claims, trusted_issuer):
    if issuer != trusted_issuer:
        return 'REJECT', 'issuer-trust'
    if any(k not in claims for k in FIXTURE['presentation']['requiredClaims']):
        return 'REJECT', 'required-claims'
    if claims['courseId'] not in FIXTURE['acceptance']['acceptedCourseIds'] or claims['name'] != FIXTURE['acceptance']['expectedApplicantName']:
        return 'REJECT', 'business-policy'
    return 'ACCEPT', 'all'


def run_metadata(implementation):
    """Record running image IDs and code hash at execution time, before reporting."""
    import datetime
    import platform
    import subprocess
    files = sorted([*ROOT.glob('scripts/*.py'), *ROOT.glob('walt-id/*.py'),
                    *ROOT.glob('procivis-one/*.py'), *ROOT.glob('fixtures/*.json'),
                    ROOT / 'compose.yaml', ROOT / 'requirements.txt', ROOT / 'versions.json',
                    ROOT / 'procivis-one/Dockerfile'])
    digest = hashlib.sha256()
    for file in files:
        digest.update(str(file.relative_to(ROOT)).encode() + b'\0' + file.read_bytes() + b'\0')
    services = ['issuer', 'wallet', 'verifier'] if implementation == 'walt' else ['core', 'database']
    images = {}
    for service in services:
        container = subprocess.check_output(['docker', 'compose', '--profile', implementation, 'ps', '-q', service], cwd=ROOT, text=True).strip()
        images[service] = subprocess.check_output(['docker', 'inspect', container, '--format', '{{.Image}}'], text=True).strip()
    return {'completedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'sampleCommit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'sampleCodeSha256': digest.hexdigest(), 'runningImageIds': images,
            'os': platform.platform(), 'architecture': platform.machine(), 'python': platform.python_version(),
            'dockerServer': subprocess.check_output(['docker', 'version', '--format', '{{.Server.Version}}'], text=True).strip()}
