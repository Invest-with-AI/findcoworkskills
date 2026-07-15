#!/usr/bin/env python3
"""findcoworkskills — find skills you can install and use in Claude Cowork.

Searches the open skill ecosystem for a topic and writes a ranked HTML report.
No token, no accounts, no npx staging. Data sources:

  1. skillsmp.com /api/skills  — 2.2M-skill catalog: descriptions, stars, GitHub links,
     and the path to each skill's SKILL.md.
  2. raw.githubusercontent.com — reads each result's actual SKILL.md (and README) to see
     which ones declare Cowork / Claude Desktop support.

Any skill listed installs in Cowork via Customize > Skills > upload. The report ranks by
GitHub stars, marks the ones whose docs mention Cowork, and separates those from the rest.

Usage:
    python3 findcoworkskills.py "equity research"
Env: FCS_OUT (optional output path).
"""
import os
import re
import sys
import json
import html as htmllib
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

MENTION = re.compile(r"\bco-?work\b|claude\s+desktop", re.I)

# Authors treated as businesses/organisations (green border on the name). Curated,
# extend as needed — there is no reliable automatic "is this a company" signal.
BUSINESS = {
    "anthropics", "anthropic", "openai", "google", "googleapis", "google-gemini",
    "microsoft", "azure", "vercel", "vercel-labs", "stripe", "notion", "cloudflare",
    "amazon", "aws", "meta", "huggingface", "langchain", "replit", "mongodb",
    "databricks", "atlassian", "gitlab", "github", "shopify", "twilio", "datadog",
    "elastic", "redis", "docker", "jetbrains", "snowflake-labs", "pionex-official",
    "longbridge", "lseg", "netresearch", "supabase", "netlify", "pinecone",
}
TRIGGER_TAIL = re.compile(r"\s*(?:Also use when|Use this skill|Use when|Triggers? on|"
                          r"Trigger when|This skill should be used).*", re.I | re.S)
TRIGGER_HEAD = re.compile(r"^\W*(?:When |Use (?:this skill )?(?:whenever|when) |"
                          r"(?:the )?user (?:wants to|asks to|needs to|needs|is)\s*)+", re.I)


def get(url, timeout=25):
    h = {"User-Agent": "findcoworkskills"}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout) as r:
            return r.read().decode("utf-8", "ignore")
    except Exception:
        return ""


def clean(t):
    return (t or "").encode("ascii", "ignore").decode()


def repo_of(github_url):
    m = re.search(r"github\.com/([\w.-]+/[\w.-]+)", github_url or "")
    return m.group(1).rstrip("/") if m else ""


def distill(desc):
    d = TRIGGER_TAIL.sub("", desc)
    d = TRIGGER_HEAD.sub("", d).strip().strip('"\u201c\u201d')
    d = re.split(r"(?<=[.!?])\s+", d)[0] if d else d
    return (d[:1].upper() + d[1:]).rstrip(".") if d else desc[:90]


# ---- data sources ----------------------------------------------------------
def search_skillsmp(query, limit=100):
    url = f"https://skillsmp.com/api/skills?search={urllib.parse.quote(query)}&limit={limit}"
    body = get(url)
    try:
        data = json.loads(body)
    except Exception:
        return []
    out = []
    for s in data.get("skills", []):
        out.append({
            "name": s.get("name", ""),
            "author": s.get("author", ""),
            "desc": clean(s.get("description", "")),
            "stars": s.get("stars") or 0,
            "repo": repo_of(s.get("githubUrl", "")),
            "path": s.get("path", ""),
            "branch": s.get("branch") or "main",
            "url": s.get("githubUrl", "") or (f"https://skillsmp.com{s.get('route','')}"),
            "cowork": False,
        })
    return out


def detect_cowork(entries):
    """Read each result's actual SKILL.md (skillsmp gives the path + branch), fall back to
    its README, and scan for the Cowork / Claude Desktop mention. No token needed."""
    for e in entries:
        hay = e["desc"]
        br = e.get("branch") or "main"
        if e["repo"] and e.get("path"):
            hay += "\n" + get(f"https://raw.githubusercontent.com/{e['repo']}/{br}/{e['path']}")
        if not MENTION.search(hay) and e["repo"]:
            for b in (br, "master", "HEAD"):
                rd = get(f"https://raw.githubusercontent.com/{e['repo']}/{b}/README.md")
                if rd:
                    hay += "\n" + rd
                    break
        e["cowork"] = bool(MENTION.search(hay))


# ---- report ----------------------------------------------------------------
def esc(t):
    return htmllib.escape(str(t))


