#!/usr/bin/env python3
"""Generate assets/stats.svg (stats, streaks, languages, activity) for a GitHub profile.

No third-party services and no dependencies: uses only the GitHub GraphQL API.
Env:  GH_TOKEN (required unless --placeholder)   GH_USER (default: sanjay-tech-io)
"""
import os, sys, json, html, datetime as dt
from urllib import request

USER = os.environ.get("GH_USER", "sanjay-tech-io")
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT", "assets/stats.svg")
F = "font-family=\"'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, sans-serif\""
esc = html.escape

QUERY = """
query($login:String!){
  user(login:$login){
    repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){
      totalCount
      nodes{ stargazerCount forkCount
        languages(first:8, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name color } } } }
    }
    contributionsCollection{
      totalCommitContributions
      contributionCalendar{ totalContributions weeks{ contributionDays{ date contributionCount } } }
    }
  }
}"""

def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {TOKEN}", "Content-Type": "application/json", "User-Agent": "profile-stats"})
    with request.urlopen(req, timeout=30) as r:
        d = json.load(r)
    if "errors" in d or not d.get("data", {}).get("user"):
        raise SystemExit(f"GraphQL error: {d}")
    u = d["data"]["user"]
    repos = u["repositories"]["nodes"]
    langs = {}
    for r in repos:
        for e in r["languages"]["edges"]:
            n = e["node"]; langs.setdefault(n["name"], [0, n["color"] or "#8888aa"])[0] += e["size"]
    cc = u["contributionsCollection"]
    days = [x for w in cc["contributionCalendar"]["weeks"] for x in w["contributionDays"]]
    return dict(
        stars=sum(r["stargazerCount"] for r in repos), forks=sum(r["forkCount"] for r in repos),
        repos=u["repositories"]["totalCount"], commits=cc["totalCommitContributions"],
        total=cc["contributionCalendar"]["totalContributions"], days=days,
        langs=sorted(([k, v[0], v[1]] for k, v in langs.items()), key=lambda x: -x[1]))

def streaks(days):
    days = sorted(days, key=lambda d: d["date"])
    cur = 0; cur_end = None; longest = 0; l_start = l_end = None; run = 0; r_start = None
    for d in days:
        if d["contributionCount"] > 0:
            if run == 0: r_start = d["date"]
            run += 1
            if run >= longest: longest, l_start, l_end = run, r_start, d["date"]
        else:
            run = 0
    # current streak: walk back from the last day (today may still be empty)
    i = len(days) - 1
    if i >= 0 and days[i]["contributionCount"] == 0: i -= 1
    c_end = days[i]["date"] if i >= 0 else None
    while i >= 0 and days[i]["contributionCount"] > 0:
        cur += 1; c_start = days[i]["date"]; i -= 1
    return (cur, c_start if cur else None, c_end if cur else None), (longest, l_start, l_end)

def fmt_range(a, b):
    if not a: return "—"
    f = lambda s: dt.date.fromisoformat(s).strftime("%b %-d")
    return f(a) if a == b else f"{f(a)} – {f(b)}"

def t(x, y, s, size, fill, weight=500, anchor="middle", ls=0, extra=""):
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" {F} font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" letter-spacing="{ls}" {extra}>{esc(str(s))}</text>')

def build(D):
    W, H = 800, 700
    pend = D is None
    v = (lambda k: "—") if pend else (lambda k: f"{D[k]:,}")
    o = []
    o.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
