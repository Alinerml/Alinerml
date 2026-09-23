"""Publish only language/editor/OS aggregates from the authenticated WakaTime user."""

import base64
from datetime import datetime
import html
import json
import math
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET


API_URL = 'https://wakatime.com/api/v1/users/current/stats/last_7_days'
START = '<!--START_SECTION:waka-->'
END = '<!--END_SECTION:waka-->'
FIELDS = (('languages', '语言'), ('editors', '编辑器'), ('operating_systems', '操作系统'))
CARDS = {'languages': 'wakatime-languages.svg', 'editors': 'wakatime-editors.svg'}


def fetch_stats(api_key):
    # Keep credentials out of URLs, exception messages, and saved API responses.
    request = Request(API_URL, headers={
        'Authorization': 'Basic ' + base64.b64encode(api_key.encode()).decode(),
        'Accept': 'application/json',
        'User-Agent': 'Alinerml-profile-wakatime',
    })
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
                status = response.status
        except HTTPError as error:
            raise ValueError(f'WakaTime API returned HTTP {error.code}; existing output kept.') from None
        except (URLError, TimeoutError, OSError, json.JSONDecodeError):
            raise ValueError('WakaTime API could not be read; existing output kept.') from None
        data = payload.get('data') if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise ValueError('WakaTime response is incomplete; existing output kept.')
        if status == 200 and data.get('is_up_to_date') is True:
            return data
        if attempt < 2:
            time.sleep(5)
    raise ValueError('WakaTime stats are still refreshing; retry the workflow later.')


def seconds(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError('WakaTime duration is invalid; existing output kept.')
    if not math.isfinite(value) or value < 0:
        raise ValueError('WakaTime duration is invalid; existing output kept.')
    return value


def aggregates(data):
    """Allowlist public fields; never retain projects, branches, machines, or paths."""
    result = {}
    for field, _ in FIELDS:
        if not isinstance(data.get(field), list):
            raise ValueError('WakaTime breakdown is incomplete; existing output kept.')
        rows = []
        for row in data[field]:
            if not isinstance(row, dict) or not isinstance(row.get('name'), str):
                raise ValueError('WakaTime breakdown is invalid; existing output kept.')
            duration = seconds(row.get('total_seconds'))
            name = ' '.join(row['name'].split())
            if not name:
                raise ValueError('WakaTime category name is empty; existing output kept.')
            if duration:
                rows.append((name, duration))
        result[field] = sorted(rows, key=lambda row: (-row[1], row[0]))
    return result


def duration_text(value):
    minutes = int(value // 60)
    if not minutes:
        return '< 1 min'
    hours, minutes = divmod(minutes, 60)
    return f'{hours} h {minutes} min' if hours else f'{minutes} min'


def card(title, rows, period):
    shown = rows[:6]
    if len(rows) > 6:
        shown.append(('Others', sum(value for _, value in rows[6:])))
    total = sum(value for _, value in rows)
    height = 105 + max(1, len(shown)) * 45
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{height}" viewBox="0 0 480 {height}" role="img" aria-labelledby="title desc">',
             f'<title id="title">{html.escape(title)}</title>',
             f'<desc id="desc">WakaTime, last 7 days: {html.escape(period)}</desc>',
             '<style>text{font-family:Segoe UI,Arial,sans-serif;fill:#24292f;font-size:12px}.title{font-size:18px;fill:#218bff}.sub{fill:#57606a}.track{fill:#eaeef2}@media(prefers-color-scheme:dark){text{fill:#c9d1d9}.sub{fill:#8b949e}.track{fill:#30363d}}</style>',
             f'<text class="title" x="20" y="30">{html.escape(title)}</text>',
             f'<text class="sub" x="20" y="53">{html.escape(period)} · Last 7 days</text>']
    for index, (name, value) in enumerate(shown):
        y = 84 + index * 45
        percent = value / total * 100
        label = name if len(name) <= 28 else name[:27] + '…'
        parts.extend([
            f'<text x="20" y="{y}"><title>{html.escape(name)}</title>{html.escape(label)}</text>',
            f'<text x="460" y="{y}" text-anchor="end">{html.escape(duration_text(value))} · {percent:.1f}%</text>',
            f'<rect class="track" x="20" y="{y + 10}" width="440" height="7" rx="3"/>',
            f'<rect x="20" y="{y + 10}" width="{440 * percent / 100:.2f}" height="7" rx="3" fill="#218bff"/>',
        ])
    if not shown:
        parts.append('<text class="sub" x="20" y="90">No recorded activity in this category</text>')
    parts.append('</svg>')
    svg = '\n'.join(parts) + '\n'
    ET.fromstring(svg)
    return svg


def markdown(data, groups):
    # Display the UTC dates from the API, without guessing the account timezone.
    dates = []
    for field in ('start', 'end'):
        value = data.get(field)
        try:
            dates.append(datetime.fromisoformat(value.replace('Z', '+00:00')).date().isoformat())
        except (AttributeError, TypeError, ValueError):
            raise ValueError('WakaTime dates are invalid; existing output kept.') from None
    period = f'{dates[0]} – {dates[1]} (UTC)'
    if not any(groups.values()):
        return '', {}
    lines = ['### 📊 WakaTime', '', f'最近 7 天 · {period}。仅展示语言、编辑器与操作系统汇总。', '']
    for field, title in FIELDS:
        rows = groups[field]
        total = sum(value for _, value in rows)
        lines.extend([f'**{title}**', '', '| 名称 | 时长 | 占比 |', '| --- | ---: | ---: |'])
        for name, value in rows:
            label = html.escape(name).replace('|', '&#124;').replace('`', '&#96;')
            lines.append(f'| {label} | {html.escape(duration_text(value))} | {value / total * 100:.1f}% |')
        if not rows:
            lines.append('| 暂无记录 | — | — |')
        lines.append('')
    cards = {filename: card('WakaTime · ' + field.title(), groups[field], period)
             for field, filename in CARDS.items()}
    lines.extend(['<p align="center">',
                  '  <img src="profile/wakatime-languages.svg" width="48%" alt="WakaTime 最近 7 天语言统计" />',
                  '  <img src="profile/wakatime-editors.svg" width="48%" alt="WakaTime 最近 7 天编辑器统计" />',
                  '</p>'])
    return '\n'.join(lines), cards


def update(root, data):
    readme = root / 'README.md'
    text = readme.read_text(encoding='utf-8')
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise ValueError('README must contain one ordered pair of waka section markers.')
    content, cards = markdown(data, aggregates(data))
    before, remainder = text.split(START)
    _, after = remainder.split(END)
    updated = before + START + '\n' + content + '\n' + END + after
    destination = root / 'profile'
    if cards:
        destination.mkdir(exist_ok=True)
    for filename in CARDS.values():
        path = destination / filename
        if filename in cards:
            path.write_text(cards[filename], encoding='utf-8')
        elif path.exists():
            path.unlink()
    readme.write_text(updated, encoding='utf-8')


def main():
    api_key = os.environ.get('WAKATIME_API_KEY', '').strip()
    if not api_key:
        print('WAKATIME_API_KEY is not configured; WakaTime update skipped.')
        return 0
    try:
        update(Path(__file__).resolve().parents[1], fetch_stats(api_key))
    except (ValueError, OSError) as error:
        # ValueError messages above are fixed strings, never API error bodies.
        print(str(error) if isinstance(error, ValueError) else 'Could not save WakaTime output.', file=sys.stderr)
        return 1
    print('WakaTime public summaries updated; private project data was not saved.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
