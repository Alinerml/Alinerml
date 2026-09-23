from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import public_repositories as repositories


PROFILE = {'login': 'Alinerml', 'public_repos': 1, 'followers': 2, 'following': 3, 'created_at': '2023-06-01T00:00:00Z'}


def repo(name='sample', **overrides):
    row = {'name': name, 'private': False, 'owner': {'login': 'Alinerml'},
           'fork': False, 'stargazers_count': 0, 'forks_count': 1}
    row.update(overrides)
    return row


class PublicRepositoryTests(unittest.TestCase):
    def test_owner_public_filter_fork_totals_and_zero_star_no_extra_requests(self):
        rows = [repo(), repo('forked', fork=True), repo('private', private=True),
                repo('organization', owner={'login': 'organization'})]
        with patch('public_repositories.get_json', side_effect=[dict(PROFILE, public_repos=2), rows]) as request:
            summary, monthly = repositories.collect()
        self.assertEqual(summary['repositories'], 2)
        self.assertEqual(summary['forks'], 1)
        self.assertEqual(summary['received_forks'], 2)
        self.assertEqual(summary['stars'], 0)
        self.assertFalse(monthly)
        self.assertEqual(request.call_count, 2)
        self.assertIn('type=owner', request.call_args.args[0])

    def test_nonzero_stars_use_dates_and_media_type_not_user_details(self):
        stars = [{'user': {'id': 1, 'login': 'not-published'}, 'starred_at': '2026-08-01T00:00:00Z'},
                 {'user': {'id': 2}, 'starred_at': '2026-09-01T00:00:00Z'}]
        with patch('public_repositories.get_json', side_effect=[PROFILE, [repo(stargazers_count=2)], stars]) as request:
            summary, monthly = repositories.collect()
        self.assertEqual(dict(monthly), {'2026-08': 1, '2026-09': 1})
        self.assertEqual(summary['stars'], 2)
        self.assertEqual(request.call_args.args[1], 'application/vnd.github.star+json')

    def test_missing_counts_and_inconsistent_snapshot_fail_instead_of_zero(self):
        with patch('public_repositories.get_json', side_effect=[PROFILE, [repo(stargazers_count=None)]]), \
                self.assertRaisesRegex(ValueError, 'count'):
            repositories.collect()
        with patch('public_repositories.get_json', side_effect=[PROFILE, [repo(stargazers_count=1)], []]), \
                self.assertRaisesRegex(ValueError, 'snapshot'):
            repositories.collect()
        with patch('public_repositories.get_json', side_effect=[PROFILE, []]), \
                self.assertRaisesRegex(ValueError, 'incomplete'):
            repositories.collect()

    def test_pagination_continues_to_completion(self):
        with patch('public_repositories.get_json', side_effect=[[repo(str(i)) for i in range(100)], [repo('last')]]) as request:
            rows = list(repositories.pages('/users/Alinerml/repos?type=owner'))
        self.assertEqual(len(rows), 101)
        self.assertTrue(request.call_args.args[0].endswith('page=2'))

    def test_generated_svg_uses_real_empty_state_and_clear_scope(self):
        with patch('public_repositories.get_json', side_effect=[PROFILE, [repo()]]):
            summary, monthly = repositories.collect()
        with tempfile.TemporaryDirectory() as directory:
            repositories.write_cards(Path(directory), summary, monthly, datetime(2026, 9, 23, tzinfo=timezone.utc))
            files = list(Path(directory, 'github-metrics').glob('*.svg'))
            self.assertEqual(len(files), 2)
            for file in files:
                ET.fromstring(file.read_text())
            stars = Path(directory, 'github-metrics/stargazers.chartist.svg').read_text()
            self.assertIn('No stars yet', stars)
            self.assertIn('removed stars are not included', stars)

    def test_off_domain_redirect_is_rejected_before_credentials_can_follow(self):
        with self.assertRaisesRegex(ValueError, 'outside the GitHub API'):
            repositories.GitHubOnlyRedirects().redirect_request(None, None, 302, '', {}, 'https://example.com')


if __name__ == '__main__':
    unittest.main()
