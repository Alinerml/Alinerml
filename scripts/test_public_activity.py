from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import public_activity as activity


NOW = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)


def event(event_id='1', **overrides):
    data = {'id': event_id, 'type': 'PushEvent', 'public': True,
            'actor': {'login': 'Alinerml'}, 'repo': {'name': 'Alinerml/Example<&'},
            'created_at': '2026-09-22T18:30:00Z',
            'payload': {'irrelevant': 'PRIVATE_COMMIT_MESSAGE'}}
    data.update(overrides)
    return data


class PublicActivityTests(unittest.TestCase):
    def test_only_owner_public_events_within_window_are_counted(self):
        rows = [event(), event(), event('2', public=False),
                event('3', actor={'login': 'github-actions[bot]'}),
                event('4', actor={'login': 'Alinerml', 'type': 'Bot'}),
                event('5', created_at='2026-07-01T00:00:00Z'),
                event('6', created_at='2027-01-01T00:00:00Z')]
        sample = activity.public_sample(rows, NOW)
        self.assertEqual(len(sample), 1)
        self.assertNotIn('payload', sample[0])
        self.assertEqual(sample[0]['created'].hour, 2)
        hours, weekdays = activity.push_counts(sample)
        self.assertEqual(hours[2], 1)
        self.assertEqual(weekdays[2], 1)  # Tuesday UTC becomes Wednesday in Beijing.

    def test_pagination_is_limited_and_duplicates_are_removed(self):
        batches = [[event(str(index)) for index in range(100)],
                   [event(str(index)) for index in range(50, 150)],
                   [event(str(index)) for index in range(100, 200)]]
        with patch('public_activity.urlopen', side_effect=[io.StringIO(json.dumps(batch)) for batch in batches]) as network:
            rows = activity.fetch_events()
        self.assertEqual(len(rows), 200)
        self.assertEqual(network.call_count, 3)
        self.assertTrue(network.call_args.args[0].full_url.endswith('page=3'))

    def test_recent_activity_uses_only_latest_five_and_escapes_external_text(self):
        rows = [event(str(index), type='Public<&Event', repo={'name': f'Alinerml/repo-{index}<&'},
                      created_at=f'2026-09-{16 + index:02d}T00:00:00Z') for index in range(7)]
        with tempfile.TemporaryDirectory() as directory:
            count, pushes = activity.write_cards(Path(directory), rows, NOW)
            self.assertEqual((count, pushes), (7, 0))
            recent = Path(directory, 'github-metrics/activity.svg').read_text()
            self.assertIn('repo-6&lt;&amp;', recent)
            self.assertNotIn('repo-0', recent)
            self.assertNotIn('repo-1', recent)
            self.assertNotIn('PRIVATE_COMMIT_MESSAGE', recent)
            for file in Path(directory, 'github-metrics').glob('*.svg'):
                ET.fromstring(file.read_text())

    def test_empty_sample_is_an_honest_empty_state(self):
        recent = activity.activity_svg([], NOW)
        habits = activity.habits_svg([], NOW)
        self.assertIn('No matching public events', recent)
        self.assertIn('No public push events', habits)
        self.assertIn('0 push events in sample', habits)
        self.assertIn('up to 300 / 30 days', habits)
        ET.fromstring(recent)
        ET.fromstring(habits)


if __name__ == '__main__':
    unittest.main()
