#!/usr/bin/env python3
"""Native wallet roundtrip plus controlled protocol client for negative cases."""
import hashlib
import json
from pathlib import Path
import sys
import time
import subprocess
import uuid
from urllib.parse import parse_qs, urlparse
import urllib.request
from jwcrypto import jwk, jwe
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lab import (ROOT, FIXTURE, CASES, ApiError, request, new_key, public_key,
                 compact, b64, unb64, sign_jwt, unpack, mutate_presentation, business_check)
BASE = 'http://localhost:18104'


def api(path, data=None):
    token = (ROOT / 'runtime/procivis/token').read_text()
    return request(BASE + path, data, headers={'Authorization': 'Bearer ' + token})


def identity(org, role):
    key = api('/api/key/v1', {'keyParams': {}, 'keyType': 'ECDSA', 'name': role,
        'organisationId': org, 'storageParams': {}, 'storageType': 'INTERNAL'})['id']
    body = {'name': role, 'organisationId': org}
    if role == 'holder':
        body['key'] = {'keyId': key}
    else:
        body['did'] = {'method': 'KEY', 'keys': {name: [key] for name in
            ('authentication', 'assertionMethod', 'keyAgreement', 'capabilityInvocation', 'capabilityDelegation')}}
    return api('/api/identifier/v1', body)['id']


def setup(case_id):
    org = api('/api/organisation/v1', {})['id']
    issuer = identity(org, 'issuer')
    trusted_did = api('/api/identifier/v1/' + issuer)['did']['did']
    schema = api('/api/credential-schema/v2', {'claims': [
        {'datatype': 'STRING', 'key': key, 'required': True} for key in FIXTURE['claims']],
        'formats': [{'format': 'SD_JWT_VC'}], 'expiration': 1 if case_id == 'expired' else 3600,
        'allowSuspension': False, 'allowRevocation': False, 'name': 'Training completion', 'organisationId': org})['id']
    schema_data = api('/api/credential-schema/v2/' + schema)
    ids = {claim['key']: claim['id'] for claim in schema_data['claims']}
    proof_schema = api('/api/proof-schema/v1', {'name': 'Training request', 'organisationId': org,
        'proofInputSchemas': [{'claimSchemas': [{'id': ids[key], 'required': True} for key in
            FIXTURE['presentation']['requiredClaims']], 'credentialSchemaId': schema}]})['id']
    claims = dict(FIXTURE['claims'])
    if case_id == 'wrong-course':
        claims['courseId'] = 'SEC-999'
    signing_issuer = identity(org, 'other-issuer') if case_id == 'untrusted-issuer' else issuer
    credential_id = api('/api/credential/v1', {'claimValues': [
        {'claimId': ids[key], 'path': key, 'value': value} for key, value in claims.items()],
        'credentialSchemaId': schema, 'protocol': 'OPENID4VCI_FINAL1', 'issuer': signing_issuer})['id']
    offer_url = api('/api/credential/v1/' + credential_id + '/share', {})['url']
    return {'org': org, 'issuer': issuer, 'trustedDid': trusted_did, 'schema': schema,
            'proofSchema': proof_schema, 'offerUrl': offer_url}


def proof_request(context):
    proof = api('/api/proof-request/v1', {'proofSchemaId': context['proofSchema'],
        'protocol': 'OPENID4VP_FINAL1', 'transport': ['HTTP'], 'verifier': context['issuer']})['id']
    url = api('/api/proof-request/v1/' + proof + '/share', {})['url']
    return proof, url


