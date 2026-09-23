import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import xml.etree.ElementTree as ET

import wakatime


def sample():
    # Synthetic fixtures; these are never written to the profile repository.
    return {
        'is_up_to_date': True,
        'start': '2026-09-15T00:00:00Z',
        'end': '2026-09-21T23:59:59Z',
        'languages': [{'name': 'Python', 'total_seconds': 7200},
                      {'name': 'C<&|`', 'total_seconds': 3600}],
        'editors': [{'name': 'Test Editor', 'total_seconds': 10800}],
        'operating_systems': [{'name': 'Test OS', 'total_seconds': 10800}],
        'projects': [{'name': 'PRIVATE_PROJECT_SENTINEL', 'total_seconds': 10800}],
        'machines': [{'name': '/private/path/sentinel', 'total_seconds': 10800}],
    }


def response(data, status=200):
    stream = io.StringIO(json.dumps({'data': data}))
    stream.status = status
    return stream


class WakaTimeTests(unittest.TestCase):
    def test_no_key_skips_without_network_or_writes(self):
        with patch.dict('os.environ', {}, clear=True), patch('wakatime.urlopen') as network, \
                patch('wakatime.update') as update, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(wakatime.main(), 0)
        network.assert_not_called()
        update.assert_not_called()

    def test_authenticated_request_keeps_key_out_of_url(self):
        with patch('wakatime.urlopen', return_value=response(sample())) as network:
            data = wakatime.fetch_stats('test-only-api-key')
        request = network.call_args.args[0]
        self.assertEqual(request.full_url, wakatime.API_URL)
        self.assertTrue(request.get_header('Authorization').startswith('Basic '))
        self.assertTrue(data['is_up_to_date'])

    def test_stale_stats_retry_then_accept_fresh_result(self):
        stale = sample()
        stale['is_up_to_date'] = False
        with patch('wakatime.urlopen', side_effect=[response(stale, 202), response(sample())]), \
                patch('wakatime.time.sleep') as sleep:
            self.assertTrue(wakatime.fetch_stats('test-only-key')['is_up_to_date'])
        sleep.assert_called_once_with(5)

    def test_stale_stats_never_replace_fresh_output(self):
        stale = sample()
        stale['is_up_to_date'] = False
        with patch('wakatime.urlopen', side_effect=[response(stale) for _ in range(3)]), \
                patch('wakatime.time.sleep'), self.assertRaisesRegex(ValueError, 'still refreshing'):
            wakatime.fetch_stats('test-only-key')

    def test_http_error_does_not_log_response_body_or_credentials(self):
        error = HTTPError('https://example.invalid/private-key', 401, 'secret-body', {}, None)
        with patch.dict('os.environ', {'WAKATIME_API_KEY': 'test-only-key'}), \
                patch('wakatime.urlopen', side_effect=error), patch('wakatime.update') as update, \
                contextlib.redirect_stderr(io.StringIO()) as log:
            self.assertEqual(wakatime.main(), 1)
        self.assertIn('HTTP 401', log.getvalue())
        self.assertNotIn('private-key', log.getvalue())
        self.assertNotIn('secret-body', log.getvalue())
        self.assertNotIn('test-only-key', log.getvalue())
        update.assert_not_called()

    def test_generated_files_only_include_allowed_fields_and_valid_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / 'README.md'
            readme.write_text('before\n' + wakatime.START + '\nold\n' + wakatime.END + '\nafter\n')
            wakatime.update(root, sample())
            updated = readme.read_text()
            self.assertTrue(updated.startswith('before\n' + wakatime.START))
            self.assertTrue(updated.endswith(wakatime.END + '\nafter\n'))
            self.assertIn('66.7%', updated)
            self.assertIn('操作系统', updated)
            self.assertIn('C&lt;&amp;&#124;&#96;', updated)
            for path in root.rglob('*'):
                if path.is_file():
                    content = path.read_text()
                    self.assertNotIn('PRIVATE_PROJECT_SENTINEL', content)
                    self.assertNotIn('/private/path/sentinel', content)
                    if path.suffix == '.svg':
                        ET.fromstring(content)
            before = {p.name: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            wakatime.update(root, sample())
            after = {p.name: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before, after)

    def test_zero_activity_shows_verified_empty_state_and_removes_old_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / 'README.md'
            readme.write_text(wakatime.START + '\n' + wakatime.END)
            wakatime.update(root, sample())
            empty = sample()
            for field, _ in wakatime.FIELDS:
                empty[field] = []
            wakatime.update(root, empty)
            self.assertIn('### 📊 WakaTime', readme.read_text())
            self.assertIn('暂未采集到编程活动', readme.read_text())
            self.assertNotIn('<img', readme.read_text())
            self.assertEqual(list((root / 'profile').glob('*.svg')), [])

    def test_bad_data_or_markers_preserve_all_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            readme = root / 'README.md'
            readme.write_text(wakatime.START + '\n' + wakatime.END)
            wakatime.update(root, sample())
            before = {p.name: p.read_bytes() for p in root.rglob('*') if p.is_file()}
            for value in [float('nan'), float('inf'), -1, True, 'unknown']:
                invalid = copy.deepcopy(sample())
                invalid['languages'][0]['total_seconds'] = value
                with self.subTest(value=value), self.assertRaises(ValueError):
                    wakatime.update(root, invalid)
                self.assertEqual(before, {p.name: p.read_bytes() for p in root.rglob('*') if p.is_file()})
            readme.write_text('missing markers')
            with self.assertRaisesRegex(ValueError, 'markers'):
                wakatime.update(root, sample())
            self.assertEqual(readme.read_text(), 'missing markers')


if __name__ == '__main__':
    unittest.main()
