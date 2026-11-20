#!/usr/bin/env python3
"""Export sanitized observations; never copy tokens, keys or raw service logs."""
import datetime
import json
import platform
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[1]
versions = json.loads((ROOT / 'versions.json').read_text())
walt = json.loads((ROOT / 'runtime/walt-results.json').read_text())
procivis = json.loads((ROOT / 'runtime/procivis-results.json').read_text())
allowed = {'caseId', 'executionStatus', 'expectedDecision', 'actualDecision', 'observedCheck', 'targetCovered',
           'ossStatus', 'httpStatus', 'policies', 'emailUndisclosed', 'disclosedClaims', 'evidence', 'command', 'holder'}
implementations = []
for name, cases in [('walt-id', walt), ('procivis-one', procivis['cases'])]:
    if len(cases) != 10 or any(case['executionStatus'] != 'COMPLETED' for case in cases):
        raise SystemExit('Incomplete run: preserve runtime results and investigate; report not overwritten.')
    meta = json.loads((ROOT / ('runtime/walt-run-meta.json' if name == 'walt-id' else 'runtime/procivis-run-meta.json')).read_text())
    implementations.append({'runMetadata': meta, 'id': name, 'status': 'MEASURED_WITH_LIMITATIONS',
        'version': versions[name]['release'], 'commit': versions[name]['commit'],
        'cases': [{k: v for k, v in case.items() if k in allowed} for case in cases]})
image = implementations[1]['runMetadata']['runningImageIds']['core']
result = {'schemaVersion': 1, 'scenarioId': 'training-completion-v1',
          'recordedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'sampleCommit': implementations[0]['runMetadata']['sampleCommit'],
          'environment': {'os': platform.platform(), 'architecture': platform.machine(), 'python': platform.python_version(),
                          'dockerServer': subprocess.check_output(['docker', 'version', '--format', '{{.Server.Version}}'], text=True).strip()},
          'procivisLocalImageId': image, 'procivisNativeWallet': procivis['nativeWallet'],
          'clockSkewSeconds': 2, 'issuerTrustSetup': 'Out-of-band pin of fresh did:jwk (walt) / did:key (Procivis)',
          'holderKeyStorage': 'Local ephemeral server memory or PostgreSQL; controlled test client memory for Procivis mutations',
          'implementations': implementations}
(ROOT / 'results/implementation-status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
for item in implementations:
    correct = sum(c['actualDecision'] == c['expectedDecision'] for c in item['cases'])
    covered = sum(c['targetCovered'] for c in item['cases'])
    print(f"{item['id']}: {correct}/10 expected decisions; {covered}/10 target checks observed")
print('Sanitized report written. Review docs/results.md for the two coverage limits.')
