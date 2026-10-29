# NewsHub Skill — curl 配方（第三层，按需读）

所有示例 base = `https://wqu.guru`，统一带 UA `newshub-skill/0.4.0`（**必须**：空 UA 或 Go 默认的
`Go-http-client` UA 会 403）。日期用 mac/linux 兜底写法（mac BSD `date -v` 失败时回退 GNU `date -d`）。

五套数据集：任意路由末尾加 `?topic=invest`（金融）/ `?topic=ship`（依赖系统变更）/
`?topic=biz`（创业与增长）/ `?topic=collab`（品牌合作动态），不传即 `topic=ai`。

**① 宽问题 → 精选 + 过去 24 小时**

```bash
SINCE=$(date -u -v-24H +%FT%TZ 2>/dev/null || date -u -d '24 hours ago' +%FT%TZ)
curl -fsSL "https://wqu.guru/api/public/items?mode=selected&since=$SINCE&take=50" \
  -H 'User-Agent: newshub-skill/0.4.0'
```

**② 今天的日报（用户明确说「日报」）**

```bash
curl -fsSL "https://wqu.guru/api/public/daily" \
  -H 'User-Agent: newshub-skill/0.4.0'
```

**③ 全部动态（用户明确说「全部 / 全量」）**

```bash
curl -fsSL "https://wqu.guru/api/public/items?mode=all&take=50" \
  -H 'User-Agent: newshub-skill/0.4.0'
```

**④ 最近一周的论文（分类 + 7 天窗）**

```bash
SINCE=$(date -u -v-7d +%FT%TZ 2>/dev/null || date -u -d '7 days ago' +%FT%TZ)
curl -fsSL "https://wqu.guru/api/public/items?mode=selected&category=paper&since=$SINCE&take=50" \
  -H 'User-Agent: newshub-skill/0.4.0'
```

**⑤ 公司 / 关键词（服务端搜索，不要客户端 grep）**

`q=` **必须配 `mode=all`**（精选池很小——`ai` 只有当天约 8%，用缺省的 selected 搜关键词几乎必然 0 条），
而且 `q=` 只搜**当前一个** topic（缺省 `ai`）——覆盖面问题要五个数据集都扫。

```bash
for T in ai invest ship biz collab; do
  curl -fsSL "https://wqu.guru/api/public/items?q=OpenAI&mode=all&topic=$T&take=50" \
    -H 'User-Agent: newshub-skill/0.4.0'
  sleep 0.2
done
```

只有这五次**全部**返回 `{"count":0}` 时，才可以说「近 7 天池子里没有这个主题」。

**⑥ 指定日期的日报（「上个月 15 号的日报」）**

那天**可能没出报**（404 是正常情况），所以这里**不要用 `-f`**——加 `-w` 把状态码带出来，
这样既能拿到 body 又能据状态码分支（200=取报、404=那天无日报、429/503=退避）。

```bash
curl -sSL -w '\n%{http_code}' "https://wqu.guru/api/public/daily/2026-05-15" \
  -H 'User-Agent: newshub-skill/0.4.0'
# 最后一行是 HTTP 状态码；404 时 body 为 {"error":"daily not found"} → 告诉用户那天没有日报
```

**哪些日期有日报（日报存档索引）**

```bash
curl -fsSL "https://wqu.guru/api/public/dailies?take=30" \
  -H 'User-Agent: newshub-skill/0.4.0'
```

**⑦ 当前最大事件（多信源热点榜）**

```bash
curl -fsSL "https://wqu.guru/api/public/hot" \
  -H 'User-Agent: newshub-skill/0.4.0'
# 空榜 {"count":0} 是正常（眼下没够热的多源事件）。
# 只看某子分类：加 ?category=<slug>（未知/跨 topic slug → 空榜不报错）。
# 放大榜单：加 ?limit=N（1–30，缺省 5）。
```

**⑧ 某个信源 / 账号的全部**

```bash
curl -fsSL "https://wqu.guru/api/public/items?source=吴说&mode=all&take=50" \
  -H 'User-Agent: newshub-skill/0.4.0'
# 信源名取自已有结果的 source 字段；聚合源（X List / 公众号）传账号显示名即穿透到该账号。
# 订阅它的 RSS：https://wqu.guru/feed/all.xml?source=<信源名>（可加 &topic=…）
```

