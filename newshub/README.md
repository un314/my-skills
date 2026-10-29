# NewsHub Skill — 今日资讯（人类可读说明）

这是 NewsHub 的 **Agent Skill**：装进你的 AI 助手后，当你问起「今天 AI 圈有什么」「今天币圈
和宏观有什么动静」「我依赖的工具最近有什么破坏性变更」「创业和增长最近有什么新观点」之类
问题时，助手会**实时**去 NewsHub 拉最新资讯，整理成带原文链接的中文简报回给你——而不是凭
过时的训练数据脑补。

覆盖五套互相隔离的数据集：**AI**（默认）、**Invest**（加密 / 股市 / 宏观 / 套利 / 研究）、
**Ship**（我们依赖的东西变了没有：客户端 / AI 编程与模型 / 交易所与金融 API / 云与平台 /
语言与库）、**Biz**（商业与创业：创业与融资 / 产品与增长 / 战略与拆解 / 组织与管理 /
独立开发与小生意）、**Collab**（合作动态：中文推特创作者的品牌合作——AI 产品与模型 / 加密与 Web3 /
交易与支付 / 工具与服务 / 课程与社群）。

> NewsHub 把全网信源采集、用 LLM 做中文化 / 评分 / 分类 / 精选 / 聚类去重后开放出来。
> 这条 Skill 只是教你的 Agent **怎么按需调它的公开 API**。匿名免费、无需 token、零配置。

## 这是什么

`SKILL.md` 是给 Agent 看的指令文件（触发设计 + 意图路由表 + 参数约定 + 链接红线）；
`references/` 里的五份（任务流程 / 数据地图 / curl 配方 / 响应样例 / 交付模板）是 Agent **用到时才读**的第三层，
这样常驻上下文里只装真正影响判断的内容。
这个 `README.md` 是给你（人类）看的安装与使用说明。

## 装到哪

Skill 文件放在你的 Agent 的 skills 目录里，每个平台不同：

| 平台 | 默认目录 |
|---|---|
| Claude Code | `~/.claude/skills/newshub` |
| Codex | `~/.codex/skills/newshub` |
| Gemini CLI | `~/.gemini/skills/newshub` |

## 一键安装

```bash
curl -fsSL https://wqu.guru/skill/install.sh | bash
```

脚本会把 `SKILL.md`、`README.md`、`references/`（五份按需读的文件）和 `scripts/nh.py`（只读调用公开 API 的辅助脚本，Python 标准库）下载到
`~/.claude/skills/newshub/`。
**不需要 sudo、不会改文件权限**——你可以先 `curl -fsSL https://wqu.guru/skill/install.sh` 看一眼脚本内容，
确认无误后再 `| bash`。

装到其他平台，用 `SKILL_DIR` 环境变量切换目录：

```bash
# Codex
SKILL_DIR="$HOME/.codex/skills/newshub" bash <(curl -fsSL https://wqu.guru/skill/install.sh)
# Gemini CLI
SKILL_DIR="$HOME/.gemini/skills/newshub" bash <(curl -fsSL https://wqu.guru/skill/install.sh)
```

**另一种装法**：直接对你的 Agent 说一句自然话——「帮我安装这个 skill：https://wqu.guru/skill/」。

## 怎么确认装的文件没被改过

`https://wqu.guru/skill/VERSION` 是一份纯文本清单，写着：

- 当前 Skill 版本，以及这批文件是从哪次源码提交构建的（revision）；
- 每个文件**提交时**（填入站点地址前）的 sha256。

安装脚本装完会按清单逐个校验，对不上就报错退出，并打印版本与 revision。装之前想先审脚本，就先
`curl -fsSL https://wqu.guru/skill/install.sh` 看内容，它的 sha256 也在清单里。

站点公开了源码时，清单里还会有 `source`（源码目录链接）和 `raw` 两行；这时安装加
`NEWSHUB_VERIFY=github`，脚本会再拿同一 revision 的原文逐个比一遍，不经过本站：

```bash
NEWSHUB_VERIFY=github bash <(curl -fsSL https://wqu.guru/skill/install.sh)
```

## 装完怎么用

重启 / 重新加载你的 Agent，然后用自然语言提问，例如：

- 「今天 AI 圈有什么新东西？」
- 「看一下今天的 AI 日报。」
- 「今天币圈 / 美股 / 宏观有什么动静？」
- 「Claude Code 最近有什么破坏性变更？」
- 「创业公司怎么找 PMF，最近有什么新观点？」
- 「最近一周的 AI 论文有哪些？」
- 「上个月 15 号的日报。」
- 「这次 Gemini 发布，各家怎么报的？谁最先报？」
- 「英伟达这周在 AI 和美股两边都有什么动态？」
- 「这周币圈哪个分类声量最大？哪些交易所上了新币？」
- 「我用 Go + Cloudflare + Claude Code，这周有哪些变更会打断我？」
- 「按这份活动 brief，找最合适的 10 个博主并排名。」
- 「过去一个月 AI 圈的大事时间线。」
- 「这周中文推特谁涨粉最多？万粉以下的呢？」
- 「@某博主 最近粉丝怎么变的？这周发了什么？」

Agent 会先判断任务类型（简报 / 事件深挖 / 实体追踪 / 跨域关联 / 统计趋势 / 行动决策 / 回溯 / 创作者榜单），
按对应流程选接口、拉数据，交付带原文链接、写明口径的中文答复。

## 三轨关系（一句话）

NewsHub 对外有三条接入轨，**共享同一批资讯、只是投影不同**：**Skill**（本项，给任意 Agent
按需拉取并整理简报）、**RSS**（给任意阅读器零配置订阅，`/feed.xml` 等三条）、**REST API**
（给开发者二次开发，`/api/public/*` + `/openapi.yaml`）。详见 https://wqu.guru/agent。

## 合理使用与测试版声明

- **测试版**：NewsHub 仍在打磨中，接口与内容可能调整。
- **原文为准**：摘要为机器生成的中文概要，请以原文链接为准。
- **链接不许编**：Skill 要求 Agent 逐字复制接口返回的原文链接；接口没给链接时它只写信源名，
  或给 NewsHub 站内条目页 `https://wqu.guru/i/{id}`——任何情况下都不该凭摘要拼出一个链接。
- **合理使用**：匿名免费、单 IP 限流 600 req/min（串行调用、翻页温柔些）；请勿滥抓。
- **必须带非空 User-Agent**（Skill 用 `newshub-skill/0.4.0`）：空 UA、SEO 采集 bot 和 Go 默认的
  `Go-http-client` UA 会被 403。自己写脚本调 API 时记得显式设置。
