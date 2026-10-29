#!/usr/bin/env python3
"""NewsHub 增长 helper: upload your own X Analytics CSVs and read the server-computed metrics.

Personal, not public: every call needs NEWSHUB_TOKEN (create it at 设置 › API on the site).
Standard library only. Talks to one host: NEWSHUB_BASE (default https://wqu.guru). 401 / 403 are never retried.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("NEWSHUB_BASE", "https://wqu.guru").rstrip("/")
UA = "newshub-skill/0.4.0 (growth.py)"


def token():
    t = os.environ.get("NEWSHUB_TOKEN", "").strip()
    if not t:
        raise SystemExit("NEWSHUB_TOKEN is not set: create a token at " + BASE + "/settings#api, then export NEWSHUB_TOKEN=nh_…")
    return t


def call(verb, path, params=None, body=None, ctype="application/json"):
    """One request to BASE+path with the bearer token. 429/503 back off by Retry-After; 401/403 stop at once."""
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    payload = body if isinstance(body, (bytes, type(None))) else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {"User-Agent": UA, "Accept": "application/json", "Authorization": "Bearer " + token()}
    if payload is not None:
        headers["Content-Type"] = ctype
    for attempt in range(5):
        req = urllib.request.Request(url, payload, headers, method=verb)
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            if e.code in (429, 503) and attempt < 4:
                time.sleep(float(e.headers.get("Retry-After") or 2) + attempt)
                continue
            raise SystemExit(f"HTTP {e.code} {verb} {path}: {text.strip()}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == 4:
                raise SystemExit(f"giving up on {url}: {e}")
            time.sleep(1 + 2 * attempt)
    raise SystemExit(f"giving up on {url}")


def cmd_push(a):
    if not a.account and not a.content:
        raise SystemExit("give --account and/or --content")
    for kind, path in (("account_overview", a.account), ("content", a.content)):
        if not path:
            continue
        with open(path, "rb") as f:
            raw = f.read()
        r = call("POST", "/api/me/growth/imports", {"kind": kind, "filename": os.path.basename(path)}, raw, "text/csv")
        print(f"{r['kind']}: import {r['importId']}, {r['rows']} rows, {r['dateFrom']} – {r['dateTo']}")


def cmd_followers(a):
    body = {"followers": a.count}
    if a.date:
        body["date"] = a.date
    r = call("POST", "/api/me/growth/followers", body=body)
    print(f"followers {r['followers']} on {r['date']}")


def fmt(v, unit):
    if v is None:
        return "—"
    if unit == "‰":
        return f"{v:.2f}"
    if unit == "%":
        return f"{round(v)}%"
    if unit == "条":
        return f"{v:.1f}"
    if unit == "天":
        return f"{round(v)} 天"
    return f"{round(v)}"


def line(m):
    t, hi, u = m["threshold"], m["thresholdHi"], m["unit"]
    n = (lambda x: f"{x:.2f}") if u == "‰" else (lambda x: f"{x:g}")
    unit = "%" if u == "%" else ""
    return {"<": f"< {n(t)}{unit}", ">": f"> {n(t)}{unit}", ">=": f"≥ {n(t)}", "outside": f"∉ {n(t)}–{n(hi)}"}[m["op"]]


def cmd_summary(a):
    s = call("GET", "/api/me/growth/summary", {"window": a.window})
    if a.json:
        json.dump(s, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return
    if not s["asOf"]:
        print("no growth data yet: run `growth.py push` first")
        return
    hits = [m for m in s["metrics"] if m["status"] == "breach"]
    print(f"as of {s['asOf']} · {len(hits)} of {len(s['metrics'])} metrics over the line (status reads the 7-day value)")
    for m in hits:
        print(f"{m['label']} {fmt(m['v7'], m['unit'])} / {line(m)}")


def cmd_labels(a):
    with open(a.file, encoding="utf-8") as f:
        labels = json.load(f)
    r = call("PUT", f"/api/me/growth/labels/{a.import_id}", body=labels)
    print(f"labels written {r['written']}, skipped {r['skipped']} (unknown post ids)")


def main():
    p = argparse.ArgumentParser(description="NewsHub 增长 helper (needs NEWSHUB_TOKEN). Base: " + BASE)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("push", help="upload X Analytics CSVs (newer file wins per day / per post)")
    s.add_argument("--account", help="account_overview CSV (one row per day)")
    s.add_argument("--content", help="content CSV (one row per post)")
    s.set_defaults(fn=cmd_push)

    s = sub.add_parser("followers", help="record today's (or --date) follower count")
    s.add_argument("count", type=int)
    s.add_argument("--date", help="YYYY-MM-DD, default today (UTC)")
    s.set_defaults(fn=cmd_followers)

    s = sub.add_parser("summary", help="print the metrics over their threshold as 指标 当前值 / 阈值")
    s.add_argument("--window", default="7d", choices=("7d", "30d", "90d"))
    s.add_argument("--json", action="store_true", help="print the full summary JSON instead")
    s.set_defaults(fn=cmd_summary)

    s = sub.add_parser("labels", help="write post labels from a JSON array of {postId, theme, mode, hook, format}")
    s.add_argument("import_id", type=int, help="importId of a content upload (from push)")
    s.add_argument("file")
    s.set_defaults(fn=cmd_labels)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
