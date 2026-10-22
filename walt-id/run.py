#!/usr/bin/env python3
"""Run actual issuer2/wallet2/verifier2 APIs, plus the employer's policy."""
import json
from pathlib import Path
import sys
import time
from urllib.parse import parse_qs, urlparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from console import introduction, step, case_start, case_result, summary
from lab import (ROOT, FIXTURE, CASES, ApiError, request, new_key, did_jwk,
                 compact, unpack, mutate_presentation, business_check)


def api(port, path, data=None):
    return request(f'http://localhost:{port}{path}', data)


def collect_policies(value, result=None):
    result = {} if result is None else result
    if isinstance(value, dict):
        if 'policy_executed' in value:
            result[value['policy_executed']['id']] = value.get('success')
        for child in value.values():
            collect_policies(child, result)
    elif isinstance(value, list):
        for child in value:
            collect_policies(child, result)
    return result


def run_case(case):
    case_id = case['id']
    wallet = api(18102, '/wallet', {})['walletId']
    path = '/wallet/' + wallet
    holder = new_key()
    key_id = api(18102, path + '/keys/import', {'key': {'type': 'jwk', 'jwk': holder}})['keyId']
    now = int(time.time())
    timing = FIXTURE['timingSecondsRelativeToT0']['expired' if case_id == 'expired' else 'valid']
    claims = dict(FIXTURE['claims'])
    if case_id == 'wrong-course':
        claims['courseId'] = 'SEC-999'
    overrides = {'credentialData': {**claims, 'iat': now + timing['issuedAt'], 'exp': now + timing['expiresAt']}}
    if case_id == 'untrusted-issuer':
        other = new_key()
        overrides.update(issuerKey={'type': 'jwk', 'jwk': other}, issuerDid=did_jwk(other))
    offer = api(18101, '/issuer2/credential-offers', {'profileId': 'training', 'authMethod': 'PRE_AUTHORIZED', 'runtimeOverrides': overrides})
    if case_id == 'happy-path':
        step(1, '研修会社が修了証の発行を準備しました。')
    received = api(18102, path + '/credentials/receive', {'offerUrl': offer['credentialOffer'], 'keyId': key_id})
    credential_id = received['credentialIds'][0]
    stored = api(18102, path + '/credentials/' + credential_id)
    assert stored['credential']['credentialData']['email'] == FIXTURE['claims']['email']
    if case_id == 'happy-path':
        step(2, '受講者のウォレットが、メールアドレスを含む修了証を受け取りました。')
    session = api(18103, '/verification-session/create', {'flow_type': 'cross_device', 'core_flow': {
        'expiration_duration': 'PT5M', 'retention_duration': 'PT1H',
        'dcql_query': {'credentials': [{'id': 'training', 'format': 'dc+sd-jwt',
            'meta': {'vct_values': ['https://training.example/credentials/completion']},
            'require_cryptographic_holder_binding': True,
            'claims': [{'path': [key]} for key in FIXTURE['presentation']['requiredClaims']]}]}}})
    if case_id == 'happy-path':
        step(3, '採用企業が氏名・研修コード・修了日の提示を要求しました。')
    url = session['bootstrapAuthorizationRequestUrl']
    vp = api(18102, path + '/credentials/present/build-vp-token', {'requestUrl': url, 'selectedCredentialIds': {'training': [credential_id]}})
    tokens = json.loads(vp['vpToken'])
    token = tokens['training'][0]
    if case_id in {'tampered-claim', 'missing-required-claim', 'wrong-nonce', 'wrong-audience', 'missing-key-binding', 'wrong-holder-key'}:
        token = mutate_presentation(token, case_id, holder)
        tokens['training'][0] = token
    issuer, disclosures = unpack(token)
    disclosed = {value[1]: value[2] for value in disclosures}
    assert 'email' not in issuer and 'email' not in disclosed
    assert FIXTURE['claims']['email'] not in compact(issuer) + compact(disclosures)
    if case_id == 'happy-path':
        step(4, 'ウォレットが作った提示データに、メールアドレスが含まれないことを確認しました。')
    # Same transport for every case, including intentionally invalid tokens.
    params = {k: v[0] for k, v in parse_qs(urlparse(session['fullAuthorizationRequestUrl']).query).items()}
    http_status = 200
    response_error = None
    try:
        request(params['response_uri'], {'vp_token': compact(tokens), 'state': params['state']}, form=True)
    except ApiError as error:
        http_status = error.status
        response_error = error.body
    for _ in range(100):
        status = api(18103, '/verification-session/' + session['sessionId'] + '/info')
        if status['status'] not in {'ACTIVE', 'CREATED', 'PROCESSING'}:
            break
        time.sleep(.1)
    policies = collect_policies(status.get('policy_results', {}))
    collect_policies(status.get('presentation_validation_results', {}), policies)
    if status['status'] == 'SUCCESSFUL':
        trusted = json.loads((ROOT / 'runtime/walt/issuer-public.json').read_text())['did']
        # Only use payload/disclosures after OSS signature, digest and request checks pass.
        decision, check = business_check(issuer['iss'], disclosed, trusted)
    else:
        decision, check = 'REJECT', None
        failed = {name for name, success in policies.items() if success is False}
        checks = {'dc+sd-jwt/exp-check': 'validity', 'dc+sd-jwt/kb-jwt_signature': 'holder-binding',
                  'dc+sd-jwt/nonce-check': 'request-binding', 'dc+sd-jwt/audience-check': 'request-binding'}
        if len(failed) == 1 and next(iter(failed)) in checks:
            check = checks[next(iter(failed))]
        elif response_error and 'Invalid disclosures:' in response_error and 'reachable from the payload hashes' in response_error:
            check = 'integrity'
        elif case_id == 'missing-key-binding' and response_error and 'String does not look like JWS' in response_error:
            check = 'presentation-parser'
        else:
            raise RuntimeError('Verifier failed without the expected diagnostic; inspect local service logs.')
    result = {'caseId': case_id, 'executionStatus': 'COMPLETED', 'expectedDecision': case['expectedDecision'],
              'actualDecision': decision, 'observedCheck': check, 'targetCovered': check == case['targetCheck'], 'ossStatus': status['status'],
              'httpStatus': http_status, 'policies': policies, 'statusReason': status.get('statusReason'),
              'responseError': json.loads(response_error) if response_error else None,
              'emailUndisclosed': True, 'disclosedClaims': sorted(disclosed),
              'evidence': ['issuer2 offer redeemed by wallet2', 'stored credential includes email', 'verifier2 session inspected'],
              'command': '.venv/bin/python walt-id/run.py'}
    return result


def main():
    introduction('walt.id')
    (ROOT / 'runtime/walt-results.json').unlink(missing_ok=True)
    results = []
    for index, case in enumerate(CASES['cases'], 1):
        case_start(index, len(CASES['cases']), case)
        try:
            result = run_case(case)
        except Exception as error:
            result = {'caseId': case['id'], 'executionStatus': 'ERROR', 'actualDecision': None, 'error': str(error)}
            if isinstance(error, ApiError):
                (ROOT / 'runtime/last-api-error.txt').write_text(error.body)
        results.append(result)
        case_result(case, result)
    output = ROOT / 'runtime/walt-results.json'
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
    from lab import run_metadata
    (ROOT / 'runtime/walt-run-meta.json').write_text(json.dumps(run_metadata('walt'), indent=2) + '\n')
    summary(CASES['cases'], results, 'runtime/walt-results.json')
    return 0 if all(r['executionStatus'] == 'COMPLETED' and r['actualDecision'] == c['expectedDecision'] for r,c in zip(results, CASES['cases'])) else 1

if __name__ == '__main__':
    sys.exit(main())
