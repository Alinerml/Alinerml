"""Render public event samples without relying on the removed PushEvent.commits field.

API limits: https://docs.github.com/en/rest/activity/events
The public timeline contains at most 300 events from the past 30 days and may lag.
"""

from datetime import datetime, timedelta, timezone
from html import escape
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


USER = 'Alinerml'
BEIJING = timezone(timedelta(hours=8))
MAX_PAGES = 3
PER_PAGE = 100


def fetch_events():
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent': 'Alinerml-public-profile',
    }
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    result = []
    seen = set()
    for page in range(1, MAX_PAGES + 1):
        url = f'https://api.github.com/users/{USER}/events/public?per_page={PER_PAGE}&page={page}'
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                batch = json.load(response)
        except HTTPError as error:
            raise ValueError(f'GitHub public events API returned HTTP {error.code}; previous cards kept.') from None
        except (URLError, OSError, json.JSONDecodeError):
            raise ValueError('GitHub public events API could not be read; previous cards kept.') from None
        if not isinstance(batch, list):
            raise ValueError('GitHub public events API returned an unexpected result.')
        for event in batch:
            if not isinstance(event, dict):
                continue
            event_id = event.get('id')
            if isinstance(event_id, str) and event_id and event_id not in seen:
                seen.add(event_id)
                result.append(event)
        if len(batch) < PER_PAGE:
            break
    return result[:MAX_PAGES * PER_PAGE]


def public_sample(events, now):
    """Copy only necessary public fields; do not read event payloads or messages."""
    result = []
    seen = set()
    for event in events:
        actor = event.get('actor') or {}
        repo = event.get('repo') or {}
        if not isinstance(actor, dict) or not isinstance(repo, dict):
            continue
        if event.get('public') is not True or actor.get('login', '').casefold() != USER.casefold():
            continue
        if actor.get('type') == 'Bot':
            continue
        event_id = event.get('id')
        name, kind, timestamp = repo.get('name'), event.get('type'), event.get('created_at')
        if not all(isinstance(value, str) and value for value in (event_id, name, kind, timestamp)):
            continue
        try:
            created = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except ValueError:
            continue
        if created.tzinfo is None or not now - timedelta(days=30) <= created <= now:
            continue
        if event_id in seen:
            continue
        seen.add(event_id)
        result.append({'type': kind, 'repo': name, 'created': created.astimezone(BEIJING)})
    return sorted(result, key=lambda item: item['created'], reverse=True)[:300]


def text(x, y, value, cls='', **attrs):
    attributes = ' '.join(f'{key.replace("_", "-")}="{escape(str(value), quote=True)}"' for key, value in attrs.items())
    return f'<text x="{x}" y="{y}" class="{cls}" {attributes}>{escape(str(value))}</text>'


def base(title, description, height):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}" viewBox="0 0 480 {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;font-size:12px;fill:#24292f}.title{font-size:18px;fill:#218bff}.sub{font-size:11px;fill:#57606a}.label{font-weight:600}.track{fill:#eaeef2}.bar{fill:#218bff}.line{stroke:#d0d7de}@media(prefers-color-scheme:dark){text{fill:#c9d1d9}.sub{fill:#8b949e}.track{fill:#30363d}.line{stroke:#30363d}}</style>',
        text(20, 30, title, 'title'),
    ]


def short(value, limit):
    return value if len(value) <= limit else value[:limit - 1] + '…'


def scope_lines(sample, now, y):
    checked = now.astimezone(BEIJING).strftime('%Y-%m-%d %H:%M')
    return [
        text(20, y, f'API sample: {len(sample)} public events · up to 300 / 30 days', 'sub'),
        text(20, y + 18, 'Public actor: Alinerml · timestamps: Beijing (UTC+8)', 'sub'),
        text(20, y + 36, f'Fetched {checked} · API may lag; incomplete history', 'sub'),
    ]


