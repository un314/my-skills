---
name: newshub
description: >-
  拉取 NewsHub 公开 API（多信源采集、已中文化、评分、聚类的五套资讯数据集），
  回答一切**依赖当下事实**的问题：简报、事件来龙去脉、公司 / 币种 / 账号追踪、跨领域影响、
  统计与趋势、依赖升级清单、博主与合作调研、创作者涨粉与活跃榜、近几个月回溯。领域是 AI / 大模型、
  投资金融（加密 / 股市 / 宏观）、开发者依赖的版本与破坏性变更、创业与增长方法、中文推特创作者的
  品牌合作与粉丝增长。典型问法：「今天 AI 圈有什么」「这件事各家怎么报的」「英伟达这周有什么」
  「我用 Go 和 Cloudflare，这周哪些变更会打断我」「哪些博主适合这个活动」「这周谁涨粉最多」
  「过去一个月 AI 大事」。
  不适用于与这五个领域无关的话题，以及不需要时效的历史知识问答。
  宁可 overtrigger：不调本 Skill，就是把过时的训练数据当作今日事实。
---

# NewsHub — 资讯情报（Agent Skill）

NewsHub 把全网信源采集后，用 LLM 中文化、评分、分类、精选、聚类去重，再对外开放。
你（Agent）按需调用它的公开 API，把结果整理成**带原文链接、口径清楚**的中文答复。

**Base URL** = `https://wqu.guru`。匿名免费，零配置。**必须带非空 User-Agent**（推荐 `newshub-skill/0.4.0`）。
**也可接成 MCP 服务器**：`claude mcp add --transport http newshub https://wqu.guru/mcp`（工具与下方端点一一对应、同一套红线）。

## 0. 先判任务类型，再选流程

| 任务 | 用户在说 | 入口（详细流程见 playbooks） |
|---|---|---|
| A 追新简报 | 今天 / 这周有什么、最新发布 | `items?mode=selected`，「最热」走 `/hot`，说了「日报」走 `/daily` |
| B 事件深挖 | 这件事怎么回事、各家怎么报、谁先报 | `/hot` 或 `items` 找到条目 id → `GET /api/public/events/{id}` |
| C 实体追踪 | 某公司 / 币 / 产品 / 账号最近的动态 | `q=<关键词>&mode=all` 逐 topic 扫；账号与频道用 `source=` |
| D 跨域关联 | A 对 B 有什么影响、两边一起看 | 同一组关键词在相关 topic 各扫一遍，按时间轴合并 |
| E 统计趋势 | 多少条、哪个在升温、哪些品牌最多 | `GET /api/public/stats?by=…`，**不要**翻页自己数 |
| F 行动决策 | 会不会打断我、给我名单、有什么风险 | 先拿到用户上下文（技术栈 / 标的 / brief），再按 C 和 E 取数、打分 |
| G 回溯 | 上个月、过去几周、某天的情况 | 7 天以内走 `items`；更早走 `/dailies` + `/daily/{date}` |
| H 创作者榜单 | 谁在涨粉、哪些博主起来了、某人粉丝趋势、最活跃的创作者 | `GET /api/public/rank`；具体某人走 `/rank/creators/{handle}` |

只要是 B–H，先读 **`https://wqu.guru/skill/references/playbooks.md`** 里对应那一节再动手。
它规定每类任务调哪些端点、扫几个 topic、什么时候停、用哪个模板交付。

## 1. 五套数据集（同一组端点，只差 `?topic=`）

| topic | 覆盖 | 量级 | 信源形态 |
|---|---|---|---|
| `ai`（默认） | 模型、产品、行业、论文、技巧 | 大 | 媒体与官方博客 RSS、X List、公众号 |
| `invest` | 加密 / 股市 / 宏观 / 套利 / 研究（`crypto` 是别名） | 最大 | RSS、Telegram 快讯、公众号、交易所公告、YouTube |
| `ship` | 依赖系统的发版、弃用、破坏性变更、安全修复 | 小 | GitHub Releases、Changelog、App Store |
| `biz` | YC / Lenny's / 20VC / Stratechery 这类方法与拆解 | 小 | Newsletter 长文、访谈转写 |
| `collab` | 中文推特创作者的品牌合作推文 | 小 | 单一 X List |

确切量级随部署和时间变化，用 `stats?topic=<t>&mode=all&by=category` 现查（`total` 即 7 天条数）。
写法：`?topic=ai` `?topic=invest` `?topic=ship` `?topic=biz` `?topic=collab`（不传即 `ai`）。
信源形态、可信度分层、各数据集的特殊字段，见 **`https://wqu.guru/skill/references/data-map.md`**。