def render(query, entries, path):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    cw = sum(1 for e in entries if e["cowork"])
    split = next((i for i, e in enumerate(entries) if not e["cowork"]), None)
    if split in (None, 0):                  # all or none cowork-ready -> no divider
        split = None
    SHOWN = 25
    rows = ""
    for i, e in enumerate(entries):
        if split is not None and i == split:
            hid = " hidden" if split >= SHOWN else ""
            rows += (f'<tr class="sep{hid}" data-i="{split}"><td colspan="4">'
                     f'they might still install, take a look</td></tr>')
        cowork_tag = '<span class="tag">cowork-ready</span>' if e["cowork"] else ""
        vendor_tag = ('<span class="tag vendor">official vendor</span>'
                      if (e["author"] or "").lower() in BUSINESS else "")
        hide = " hidden" if i >= SHOWN else ""
        stars = f'{e["stars"]:,}<span class="unit">stars</span>'
        link = f'<a href="{esc(e["url"])}" target="_blank" rel="noopener">source&nbsp;&#8599;</a>' if e["url"] else ""
        rows += f"""<tr class="sk{hide}" data-i="{i}">
          <td class="c-name"><span class="ident">{esc(e['name'])}</span>{vendor_tag}
            <div class="owner">{esc(e['author'] or e['repo'])}</div>{cowork_tag}</td>
          <td class="c-num">{stars}</td>
          <td class="c-desc">{esc(distill(e['desc'])) or '<span class="none">no description</span>'}</td>
          <td class="c-fetch">{link}</td></tr>"""
    more = (f'<button id="more" class="more">Show 25 more '
            f'<span class="count">({len(entries) - SHOWN} left)</span></button>'
            if len(entries) > SHOWN else "")

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>findcoworkskills · {esc(query)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Condensed:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{{--paper:#EFF0ED;--panel:#FCFCFB;--ink:#14171C;--muted:#6C7178;--rule:#D7D9D3;--hair:#E4E6E0;--accent:#E25D54;--accent-dk:#C04840}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:14px;line-height:1.5}}
.wrap{{max-width:1160px;margin:0 auto;padding:0 26px 90px}}
.mast{{border-top:5px solid var(--ink);padding-top:16px;margin-top:34px}}
.eyebrow{{display:flex;justify-content:space-between;font-family:"IBM Plex Mono";font-size:11px;letter-spacing:.18em;text-transform:uppercase;color:var(--muted)}}
.eyebrow b{{color:var(--accent);font-weight:600}}
h1{{font-family:"IBM Plex Sans Condensed";font-weight:700;font-size:36px;letter-spacing:-.01em;margin:10px 0 6px}}
.asof{{font-family:"IBM Plex Mono";font-size:12px;color:var(--muted);padding-bottom:14px;border-bottom:1.5px solid var(--accent)}}
.lead{{margin:16px 0 0;font-size:14px;color:#3a3f45}}
.strip{{display:flex;gap:0;margin:20px 0 6px;border-bottom:1px solid var(--rule)}}
.cell{{padding:12px 26px 12px 0;margin-right:26px;border-right:1px solid var(--hair)}}
.cell:last-child{{border-right:none}}
.cell .fig{{font-family:"IBM Plex Mono";font-weight:600;font-size:22px;font-variant-numeric:tabular-nums}}
.cell .lbl{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin-top:4px}}
.method{{font-family:"IBM Plex Mono";font-size:11.5px;color:var(--muted);margin:16px 0 26px}}
.method b{{color:var(--accent-dk)}}
table{{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--rule)}}
th{{font-family:"IBM Plex Mono";text-align:left;font-size:10.5px;font-weight:500;letter-spacing:.09em;text-transform:uppercase;color:var(--muted);padding:11px 14px;border-bottom:1.5px solid var(--ink)}}
td{{padding:14px;border-bottom:1px solid var(--hair);vertical-align:top}}
tr:last-child td{{border-bottom:none}}tbody tr:hover td{{background:#F6F7F4}}
.ident{{display:inline-block;font-family:"IBM Plex Mono";font-weight:600;font-size:14px;word-break:break-word}}
.tag.vendor{{color:#1C7A46;border-color:#1C7A46;margin-left:8px;margin-top:0;vertical-align:middle}}
.hidden{{display:none}}
.sep td{{background:#F0F1EE;font-family:"IBM Plex Mono";font-size:10.5px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--muted);padding:8px 14px;border-bottom:1px solid var(--hair)}}
.more{{display:inline-flex;align-items:center;gap:8px;margin:16px 0 0;cursor:pointer;
  font-family:"IBM Plex Mono";font-size:12px;font-weight:600;letter-spacing:.04em;color:var(--ink);
  background:var(--panel);border:1.5px solid var(--ink);border-radius:6px;padding:9px 16px;transition:background .12s}}
.more:hover{{background:var(--ink);color:var(--panel)}}
.more .count{{font-weight:400;color:var(--muted)}}.more:hover .count{{color:#B9BCC2}}
.owner{{font-size:12px;color:var(--muted);margin-top:2px}}
.tag{{display:inline-block;margin-top:6px;font-family:"IBM Plex Mono";font-size:10px;color:var(--accent-dk);border:1px solid var(--accent);border-radius:3px;padding:1px 6px}}
.c-num{{font-family:"IBM Plex Mono";font-variant-numeric:tabular-nums;font-weight:600;white-space:nowrap}}
.c-num .unit{{display:block;font-weight:400;font-size:10px;color:var(--muted);text-transform:uppercase;margin-top:3px}}
.c-desc{{color:#33373D;max-width:560px;font-size:13.5px}}
.c-fetch a{{font-family:"IBM Plex Mono";color:var(--accent-dk);text-decoration:none;border-bottom:1px solid var(--hair)}}
.c-fetch a:hover{{border-bottom-color:var(--accent)}}.none{{color:var(--muted)}}
footer{{margin-top:34px;padding-top:16px;border-top:1px solid var(--rule);font-family:"IBM Plex Mono";font-size:11px;color:var(--muted);line-height:1.7}}
footer a{{color:var(--accent-dk);text-decoration:none}}
</style></head><body><div class="wrap">
<div class="mast"><div class="eyebrow"><span>Skill coverage screen</span><span><b>findcoworkskills</b></span></div>
<h1>{esc(query)}</h1>
<div class="asof">as of {ts} &nbsp;&middot;&nbsp; source: skillsmp catalog + each skill's SKILL.md</div>
<p class="lead">Skills for this task from the open catalog, ranked by GitHub stars, cowork-ready first. Any of them installs
in Cowork via Customize &gt; Skills &rarr; upload. The <span class="tag">cowork-ready</span> tag marks the
ones whose docs mention Cowork / Claude Desktop directly; a green <span class="tag vendor" style="margin-left:0">official vendor</span>
box marks skills published by a known business.</p></div>
<div class="strip">
  <div class="cell"><div class="fig">{len(entries)}</div><div class="lbl">Shown</div></div>
  <div class="cell"><div class="fig">{cw}</div><div class="lbl">Cowork-ready</div></div>
</div>
<table><thead><tr><th>Skill</th><th>Stars</th><th>What it does</th><th>Fetch</th></tr></thead>
<tbody>{rows or '<tr><td colspan=4 class=none style=padding:18px>No results.</td></tr>'}</tbody></table>
{more}
<script>
(function(){{
  var limit=25, total={len(entries)}, btn=document.getElementById('more');
  function apply(){{
    document.querySelectorAll('tr[data-i]').forEach(function(el){{
      el.classList.toggle('hidden', parseInt(el.getAttribute('data-i'))>=limit);
    }});
    if(!btn) return;
    var left=total-limit;
    if(left<=0){{ btn.style.display='none'; }}
    else {{ btn.querySelector('.count').textContent='('+left+' left)'; }}
  }}
  if(btn) btn.addEventListener('click', function(){{ limit+=25; apply(); }});
}})();
</script>
<footer>Any skill here installs in Cowork (Customize &gt; Skills &rarr; upload, or open the source). Ranked by
GitHub stars, cowork-ready first. Review any third-party skill before enabling.
<div>findcoworkskills &middot; built by <a href="https://investwithai.substack.com">Invest with AI</a>, an <a href="https://www.atomicalcapital.com">Atomical Capital</a> publication &middot; free to use</div>
</footer></div></body></html>"""
    Path(path).write_text(doc, encoding="utf-8")
    return cw


def main():
    if len(sys.argv) < 2:
        print("usage: findcoworkskills.py <topic>")
        sys.exit(1)
    query = " ".join(a for a in sys.argv[1:] if not a.isdigit())

    entries = search_skillsmp(query)

    # dedupe copies/forks (keep the most-starred), then read each skill's docs
    best = {}
    for e in entries:
        sig = (e["name"].lower().strip(), re.sub(r"\s+", " ", e["desc"].lower())[:70])
        if sig not in best or (e["stars"] or 0) > (best[sig]["stars"] or 0):
            best[sig] = e
    entries = list(best.values())

    detect_cowork(entries)

    # cowork-ready first, then by GitHub stars
    entries.sort(key=lambda e: (not e["cowork"], -(e["stars"] or 0)))
    entries = entries[:100]

    out = os.environ.get("FCS_OUT", "findcoworkskills_report.html")
    cw = render(query, entries, out)
    print(f"query={query!r}  shown={len(entries)}  cowork-ready={cw}")
    print(f"report: {os.path.abspath(out)}")


if __name__ == "__main__":
    main()