<radialGradient id="g1"><stop offset="0%" stop-color="rgba(120,40,255,.55)"/><stop offset="100%" stop-color="rgba(120,40,255,0)"/></radialGradient>
<radialGradient id="g2"><stop offset="0%" stop-color="rgba(0,200,220,.4)"/><stop offset="100%" stop-color="rgba(0,200,220,0)"/></radialGradient>
<radialGradient id="g3"><stop offset="0%" stop-color="rgba(220,40,200,.35)"/><stop offset="100%" stop-color="rgba(220,40,200,0)"/></radialGradient>
<linearGradient id="scg"><stop offset="0%" stop-color="rgba(120,200,255,0)"/><stop offset="50%" stop-color="rgba(160,120,255,.45)"/><stop offset="100%" stop-color="rgba(120,200,255,0)"/></linearGradient>
<linearGradient id="ring" x1="0" x2="1" y1="0" y2="1"><stop offset="0%" stop-color="#7828ff"/><stop offset="100%" stop-color="#ff88cc"/></linearGradient>
<linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stop-color="rgba(160,120,255,.45)"/><stop offset="100%" stop-color="rgba(160,120,255,0)"/></linearGradient>
<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0L0 0 0 40" fill="none" stroke="rgba(110,80,220,.07)" stroke-width=".5"/></pattern>
<style>
@keyframes dl{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(-30px,14px)}}}}
@keyframes dr{{0%,100%{{transform:translate(0,0)}}50%{{transform:translate(35px,-16px)}}}}
@keyframes scan{{0%{{transform:translate(-900px,0)}}100%{{transform:translate(900px,0)}}}}
@keyframes draw{{0%{{stroke-dashoffset:1}}100%{{stroke-dashoffset:0}}}}
.dl{{animation:dl 9s ease-in-out infinite}}.dr{{animation:dr 8s ease-in-out infinite}}.scan{{animation:scan 4.5s linear infinite}}
.line{{stroke-dasharray:1;animation:draw 3s ease-out forwards}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.line{{stroke-dasharray:none}}}}
</style></defs>
<rect width="{W}" height="{H}" rx="24" fill="#060610" stroke="rgba(110,80,220,.25)" stroke-width="1.5"/>
<rect width="{W}" height="{H}" rx="24" fill="url(#grid)"/>''')
    sep = 'stroke="rgba(110,80,220,.18)" stroke-width=".8"'
    # ---- stats row
    o.append(f'<ellipse class="dl" cx="400" cy="70" rx="320" ry="55" fill="url(#g1)" opacity=".7"/>'
             f'<rect class="scan" x="-200" y="70" width="200" height="2" fill="url(#scg)"/>')
    items = [("STARS", v("stars"), "#ffcc33"), ("FORKS", v("forks"), "#e8c8ff"),
             ("REPOS", v("repos"), "#7ee7ff"), ("COMMITS · 1Y", v("commits"), "#ff88cc")]
    for i, (lab, val, c) in enumerate(items):
        cx = 100 + i * 200
        o.append(t(cx, 78, val, 32, "#fff", 900) + t(cx, 100, lab, 9, c, 800, ls=2.5))
        if i: o.append(f'<line x1="{cx-100}" y1="48" x2="{cx-100}" y2="108" {sep} stroke-dasharray="3 3"/>')
    o.append(f'<line x1="28" y1="150" x2="772" y2="150" {sep}/>')
    # ---- streak panel
    o.append(t(40, 178, "CONTRIBUTION STREAKS", 10, "rgba(126,231,255,.85)", 800, "start", 4))
    if pend:
        tot, cur, lon = "—", (0, None, None), (0, None, None)
    else:
        cur, lon = streaks(D["days"]); tot = f"{D['total']:,}"
    cols = [133, 400, 667]
    o.append(t(cols[0], 250, tot, 34, "#fff", 900) + t(cols[0], 276, "Contributions", 13, "#e8c8ff", 500) +
             t(cols[0], 300, "past 12 months", 10, "rgba(140,140,180,.75)"))
    # ring
    R = 42; circ = 2 * 3.14159 * R
    frac = 0 if pend else min(cur[0] / 30, 1)
    o.append(f'<circle cx="{cols[1]}" cy="236" r="{R}" fill="none" stroke="rgba(255,255,255,.07)" stroke-width="5"/>'
             f'<circle cx="{cols[1]}" cy="236" r="{R}" fill="none" stroke="url(#ring)" stroke-width="5" stroke-linecap="round" '
             f'stroke-dasharray="{circ*frac:.1f} {circ:.1f}" transform="rotate(-90 {cols[1]} 236)"/>')
    o.append(t(cols[1], 246, "—" if pend else cur[0], 30, "#fff", 900) +
             t(cols[1], 304, "Current Streak", 13, "#7ee7ff", 700) +
             t(cols[1], 322, fmt_range(cur[1], cur[2]), 10, "rgba(140,140,180,.75)"))
    o.append(t(cols[2], 250, "—" if pend else lon[0], 34, "#fff", 900) + t(cols[2], 276, "Longest Streak", 13, "#e8c8ff", 500) +
             t(cols[2], 300, fmt_range(lon[1], lon[2]), 10, "rgba(140,140,180,.75)"))
    for x in (266, 533): o.append(f'<line x1="{x}" y1="205" x2="{x}" y2="320" {sep} stroke-dasharray="3 3"/>')
    o.append(f'<line x1="28" y1="352" x2="772" y2="352" {sep}/>')
    # ---- stack analytics
    o.append(f'<ellipse class="dr" cx="640" cy="440" rx="180" ry="70" fill="url(#g3)" opacity=".6"/>')
    o.append(t(40, 380, "STACK ANALYTICS", 10, "rgba(126,231,255,.85)", 800, "start", 4))
    o.append('<rect x="40" y="398" width="720" height="8" rx="4" fill="rgba(255,255,255,.06)"/>')
    if pend:
        o.append(t(400, 452, "Languages appear after the first sync", 11, "rgba(140,140,180,.7)"))
    else:
        L = D["langs"][:8]; tot_sz = sum(x[1] for x in L) or 1
        x = 40.0; parts = []; lx = 0
        o.append('<clipPath id="bar"><rect x="40" y="398" width="720" height="8" rx="4"/></clipPath><g clip-path="url(#bar)">')
        for name, sz, col in L:
            w = 720 * sz / tot_sz
            o.append(f'<rect x="{x:.1f}" y="398" width="{w:.1f}" height="8" fill="{col}" opacity=".92"/>'); x += w
        o.append('</g>')
        for i, (name, sz, col) in enumerate(L):
            cx = 40 + (i % 4) * 180; cy = 434 + (i // 4) * 26
            o.append(f'<circle cx="{cx+4}" cy="{cy-4}" r="4" fill="{col}"/>' +
                     t(cx + 14, cy, name, 11, "rgba(232,224,255,.9)", 600, "start") +
                     t(cx + 14 + 12 + len(name) * 6.9, cy, f"{sz*100/tot_sz:.0f}%", 11, "rgba(140,140,180,.9)", 500, "start"))
    o.append(f'<line x1="28" y1="500" x2="772" y2="500" {sep}/>')
    # ---- activity pulse
    o.append(t(40, 528, "ACTIVITY PULSE", 10, "rgba(126,231,255,.85)", 800, "start", 4))
    x0, x1, yb, yt = 50, 750, 660, 555
    if pend:
        o.append(f'<line x1="{x0}" y1="{yb}" x2="{x1}" y2="{yb}" stroke="rgba(160,120,255,.35)" stroke-dasharray="4 5"/>')
        o.append(t(400, 612, "Awaiting first sync — run the “Update profile stats” workflow", 11, "rgba(140,140,180,.7)"))
    else:
        days = sorted(D["days"], key=lambda d: d["date"])
        weeks = [sum(d["contributionCount"] for d in days[i:i+7]) for i in range(0, len(days), 7)]
        mx = max(max(weeks), 1); n = len(weeks)
        pts = [(x0 + (x1 - x0) * i / (n - 1), yb - (yb - yt) * w / mx) for i, w in enumerate(weeks)]
        path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        o.append(t(760, 528, f"{D['total']:,} contributions", 11, "#e8c8ff", 700, "end"))
        for k in range(1, 4):
            gy = yb - (yb - yt) * k / 3
            o.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x1}" y2="{gy:.1f}" stroke="rgba(110,80,220,.12)" stroke-width=".6"/>')
        o.append(f'<path d="{path} L{x1},{yb} L{x0},{yb} Z" fill="url(#area)"/>')
        o.append(f'<path class="line" pathLength="1" d="{path}" fill="none" stroke="#a078ff" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
        px, py = pts[-1]
        o.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="#ff88cc"/>')
        # month labels
        last = None; lastx = -99
        for i in range(0, len(days), 7):
            m = dt.date.fromisoformat(days[i]["date"]).strftime("%b")
            lx = x0 + (x1 - x0) * (i // 7) / (n - 1)
            if m != last and lx - lastx > 40:
                o.append(t(lx, 682, m.upper(), 8.5, "rgba(140,140,180,.7)", 600, ls=1.5)); lastx = lx
            last = m
    o.append('</svg>')
    return "\n".join(o)

if __name__ == "__main__":
    if "--placeholder" in sys.argv:
        D = None
    elif "--demo" in sys.argv:  # local visual test only
        import random; random.seed(3)
        base = dt.date.today() - dt.timedelta(days=364)
        days = [{"date": (base + dt.timedelta(days=i)).isoformat(), "contributionCount": max(0, random.randint(-3, 6))} for i in range(365)]
        D = dict(stars=44, forks=5, repos=81, commits=995, total=sum(d["contributionCount"] for d in days), days=days,
                 langs=[["C++", 28, "#f34b7d"], ["TypeScript", 15, "#3178c6"], ["Python", 12, "#3572A5"], ["JavaScript", 10, "#f1e05a"],
                        ["CSS", 9, "#663399"], ["HTML", 8, "#e34c26"], ["Shell", 6, "#89e051"], ["SQL", 4, "#e38c00"]])
    else:
        if not TOKEN: raise SystemExit("GH_TOKEN is required")
        D = fetch()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    open(OUT, "w", encoding="utf-8").write(build(D))
    print("wrote", OUT)
