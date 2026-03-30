#!/usr/bin/env python3
"""
Fetches all repos + latest Actions run for ozaretskyi
and bakes a fully static index.html — no token in output.
"""
import os, json, urllib.request, urllib.error, datetime

TOKEN = os.environ["GH_PAT"]
USER  = "ozaretskyi"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

LANG_COLORS = {
    "JavaScript":"#f1e05a","TypeScript":"#3178c6","Python":"#3572A5",
    "Java":"#b07219","Go":"#00ADD8","Rust":"#dea584","Shell":"#89e051",
    "HTML":"#e34c26","CSS":"#563d7c","Ruby":"#701516","Kotlin":"#A97BFF",
    "Dockerfile":"#384d54","HCL":"#844FBA","YAML":"#cb171e","Groovy":"#e69f56",
}

def gh(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def fetch_repos():
    repos, page = [], 1
    while True:
        batch = gh(f"https://api.github.com/user/repos?per_page=100&page={page}&sort=pushed&affiliation=owner")
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos

def fetch_run(repo_name):
    try:
        data = gh(f"https://api.github.com/repos/{USER}/{repo_name}/actions/runs?per_page=1")
        runs = data.get("workflow_runs", [])
        if not runs:
            return None
        r = runs[0]
        return {
            "name":       r.get("name") or r.get("event", ""),
            "conclusion": r.get("conclusion"),
            "status":     r.get("status"),
            "html_url":   r.get("html_url"),
            "updated_at": r.get("updated_at"),
        }
    except:
        return None

def filter_key(run):
    if not run:
        return "none"
    s, c = run.get("status"), run.get("conclusion")
    if s in ("in_progress", "queued", "waiting"):
        return "in_progress"
    if c == "success":  return "success"
    if c == "failure":  return "failure"
    return "none"

print("Fetching repos...")
repos = fetch_repos()
print(f"  {len(repos)} repos found")

result = []
for i, repo in enumerate(repos):
    print(f"  [{i+1}/{len(repos)}] {repo['name']}")
    run = fetch_run(repo["name"])
    result.append({
        "name":             repo["name"],
        "description":      repo.get("description") or "",
        "private":          repo.get("private", False),
        "fork":             repo.get("fork", False),
        "archived":         repo.get("archived", False),
        "language":         repo.get("language") or "",
        "lang_color":       LANG_COLORS.get(repo.get("language",""), "#8b949e"),
        "stars":            repo.get("stargazers_count", 0),
        "forks":            repo.get("forks_count", 0),
        "pushed_at":        repo.get("pushed_at") or "",
        "html_url":         repo.get("html_url",""),
        "actions_url":      f"https://github.com/{USER}/{repo['name']}/actions",
        "run":              run,
        "filter_key":       filter_key(run),
    })

# Sort: failure -> in_progress -> success -> none
order = {"failure":0,"in_progress":1,"success":2,"none":3}
result.sort(key=lambda r: order.get(r["filter_key"], 4))

built_at = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
data_json = json.dumps(result)

stats = {
    "total":   len(result),
    "success": sum(1 for r in result if r["filter_key"]=="success"),
    "failure": sum(1 for r in result if r["filter_key"]=="failure"),
    "running": sum(1 for r in result if r["filter_key"]=="in_progress"),
    "none":    sum(1 for r in result if r["filter_key"]=="none"),
}

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>ozaretskyi / repos</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&display=swap');
  :root{{
    --bg:#0d1117;--surface:#161b22;--border:#30363d;--border-h:#484f58;
    --text:#e6edf3;--muted:#8b949e;--link:#58a6ff;--green:#3fb950;
    --red:#f85149;--yellow:#d29922;--purple:#bc8cff;--accent:#1f6feb;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px;min-height:100vh}}
  header{{border-bottom:1px solid var(--border);padding:12px 24px;display:flex;align-items:center;gap:12px;
    position:sticky;top:0;background:rgba(13,17,23,.92);backdrop-filter:blur(8px);z-index:10}}
  .header-title{{font-size:14px;font-weight:700;color:var(--text);text-decoration:none}}
  .header-sep{{color:var(--border-h)}}
  .header-sub{{color:var(--muted);font-size:12px}}
  .header-right{{margin-left:auto;display:flex;align-items:center;gap:16px}}
  #last-updated{{color:var(--muted);font-size:11px}}
  main{{max-width:1100px;margin:0 auto;padding:24px 16px}}
  .stats-bar{{display:flex;gap:12px;margin-bottom:20px;flex-wrap:wrap}}
  .stat-pill{{background:var(--surface);border:1px solid var(--border);border-radius:20px;
    padding:4px 12px;font-size:12px;color:var(--muted);display:flex;align-items:center;gap:6px}}
  .stat-pill strong{{color:var(--text)}}
  .filters{{display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap;align-items:center}}
  .filter-btn{{background:transparent;border:1px solid var(--border);color:var(--muted);
    padding:4px 12px;border-radius:6px;cursor:pointer;font-family:inherit;font-size:12px;transition:all .15s}}
  .filter-btn:hover{{border-color:var(--border-h);color:var(--text)}}
  .filter-btn.active{{background:var(--accent);border-color:var(--accent);color:#fff}}
  .search-box{{margin-left:auto;background:var(--surface);border:1px solid var(--border);
    color:var(--text);padding:4px 12px;border-radius:6px;font-family:inherit;font-size:12px;
    width:200px;outline:none;transition:border-color .15s}}
  .search-box:focus{{border-color:var(--accent)}}
  .search-box::placeholder{{color:var(--muted)}}
  .repo-list{{display:flex;flex-direction:column;gap:1px;border:1px solid var(--border);border-radius:8px;overflow:hidden}}
  .repo-row{{background:var(--surface);padding:14px 16px;display:grid;grid-template-columns:1fr auto;
    gap:8px;align-items:start;border-bottom:1px solid var(--border);transition:background .1s}}
  .repo-row:last-child{{border-bottom:none}}
  .repo-row:hover{{background:#1c2128}}
  .repo-name-line{{display:flex;align-items:center;gap:8px;margin-bottom:4px;flex-wrap:wrap}}
  .repo-name{{color:var(--link);font-weight:700;font-size:13px;text-decoration:none}}
  .repo-name:hover{{text-decoration:underline}}
  .badge{{font-size:10px;padding:2px 7px;border-radius:20px;border:1px solid}}
  .badge-private{{color:var(--muted);border-color:var(--border)}}
  .badge-public{{color:var(--green);border-color:#238636}}
  .badge-fork{{color:var(--purple);border-color:#6e40c9}}
  .badge-archived{{color:var(--yellow);border-color:#9e6a03}}
  .repo-desc{{color:var(--muted);font-size:12px;margin-bottom:8px;line-height:1.5;max-width:700px}}
  .repo-meta{{display:flex;align-items:center;gap:14px;flex-wrap:wrap}}
  .meta-item{{display:flex;align-items:center;gap:4px;color:var(--muted);font-size:11px}}
  .lang-dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
  .repo-actions{{text-align:right;min-width:140px}}
  .run-status{{display:inline-flex;align-items:center;gap:6px;padding:4px 10px;border-radius:6px;
    font-size:11px;font-weight:500;border:1px solid;white-space:nowrap;text-decoration:none}}
  .run-status:hover{{opacity:.85}}
  .status-success{{color:var(--green);border-color:#238636;background:rgba(35,134,54,.1)}}
  .status-failure{{color:var(--red);border-color:#da3633;background:rgba(218,54,51,.1)}}
  .status-in_progress{{color:var(--yellow);border-color:#9e6a03;background:rgba(158,106,3,.1)}}
  .status-none{{color:var(--muted);border-color:var(--border);background:transparent}}
  .run-workflow{{color:var(--muted);font-size:10px;margin-top:4px}}
  .run-time{{color:var(--muted);font-size:10px}}
  .empty-row{{padding:40px;text-align:center;color:var(--muted)}}
  @media(max-width:600px){{
    .repo-row{{grid-template-columns:1fr}}
    .repo-actions{{text-align:left}}
    .search-box{{width:100%}}
  }}
</style>
</head>
<body>
<header>
  <svg height="28" viewBox="0 0 16 16" width="28" fill="#e6edf3">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
      0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13
      -.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66
      .07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15
      -.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27
      .68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12
      .51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48
      0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
  </svg>
  <a class="header-title" href="https://github.com/{USER}" target="_blank">{USER}</a>
  <span class="header-sep">/</span>
  <span class="header-sub">repositories</span>
  <div class="header-right">
    <span id="last-updated">Built {built_at}</span>
  </div>
</header>
<main>
  <div class="stats-bar">
    <div class="stat-pill">📦 <strong>{stats['total']}</strong> repos</div>
    <div class="stat-pill">✅ <strong>{stats['success']}</strong> passing</div>
    <div class="stat-pill">❌ <strong>{stats['failure']}</strong> failing</div>
    {'<div class="stat-pill">⏳ <strong>' + str(stats['running']) + '</strong> running</div>' if stats['running'] else ''}
    <div class="stat-pill">— <strong>{stats['none']}</strong> no CI</div>
  </div>
  <div class="filters">
    <button class="filter-btn active" data-filter="all">All</button>
    <button class="filter-btn" data-filter="success">✅ Passing</button>
    <button class="filter-btn" data-filter="failure">❌ Failing</button>
    <button class="filter-btn" data-filter="in_progress">⏳ Running</button>
    <button class="filter-btn" data-filter="none">— No CI</button>
    <input class="search-box" id="search" type="text" placeholder="Search repos..."/>
  </div>
  <div class="repo-list" id="repo-list"></div>
</main>
<script>
const REPOS = {data_json};
let activeFilter = 'all', searchTerm = '';

function timeAgo(dateStr) {{
  if (!dateStr) return '';
  const diff = Date.now() - new Date(dateStr);
  const m = Math.floor(diff/60000);
  if (m < 1)  return 'just now';
  if (m < 60) return m+'m ago';
  const h = Math.floor(m/60);
  if (h < 24) return h+'h ago';
  const d = Math.floor(h/24);
  if (d < 30) return d+'d ago';
  return new Date(dateStr).toLocaleDateString('en-GB',{{day:'numeric',month:'short',year:'numeric'}});
}}

function statusInfo(run) {{
  if (!run) return {{icon:'—', label:'No runs', cls:'status-none'}};
  const s = run.status, c = run.conclusion;
  if (s==='in_progress'||s==='queued'||s==='waiting') return {{icon:'⏳',label:'Running',cls:'status-in_progress'}};
  if (c==='success')   return {{icon:'✅',label:'Passing',  cls:'status-success'}};
  if (c==='failure')   return {{icon:'❌',label:'Failing',  cls:'status-failure'}};
  if (c==='cancelled') return {{icon:'⊘',label:'Cancelled',cls:'status-none'}};
  return {{icon:'—',label:'No runs',cls:'status-none'}};
}}

function render() {{
  const filtered = REPOS.filter(r => {{
    const mf = activeFilter==='all' || r.filter_key===activeFilter;
    const ms = !searchTerm || r.name.toLowerCase().includes(searchTerm) || r.description.toLowerCase().includes(searchTerm);
    return mf && ms;
  }});
  const list = document.getElementById('repo-list');
  if (!filtered.length) {{ list.innerHTML='<div class="empty-row">No repositories match.</div>'; return; }}
  list.innerHTML = filtered.map(repo => {{
    const si = statusInfo(repo.run);
    const runUrl = repo.run?.html_url || repo.actions_url;
    const badges = [
      repo.private  ? '<span class="badge badge-private">private</span>'  : '<span class="badge badge-public">public</span>',
      repo.fork     ? '<span class="badge badge-fork">fork</span>'        : '',
      repo.archived ? '<span class="badge badge-archived">archived</span>': '',
    ].join('');
    return `
    <div class="repo-row">
      <div class="repo-main">
        <div class="repo-name-line">
          <a class="repo-name" href="${{repo.html_url}}" target="_blank">${{repo.name}}</a>
          ${{badges}}
        </div>
        ${{repo.description ? `<div class="repo-desc">${{repo.description}}</div>` : ''}}
        <div class="repo-meta">
          ${{repo.language ? `<span class="meta-item"><span class="lang-dot" style="background:${{repo.lang_color}}"></span>${{repo.language}}</span>` : ''}}
          ${{repo.stars > 0 ? `<span class="meta-item">⭐ ${{repo.stars}}</span>` : ''}}
          ${{repo.forks > 0 ? `<span class="meta-item">🍴 ${{repo.forks}}</span>` : ''}}
          <span class="meta-item">Updated ${{timeAgo(repo.pushed_at)}}</span>
        </div>
      </div>
      <div class="repo-actions">
        <a class="run-status ${{si.cls}}" href="${{runUrl}}" target="_blank">${{si.icon}} ${{si.label}}</a>
        ${{repo.run ? `<div class="run-workflow">${{repo.run.name}}</div><div class="run-time">${{timeAgo(repo.run.updated_at)}}</div>` : ''}}
      </div>
    </div>`;
  }}).join('');
}}

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    render();
  }});
}});
document.getElementById('search').addEventListener('input', e => {{
  searchTerm = e.target.value.toLowerCase();
  render();
}});
render();
</script>
</body>
</html>"""

with open("index.html", "w") as f:
    f.write(HTML)

print(f"Done! index.html built — {len(result)} repos, {built_at}")
