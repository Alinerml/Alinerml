import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
USER='Alinerml'
today=dt.datetime.now(dt.timezone.utc).date()
colors=['#ebedf0','#9be9a8','#40c463','#30a14e','#216e39']
levels=['NONE','FIRST_QUARTILE','SECOND_QUARTILE','THIRD_QUARTILE','FOURTH_QUARTILE']
gh=shutil.which('gh') or shutil.which('gh.exe')
if not gh:
    windows_gh=Path('/mnt/c/Program Files/GitHub CLI/gh.exe')
    if windows_gh.is_file(): gh=str(windows_gh)
if not gh: raise RuntimeError('GitHub CLI is required: install gh or add gh.exe to PATH')
def query(q):
    r=subprocess.run([gh,'api','graphql','-f','query='+q],check=True,capture_output=True,text=True)
    d=json.loads(r.stdout)
    if d.get('errors'): raise RuntimeError(d['errors'])
    return d['data']['user']
def calendar(a,b):
    return query('query { user(login: "%s") { contributionsCollection(from: "%sT00:00:00Z", to: "%sT23:59:59Z") { contributionCalendar { weeks { contributionDays { date contributionCount contributionLevel weekday } } } } } }'%(USER,a,b))['contributionsCollection']['contributionCalendar']['weeks']