def native_roundtrip():
    context = setup('happy-path')
    org = api('/api/organisation/v1', {})['id']
    holder = identity(org, 'holder')
    invite = api('/api/interaction/v1/handle-invitation', {'organisationId': org,
        'transport': ['HTTP'], 'url': context['offerUrl']})
    held = api('/api/interaction/v1/issuance-accept', {'identifierId': holder, 'interactionId': invite['interactionId']})['id']
    proof, url = proof_request(context)
    invitation = api('/api/interaction/v1/handle-invitation', {'organisationId': org, 'transport': ['HTTP'], 'url': url})
    definition = api('/api/proof-request/v2/' + invitation['proofId'] + '/presentation-definition')
    query = next(iter(definition['credentialQueries']))
    api('/api/interaction/v2/presentation-submit', {'interactionId': invitation['interactionId'],
        'submission': {query: [{'credentialId': held}]}})
    result = api('/api/proof-request/v1/' + proof)
    claims = {c['path']: c['value'] for c in result['proofInputs'][0]['claims']}
    assert result['state'] == 'ACCEPTED'
    assert claims == {k: FIXTURE['claims'][k] for k in FIXTURE['presentation']['requiredClaims']}
    return {'executionStatus': 'COMPLETED', 'ossStatus': result['state'],
            'holder': 'Procivis Core wallet API', 'verifiedClaimNames': sorted(claims),
            'wireInspection': 'Native encrypted VP not decrypted by harness; controlled-client cases inspect plaintext before encryption.'}


def receive_controlled(context, holder):
    # This test client owns its key, allowing one-condition-at-a-time KB mutations.
    offer = request(parse_qs(urlparse(context['offerUrl']).query)['credential_offer_uri'][0])
    issuer = offer['credential_issuer']
    parsed = urlparse(issuer)
    metadata = request(parsed._replace(path='/.well-known/openid-credential-issuer' + parsed.path).geturl())
    auth = request(parsed._replace(path='/.well-known/oauth-authorization-server' + parsed.path).geturl())
    pre = offer['grants']['urn:ietf:params:oauth:grant-type:pre-authorized_code']['pre-authorized_code']
    access = request(auth['token_endpoint'], {'grant_type': 'urn:ietf:params:oauth:grant-type:pre-authorized_code',
        'pre-authorized_code': pre}, form=True)
    nonce = request(metadata['nonce_endpoint'], {})['c_nonce']
    proof = sign_jwt({'aud': issuer, 'nonce': nonce, 'iat': int(time.time())}, holder,
                     'openid4vci-proof+jwt', {'jwk': public_key(holder)})
    issued = request(metadata['credential_endpoint'], {'credential_configuration_id': offer['credential_configuration_ids'][0],
        'proofs': {'jwt': [proof]}}, headers={'Authorization': 'Bearer ' + access['access_token']})
    return issued['credentials'][0]['credential']


