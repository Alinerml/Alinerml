"""Accurate public owned-repository totals and current stars, using GitHub REST."""

from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET

from public_activity import USER, base, text


class GitHubOnlyRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        target = urlparse(url)
        if target.scheme != 'https' or target.hostname != 'api.github.com':
            raise ValueError('Refusing a redirect outside the GitHub API.')
        return super().redirect_request(request, response, code, message, headers, url)


def get_json(path, accept='application/vnd.github+json'):
    headers = {'Accept': accept, 'X-GitHub-Api-Version': '2022-11-28',
               'User-Agent': 'Alinerml-public-profile'}
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = 'Bearer ' + token
    try:
        request = Request('https://api.github.com' + path, headers=headers)
        with build_opener(GitHubOnlyRedirects()).open(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        raise ValueError(f'GitHub REST returned HTTP {error.code}; previous cards kept.') from None
    except (URLError, OSError, json.JSONDecodeError):
        raise ValueError('GitHub REST could not be read; previous cards kept.') from None


def pages(path, accept='application/vnd.github+json'):
    separator = '&' if '?' in path else '?'
    # Fail instead of silently publishing incomplete counts if the limit is hit.
    for page in range(1, 101):
        batch = get_json(f'{path}{separator}per_page=100&page={page}', accept)
        if not isinstance(batch, list) or any(not isinstance(row, dict) for row in batch):
            raise ValueError('GitHub REST list is invalid; previous cards kept.')
        yield from batch
        if len(batch) < 100:
            return
    raise ValueError('GitHub REST pagination limit reached; previous cards kept.')


def count(value):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError('GitHub REST count is missing or invalid; previous cards kept.')
    return value


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if result.tzinfo is None:
            raise ValueError()
        return result.astimezone(timezone.utc)
    except (AttributeError, ValueError):
        raise ValueError('GitHub REST date is invalid; previous cards kept.') from None


def collect():
    profile = get_json(f'/users/{USER}')
    if not isinstance(profile, dict) or profile.get('login') != USER:
        raise ValueError('GitHub REST profile does not match the expected account.')
    summary = {'followers': count(profile.get('followers')), 'following': count(profile.get('following')),
               'joined': timestamp(profile.get('created_at')).year}
    expected_repositories = count(profile.get('public_repos'))
    repositories = {}
    for repo in pages(f'/users/{USER}/repos?type=owner'):
        owner = repo.get('owner') or {}
        if repo.get('private') is not False or not isinstance(owner, dict) or owner.get('login') != USER:
            continue
        name = repo.get('name')
        if not isinstance(name, str) or not name or not isinstance(repo.get('fork'), bool):
            raise ValueError('GitHub REST repository metadata is incomplete.')
        repositories[name] = {'fork': repo['fork'], 'stars': count(repo.get('stargazers_count')),
                              'forks': count(repo.get('forks_count'))}
    if len(repositories) != expected_repositories:
        raise ValueError('Public repository counts changed or the list is incomplete; retry collection.')
    summary.update(repositories=len(repositories), forks=sum(r['fork'] for r in repositories.values()),
                   stars=sum(r['stars'] for r in repositories.values()),
                   received_forks=sum(r['forks'] for r in repositories.values()))
    monthly = Counter()
    for name, repo in repositories.items():
        if not repo['stars']:
            continue
        stargazers = {}
        for star in pages(f'/repos/{USER}/{quote(name, safe="")}/stargazers', 'application/vnd.github.star+json'):
            user = star.get('user') or {}
            if not isinstance(user, dict) or not isinstance(user.get('id'), int):
                raise ValueError('GitHub REST stargazer data is incomplete.')
            stargazers[user['id']] = timestamp(star.get('starred_at')).strftime('%Y-%m')
        if len(stargazers) != repo['stars']:
            raise ValueError('Star counts changed during collection; retry to obtain a consistent snapshot.')
        monthly.update(stargazers.values())
    return summary, monthly


def overview(summary, fetched):
    parts = base(f'{USER} · GitHub overview', 'Public repositories owned by Alinerml, including forks; no private or organization-owned repositories.', 310)
    parts.append(text(20, 54, 'Public repositories owned by Alinerml · including forks', 'sub'))
    values = [
        ('Public owned repos', summary['repositories']),
        ('Non-fork repos', summary['repositories'] - summary['forks']),
        ('Forked repos', summary['forks']),
        ('Stars received', summary['stars']),
        ('Forks received', summary['received_forks']),
        ('Joined GitHub', summary['joined']),
        ('Followers', summary['followers']),
        ('Following', summary['following']),
    ]
    for index, (label, value) in enumerate(values):
        column, row = index % 2, index // 2
        x, y = 20 + column * 235, 88 + row * 43
        parts.append(text(x, y, label, 'sub'))
        parts.append(text(x, y + 21, f'{value:,}', 'label'))
    parts.append(text(20, 279, 'Scope excludes private repos and repos owned by organizations.', 'sub'))
    parts.append(text(20, 298, f'GitHub REST · fetched {fetched}', 'sub'))
    return '\n'.join(parts + ['</svg>']) + '\n'


def stars_chart(summary, monthly, fetched):
    months = sorted(monthly)
    height = 192 + max(1, len(months)) * 27
    parts = base('Stars · public owned repositories', 'Current stargazers grouped by the month of their starred_at timestamp in UTC; removed stars are not included.', height)
    parts.extend([text(20, 54, f'{summary["stars"]:,} current stars across {summary["repositories"]} public owned repos', 'sub'),
                  text(20, 75, 'Grouped by starred month (UTC); removed stars are not included.', 'sub')])
    peak = max(monthly.values(), default=1)
    for index, month in enumerate(months):
        y = 103 + index * 27
        value = monthly[month]
        parts.append(text(20, y + 10, month, 'sub'))
        parts.append(f'<rect class="track" x="91" y="{y}" width="325" height="12" rx="3"/>')
        parts.append(f'<rect class="bar" x="91" y="{y}" width="{325 * value / peak:.1f}" height="12" rx="3"/>')
        parts.append(text(460, y + 10, value, 'label', text_anchor='end'))
    if not months:
        parts.append(text(20, 118, 'No stars yet in public owned repositories.', 'label'))
    parts.append(text(20, height - 43, 'Counts star-to-repository pairs, including forked repositories.', 'sub'))
    parts.append(text(20, height - 24, f'GitHub REST · fetched {fetched}', 'sub'))
    return '\n'.join(parts + ['</svg>']) + '\n'


def write_cards(root, summary, monthly, now):
    fetched = now.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    cards = {'base.svg': overview(summary, fetched),
             'stargazers.chartist.svg': stars_chart(summary, monthly, fetched)}
    for svg in cards.values():
        ET.fromstring(svg)
    destination = root / 'github-metrics'
    destination.mkdir(exist_ok=True)
    for name, svg in cards.items():
        destination.joinpath(name).write_text(svg, encoding='utf-8')


def main():
    try:
        summary, monthly = collect()
        write_cards(Path(__file__).resolve().parents[1], summary, monthly, datetime.now(timezone.utc))
    except (ValueError, OSError) as error:
        print(str(error) if isinstance(error, ValueError) else 'Could not save public repository cards.', file=sys.stderr)
        return 1
    print('Validated public owned repositories:', json.dumps(summary, sort_keys=True))
    print(f'Validated current-star chart: {sum(monthly.values())} stars in {len(monthly)} months.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
