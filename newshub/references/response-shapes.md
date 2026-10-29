# NewsHub Skill — 响应 shape（第三层，按需读）

权威 schema 以 `https://wqu.guru/openapi.yaml` 为准；本文件只讲样例与易错点。

**items 响应（envelope）**

```json
{
  "count": 50,
  "hasNext": true,
  "nextCursor": "opaque-token-or-null",
  "items": [
    {
      "id": "01J...",
      "title": "中文展示标题",
      "title_orig": "Original title or null",
      "url": "https://原文链接",
      "source": "信源人话名（如 Anthropic Newsroom）",
      "publishedAt": "2026-06-10T01:41:12.000Z",
      "summary": "事实性中文摘要",
      "category": "ai-models",
      "score": 82,
      "selected": true
    }
  ]
}
```

- Item 只有这 **10 个语义字段**；`source` 是字符串（人话源名），不是对象。
- **不带**标签 / 相关度 / 聚类等内部字段——别在 items 里找 `tags`（按标签过滤用 `tag=`，看标签用 `/events` 或日报）。
  多源印证在 `/hot` 给，同一事件的全部报道在 `/events/{id}` 给。
- `id` 对应站内条目页 `https://wqu.guru/i/{id}`（每个 id 都有；缺 `url` 或用户要可分享链接时用它）。

**daily 响应（`/daily` 与 `/daily/{date}` 同 shape）**

```json
{
  "date": "2026-06-10",
  "generatedAt": 1749519672000,
  "windowStart": 1749427200000,
  "windowEnd": 1749513600000,
  "lead": { "title": "导语标题", "paragraph": "导语段落" },
  "sections": [
    {
      "label": "模型发布/更新",
      "items": [
        { "title": "条目标题", "summary": "中文摘要",
          "sourceUrl": "https://原文链接", "sourceName": "信源名",
          "id": "01...", "duplicateCount": 3, "tags": ["OpenAI", "Agent"],
          "publishedAt": 1749506400000 }
      ]
    }
  ]
}
```

- `lead` 可能为 `null`；`sections[].label` 只会是该 topic 那 5 个固定中文值；空版块会被省略。
- `tags` 与 `publishedAt` 是可选字段（旧日报可能缺失）；后者为原条目的 unix 毫秒发布时间。
- `topic=ship` 的日报里 **`tags[0]` 是影响性质**（`破坏性` | `弃用` | `安全` | `新功能` |
  `修复`）——输出时当成条目前缀标签，读者据此判断「会不会打断我」。
- ⚠️ `/daily` 的 `generatedAt` 是 **unix 毫秒整数**，而 `/dailies` 索引里的 `generatedAt` 是
  **RFC3339 字符串**——两处类型不同，别混用。

**hot 响应（`/hot`）**

```json
{
  "count": 5,
  "items": [
    {
      "id": "01J...", "title": "事件头条", "url": "https://原文链接",
      "source": "代表信源（已穿透到账号）", "publishedAt": "2026-06-15T...Z",
      "earliestPublishedAt": "...", "latestPublishedAt": "...",
      "duplicateCount": 13,
      "duplicateSources": ["华尔街见闻（RSS）", "宝玉", "IT之家（RSS）"],
      "heat": 8.4
    }
  ]
}
```

- `duplicateCount` = 除代表外还有几家**不同信源**报道同一事件（多源印证强度）；
  `duplicateSources` = 那些信源的**具名清单**（聚合源已穿透到账号）。
- 空榜 `{"count":0,"items":[]}` 是正常结果，不是错误。

**events 响应（`/events/{id}`）**

```json
{
  "id": "01J...（事件代表条目）",
  "title": "事件标题",
  "topic": "ai",
  "category": "ai-models",
  "earliestPublishedAt": "2026-10-13T13:33:25.000Z",
  "latestPublishedAt": "2026-10-14T05:03:34.000Z",
  "sourceCount": 19,
  "reportCount": 21,
  "capped": false,
  "reports": [
    {
      "id": "01J...", "title": "中文标题", "title_orig": "Original or null",
      "url": "https://该信源自己的原文链接", "source": "信源名（已穿透到账号）",
      "publishedAt": "2026-10-13T13:33:25.000Z", "summary": "中文摘要",
      "category": "ai-models", "score": 88, "selected": true,
      "tags": ["Google", "Gemini"], "sourceReportCount": 1
    }
  ]
}
```

- `reports` 按 `publishedAt` **正序**：第一条是最早的报道。每条的 `url` 是那家信源自己的链接，可以逐条引用。
- `sourceReportCount` > 1 表示同一信源对这件事发了多篇，这里只列了一篇。`capped=true` 表示成员太多被截断。
- 不受 7 天窗限制；id 不存在或条目已隐藏返回 404 `{"error":"event not found"}`。
- 每家信源只列一条：被查询的那条代表它自己的信源，其他信源列最早的一篇；`sourceReportCount` 是该信源的总篇数。
- 顶层 `title` / `topic` / `category` 取自事件的代表条目。

**stats 响应（`/stats`）**