`category` slug（随 topic 变，也是日报 `sections[].label` 的中文名）：
- `ai`：`ai-models` 模型发布/更新、`ai-products` 产品发布/更新、`industry` 行业动态、`paper` 论文研究、`tip` 技巧与观点。
- `invest`：`invest-crypto` 加密货币、`invest-stock` 股市、`invest-macro` 宏观、`invest-arb` 套利与机会、`invest-research` 研究与分析。
- `ship`：`ship-client` 客户端、`ship-agent` AI 编程与模型、`ship-exchange` 交易所与金融 API、`ship-infra` 云与平台、`ship-runtime` 语言与库。
- `biz`：`biz-startup` 创业与融资、`biz-product` 产品与增长、`biz-strategy` 战略与拆解、`biz-ops` 组织与管理、`biz-solo` 独立开发与小生意。
- `collab`：`collab-ai` AI 产品与模型、`collab-crypto` 加密与 Web3、`collab-fintech` 交易与支付、`collab-service` 工具与服务、`collab-course` 课程与社群。

**榜单不是第六个 topic**：中文 X 创作者的涨粉榜 / 活跃榜（`/api/public/rank*`）与五套条目数据分开，
不带 `?topic=`。粉丝数、粉丝曲线、推文互动量**只在榜单端点里有**，`/items` 依旧没有。

三个容易踩的坑：
- `mode=all`（包括 `q=` 关键词检索）**会排除 `paper`**；精选里有论文名额，不受影响。
  在 `ai` 里做关键词检索或全量拉取时，要论文就再用 `category=paper` 查一次。
- `tags` 不在 `/items` 的返回里。ship 的 `tags[0]` 是影响性质（`破坏性` > `弃用` > `安全` > `新功能` > `修复`），
  collab 的 `tags[0]` 是活动品牌。要按标签取条目用 `items?tag=<标签>`，要看标签本身用 `/events` 或日报。
- `biz` 和 `collab` 的量小、聚类稀疏，日报经常是空的，这是正常结果，不是调用出错。

## 2. 端点

| 端点 | 用途 |
|---|---|
| `GET /api/public/items` | 条目列表。`mode` `topic` `category` `since` `take` `cursor` `q` `source` `tag` |
| `GET /api/public/hot` | 72 小时多信源大事件热度榜。`topic` `category` `limit`（1–30，缺省 5） |
| `GET /api/public/events/{id}` | 某条目所在事件的**全部报道**：各信源的链接、摘要、`tags`，按时间正序，不受 7 天窗限制 |
| `GET /api/public/stats` | 与 `items` 同一套过滤条件，按 `by=category\|source\|day\|tag` 返回计数和 `total` |
| `GET /api/public/daily` / `daily/{YYYY-MM-DD}` | 某个 UTC 日的日报（导语 + 分版块，条目带 `tags`） |
| `GET /api/public/dailies` | 日报索引（`take` ≤ 180），用来确定能回溯到哪天 |
| `GET /api/public/sources` | 信源墙：已收录信源的 `name` / `url`，全量、不分 topic |
| `GET /api/public/rank` | 创作者榜单：近 7 天涨粉榜（按净增，全部达标者）+ 活跃榜前 20。`tier=small\|mid\|large` |
| `GET /api/public/rank/creators/{handle}` | 上过榜的创作者：逐日粉丝 `history`、两榜名次、上榜概要与原推。没上过榜 404 |

意图对应的路由（简报类问题按这张表选）：

| 用户在说 | 调用 |
|---|---|
| 宽问题：「今天 AI 圈」「过去 24 小时」 | `items?mode=selected&since=<24h>&take=50`（`ship` / `biz` / `collab` 量小，宽问题用 `since=<7d>`） |
| 最大 / 最重要 / 最热 / 头条 | `GET /api/public/hot` |
| 明确说「日报」 | `GET /api/public/daily`（带日期走 `/daily/{date}`） |
| 明确说「全部 / 全量 / 所有」 | `items?mode=all&take=50` |
| 带分类：「最近一周的论文」 | `items?mode=selected&category=<slug>&since=<7d>` |
| 公司 / 关键词 | `items?q=<关键词>&mode=all`，**五个 topic 逐一问** |
| 某信源 / 账号 / 频道的全部 | `items?source=<信源名>&mode=all` |
| 「你们收了哪些信源」 | `GET /api/public/sources`（信源墙） |
| 谁涨粉最多 / 哪些博主起来了 / 最活跃 | `GET /api/public/rank`（分档用 `tier=`） |
| 某个博主的粉丝趋势、为什么上榜、发了什么 | `GET /api/public/rank/creators/{handle}`（handle 不带 `@`） |

