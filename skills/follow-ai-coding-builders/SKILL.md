---
name: follow-ai-coding-builders
description: 搜索过去7天 AI 编程领域与工程范式高信号动态（最新AI动态 / AI雷达 / 最近AI新技术 / AI工程实践 / AI协作范式 / AI工具链）
---

# Follow AI Coding Builders

## 职责

搜索 AI 编程领域与工程范式过去 7 天的一手信息和高信号工程讨论，为"每周 AI 编程技术雷达"提供候选素材。覆盖产品动态、协作模式、工程方法论和工具链。

## 重点寻找

1. **官方博客**、Release Notes、产品文档
2. **GitHub Repo / Release / Issue / Discussion**
3. **工程师实测**、真实项目复盘、技术博客
4. **Benchmark**、论文、评测文章
5. **高信号人物**和工程团队观点

## 触发条件

用户提到以下关键词时激活：
- "最新AI动态"
- "AI雷达"
- "最近AI新技术"
- "AI工程实践"
- "AI协作范式"
- "AI工具链"

## 关注方向

- AI Coding Agent（Claude Code、Codex、Cursor、GitHub Copilot、Windsurf、JetBrains AI、Sourcegraph、Qwen Code 等）
- IDE / CLI 工具链
- Anthropic / OpenAI 开发者动态
- Agentic Workflow、MCP、Tools、Skills
- AI 辅助真实开发实践（非演示、非 Demo）
- **AI 协作范式**（小团队 + AI 工作模式、远程协作、code review / 测试 / 部署范式变化）
- **工程方法论**（AI 时代的开发流程、质量保障、交付节奏）
- **工具链新发现**（debug、监控、CI/CD 的 AI 化，周边效率工具）

## 排除标准

不要收录：
- 泛泛 AI 新闻（大模型参数、通用 AI 能力讨论）
- 营销稿、软文、PR 通稿
- 重复转述（二手、三手搬运）
- 低价值榜单（"Top 10 AI Tools"类）
- 纯学术研究且无工程落地关联
- 纯观点输出（没有代码、产品、实测的内容）——只看建造者，不跟网红
- 不推测、不脑补：不根据某人沉默、缺席或间接线索推测其动向，只收录已公开发布的内容
- **纯理论讨论**——只有观点没有实际项目/团队/代码佐证的"AI 会改变一切"类文章
- **工具软文**——"10 个提升你 10 倍效率的 AI 工具"类列表文

## 工作流程

### 1. 搜索与过滤

#### 优先关注的高信号来源

搜索时优先覆盖以下来源，确保信息质量。以下来源从 zarazhangrui/follow-builders 的 25 人完整清单中精选：

**个人（一线建造者）**
- Andrej Karpathy — AI 研究者、工程实践
- Swyx（Shawn Wang）— AI 开发者生态、Agent 实践
- Amjad Masad（Replit CEO）— AI 编程工具实践
- Guillermo Rauch（Vercel CEO）— 开发者工具、AI 产品化
- Aaron Levie（Box CEO）— 企业 AI 落地、Agent 实施
- Sam Altman（OpenAI CEO）— OpenAI 产品方向、AGI 动态
- Garry Tan（YC CEO）— AI 创业投资、Agent 工具链
- Peter Steinberger — OpenClaw 创始人、多 Agent 实践
- Dan Shipper（Every CEO）— MCP、AI 工程化
- Aditya Agarwal（South Park Commons）— 早期 AI 投资、技术判断

**团队/官方**
- Anthropic Engineering Blog
- OpenAI / Codex 官方渠道
- Google AI Blog / Google Labs
- Vercel Blog
- Claude Blog
- Netflix Engineering Blog
- Spotify Engineering
- Stripe Blog

**社区**
- Hacker News 深度帖（高评论、有工程团队参与讨论的）

**播客**
- Latent Space
- No Priors
- The MAD Podcast
- Unsupervised Learning
- AI & I by Every

#### 搜索范围

对不同内容类型采用不同的时间窗口，避免统一窗口导致推文噪音过多或播客内容过少：

- X 社交动态：搜索最近 2-3 天（高频发布）
- 官方博客：搜索最近 7 天（中频发布）
- 播客：搜索最近 14 天（低频发布）

搜索方向：

- Anthropic / Claude Code 官方动态
- OpenAI / Codex 官方动态
- Cursor、Windsurf、GitHub Copilot 更新
- GitHub 热门 AI coding 仓库 Release
- 工程师实测博客（Vercel、Supabase、Linear 等技术团队）
- Benchmark 与评测