```json
{
  "topic": "invest", "mode": "all", "by": "category",
  "since": "2026-10-07T08:00:00.000Z", "until": "2026-10-14T08:00:00.000Z",
  "total": 8581,
  "buckets": [ { "key": "invest-crypto", "count": 4614 }, { "key": "invest-stock", "count": 2259 } ]
}
```

- `total` 是符合过滤条件的条目总数；`buckets` 按 `count` 倒序，`by=day` 时按日期正序（UTC 日）。
- `by=tag` 统计的是 `tags[0]`：ship 是影响性质，collab 是活动品牌，其他数据集是第一个关键词。没有标签的条目计入 `total`，但不进任何桶。
  注意 `items?tag=` 匹配的是**任意一个**标签，和 `by=tag` 只看第一个不同。
- `mode` 缺省是 `selected`；要全量计数必须显式传 `mode=all`。
- 过滤条件、7 天窗、paper 排除都与 `/items` 完全一致，所以 `/stats` 的数和 `/items` 翻完的条数对得上。

**rank 响应（`/rank`）**

```json
{
  "windowStart": "2026-10-08", "windowEnd": "2026-10-14", "days": 7,
  "tiers": { "all": 110, "small": 46, "mid": 58, "large": 6 },
  "rise": [
    {
      "handle": "alice_ai", "username": "Alice_AI", "name": "Alice",
      "followers": 44624, "gained": 9340, "pct": 26.47, "posts": 325,
      "title": "模型写的一句话标题", "summary": "模型写的概要（只描述推文内容）",
      "avatar": "/og/rank/avatar/alice_ai.jpg", "related": 0, "tier": "mid", "approx": false,
      "spark": [33438, 33502, "… 30 个逐日粉丝数 …", 44624]
    }
  ],
  "active": [
    { "handle": "carol", "username": "Carol", "name": "卡罗尔", "followers": 4438,
      "score": 186, "counted": 5, "likes": 11506, "avatar": "/og/rank/avatar/carol.jpg" }
  ]
}
```

- `rise` 按 `gained`（近 7 天净增）降序，达标者全部列出；`tier=` 只筛 `rise`，`tiers` 与 `active` 不受影响。
- `title` / `summary` 只有每档前 15 名有，其余是空串。`approx=true` 时数字是日榜加总，偏高。
- `pct` 是百分数（26.47 = 26.47%）。`avatar` 是站内路径；没有头像是空串。
- 本人主页 = `https://x.com/<username>`（`username` 保留原大小写，`handle` 是小写）。

**rank creator 响应（`/rank/creators/{handle}`）**

```json
{
  "handle": "alice_ai", "username": "Alice_AI", "name": "Alice", "bio": "本人 X 简介原文", "avatar": "/og/rank/avatar/alice_ai.jpg",
  "history": [ { "day": "2026-09-02", "followers": 32433 }, { "day": "2026-10-14", "followers": 44624 } ],
  "rise": { "windowEnd": "2026-10-14", "rank": 2, "tier": "mid", "gained": 9340, "pct": 26.47, "followers": 44624, "approx": false },
  "active": { "windowEnd": "2026-10-14", "rank": 2, "score": 109.5, "followers": 44624, "likes": 17355, "tweets": [ "…同 tweets…" ] },
  "moves": [
    {
      "windowEnd": "2026-10-14", "followers": 44624, "gained": 9340, "pct": 26.47, "posts": 325,
      "title": "…", "summary": "…",
      "tweets": [
        { "id": "1900000000000000001", "text": "推文正文", "url": "https://x.com/Alice_AI/status/1900000000000000001",
          "createdAt": 1791889218000, "likes": 15232, "retweets": 1546, "quotes": 795, "replies": 1289, "views": 2810679,
          "photos": 0, "videos": 0, "quoteUsername": "", "quoteName": "", "quoteText": "" }
      ],
      "related": [ { "id": "01J...", "title": "条目标题", "topic": "ai", "source": "信源名" } ]
    }
  ],
  "peers": [ { "handle": "bob_dev", "name": "Bob", "gained": 9883, "avatar": "/og/rank/avatar/bob_dev.jpg" } ]
}
```

- `history` 是全部逐日读数（UTC 日升序），掉粉的日子也在；趋势、近 30 天变化都从这里算。
- `rise` 是**档内**名次，不在涨粉榜上为 `null`。`active.rank` 是完整活跃榜里的名次（可能大于 20），`0` = 不够上榜条件；
  近 7 天没有推文记录时 `active` 为 `null`。
- `moves` 最多 6 条、新到旧；只有第一条带 `tweets` 和 `related`，更早的只有数字和概要。
- 推文互动数是采集那一刻的读数；图片和视频只有数量（`photos` / `videos`），看原推请用 `url`。
- 没在日榜上出现过的 handle：404 `{"error":"not found"}`。出现过但不在跟踪范围的（英文账号、百万粉以上）：200，
  `history` / `moves` 为 `[]`、`rise` / `active` 为 `null`——同样是「没有粉丝数据」。