**路由规则**：
- **默认精选**：没有明确信号时用 `mode=selected`。没说「日报」不要走 `/daily`（它是 UTC 整日切片，
  和「过去 24 小时」对不上）；没说「全部」不要走 `mode=all`。
- **关键词检索必须 `mode=all`，而且必须逐个 topic 问一遍**：精选池很小，`q=` 又只搜当前一个 topic。
  `?q=blender` 返回 0，而 `?q=blender&mode=all` 在 `ai` 和 `biz` 里都有。五次全空才能说「没有」。
- 关键词一律用服务端 `q=`（搜标题、原文标题、摘要、标签、账号名，账号 handle 也能搜到），不要拉一页回来自己 grep。
  `/items?q=` 按 `publishedAt` 倒序，**不按相关度、不折叠事件**；同一事件请用 `/events/{id}` 合并。
- 某信源的全部用 `source=<精确信源名>`。聚合源（X List / 公众号 / Telegram）传账号或频道的显示名，就能穿透到该账号。
- **计数一律用 `/stats`**。`items` 返回的 `count` 是本页条数，不是总数，不能当统计结果。

## 3. 参数与调用约定

- `since`：RFC3339，**7 天硬上限**（更早会被 clamp 到 7 天前，不报错）；晚于现在 1 分钟以上返回 400。
- `take` ≤ 100（默认 50）。`cursor` 是黑盒，只能原样跟随；`hasNext=false` 或 `nextCursor=null` 就停。
- `topic` 只认五个值，其它值返回 400；`category` 必须属于当前 topic。
- **限流**：单 IP 600 次/分钟，串行调用、间隔约 200ms。429 / 503 按 `Retry-After` 退避后重试。
- 空 UA、采集 bot、Go 默认的 `Go-http-client` UA 一律 403。预期可能非 2xx 的请求不要用 `curl -f`，
  改用 `curl -sSL -w '\n%{http_code}'`，否则看不到 `{"error":"..."}` 的说明。
- **调用预算**：先用 `/hot`、`/daily`、`mode=selected`、`/stats`，再用 `q` / `source` / `category` / `tag` 定向收窄。
  只在确实需要逐条材料时才全量翻页（先用 `/stats` 的 `total` 估算页数，大数据集一周可能上百页）；要批量拉取，用下面的脚本。

**附带脚本**（Python 3 标准库，只读调用本站公开 API，可先审阅再运行）：
`https://wqu.guru/skill/scripts/nh.py`。子命令有 `pull`（多 topic 拉取到 jsonl，自动翻页、限流、退避）、
`rollup`（按信源 / 分类 / 日期 / 账号计数）、`timeline`（多文件按 url 去重后排成时间轴）、
`dailies`（批量拉取一段日期的日报条目）、`rank`（榜单落 jsonl）、`creators`（按账号查粉丝与 7 / 30 天变化，
可直接读 `pull` 的结果）。用法见 playbooks。

完整 curl 配方：**`https://wqu.guru/skill/references/curl-recipes.md`**。
响应字段与样例：**`https://wqu.guru/skill/references/response-shapes.md`**（权威 schema 是 `https://wqu.guru/openapi.yaml`）。

## 4. 链接与事实红线（交付前逐条核对）

- **链接一律逐字复制**：每个 URL 都必须原样照抄 payload 的 `url`（items / hot / events）或 `sourceUrl`（daily）。
  **禁止**拼接、猜测、缩短、「修正」域名，禁止从摘要、信源名或记忆里推断链接格式。编出来的链接比不给链接有害得多。
- payload 里没有链接，就只写信源名；或者给站内条目页 `https://wqu.guru/i/{id}`（每个 id 都有），并说明这是 NewsHub 的条目页，不是原文。
- `/hot` 的 `duplicateSources` 只是信源名，不带链接。要各家的链接，调 `/events/{id}`，不要自己编。
- **事实只能来自返回的 `title` / `summary` / `tags`**：每个数字、日期、结论都要在 payload 里找得到出处。
- **统计数只能来自 `/stats` 或你自己数过的完整结果**，并写明口径：topic、mode、时间窗、过滤条件。
  只拉了一部分就不要报总数。
- **数据里没有的东西不要补**：条目数据（items / hot / events / daily）没有粉丝数、互动量；只有**上过榜的中文创作者**
  能从 `/rank*` 拿到粉丝数、粉丝曲线和概要推文的互动数，`/rank/creators/{handle}` 404、或 200 但 `history` 为空的人就是没有。
  报价、行情价格、持仓一律没有。缺的数据直接说明、请用户另行提供；不要估算，也不要用训练记忆填。