**搜索批次与上限**：最多执行 2 轮搜索，总计不超过 8 次 WebSearch。
- **第 1 轮（必执行，5-6 次并行）**：覆盖核心产品 + 高信号人物 + 范式与工具。推荐关键词：
  - `Claude Code OR Codex OR Cursor update latest`
  - `Anthropic OR OpenAI OR Google AI coding agent`
  - `GitHub Copilot agent changelog`
  - `Latent Space podcast AI coding`
  - `karpathy OR swyx OR "Amjad Masad" OR "Guillermo Rauch" AI`
  - `AI engineering team workflow OR collaboration OR "how we build"`
- **第 2 轮（可选，仅当高信号来源无有效素材时补搜，1-2 次）**：针对缺失来源补搜。
  - X 定向搜索示例：`site:x.com karpathy`、`site:x.com swyx`
  - 播客定向搜索示例：`Latent Space podcast episode 2026`
  - 范式与工具补搜示例：`site:news.ycombinator.com AI engineering lessons`
- 达到 8 次上限后停止搜索，基于已有素材整理输出。宁可输出少，不为了凑数而搜索。

**时间过滤**：以当前日期为锚点，按以下窗口逐条检查搜索结果发布时间：
- X 社交动态：最近 2-3 天
- 官方博客：最近 7 天
- 播客：最近 14 天
超过对应窗口的素材直接丢弃，不进入后续整理环节。无法确认时间的素材标记为"时间不明"并排除。
**补搜机制**：过滤后如果某高信号来源素材不足，针对该来源补一轮搜索。

**来源限流**：同一来源（同一人或同一博客）最多收录 3 条素材，超过时只保留最重要的，防止单一话痨来源霸占推送。

### 2. 整理素材

只输出候选素材，不写周报。采用紧凑推送格式，适配手机屏幕扫读。

**区块顺序与排序规则**：
先按以下顺序分四个区块，每个区块内部按重要性从高到低排列：

1. X / 社交动态 — 建造者近期发言与产品发布
2. 官方博客 — Anthropic、OpenAI、Google、Vercel、Netflix、Spotify、Stripe 等
3. 播客 — Latent Space、No Priors、MAD Podcast 等
4. 范式与工具 — 协作模式、工程方法论、工具链新发现

**同级别次级排序**：同一区块内重要性等级相同时，按时间倒序排列（最新的在前）。

**"范式与工具"区块限流**：该区块上限 5 条。如果当周有高质量范式与工具动态，至少收录 1-3 条；不足 1 条时直接跳过该区块，不强行凑数。

每条素材格式如下：

```
🔴 高 | [事件简述]
[URL]
来源：[发布方/作者]

🟡 中 | [事件简述]
[URL]
来源：[发布方/作者]
```

每条 3-4 行，重要性用 emoji 标识：

- 🔴 高 = 产品发布/重大技术突破/颠覆性观点
- 🟡 中 = 常规更新/产品迭代/有价值的讨论
- 🟢 低 = 次要动态/有趣但不核心的观察

**确定性数据原则**：摘要中只能引用搜索结果中实际存在的内容（原文、原文观点、原文数据），不得添加、推测或脑补搜索结果中未出现的信息。区分"数据来源"（搜索结果中的事实）和"摘要加工"（AI 的格式化和精简），禁止在摘要中添加搜索结果中不存在的内容。

**摘要质量规则**：
- **全名+职位**：使用全名+职位/公司（例："Replit CEO Amjad Masad"，不写"Amjad"或"@amasad"）
- **无链接不收录**：每条必须附带原始 URL，无法确认 URL 的素材不收录
- **核心判断前置**：摘要开头优先写大胆预测、反主流观点或关键产品发布，不按时间顺序平铺。2-4 句话说明核心内容，不凑字数
- **转引带上下文**：转发、引用或回应他人内容时，说明原推背景和上下文，不孤立摘录
- **thread 整体概括**：连续系列推文作为一条处理，整体概括核心观点，不逐条摘录
- **无实质内容直接跳过**：某来源这周只有日常问候、纯转发、营销内容或空洞感慨时，不写入推送，直接跳过该来源

**播客摘要规则**：
- 按 episode 处理，不按片段或单条引用
- 标注节目名称、嘉宾身份和核心论点
- 只收录与 AI 编程直接相关的讨论（Agent、MCP、Skills、IDE 工具链等），纯投资/商业话题不收录

### 3. 输出

**区块分隔**：四个区块之间用空行分隔，手机屏幕上一屏能看清边界。

**来源去重**：同一事件优先保留最一手来源（原推/官方博客），转发/回应作为上下文补充收录，不与原推重复列为两条。

