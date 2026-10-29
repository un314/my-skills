#!/usr/bin/env python3
"""NewsHub Skill helper: bulk-read the public API into JSONL, then count or merge locally.

Read-only. Standard library only. Talks to one host: NEWSHUB_BASE (default https://wqu.guru).
"""
import argparse
import collections
import datetime as dt
import json
import os
import re
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("NEWSHUB_BASE", "https://wqu.guru").rstrip("/")
UA = "newshub-skill/0.4.0 (nh.py)"
TOPICS = ("ai", "invest", "ship", "biz", "collab")
PAUSE = 0.25
HANDLE = re.compile(r"^https?://(?:www\.)?(?:x|twitter)\.com/([^/?#]+)/status/", re.I)


def get(path, params=None, allow_404=False):
    """GET BASE+path; retries 429/503 by Retry-After and transient network errors. Returns parsed JSON or None on 404."""
    url = BASE + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    last = "rate limited"
    for attempt in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 404 and allow_404:
                return None
            if e.code in (429, 503):
                time.sleep(float(e.headers.get("Retry-After") or 2) + attempt)
                continue
            raise SystemExit(f"HTTP {e.code} {url}\n{body}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            time.sleep(1 + 2 * attempt)
            last = e
    raise SystemExit(f"giving up on {url}: {last}")


def since_arg(s):
    """Accept RFC3339 or a relative window like 24h / 7d."""
    if not s:
        return None
    m = re.fullmatch(r"(\d+)([hd])", s)
    if not m:
        return s
    delta = dt.timedelta(hours=int(m[1])) if m[2] == "h" else dt.timedelta(days=int(m[1]))
    return (dt.datetime.now(dt.timezone.utc) - delta).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_jsonl(paths):
    for p in paths:
        with (sys.stdin if p == "-" else open(p, encoding="utf-8")) as f:
            for line in f:
                if line.strip():
                    yield json.loads(line)


def open_out(path):
    return sys.stdout if path in (None, "-") else open(path, "w", encoding="utf-8")


def cmd_pull(a):
    topics = [t.strip() for t in a.topics.split(",") if t.strip()]
    bad = [t for t in topics if t not in TOPICS]
    if bad:
        raise SystemExit(f"unknown topic(s): {bad}; want {TOPICS}")
    queries = a.q or [None]
    sources = a.source or [None]
    seen, n_calls = set(), 0
    out = open_out(a.out)
    for topic in topics:
        for q in queries:
            for src in sources:
                params = {"topic": topic, "mode": a.mode, "take": 100}
                for k, v in (("q", q), ("source", src), ("category", a.category), ("tag", a.tag),
                             ("since", since_arg(a.since))):
                    if v:
                        params[k] = v
                cursor, pages = None, 0
                while pages < a.max_pages:
                    if cursor:
                        params["cursor"] = cursor
                    page = get("/api/public/items", params)
                    n_calls += 1
                    pages += 1
                    for it in page.get("items", []):
                        if it["id"] in seen:
                            continue
                        seen.add(it["id"])
                        it["_topic"], it["_query"], it["_source_filter"] = topic, q, src
                        out.write(json.dumps(it, ensure_ascii=False) + "\n")
                    cursor = page.get("nextCursor")
                    if not page.get("hasNext") or not cursor:
                        break
                    time.sleep(PAUSE)
                time.sleep(PAUSE)
    if out is not sys.stdout:
        out.close()
    print(f"pulled {len(seen)} unique items in {n_calls} calls", file=sys.stderr)


def bucket_key(it, by):
    if by == "day":
        return (it.get("publishedAt") or "")[:10] or (it.get("_date") or "")
    if by == "handle":
        if it.get("username"):
            return "@" + it["username"]
        m = HANDLE.match(it.get("url") or it.get("sourceUrl") or "")
        return "@" + m[1] if m else "(非 X)"
    if by == "tag":
        tags = it.get("tags") or []
        return tags[0] if tags else "(无标签)"
    if by == "topic":
        return it.get("_topic") or ""
    if by == "source":
        return it.get("source") or it.get("sourceName") or ""
    return it.get(by) or it.get("_section") or ""


def cmd_rollup(a):
    count, scores = collections.Counter(), collections.defaultdict(list)
    total = 0
    for it in read_jsonl(a.files):
        total += 1
        k = bucket_key(it, a.by)
        count[k] += 1
        if isinstance(it.get("score"), (int, float)):
            scores[k].append(it["score"])
    rows = sorted(count.items(), key=(lambda kv: kv[0]) if a.by == "day" else (lambda kv: -kv[1]))
    print(f"| {a.by} | 条数 | 平均分 |\n|---|---|---|")
    for k, n in rows[: a.limit]:
        avg = f"{sum(scores[k]) / len(scores[k]):.1f}" if scores[k] else "—"
        print(f"| {k} | {n} | {avg} |")
    print(f"\n共 {total} 条，{len(count)} 个分组（口径：输入文件里去重后的条目）")


def cmd_timeline(a):
    seen, rows = set(), []
    for it in read_jsonl(a.files):
        url = it.get("url") or it.get("sourceUrl") or ""
        key = url or it.get("id")
        if key in seen:
            continue
        seen.add(key)
        rows.append(it)
    rows.sort(key=lambda it: it.get("publishedAt") or "")
    for it in rows:
        when = (it.get("publishedAt") or "")[:16].replace("T", " ")
        src = it.get("source") or it.get("sourceName") or ""
        meta = "/".join(x for x in (it.get("_topic"), it.get("category")) if x)
        url = it.get("url") or it.get("sourceUrl")
        title = it.get("title", "")
        head = f"[{title}]({url})" if url else title
        print(f"- {when} UTC {head} — {src}" + (f"（{meta}）" if meta else ""))


def cmd_dailies(a):
    start = dt.date.fromisoformat(a.date_from)
    end = dt.date.fromisoformat(a.date_to)
    out, n_days, n_items = open_out(a.out), 0, 0
    day = start
    while day <= end:
        d = get(f"/api/public/daily/{day.isoformat()}", {"topic": a.topic}, allow_404=True)
        if d:
            n_days += 1
            for sec in d.get("sections", []):
                for it in sec.get("items", []):
                    if isinstance(it.get("publishedAt"), (int, float)):
                        it["publishedAt"] = dt.datetime.fromtimestamp(
                            it["publishedAt"] / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                    it["_topic"], it["_date"], it["_section"] = a.topic, d.get("date"), sec.get("label")
                    out.write(json.dumps(it, ensure_ascii=False) + "\n")
                    n_items += 1
        day += dt.timedelta(days=1)
        time.sleep(PAUSE)
    if out is not sys.stdout:
        out.close()
    print(f"{n_days} dailies, {n_items} items ({start}..{end}, topic={a.topic}; 404 days skipped)", file=sys.stderr)


def cmd_rank(a):
    params = {"tier": a.tier} if a.tier else None
    b = get("/api/public/rank", params)
    out, n = open_out(a.out), 0
    for board in ("rise", "active"):
        if a.board not in (board, "both"):
            continue
        for i, row in enumerate(b.get(board, []), 1):
            row["_board"], row["_rank"], row["_window"] = board, i, b.get("windowEnd")
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    if out is not sys.stdout:
        out.close()
    print(f"{n} rows, window {b.get('windowStart') or '-'}..{b.get('windowEnd') or '-'} "
          f"({b.get('days', 0)}/7 days), tiers {b.get('tiers')}", file=sys.stderr)


def creator_row(h, c):
    if c is None:
        return [f"@{h}", "—", "—", "不在榜单数据里", "—", "—"]
    hist = c.get("history") or []
    if not hist and not c.get("rise"):
        return [f"@{c['username']}", c["name"], "—", "无粉丝数据（不在跟踪范围）", "—", "—"]
    last = hist[-1]["followers"] if hist else None
    d30 = f"{last - hist[-31]['followers']:+,}" if len(hist) > 30 else "—"
    rise, act = c.get("rise"), c.get("active")
    r7 = f"{'≈' if rise['approx'] else ''}{rise['gained']:+,}（{rise['tier']} 第 {rise['rank']}）" if rise else "不在涨粉榜"
    ar = f"第 {act['rank']}" if act and act.get("rank") else "—"
    return [f"@{c['username']}", c["name"], f"{last:,}" if last is not None else "—", r7, d30, ar]


def cmd_creators(a):
    handles = [h.lstrip("@").lower() for h in (a.handles or [])]
    if a.from_files:
        counts = collections.Counter(bucket_key(it, "handle") for it in read_jsonl(a.from_files))
        handles += [k[1:].lower() for k, _ in counts.most_common() if k.startswith("@")]
    handles = list(dict.fromkeys(h for h in handles if re.fullmatch(r"[a-z0-9_]{1,15}", h)))[: a.limit]
    out = open_out(a.out) if a.out else None
    print("| 账号 | 名字 | 粉丝 | 近 7 天净增 | 近 30 天 | 活跃榜 |\n|---|---|---|---|---|---|")
    found = 0
    for h in handles:
        c = get(f"/api/public/rank/creators/{h}", allow_404=True)
        found += c is not None
        print("| " + " | ".join(creator_row(h, c)) + " |")
        if out and c is not None:
            out.write(json.dumps(c, ensure_ascii=False) + "\n")
        time.sleep(PAUSE)
    if out:
        out.close()
    print(f"\n{found}/{len(handles)} 个账号在榜单数据里（口径：/api/public/rank/creators；不在榜单 ≠ 账号不存在）")


def main():
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    p = argparse.ArgumentParser(description="NewsHub public API helper (read-only). Base: " + BASE)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pull", help="page /api/public/items into JSONL (dedup by id)")
    s.add_argument("--topics", default="ai", help="comma list of ai,invest,ship,biz,collab")
    s.add_argument("--mode", default="all", choices=("all", "selected"))
    s.add_argument("--q", action="append", help="keyword; repeat for aliases")
    s.add_argument("--source", action="append", help="exact source / account name; repeatable")
    s.add_argument("--category")
    s.add_argument("--tag")
    s.add_argument("--since", help="RFC3339 or 24h / 7d (server clamps to 7 days)")
    s.add_argument("--max-pages", type=int, default=200)
    s.add_argument("--out", help="JSONL path (default stdout)")
    s.set_defaults(fn=cmd_pull)

    s = sub.add_parser("rollup", help="count JSONL items by a key")
    s.add_argument("files", nargs="+")
    s.add_argument("--by", default="source", choices=("source", "category", "day", "topic", "handle", "tag"))
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(fn=cmd_rollup)

    s = sub.add_parser("timeline", help="merge JSONL files, dedup by url, print a markdown timeline")
    s.add_argument("files", nargs="+")
    s.set_defaults(fn=cmd_timeline)

    s = sub.add_parser("dailies", help="fetch daily reports for a date range into JSONL")
    s.add_argument("--topic", default="ai", choices=TOPICS)
    s.add_argument("--from", dest="date_from", required=True, help="YYYY-MM-DD (UTC)")
    s.add_argument("--to", dest="date_to", required=True, help="YYYY-MM-DD (UTC)")
    s.add_argument("--out")
    s.set_defaults(fn=cmd_dailies)

    s = sub.add_parser("rank", help="dump the 榜单 (涨粉榜 / 活跃榜) into JSONL")
    s.add_argument("--tier", choices=("small", "mid", "large"))
    s.add_argument("--board", default="both", choices=("rise", "active", "both"))
    s.add_argument("--out")
    s.set_defaults(fn=cmd_rank)

    s = sub.add_parser("creators", help="look up X accounts in the 榜单 data (followers, 7/30-day change)")
    s.add_argument("handles", nargs="*", help="X usernames, @ optional")
    s.add_argument("--from", dest="from_files", nargs="+", help="JSONL from pull/rank: use its x.com handles, most frequent first")
    s.add_argument("--limit", type=int, default=30)
    s.add_argument("--out", help="JSONL of full creator profiles")
    s.set_defaults(fn=cmd_creators)

    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