def activity_svg(sample, now):
    parts = base('Recent public activity', 'Latest five public GitHub events by Alinerml, from a limited API sample.', 456)
    parts.extend(scope_lines(sample, now, 53))
    for index, event in enumerate(sample[:5]):
        y = 126 + index * 62
        parts.append(text(20, y, short(event['type'], 25), 'label'))
        parts.append(text(460, y, event['created'].strftime('%m-%d %H:%M'), 'sub', text_anchor='end'))
        parts.append(f'<g><title>{escape(event["repo"])}</title>{text(20, y + 21, short(event["repo"], 58), "sub")}</g>')
        parts.append(f'<line class="line" x1="20" y1="{y + 35}" x2="460" y2="{y + 35}"/>')
    if not sample:
        parts.append(text(20, 145, 'No matching public events in this API sample.', 'sub'))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def push_counts(sample):
    hours, weekdays = [0] * 24, [0] * 7
    for event in sample:
        if event['type'] == 'PushEvent':
            hours[event['created'].hour] += 1
            weekdays[event['created'].weekday()] += 1
    return hours, weekdays


def habits_svg(sample, now):
    hours, weekdays = push_counts(sample)
    total = sum(hours)
    parts = base('Public push events · last 30 days', 'Hourly and weekday counts of public PushEvent entries by Alinerml; not commits or coding time.', 534)
    parts.extend(scope_lines(sample, now, 53))
    parts.append(text(20, 120, f'{total} push events in sample · not commits or coding time', 'label'))
    parts.append(text(20, 149, 'Hour of day · Beijing time', 'sub'))
    max_hour = max(max(hours), 1)
    for hour, count in enumerate(hours):
        x = 20 + hour * 18.4
        height = count / max_hour * 78
        parts.append(f'<rect class="track" x="{x:.1f}" y="166" width="12" height="78" rx="2"/>')
        parts.append(f'<rect class="bar" x="{x:.1f}" y="{244 - height:.1f}" width="12" height="{height:.1f}" rx="2"><title>{hour:02d}:00 — {count} push events</title></rect>')
        if hour % 3 == 0:
            parts.append(text(f'{x + 6:.1f}', 264, f'{hour:02d}', 'sub', text_anchor='middle'))
    parts.append(text(20, 297, 'Day of week · Beijing time', 'sub'))
    max_weekday = max(max(weekdays), 1)
    for day, (label, count) in enumerate(zip(('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'), weekdays)):
        y = 314 + day * 25
        parts.append(text(20, y + 10, label, 'sub'))
        parts.append(f'<rect class="track" x="65" y="{y}" width="350" height="11" rx="3"/>')
        parts.append(f'<rect class="bar" x="65" y="{y}" width="{350 * count / max_weekday:.1f}" height="11" rx="3"/>')
        parts.append(text(460, y + 10, count, 'sub', text_anchor='end'))
    if not total:
        parts.append(text(20, 512, 'No public push events in this API sample.', 'sub'))
    else:
        parts.append(text(20, 512, 'Frequency within returned events; not a complete activity record.', 'sub'))
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'


def write_cards(root, events, now):
    sample = public_sample(events, now)
    cards = {'activity.svg': activity_svg(sample, now), 'habits.charts.svg': habits_svg(sample, now)}
    for value in cards.values():
        ET.fromstring(value)
    destination = root / 'github-metrics'
    destination.mkdir(exist_ok=True)
    for name, value in cards.items():
        destination.joinpath(name).write_text(value, encoding='utf-8')
    return len(sample), sum(push_counts(sample)[0])


def main():
    try:
        events = fetch_events()
        count, pushes = write_cards(Path(__file__).resolve().parents[1], events, datetime.now(timezone.utc))
    except (ValueError, OSError) as error:
        print(str(error) if isinstance(error, ValueError) else 'Could not save public activity cards.', file=sys.stderr)
        return 1
    print(f'Validated public activity cards: {count} owner events, {pushes} push events in the API sample.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