**来源限流裁剪**：同一来源超过 3 条时，按以下优先级保留：
1. 重要性优先（🔴 > 🟡 > 🟢）
2. 同级内按时间倒序（最新的在前）

**数量限制**：最多输出 18 条。低于 3 条时说明本周动态较少，附一句简短说明。

**末尾署名**：推送末尾加一行 `—— AI 技术雷达 · 自动生成`，便于转发时标识来源。

**自动化推送模式**：当由龙虾/OpenClaw 定时触发时（检测到 PLATFORM=openclaw 或 cron 环境），只输出纯净推送素材，不附加任何解释性文字、思考过程、总结段落或确认提示。确保 stdout 内容可直接转发到企微群。

## 变更记录

### 2026-05-26
- 扩展内容范围：从纯 AI 编程产品动态扩展到包含协作范式、工程方法论、工具链（"上一层"内容）
- 新增触发条件："AI工程实践"、"AI协作范式"、"AI工具链"
- 新增独立区块"范式与工具"作为第四区块，上限 5 条，质量不足时跳过
- 搜索策略：第 1 轮 5-6 次，第 2 轮补搜范式/工具，预留 2-3 次补搜容量
- 新增高信号来源：Netflix/Spotify/Stripe Engineering Blog、Hacker News 深度帖
- 新增搜索关键词：AI team workflow/collaboration（第1轮）、HN 工程帖（第2轮补搜）
- 新增排除标准：纯理论讨论（无项目/团队/代码佐证）、工具软文（"10 个工具"类列表文）

### 2026-05-22
- 试运行后评估，修复 3 项问题：
  - 时间过滤：增加具体窗口定义 + 补搜机制，防止混入超期内容
  - 同级别次级排序：明确"同级内按时间倒序"
  - 来源限流裁剪：明确"按重要性优先 > 同级内时间倒序"的裁剪策略
- grill-me 讨论确认：区块分类结构保持不变、重要性分级不做过度细化
- 补充搜索上限：最多 2 轮 / 8 次 WebSearch，防止过度搜索
- 增加 X 平台定向搜索关键词（site:x.com）和播客定向搜索，提升 X/播客区块覆盖率

### 2026-05-21
- 重写 SKILL.md：从"跟踪公开 skill 模式"改为"搜索 AI 编程领域周间动态，为周报提供素材"
- 补充触发条件（中文）和 description 中英混合
- 新增时间过滤步骤，超过 7 天丢弃
- 输出格式改为紧凑推送格式，适配企微/微信
- 新增"只看建造者"排除标准
- 吸收 [zarazhangrui/follow-builders](https://github.com/zarazhangrui/follow-builders) 的 3 个模式：
  - 优先关注的高信号来源列表（X 建造者 + 团队/官方博客 + 播客）
  - 摘要质量规则（全名+职位、无链接不收录、跳过空洞内容、2-4 句话）
  - 推送区块顺序（X / 官方博客 / 播客）
- 补充 5 条摘要规则（来自 zarazhangrui/follow-builders 的 prompts/summarize-tweets.md 和 prompts/digest-intro.md）：
  - 核心判断前置：摘要开头优先写大胆预测/反主流观点
  - 转引带上下文：转发/回应他人内容时说明原推背景
  - thread 整体概括：连续系列推文作为一条处理，不逐条摘录
  - 无实质内容跳过：某来源本周无内容时直接跳过，不凑数
  - 播客摘要规则：按 episode 处理，标注嘉宾+核心论点，只收录 AI 编程相关
- 补充 5 条轻量模式（不涉及复杂数据采集）：
  - 不推测不脑补：排除基于沉默/缺席/间接线索的推测
  - 重要性三级定义：🔴 产品突破 / 🟡 常规更新 / 🟢 次要动态
  - 区块空行分隔：适配手机屏幕扫读
  - 来源去重细化：原推优先，转评作上下文补充
  - 末尾署名：AI 技术雷达 · 自动生成
- 借鉴 zarazhangrui/follow-builders 数据采集架构的 3 个设计原则：
  - 分时间窗口搜索：X 2-3 天、博客 7 天、播客 14 天（原 generate-feed.js 的 lookbackHours 设计）
  - 来源限流：同一来源最多 3 条（原 MAX_TWEETS_PER_USER / MAX_ARTICLES_PER_BLOG 设计）
  - 确定性数据原则：摘要不添加搜索结果中不存在的内容（原 prepare-digest.js 的 LLM remix 架构理念）
- 新增自动化推送模式：龙虾定时触发时只输出纯净素材，stdout 可直接转发企微群