- **榜单只记录、不解释**：`summary` 只描述推文内容。不要替它补因果（「因为发了 X 所以涨粉」），也不要判断
  真假、营销或刷量。`approx=true` 的数字按日榜加总、掉粉时偏高，引用时写「约」。
  链接照抄推文的 `url`；本人主页是唯一可以拼的链接：`https://x.com/<username>`。
- **collab 只记录、不评判**：可以说谁接了什么合作、怎么写的；不判断「是否商业关联、是否未披露」。
  给博主排名时，写明排的是「与需求的内容契合度」；影响力只能引用 `/rank/creators/{handle}` 返回的粉丝数，
  不在榜单数据里的候选写「影响力数据缺失」。

交付模板（简报、事件档案、实体周报、跨域影响表、趋势表、升级清单、候选排名、榜单速览、创作者档案）：
**`https://wqu.guru/skill/references/output-templates.md`**。

## 5. 边界（做不到就明说，并给替代入口）

- 逐条数据只有最近 7 天；更早的只有日报存档（精选条目，按 UTC 日），用 `/dailies` 查能回溯到哪天。
- 只覆盖已接入的信源（清单看 `/sources`）。**「查不到」不等于「没覆盖」**：宣布某主题不在覆盖面之前，
  必须先做完 `?q=<关键词>&mode=all` × 五个 topic 的扫描。
- 只有摘要，没有原文全文或播客完整转写。用户要深读时，给原文链接。
- 榜单只覆盖第三方公开日榜上出现过的中文 X 创作者，粉丝曲线从开始跟踪那天算起；不是全网排名，
  也不覆盖英文账号。榜单为空（`windowEnd` 是空串）是正常结果。
- 站内网页的搜索、相关推荐等是另一套接口，不属于本契约，不要调用或模仿它们的行为。

## 6. 本文档过期了怎么办

references 和脚本每次都按上面的 URL 现拉，永远是最新的；会过期的只有你手上这份 SKILL.md。
返回值里出现本文档没写的 topic、字段或分类，或者按这里写的调用被拒，就重新读一遍 `https://wqu.guru/skill/`。
覆盖磁盘上的旧版：`bash <(curl -fsSL https://wqu.guru/skill/install.sh)`。

## 7. 个人接口（需要 Token）

前 6 节的公开接口照旧匿名。用户在站点「设置 › API」（`https://wqu.guru/settings#api`）生成 Token、
设置 `NEWSHUB_TOKEN` 之后，才能调用下面的 `/api/me/growth/*`，请求头带 `Authorization: Bearer $NEWSHUB_TOKEN`。
**没有 Token 就不要调用**，直接告诉用户去哪里生成。

| 端点 | 权限 | 用途 |
|---|---|---|
| `POST /api/me/growth/imports?kind=account_overview\|content` | `growth:write` | 上传 X Analytics 导出的 CSV（`text/csv` 原文作 body），返回 `importId`、日期范围、行数 |
| `POST /api/me/growth/followers` | `growth:write` | 关注者快照 `{date, followers}`（CSV 里没有总数） |
| `GET /api/me/growth/summary?window=7d\|30d\|90d` | `growth:read` | 服务端算好的 10 项指标、阈值与状态（`status: breach\|ok\|off\|nodata`）、每日 / 每周、Top 帖子、`labelVocab` |
| `PUT /api/me/growth/labels/{importId}` | `growth:write` | 给帖子写标签 `[{postId, theme, mode, hook, format}]`，页面的「按主题」靠它 |

**增长同步流程**：用户说「同步增长数据」或给出 X 的 CSV 时——

1. `python3 scripts/growth.py push --account <csv> --content <csv>`（`https://wqu.guru/skill/scripts/growth.py`，
   标准库）。同一天 / 同一帖重复上传，以新文件为准。
2. `python3 scripts/growth.py summary --window 7d`：读服务端的指标。**不要在本地重算**，页面和 Agent 用同一套口径。
3. 只回报越线的指标，格式是「指标 当前值 / 阈值」，不写结论散文。阈值由用户在设置页配置，**Agent 不改**（Token 也改不了）。
4. 要打标签时用 `growth.py labels <importId> labels.json`：`mode` / `hook` / `format` 只能取 `summary.labelVocab` 里的值，
   `theme` 是用户自己的主题名（≤ 24 字）；`format=article` 会参与「距上篇 Article」。

红线：
- CSV、指标与标签只属于这个用户，**不得出现在任何公开输出里**（不贴进公开回答、不发到别处）。
- 401 / 403 表示 Token 缺失、失效或权限不够，**原样告诉用户，不要重试**。
- 导出只有日期没有时刻，**不要**推算「最佳发帖时间」；帖子级新增只占账户新增的一部分，账户级数字只看 summary。