def run_case(case):
    case_id = case['id']
    context = setup(case_id)
    holder = new_key()
    credential = receive_controlled(context, holder)
    core, full_disclosures = unpack(credential)
    assert any(d[1:] == ['email', FIXTURE['claims']['email']] for d in full_disclosures)
    proof, request_url = proof_request(context)
    # Request is fetched only from the local verifier we just invoked. This test
    # harness is not a general wallet: it does not implement request JWT trust.
    url = parse_qs(urlparse(request_url).query)['request_uri'][0]
    with urllib.request.urlopen(urllib.request.Request(url, headers={'Accept': 'application/oauth-authz-req+jwt'}), timeout=30) as response:
        auth_request = json.loads(unb64(response.read().decode().split('.')[1]))
    if case_id == 'expired':
        # Public API exposes TTL via schema expiration, not per-VC iat/exp.
        # Wait for a legitimately issued short-lived credential to expire.
        delay = core['exp'] + 3 - time.time()
        if delay > 0:
            time.sleep(delay)
    selected = [d for d in credential.split('~')[1:] if d and
                json.loads(unb64(d))[1] in FIXTURE['presentation']['requiredClaims']]
    unsigned = credential.split('~')[0] + '~' + '~'.join(selected) + '~'
    token = unsigned + sign_jwt({'iat': int(time.time()), 'nonce': auth_request['nonce'],
        'aud': auth_request['client_id'], 'sd_hash': b64(hashlib.sha256(unsigned.encode()).digest())}, holder)
    if case_id in {'tampered-claim', 'missing-required-claim', 'wrong-nonce', 'wrong-audience', 'missing-key-binding', 'wrong-holder-key'}:
        token = mutate_presentation(token, case_id, holder)
    issuer, disclosures = unpack(token)
    disclosed = {value[1]: value[2] for value in disclosures}
    assert 'email' not in issuer and 'email' not in disclosed
    assert FIXTURE['claims']['email'] not in compact(issuer) + compact(disclosures)
    query = auth_request['dcql_query']['credentials'][0]['id']
    key = auth_request['client_metadata']['jwks']['keys'][0]
    envelope = jwe.JWE(compact({'vp_token': {query: [token]}, 'state': auth_request['state']}).encode(),
        protected=compact({'alg': 'ECDH-ES', 'enc': 'A256GCM', 'kid': key['kid'],
                           'apu': b64(b'local-test-client'), 'apv': b64(auth_request['nonce'].encode())}))
    envelope.add_recipient(jwk.JWK(**key))
    http_status, error_body = 200, None
    request_id = str(uuid.uuid4())
    try:
        request(auth_request['response_uri'], {'response': envelope.serialize(compact=True)}, form=True, headers={'X-Request-Id': request_id})
    except ApiError as error:
        http_status = error.status
        try:
            error_body = json.loads(error.body)
        except json.JSONDecodeError:
            error_body = {'text': error.body[:1000]}
    status = api('/api/proof-request/v1/' + proof)
    if status['state'] == 'ACCEPTED':
        decision, observed = business_check(issuer['iss'], disclosed, context['trustedDid'])
    else:
        decision, observed = 'REJECT', None
        # Server omits detailed causes from some HTTP responses. Match only the
        # correlated request's logs and retain a fixed diagnostic label, not raw logs.
        logs = subprocess.run(['docker', 'compose', '--profile', 'procivis', 'logs', '--no-color', '--since', '2m', 'core'],
                              cwd=ROOT, capture_output=True, text=True, check=True)
        correlated = '\n'.join(line for line in (logs.stdout + logs.stderr).splitlines() if request_id in line)
        patterns = {'Required claim not submitted': 'required-claims',
                    'ValidationError("Expired")': 'validity',
                    'verifying SD-JWT key binding token': 'holder-binding',
                    'Invalid key binding token nonce': 'request-binding',
                    'Invalid key binding token aud': 'request-binding',
                    'Missing key binding token': 'holder-binding'}
        observed = next((check for pattern, check in patterns.items() if pattern in correlated.replace('\\"', '"')), None)
        if observed is None:
            raise RuntimeError('Verifier failed without a correlated diagnostic; inspect local service logs.')
    return {'caseId': case_id, 'executionStatus': 'COMPLETED', 'actualDecision': decision,
            'expectedDecision': case['expectedDecision'], 'observedCheck': observed, 'targetCovered': observed == case['targetCheck'], 'ossStatus': status['state'],
            'httpStatus': http_status, 'responseError': error_body, 'holder': 'Python adversarial protocol client',
            'emailUndisclosed': True, 'disclosedClaims': sorted(disclosed),
            'command': '.venv/bin/python procivis-one/run.py',
            'evidence': ['Procivis issuer credential response', 'plaintext VP excludes email', 'Procivis verifier proof request inspected']}


def main():
    (ROOT / 'runtime/procivis-results.json').unlink(missing_ok=True)
    native = native_roundtrip()
    print('native-wallet', native['ossStatus'], flush=True)
    results = []
    for case in CASES['cases']:
        try:
            result = run_case(case)
        except Exception as error:
            result = {'caseId': case['id'], 'executionStatus': 'ERROR', 'actualDecision': None, 'error': str(error)}
            if isinstance(error, ApiError):
                (ROOT / 'runtime/last-api-error.txt').write_text(error.body)
        results.append(result)
        print(case['id'], result['executionStatus'], result.get('actualDecision'), result.get('ossStatus', ''), 'target=' + str(result.get('targetCovered')), flush=True)
    (ROOT / 'runtime/procivis-results.json').write_text(json.dumps({'nativeWallet': native, 'cases': results}, ensure_ascii=False, indent=2) + '\n')
    from lab import run_metadata
    (ROOT / 'runtime/procivis-run-meta.json').write_text(json.dumps(run_metadata('procivis'), indent=2) + '\n')
    return 0 if all(r['executionStatus'] == 'COMPLETED' and r['actualDecision'] == c['expectedDecision'] for r,c in zip(results, CASES['cases'])) else 1

if __name__ == '__main__':
    sys.exit(main())
