# NewsHub Skill — 任务流程（第三层，按需读）

每类任务一节：**先做什么、调什么、扫几个 topic、什么时候停、用哪个模板交付**。
base = `https://wqu.guru`，UA 一律 `newshub-skill/0.4.0`。脚本 `nh.py` 的安装：

```bash
curl -fsSL https://wqu.guru/skill/scripts/nh.py -o nh.py   # 只读调用本站公开 API，标准库，先审阅再运行
python3 nh.py --help
```

装过 Skill 的话，脚本已经在 `<skill 目录>/scripts/nh.py`。

---

## A 追新简报

1. 宽问题：`items?mode=selected&since=<24h>`；`ship` / `biz` / `collab` 用 `since=<7d>`。
2. 「最大 / 最热」：`/hot`；用户说了「日报」：`/daily`。
3. 用户关心论文：精选里已有论文名额；要更全的，用 `topic=ai&mode=all&category=paper`（不带 `category` 的 `mode=all` 会排除论文）。
4. ship 想知道「会不会打断我」：`items?topic=ship&tag=破坏性`，再按 `弃用`、`安全` 各查一次。

停止条件：一页够用就不翻页。模板：**简报**。

## B 事件深挖（来龙去脉、各家怎么报、谁先报）

1. 定位事件：先查 `/hot?topic=<t>&limit=30`。不在榜上的话，用 `items?q=<关键词>&mode=all` 在相关 topic 里找到一条。
2. 拿到任意一条的 `id` 后调 `GET /api/public/events/{id}`：返回同一事件的全部报道，按时间正序，
   每条都有自己的 `url`、`source`、`summary`、`tags`。
3. 「谁先报」看 `reports` 的第一条和 `earliestPublishedAt`；「各家说法」逐条对比 `summary`，
   区分官方一手、媒体、社群快讯、KOL 评论（分层见 data-map.md）。
4. 跨 topic 的同一件事（例如 ai 里的发布和 invest 里的股价反应）是不同的事件，用 D 的方法补齐。

停止条件：`/events` 一次就拿到全部成员，不需要再用关键词反查。模板：**事件档案**。

## C 实体追踪（公司 / 币 / 产品 / 账号 / 频道）

1. 列别名：中文名、英文名、代码或 ticker、产品名（如「英伟达 / NVIDIA / NVDA」）。
2. 每个别名 × 五个 topic：`items?q=<别名>&mode=all&topic=<t>`，按 `id` 去重合并。
   `mode=all` 会排除论文，实体可能出现在论文里时，在 `ai` 再加一次 `category=paper`。
   用脚本一次做完：
   ```bash
   python3 nh.py pull --topics ai,invest,ship,biz,collab --mode all --q 英伟达 --q NVIDIA --q NVDA --out nvda.jsonl
   ```
3. 账号、公众号、Telegram 频道、X 博主：用 `source=<显示名>&mode=all`。X 账号的 handle 也能用 `q=` 搜到。
   中文 X 博主再查一次 `/api/public/rank/creators/{handle}`：在榜单数据里就有粉丝曲线和近期高互动推文（见 H）。
4. 交易所动作（上币、下架、维护）：`source=<交易所公告信源名>` 加 `q=上线` / `q=下架`。信源名先从 `/sources` 里查。
5. 量大时先用 `stats?topic=<t>&mode=all&q=<别名>&by=category`（或 `by=day`）看分布，再决定拉哪部分。

停止条件：每个别名在每个 topic 都翻到 `hasNext=false`，或者已经足够回答。模板：**实体周报**。

## D 跨域关联（A 对 B 的影响、两边一起看）

1. 把问题拆成「源事件」和「受影响的领域」，比如 OpenAI 发布（ai）→ 美股和 AI 概念币（invest）。
2. 用 C 的方法，对同一组关键词分别在相关 topic 里拉取，然后合并成一条时间轴：
   ```bash
   python3 nh.py pull --topics ai,invest --mode all --q OpenAI --out oai.jsonl
   python3 nh.py timeline oai.jsonl > oai-timeline.md
   ```
3. 对每个跨 topic 的配对，用 `/events/{id}` 确认各自事件的完整报道，不要只凭标题相似就认定是同一件事。
4. 写结论时分清「数据里有人这样说」和「你的推断」；推断要标出来。

停止条件：时间轴两端都有证据，或者明确说明另一端没有讨论。模板：**跨域影响表**。

## E 统计与趋势

1. 计数一律用 `/stats`，它和 `items` 用同一套过滤条件（topic、mode、since、category、q、source、tag）：
   - 各分类各多少：`stats?topic=invest&mode=all&by=category`
   - 某话题每天的声量：`stats?topic=ai&mode=all&q=Agent&by=day`
   - 最活跃的信源或账号：`stats?topic=collab&mode=all&by=source`
   - ship 影响性质分布、collab 品牌排行：`stats?topic=ship&by=tag`、`stats?topic=collab&mode=all&by=tag`
2. 「升温」要有对照：把 7 天拆成前后两段（两次调用，分别设 `since`），或者看 `by=day` 的走势。
   超过 7 天的对比只能用日报存档，而日报只含精选，口径要写明。
