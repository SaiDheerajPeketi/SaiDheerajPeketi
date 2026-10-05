"""Generate repository-owned profile graphics using only public GitHub data."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import urllib.request
from xml.sax.saxutils import escape

USER = "SaiDheerajPeketi"
COLORS = ["#78a8ff", "#f0b86e", "#c1a0fa", "#75d7b3", "#a2b3ce"]


def request_json(path):
    headers = {"User-Agent": "SaiDheerajPeketi-profile", "Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    request = urllib.request.Request("https://api.github.com" + path, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def collect(fetch=request_json):
    user = fetch(f"/users/{USER}")
    repos = []
    page = 1
    while True:
        batch = fetch(f"/users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos.extend(r for r in batch if not r["private"])
        if len(batch) < 100:
            break
        page += 1
    original = [r for r in repos if not r["fork"]]
    languages = Counter(r["language"] for r in original if r.get("language"))
    merged = fetch(f"/search/issues?q=author%3A{USER}+is%3Apr+is%3Amerged+is%3Apublic&per_page=1")
    if merged.get("incomplete_results"):
        raise RuntimeError("GitHub returned incomplete pull request totals; keeping the previous graphics.")
    return {"repositories": user["public_repos"], "merged_prs": merged["total_count"],
            "followers": user["followers"], "languages": dict(sorted(languages.items(), key=lambda x: (-x[1], x[0])))}


def render(data, date, mobile=False):
    width, height = (480, 460) if mobile else (880, 350)
    language_items = list(data["languages"].items())
    entries = language_items[:4]
    other = sum(value for _, value in language_items[4:])
    if other:
        entries.append(("Other", other))
    total = sum(data["languages"].values())
    title = f'{data["repositories"]} public repositories; {data["merged_prs"]} merged public pull requests; {data["followers"]} followers.'
    description = "Primary languages by public, non-fork repository count: " + "; ".join(f"{name}: {count}" for name, count in language_items)
    pieces = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">',
              f'<title id="title">{escape(title)}</title><desc id="description">{escape(description)}</desc>',
              f'<rect width="{width}" height="{height}" rx="8" fill="#101d36"/>',
              '<g font-family="Verdana,sans-serif" fill="#f2f7ff">',
              '<text x="30" y="58" font-size="30" font-weight="bold">Open source activity</text>']
    lines = [f'{data["repositories"]} public repositories', f'{data["merged_prs"]} merged public pull requests', f'{data["followers"]} followers']
    if mobile:
        for i, line in enumerate(lines):
            pieces.append(f'<text x="30" y="{106+i*34}" font-size="21">{line}</text>')
        bar_y, legend_y, columns = 250, 310, 2
        pieces.append('<text x="30" y="220" font-size="20" fill="#c7d9f5">Primary languages · public source repos</text>')
    else:
        pieces.append(f'<text x="30" y="108" font-size="25">{escape("  ·  ".join(lines))}</text>')
        pieces.append('<text x="30" y="163" font-size="21" fill="#c7d9f5">Primary languages · public source repos (forks excluded)</text>')
        bar_y, legend_y, columns = 187, 251, 3
    cursor = 30.0
    for i, (name, count) in enumerate(entries):
        segment = (width-60)*count/total
        pieces.append(f'<rect x="{cursor:.2f}" y="{bar_y}" width="{segment:.2f}" height="24" fill="{COLORS[i]}"/>')
        cursor += segment
        x, y = 30 + (i % columns)*((width-60)//columns), legend_y + (i//columns)*33
        pieces.append(f'<circle cx="{x+6}" cy="{y-7}" r="6" fill="{COLORS[i]}"/>')
        pieces.append(f'<text x="{x+22}" y="{y}" font-size="18">{escape(name)} · {count}</text>')
    if not total:
        pieces.append(f'<text x="30" y="{legend_y}" font-size="20">No public language data available.</text>')
    pieces.append(f'<text x="30" y="{height-25}" font-size="16" fill="#c7d9f5">Public GitHub data · Updated {date} UTC</text></g></svg>\n')
    return "".join(pieces)


def update(output, fetch=request_json):
    data = collect(fetch)  # Fetch all data before touching the last successful assets.
    date = datetime.now(timezone.utc).date().isoformat()
    graphics = {"activity.svg": render(data, date), "activity-mobile.svg": render(data, date, True)}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, graphic in graphics.items():
        temporary = output / (name + ".tmp")
        temporary.write_text(graphic, encoding="utf-8")
        temporary.replace(output / name)
    print(json.dumps(data))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "assets")
    update(parser.parse_args().output)
