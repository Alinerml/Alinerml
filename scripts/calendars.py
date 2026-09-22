import datetime as dt
import json
import subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
USER='Alinerml'
today=dt.datetime.now(dt.timezone.utc).date()
colors=['#ebedf0','#9be9a8','#40c463','#30a14e','#216e39']
levels=['NONE','FIRST_QUARTILE','SECOND_QUARTILE','THIRD_QUARTILE','FOURTH_QUARTILE']
def query(q):
    r=subprocess.run(['gh','api','graphql','-f','query='+q],check=True,capture_output=True,text=True)
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
    Path('profile',name).write_text(s)
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
for y,text in [(67,'Commits streaks'),(88,f'Current streak {current} days'),(109,f'Best streak {best} days'),(140,'Commits per day'),(161,f'Highest in a day at {max(counts)}'),(182,f'Average per day at ~{sum(counts)/len(counts):.2f}')]:
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
print(f'Validated {len(years)} years and {len(days)} isometric days')
