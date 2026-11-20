"""An API-only success must not hide missing Swagger files in the image."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import runpy
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlparse

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/wait-ready.py'


class ReadinessTests(unittest.TestCase):
    def run_probe(self, implementation, missing=None, invalid=None):
        requests = []

        def respond(request, **kwargs):
            path = urlparse(request.full_url).path
            requests.append(request)
            if path == missing:
                raise HTTPError(request.full_url, 404, 'Not Found', {}, None)
            if path == invalid:
                return io.BytesIO(b'<html>Missing resource</html>')
            if path.endswith('.json') or path == '/api/config/v1':
                return io.BytesIO(b'{}')
            # All valid markers together; tests target packaging availability,
            # not Swagger's JavaScript behavior (verified in the real browser).
            return io.BytesIO(b'swagger-ui .swagger-ui SwaggerUIBundle SwaggerUIStandalonePreset')

        output = io.StringIO()
        with patch('sys.argv', [str(SCRIPT), implementation]), \
                patch('pathlib.Path.read_text', return_value='test-only-token'), \
                patch('urllib.request.urlopen', side_effect=respond), \
                patch('time.monotonic', side_effect=range(0, 10000, 181)), \
                redirect_stdout(output):
            runpy.run_path(str(SCRIPT), run_name='__main__')
        return requests, output.getvalue()

    def test_api_success_does_not_mask_missing_swagger_assets(self):
        for missing in ['/swagger-ui/index.html', '/swagger-ui/swagger-ui.css',
                        '/swagger-ui/swagger-ui-bundle.js']:
            with self.subTest(path=missing), self.assertRaises(SystemExit) as error:
                self.run_probe('procivis', missing=missing)
            self.assertIn(missing, str(error.exception))

    def test_html_error_page_with_status_200_is_not_ready(self):
        with self.assertRaises(SystemExit):
            self.run_probe('procivis', invalid='/swagger-ui/swagger-ui-bundle.js')

    def test_complete_ui_is_ready_without_sending_token_to_public_assets(self):
        requests, output = self.run_probe('procivis')
        self.assertIn('READY: procivis', output)
        self.assertEqual([urlparse(r.full_url).path for r in requests if r.has_header('Authorization')],
                         ['/api/config/v1'])

    def test_walt_checks_all_three_json_apis(self):
        requests, output = self.run_probe('walt')
        self.assertEqual([urlparse(r.full_url).port for r in requests], [18101, 18102, 18103])
        self.assertIn('READY: walt', output)


if __name__ == '__main__':
    unittest.main()