**⑨ 收录了哪些信源（信源墙）**

```bash
curl -fsSL "https://wqu.guru/api/public/sources" \
  -H 'User-Agent: newshub-skill/0.4.0'
# 全量无分页（约二百多条）、不分 topic；items[].name 可直接作 items?source=<name> 过滤。
# 聚合源（X List / 公众号）只有源本身在墙上，账号显示名要从 items 结果的 source 字段取。
```

**翻页（cursor 黑盒，只顺序跟随）**

```bash
# 把上一页响应里的 nextCursor 原样塞回去，直到 hasNext=false 或 nextCursor=null
curl -fsSL "https://wqu.guru/api/public/items?mode=selected&cursor=<上一页的 nextCursor>&take=50" \
  -H 'User-Agent: newshub-skill/0.4.0'
# 串行、间隔 ~200ms；429 按 Retry-After 退避，503 busy 同样退避重试。
```

**⑩ 事件的全部报道（深挖、谁先报、各家怎么说）**

```bash
# id 取自 /hot、/items 或日报里任意一条；不受 7 天窗限制
curl -sSL -w '\n%{http_code}' "https://wqu.guru/api/public/events/<id>" \
  -H 'User-Agent: newshub-skill/0.4.0'
# 404 {"error":"event not found"} = id 不存在或已隐藏；reports 按 publishedAt 正序，第一条就是最早的报道
```

**⑪ 计数与趋势（不要翻页自己数）**

```bash
# 与 items 同一套过滤；by = category | source | day | tag（tag 指 tags[0]）
curl -fsSL "https://wqu.guru/api/public/stats?topic=invest&mode=all&by=category" \
  -H 'User-Agent: newshub-skill/0.4.0'
curl -fsSL "https://wqu.guru/api/public/stats?topic=ai&mode=all&q=Agent&by=day" \
  -H 'User-Agent: newshub-skill/0.4.0'
curl -fsSL "https://wqu.guru/api/public/stats?topic=ship&mode=all&by=tag" \
  -H 'User-Agent: newshub-skill/0.4.0'
# total = 符合条件的条目总数；items 响应里的 count 只是本页条数
```

**⑫ 按标签取条目（ship 的破坏性变更、collab 的某个品牌）**

```bash
curl -fsSL "https://wqu.guru/api/public/items?topic=ship&mode=all&tag=破坏性&take=100" \
  -H 'User-Agent: newshub-skill/0.4.0'
```

**⑬ 批量拉取与回溯（脚本）**

```bash
curl -fsSL https://wqu.guru/skill/scripts/nh.py -o nh.py
python3 nh.py pull --topics ai,invest --mode all --q 英伟达 --q NVIDIA --out nv.jsonl
python3 nh.py rollup nv.jsonl --by day
python3 nh.py timeline nv.jsonl
python3 nh.py dailies --topic ai --from 2026-09-01 --to 2026-09-30 --out sep.jsonl
python3 nh.py rank --tier mid --out mid.jsonl
python3 nh.py creators alice_ai bob_dev
```

**⑭ 创作者榜单（谁在涨粉 / 最活跃）**

```bash
curl -fsSL "https://wqu.guru/api/public/rank" \
  -H 'User-Agent: newshub-skill/0.4.0'
# 只看某一档：?tier=small（<1 万粉）| mid（1–10 万）| large（10–100 万）；其它值等于不筛，不报错。
# rise = 涨粉榜（按 gained 净增降序，全部达标者），active = 活跃榜前 20；tiers 永远是全量人数。
# windowEnd 为空串 = 还没有榜单数据（正常结果）；days < 7 = 窗口里有缺天。
```

**⑮ 某位创作者的档案（粉丝曲线、上榜推文）**

```bash
curl -sSL -w '\n%{http_code}' "https://wqu.guru/api/public/rank/creators/alice_ai" \
  -H 'User-Agent: newshub-skill/0.4.0'
# handle = X 用户名，不带 @，大小写不敏感。404 {"error":"not found"} = 没在日榜上出现过，不是账号不存在；
# 200 但 history 为空 = 出现过但不在跟踪范围（英文账号、百万粉以上），同样没有粉丝数据。
# history = 全部逐日粉丝；moves[0].tweets[].url 是原推链接（逐字引用）；moves[0].related[].id 可交给 /events/{id}。
```
