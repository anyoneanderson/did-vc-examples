#!/usr/bin/env python3
"""Create local keys/configuration and fetch the exact Procivis source commit."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
from lab import ROOT, FIXTURE, new_key, public_key, did_jwk, compact


def write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    path.chmod(mode)


def walt():
    root = ROOT / 'runtime/walt'
    if (root / 'ready').exists():
        return
    issuer = new_key()
    for name, port in [('issuer', 18101), ('wallet', 18102), ('verifier', 18103)]:
        write(root / name / 'web.conf', {'webHost': '0.0.0.0', 'webPort': port})
        write(root / name / '_features.conf', {'enabledFeatures': [],
            'disabledFeatures': ['auth', 'wallet2-persistence'] if name == 'wallet' else []})
    write(root / 'issuer/issuer-service.conf', {'baseUrl': 'http://localhost:18101',
        'ciTokenKey': compact({'type': 'jwk', 'jwk': new_key()})})
    write(root / 'issuer/credential-issuer-metadata.conf', {'credentialConfigurations': {'training': {
        'format': 'dc+sd-jwt', 'vct': 'https://training.example/credentials/completion',
        'cryptographic_binding_methods_supported': ['jwk'], 'credential_signing_alg_values_supported': ['ES256'],
        'proof_types_supported': {'jwt': {'proof_signing_alg_values_supported': ['ES256']}}}}})
    write(root / 'issuer/issuer2-profiles.conf', {'profiles': {'training': {
        'name': 'Training completion', 'credentialConfigurationId': 'training',
        'issuerKey': {'type': 'jwk', 'jwk': issuer}, 'issuerDid': did_jwk(issuer), 'credentialData': {},
        'selectiveDisclosure': {'fields': {key: {'sd': True} for key in FIXTURE['claims']}}}}})
    write(root / 'wallet/wallet-service.conf', {'publicBaseUrl': 'http://localhost:18102'})
    write(root / 'verifier/verifier-service.conf', {'urlPrefix': 'http://localhost:18103/verification-session',
        'urlHost': 'openid4vp://authorize', 'clientMetadata': {'client_name': 'Example employer'}})
    write(root / 'issuer-public.json', {'did': did_jwk(issuer), 'jwk': public_key(issuer)})
    (root / 'ready').touch()


def procivis():
    root = ROOT / 'runtime/procivis'
    if not (root / 'ready').exists():
        root.mkdir(parents=True, exist_ok=True)
        password, token = secrets.token_hex(24), secrets.token_hex(32)
        (root / 'token').write_text(token)
        (root / 'token').chmod(0o600)
        (root / 'db.env').write_text('POSTGRES_USER=core\nPOSTGRES_DB=core\nPOSTGRES_PASSWORD=' + password + '\n')
        (root / 'db.env').chmod(0o600)
        config = {'app': {'databaseUrl': 'postgresql://core:' + password + '@database/core',
            'coreBaseUrl': 'http://localhost:18104', 'serverIp': '0.0.0.0', 'serverPort': 18104,
            'traceJson': False, 'traceLevel': 'warn', 'hideErrorResponseCause': False,
            'enableServerInfo': True, 'enableOpenApi': True, 'enableExternalEndpoints': True,
            'enableManagementEndpoints': True, 'enableHistoryCreateEndpoint': True,
            'auth': {'mode': 'UNSAFE_STATIC', 'staticToken': token}},
            'verificationProtocol': {'OPENID4VP_FINAL1': {'params': {'public': {'allowInsecureHttpTransport': True}}}},
            'globalSettings': {'httpClient': {'insecureHttpTransportAllowed': True}},
            'keyStorage': {'INTERNAL': {'params': {'private': {'encryption': secrets.token_hex(32)}}}},
            'format': {'SD_JWT_VC': {'params': {'public': {'leewaySeconds': 2}}}}}
        for key in ['OPENID4VCI_FINAL1', 'OPENID4VCI_FINAL1_HAIP', 'OPENID4VCI_FINAL1_SWIYU']:
            config.setdefault('issuanceProtocol', {})[key] = {'params': {'private': {'encryption': secrets.token_hex(32), 'nonce': {'signingKey': secrets.token_hex(32), 'expirationSeconds': 300, 'leewaySeconds': 0}}}}
        write(root / 'override.json', config)
        (root / 'ready').touch()
    version = json.loads((ROOT / 'versions.json').read_text())['procivis-one']
    source = ROOT / 'runtime/upstream/one-core'
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', '--depth', '1', '--branch', version['release'], version['repository'], str(source)], check=True)
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if actual != version['commit']:
        raise RuntimeError('Upstream source SHA does not match versions.json; use a fresh checkout.')
    subprocess.run(['git', '-C', str(source), 'diff', '--exit-code', 'HEAD'], check=True, stdout=subprocess.DEVNULL)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('implementation', choices=['walt', 'procivis', 'all'], default='all', nargs='?')
    args = parser.parse_args()
    runtime = ROOT / 'runtime'
    runtime.mkdir(exist_ok=True)
    runtime.chmod(0o700)
    if args.implementation in ('walt', 'all'):
        walt()
    if args.implementation in ('procivis', 'all'):
        procivis()
    print('Prepared local configuration. Secrets are under ignored runtime/.')