3. 需要列出具体条目时，再按计数最大的那几个桶，用 `items` 定向取样。

停止条件：数字全部来自 `/stats` 的返回。模板：**趋势表**（必须写口径）。

## F 行动决策（会不会打断我 / 给我名单 / 有什么风险）

先拿到**用户上下文**，没有就问，或者从用户给的文件里读：

| 决策 | 需要的上下文 | 取数 |
|---|---|---|
| 升级清单 | 技术栈和依赖清单（语言、框架、云、客户端、SDK） | `items?topic=ship&mode=all&since=<7d>`（ship 量小，通常一两页拉完），按依赖名过滤；再用 `tag=破坏性`、`弃用`、`安全` 复核 |
| 候选名单（博主、媒体、合作方） | brief：产品、卖点、目标圈层、调性、禁区 | 用 C 的方法按 brief 关键词拉取；`/stats?by=source` 找活跃账号；collab 里看同类合作 |
| 风险提示 | 关注的标的、交易所、链 | 用 C 的方法逐个标的扫；交易所公告用 `source=`；宏观看 `invest-macro` |

候选排名的打分口径（每一项都要能指回具体的帖子）：
- **契合度**：近期内容与 brief 主题的重合程度，附 1–3 条代表帖。
- **活跃度**：7 天内的条数（来自 `/stats?by=source` 或自己数过的完整结果）。
- **内容质量**：相关条目的平均 `score`。
- **同类经验**：collab 里是否接过同类型的合作（只陈述事实，不评价）。
- **调性**：从摘要里归纳，标明是推断。

- **影响力**（可选）：候选在榜单数据里就引用 `/rank/creators/{handle}` 的粉丝数与近 30 天变化，
  一次查完：`python3 nh.py creators --from collab.jsonl`；不在榜单数据里的写「影响力数据缺失」，不要估。

互动量只有榜单推文有，报价一律没有。排名仍按契合度，影响力只作旁注。模板：**升级清单** / **候选排名**。

## G 回溯（上个月、过去几周、某一天）

1. 7 天以内：`items` + `since`。
2. 更早：先 `GET /api/public/dailies?topic=<t>&take=180` 看存档覆盖到哪天，再逐日取 `/daily/{date}`。
   一个月约 30 次调用：
   ```bash
   python3 nh.py dailies --topic ai --from 2026-09-01 --to 2026-09-30 --out sep.jsonl
   python3 nh.py rollup sep.jsonl --by category
   ```
3. 日报只包含精选条目，回答「某账号上个月发了几条」这类问题时，要说明这个口径不够。
4. 某条历史条目要看同事件的其他报道，`/events/{id}` 不受 7 天窗限制。

停止条件：时间范围内每一天都取过（404 表示那天没出日报，不是错误）。模板：**事件档案**或**趋势表**。

## H 创作者榜单（谁在涨粉、某人的粉丝趋势、最活跃的创作者）

1. 整张榜：`GET /api/public/rank`。`rise` 是涨粉榜，按近 7 天**净增**排、达标者全列；`active` 是活跃榜前 20。
   用户说了量级（「小博主」「万粉以下」「十万粉以上」）就加 `tier=small|mid|large`（<1 万 / 1–10 万 / 10–100 万）。
   先看 `windowStart`–`windowEnd` 和 `days`：`days < 7` 时窗口有缺天，要写进口径。
2. 某个人：`GET /api/public/rank/creators/{handle}`（X 用户名，不带 `@`）。
   - 粉丝趋势读 `history`（逐日，掉粉的日子也在）；不要拿 `/rank` 里的 `spark`（只有 30 天）去回答「全部」。
   - 「最近发了什么 / 为什么上榜」：只能复述 `moves[0].summary` 并逐条引用 `moves[0].tweets` 的 `url`，
     写「这周互动最高的推文是……」，**不要写成因果**。
   - `moves[0].related` 的 `id` 交给 `/api/public/events/{id}`，就能把这个人聊的事和资讯里的报道接起来。
   - 404 = 没在日榜上出现过；200 但 `history` 为空、`rise` / `active` 为 `null`（多见于英文大号）= 在日榜上出现过但
     不在跟踪范围。两种都回答「榜单数据里没有这个人的粉丝数据」，不是「这个人不存在」，也不要估。
3. 批量（候选名单、某个圈子）：
   ```bash
   python3 nh.py rank --tier mid --out mid.jsonl            # 整张榜落 jsonl（_board / _rank 字段）
   python3 nh.py creators alice_ai bob_dev                 # 指定账号的粉丝、7 天净增、30 天变化、活跃榜名次
   python3 nh.py pull --topics collab --mode all --since 7d --out collab.jsonl
   python3 nh.py creators --from collab.jsonl --limit 20    # 从条目里的 x.com 链接取账号再查
   ```
4. 交叉：榜上的人有没有接合作，用 `items?topic=collab&mode=all&q=<handle>`；这个人在聊的话题有没有资讯报道，
   用上面第 2 步的 `related`。只陈述两边的事实，不推断「接合作导致涨粉」。

停止条件：一次 `/rank` 就有整张榜；个人页一人一次。模板：**榜单速览** / **创作者档案**。
