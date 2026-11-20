"""Ensure adversarial inputs change one property while retaining valid KB proofs."""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, utils
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from lab import b64, unb64, compact, new_key, sign_jwt, mutate_presentation, unpack, business_check, FIXTURE


def verify(token, key):
    head, body, signature = token.split('.')
    sig = unb64(signature)
    public = ec.EllipticCurvePublicNumbers(int.from_bytes(unb64(key['x']), 'big'),
        int.from_bytes(unb64(key['y']), 'big'), ec.SECP256R1()).public_key()
    public.verify(utils.encode_dss_signature(int.from_bytes(sig[:32], 'big'), int.from_bytes(sig[32:], 'big')),
                  (head + '.' + body).encode(), ec.ECDSA(hashes.SHA256()))


class MutationTests(unittest.TestCase):
    def setUp(self):
        self.issuer, self.holder = new_key(), new_key()
        self.disclosures = [b64(compact(['unique-salt-' + k, k, v]).encode()) for k,v in FIXTURE['claims'].items() if k != 'email']
        signed = sign_jwt({'_sd': [b64(hashlib.sha256(d.encode()).digest()) for d in self.disclosures]}, self.issuer, 'dc+sd-jwt')
        unsigned = signed + '~' + '~'.join(self.disclosures) + '~'
        self.token = unsigned + sign_jwt({'iat': 1, 'nonce': 'expected-nonce', 'aud': 'expected-audience',
            'sd_hash': b64(hashlib.sha256(unsigned.encode()).digest())}, self.holder)

    def test_disclosure_mutations_retain_issuer_signature_and_correct_key_binding(self):
        for case in ['tampered-claim', 'missing-required-claim']:
            with self.subTest(case=case):
                result = mutate_presentation(self.token, case, self.holder)
                self.assertEqual(result.split('~')[0], self.token.split('~')[0])
                verify(result.split('~')[0], self.issuer)
                verify(result.split('~')[-1], self.holder)
                kb = json.loads(unb64(result.split('~')[-1].split('.')[1]))
                self.assertEqual(kb['sd_hash'], b64(hashlib.sha256((result.rsplit('~', 1)[0]+'~').encode()).digest()))
                issuer, disclosures = unpack(result)
                if case == 'tampered-claim':
                    changed = next(d for d in result.split('~')[1:-1] if json.loads(unb64(d))[1] == 'courseId')
                    self.assertNotIn(b64(hashlib.sha256(changed.encode()).digest()), issuer['_sd'])
                else:
                    self.assertNotIn('name', [d[1] for d in disclosures])

    def test_wrong_request_changes_only_nonce_or_audience(self):
        original = json.loads(unb64(self.token.split('~')[-1].split('.')[1]))
        for case, field in [('wrong-nonce', 'nonce'), ('wrong-audience', 'aud')]:
            result = mutate_presentation(self.token, case, self.holder)
            verify(result.split('~')[-1], self.holder)
            changed = json.loads(unb64(result.split('~')[-1].split('.')[1]))
            self.assertEqual({k for k in original if changed[k] != original[k]}, {field})

    def test_wrong_holder_signature_fails_but_issuer_signature_remains_valid(self):
        result = mutate_presentation(self.token, 'wrong-holder-key', self.holder)
        verify(result.split('~')[0], self.issuer)
        with self.assertRaises(InvalidSignature):
            verify(result.split('~')[-1], self.holder)

    def test_missing_key_binding_preserves_issuer_and_disclosures(self):
        self.assertEqual(mutate_presentation(self.token, 'missing-key-binding', self.holder), self.token.rsplit('~', 1)[0]+'~')

    def test_valid_signature_alone_does_not_satisfy_employer_policy(self):
        for issuer, claims, expected in [
            ('other', FIXTURE['claims'], 'issuer-trust'),
            ('trusted', {k:v for k,v in FIXTURE['claims'].items() if k != 'name'}, 'required-claims'),
            ('trusted', {**FIXTURE['claims'], 'courseId': 'SEC-999'}, 'business-policy'),
            ('trusted', {**FIXTURE['claims'], 'name': 'different applicant'}, 'business-policy')]:
            self.assertEqual(business_check(issuer, claims, 'trusted'), ('REJECT', expected))

if __name__ == '__main__':
    unittest.main()