def base(h):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="480" height="{h}" viewBox="0 0 480 {h}">','<style>text{font-family:Segoe UI,Arial;font-size:12px;fill:#777}.title{fill:#218bff;font-size:16px}.label{fill:#218bff;font-size:13px}</style>','<text class="title" x="16" y="26">▦ Contributions calendar</text>']
def save(name,parts):
    s=''.join(parts)+'</svg>'
    ET.fromstring(s)
    assert '<rect' in s or '<polygon' in s
    Path('profile').mkdir(exist_ok=True)
    Path('profile',name).write_text(s,encoding='utf-8')
    aliases={'isocalendar.svg':'isocalendar.fullyear.svg','calendar-full.svg':'calendar.full.svg'}
    if name in aliases:
        destination=Path('github-metrics');destination.mkdir(exist_ok=True)
        destination.joinpath(aliases[name]).write_text(s,encoding='utf-8')
def activity(days):
    recent=sorted(days,key=lambda d:d['date'])[-30:]
    assert len(recent)==30
    assert recent[-1]['date']==today.isoformat()
    for previous,day in zip(recent,recent[1:]):
        assert dt.date.fromisoformat(day['date'])-dt.date.fromisoformat(previous['date'])==dt.timedelta(days=1)
    total=sum(d['contributionCount'] for d in recent)
    peak=max(1,max(d['contributionCount'] for d in recent))
    parts=[
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="270" viewBox="0 0 960 270" role="img" aria-labelledby="activity-title activity-desc">',
        '<title id="activity-title">GitHub contribution trend over the last 30 days</title>',
        f'<desc id="activity-desc">{USER}: {total} contributions from {recent[0]["date"]} to {recent[-1]["date"]}, using GitHub contribution calendar data. Dates are UTC and the current day is incomplete.</desc>',
        '<style>text{font-family:Segoe UI,Arial,sans-serif;font-size:12px;fill:#57606a}.heading{font-size:20px;font-weight:600;fill:#0969da}.summary{font-size:13px}.grid{stroke:#d0d7de;stroke-width:1}.bar{fill:#9be9a8}.trend{fill:none;stroke:#1a7f37;stroke-width:2.5}.dot{fill:#1a7f37}@media(prefers-color-scheme:dark){text{fill:#8b949e}.heading{fill:#58a6ff}.grid{stroke:#30363d}.bar{fill:#196c2e}.trend{stroke:#3fb950}.dot{fill:#3fb950}}</style>',
        '<text class="heading" x="24" y="32">GitHub contribution trend</text>',
        f'<text class="summary" x="24" y="55">Last 30 days · {total} contributions · {recent[0]["date"]} – {recent[-1]["date"]}</text>',
    ]
    left,right,top,bottom=60,930,82,208
    scale=bottom-top
    for fraction in (0,0.5,1):
        y=bottom-scale*fraction
        label=f'{peak*fraction:g}'
        parts.append(f'<line class="grid" x1="{left-12}" y1="{y:.1f}" x2="{right+12}" y2="{y:.1f}"/><text x="{left-22}" y="{y+4:.1f}" text-anchor="end">{label}</text>')
    points=[]
    for index,day in enumerate(recent):
        x=left+index*(right-left)/(len(recent)-1)
        height=day['contributionCount']/peak*scale
        y=bottom-height
        parts.append(f'<rect class="bar" x="{x-8:.1f}" y="{y:.1f}" width="16" height="{height:.1f}" rx="2"><title>{day["date"]}: {day["contributionCount"]} contributions</title></rect>')
        points.append(f'{x:.1f},{y:.1f}')
        if index in (0,7,14,21,29):
            parts.append(f'<text x="{x:.1f}" y="229" text-anchor="middle">{day["date"][5:]}</text>')
    parts.append(f'<polyline class="trend" points="{" ".join(points)}"/>')
    for point,day in zip(points,recent):
        x,y=point.split(',')
        parts.append(f'<circle class="dot" cx="{x}" cy="{y}" r="3"><title>{day["date"]}: {day["contributionCount"]} contributions</title></circle>')
    parts.append('<text x="24" y="254">Source: GitHub contribution calendar · UTC · Today is still in progress</text>')
    save('activity.svg',parts)
created=int(query('query { user(login: "%s") { createdAt } }'%USER)['createdAt'][:4])
years=list(range(today.year,created-1,-1))
full=base(44+len(years)*82)
for i,year in enumerate(years):
    weeks=calendar(dt.date(year,1,1),min(today,dt.date(year,12,31)))
    assert weeks
    y=46+i*82
    full.append(f'<text x="16" y="{y}">{year}</text>')
    for col,w in enumerate(weeks):
        for d in w['contributionDays']:
            c=colors[levels.index(d['contributionLevel'])]
            full.append(f'<rect x="{16+col*8.3:.1f}" y="{y+5+d["weekday"]*8.3:.1f}" width="6.5" height="6.5" rx="1" fill="{c}"><title>{d["date"]}: {d["contributionCount"]} contributions</title></rect>')
save('calendar-full.svg',full)
weeks=calendar(today-dt.timedelta(days=364),today)
days=[d for w in weeks for d in w['contributionDays']]
assert len(days)>=365
counts=[d['contributionCount'] for d in days]
best=streak=0
for n in counts:
    streak=streak+1 if n else 0
    best=max(best,streak)
current=0
for n in reversed(counts if counts[-1] else counts[:-1]):
    if not n: break
    current+=1
iso=base(430)
for y,text in [(67,'Contribution streaks'),(88,f'Current streak {current} days'),(109,f'Best streak {best} days'),(140,'Contributions per day'),(161,f'Highest in a day at {max(counts)}'),(182,f'Average per day at ~{sum(counts)/len(counts):.2f}')]:
    iso.append(f'<text x="255" y="{y}">{text}</text>')
for col,w in enumerate(weeks):
    for d in w['contributionDays']:
        row=d['weekday'];x=62+col*6-row*6;y=112+col*3+row*3
        h=min(28,d['contributionCount']*3);c=colors[levels.index(d['contributionLevel'])]
        if h:
            iso.append(f'<polygon points="{x-6},{y} {x},{y+3} {x},{y+3-h} {x-6},{y-h}" fill="#216e39"/>')
            iso.append(f'<polygon points="{x},{y+3} {x+6},{y} {x+6},{y-h} {x},{y+3-h}" fill="#30a14e"/>')
        iso.append(f'<polygon points="{x},{y-3-h} {x+6},{y-h} {x},{y+3-h} {x-6},{y-h}" fill="{c}" stroke="#aaa" stroke-width=".2"><title>{d["date"]}: {d["contributionCount"]} contributions</title></polygon>')
save('isocalendar.svg',iso)
activity(days)
print(f'Validated {len(years)} years, {len(days)} isometric days and 30 activity days')
