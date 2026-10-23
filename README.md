# astrbot_plugin_stalzone

AstrBot 插件：在 QQ 内查询 STALZONE（原 STALCRAFT: X）官方公开数据。

- 拍卖行在售 / 近期成交
- 当前辐射爆发 / 上次爆发
- 角色公开资料（等级字段以 API 实际返回为准）
- 战队资料/列表、物品中英文名查询、行动记录、区服列表

实时数据只走官方 API，不写入 RAG 知识库；插件不需要玩家账号、OAuth 登录或保持任何软件在线。

## 文件结构

```text
astrbot_plugin_stalzone/
├── main.py              # AstrBot 入口：解析指令、调用 client、输出纯文本
├── api_client.py        # httpx.AsyncClient 封装、认证头、超时、错误分类
├── formatters.py        # 纯文本格式化（可单测）
├── command_parser.py    # /sz 指令解析（可单测）
├── item_index.py        # 中/英/俄文物品名 → item_id 解析
├── item_index.json      # 2,615 个物品的双语索引（由脚本生成）
├── item_details.json    # 1,338 个物品的属性/描述详情
├── item_icons/          # 武器/护甲/神器图标（590 个，离线可用）
├── image_renderer.py    # 可选 Pillow 图片卡片（无字体时自动退回文本）
├── lunar_client.py      # 可选 Lunar 第三方战队战报（K/D/KDA/战斗分）
├── _conf_schema.json    # AstrBot 配置项
├── metadata.yaml        # 插件元数据
├── requirements.txt     # 运行依赖
├── README.md
└── tests/
    ├── test_plugin.py             # client/formatter/index/parser 单测
    ├── test_main_integration.py   # AstrBot stub 下的 handler 测试
    └── demo_smoke.py              # 演示服真实接口冒烟
```

## 指令

| 指令 | 说明 |
| --- | --- |
| `/sz auction <物品ID/中文名/英文名> [品质] [日期] [数量]`（`/sz 拍卖行`） | 在售 + 成交；神器按品质分组，非神器显示 `物品×数量 / 起拍 / 买断 / 单价 / 剩余时间`；加日期后只查该日及之前的成交，数量需同时有品质和日期 |
| `/sz emission [EU/RU/NA/SEA/NEA]`（`/sz 风暴`） | 末日风大字计时卡：`距离上次风暴` + `xx小时xx分xx秒`（两行），下方保留当前/上次爆发记录；区服可写 EU/RU/NA/SEA/NEA（不区分大小写），省略时用配置区服 |
| `/sz player <角色名/UUID> [区服]`（`/sz 玩家`） | 公开资料：阵营徽记、状态、最后登录、战队、官方统计；区服可写 EU/RU/NA/SEA（不区分大小写），省略时用配置区服；可选 Lunar 战队战报 K/D |
| `/sz item / 物品 <中文名/英文名/ID>` | 查物品 ID、中/英/俄名、类别、完整属性、中文描述和图标 |
| `/sz 候选 <序号>` | 使用最近一次候选列表中的物品/战队，自动重放原指令（拍卖的品质、日期、数量会保留）；候选列表为两列卡片：大序号、品质色名称、ID/类别和右侧物品图标 |
| `/sz 调整 / 平衡 <武器/神器/装备>` | 查官方 Patch Note 中的平衡调整历史；中文长期索引 + 2023-2026 官方公告逐条记录（含神器） |
| `/sz 通行证计算 <等级> <每日任务>[+超载] <剩余天数> [每周天数]` | 赛季通行证经验/等级预测；也支持 `<等级> <每日任务> <超载> <剩余天数> [每周天数]`；别名 通行证、赛季通行证、通行证预测等 |
| `/sz clan / 战队 <战队名/标签/ID>` | 战队公开资料；输入 4 个英文字母（可带 `[]`）时只按标签精确匹配，不区分大小写，不再匹配全名 |
| `/sz clans [页码]` | 战队列表，每页 10 个 |
| `/sz operations [地图ID]` | 最近行动记录 |
| `/sz regions` | 官方区服列表 |
| `/sz help` | 图片帮助菜单（壁纸背景 + 模块化排版，生成后缓存） |

`/sz` 的斜杠可以省略，但 `sz` 后必须加一个空格才触发：`sz 拍卖 原子` 与 `/sz 拍卖 原子` 等价。单独发 `sz` 不会触发；需要帮助请发 `/sz` 或 `sz help`。

所有展示时间统一为 **UTC+8（北京时间）**。中文/英文/ID 都可以用于物品查询，例如：

```text
/sz item 寒冰
/sz item Chilly
/sz auction 寒冰
/sz auction Chilly
/sz auction ljn2
/sz 拍卖 原子 粉 6.11 20
```

日期支持 `6.11`、`6/11`（默认当前年份）和 `25.6.11`、`25/6/11`；日期按 UTC+8 自然日计算，包含当天全部成交。填日期后不再显示当前在售。（注: 官方api仅能查近200条数据，需要更多历史数据需第三方网站或持久化到本地）

中文翻译来自@inkstarry提供的本地化翻译文件zh.lang（神器部分在 12358–12576 行），英文名来自官方物品库；匹配支持中文全名、英文名、括号内英文、ID 和去空格/连字符写法。

> 角色列表、好友、战队成员列表属于 UserAuth 端点，需要用户 OAuth token，本插件使用应用级 `Client-Id`/`Client-Secret`，因此不提供这三类接口。

## 配置

在 AstrBot WebUI → 插件 → `STALZONE 数据查询` 中填写：
**注**： **client_id** 和 **client_secret** 的获取方法见 [应用管理 — STALZONE API 文档](https://eapi.stalzone.com/registration.html) （无要求，很简单就能获取）

| 配置项 | 默认 | 说明 |
| --- | --- | --- |
| `client_id` | 空 | EXBO 应用管理页获批后获得的 Client-Id |
| `client_secret` | 空 | Client-Secret；UI 会掩码，不要发群里 |
| `region` | `ru` | `ru/eu/na/sea/nea`；EU 群建议 `eu` |
| `lunar_enrich` | `true` | 角色资料追加 Lunar 第三方 K/D、KDA、战斗分；关闭后不请求第三方 |
| `sc_core_fallback` | `true` | 官方成交历史接口重复返回同一页时，用 SC CORE 公开历史接口补全旧成交；输出标注第三方存档，关闭后只用官方 API |
| `api_base` | 生产 | 可选 `https://dapi.stalzone.com` 演示环境；先跑通再切生产 |
| `render_mode` | `auto` | `auto`：有 Pillow+中文字体就发图片，否则发文本；`text`：始终文本卡片；`image`：强制图片（失败退回文本） |
| `font_path` | 空 | Linux 中文字体路径，例如 `/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`；留空自动查找 |

> `api_base` 是在需求的三项之外增加的第四项，仅用于演示/生产切换，避免改代码或环境变量。

认证使用 `Client-Id` + `Client-Secret` 请求头，不需要 OAuth 用户授权。API 为 Beta，返回字段可能变化；插件对缺失字段做了容错。

> 未引入 `pyscx`：该库当前要求 Python 3.13+，而本项目开发环境是 Python 3.12；直接调用官方 OpenAPI 也更方便控制超时和错误提示。

## 双语物品索引

插件自带 `item_index.json`（2,615 个物品，约 400 KB）。生成/更新时，在项目根目录（与 `astrbot_plugin_stalzone` 同级）执行：

```bash
python scripts/build_item_catalog.py --lang "xxx/zh.lang"
```

脚本需要 `data/category_all.json`（由 WIKI 分类页抓取）和 `zh.lang`。重新生成后重启/重载插件即可。中文名缺失时会回退到英文名，不会影响 ID 查询。

## 拍卖品质、强化等级与筛选

`/sz auction` 会读取拍品 `additional.qlt` 和 `additional.ptn`：

| 数值 | 品质 | 颜色 |
| ---: | --- | --- |
| 0 | 常见 | 白 |
| 1 | 罕见 | 绿 |
| 2 | 特殊 | 蓝 |
| 3 | 稀有 | 粉 |
| 4 | 独特 | 红 |
| 5 | 传奇 | 金 |

默认行为：

- **在售**：不分品质，按买断价从高到低全部列出，名称按品质颜色显示。
- **神器成交**：用横线与在售隔开，品质从高到低分组（金→红→粉→蓝→绿→白），组内按时间倒序，每个品质最多 3 条。
- **非神器在售**：不显示品质分组，按买断价从高到低；名称显示为 `物品×数量` 并使用该物品的固定品质颜色（如 Picklock 白色、Master 红色），列为 `起拍 / 买断 / 单价 / 剩余时间`，买断单价最低的条目名称右侧有绿色“最低单价”框。
- **非神器成交**：不显示品质分组，最多平铺 **10 条**，仍按时间倒序；名称同样显示 `物品×数量`，新增“单价”列，单价最低的条目带绿色“最低单价”框；有数量参数时按数量为准。
- 名称显示 `＋N` 强化等级，`＋0` 不显示。
- 如果拍品没有品质字段，归到“品质未标注”，不显示数字品质。

输入品质后（例如 `/sz 市场 原子 粉`）：

- 在售只保留该品质；
- 最近成交改为该品质最多 **10 条**，仍按时间倒序；
- 不会显示其他品质。

输入日期后（例如 `/sz 拍卖 原子 粉 6.11 20`）：

- 只显示该日期及之前的**历史成交**，不再显示当前在售；
- 神器：有品质时默认 **20 条**；只有日期、没有品质时每个品质 **5 条**；
- 非神器：默认平铺 **10 条**，不显示品质分组，成交带单价列；在品质和日期后写数字时按自定义数量；
- 数量参数范围 1–200；
- 日期按 UTC+8 自然日计算，`6.11` 包含 6 月 11 日全天；未写年份时使用当前年份；
- 日期查询从最新一页开始，每次读取 200 条向后翻，达到日期和数量后立即停止；最多检查 **4000 条**。如果官方接口重复返回同一页或 200 条分页异常，会自动降为 100 条/页重试；仍无法翻页时切换到 SC CORE 第三方历史存档按时间游标补全旧记录，并在结果底部明确标注来源。SC CORE 也有采集起点；如果目标日期早于它的覆盖范围，回复会直接显示存档起始日期，不会把重复页误报成“查了 4000 条”。

物品名/ID 匹配忽略大小写，`ak-308`、`AK-308`、`Ak-308` 都会精确解析到 AK-308。物品名没有精确匹配时，会用单字/片段和常用同义词搜索物品库并列出候选。例如 `/sz 市场 原` 会提示你可能想找 `原子`；`/sz 拍卖 高级会员` 或 `/sz 物品 高级会员` 会提示 `高级账户 1天` 到 `高级账户 180天`，而不是直接返回“未找到”。成交为空时会显示具体物品名，例如“没有找到原子成交记录”；图片空状态卡片中的物品名按查询品质着色，不附加“稀有（粉）”这类后缀。

候选列表在图片模式下渲染为两列卡片，每项一个大序号、品质色名称、ID/类别和右侧物品图标，行数随候选数量增加（最多展示最接近的前 20 个），不再固定只显示前 12/8 个；没有本地图标时会自动从物品 CDN 批量补齐，失败才显示占位符。候选列表出现后，回复 `sz 候选 1` 即可选用第 1 项，并自动重放原指令。拍卖会保留原查询中的品质、日期和数量：例如 `sz 拍卖 原 粉` 的候选 1 是原子，选后等价于执行 `sz 拍卖 原子 粉`。`物品`、`拍卖`、`调整`、`战队` 都支持；候选按群/会话保存 10 分钟，成功选择后或发送其他新指令时清除。

可识别品质词：

- 白 / 绿 / 蓝 / 粉 / 红 / 金
- 常见 / 罕见 / 特殊 / 稀有 / 独特 / 传奇
- common / uncommon / special / rare / unique / legendary
- white / green / blue / pink / red / gold

名称颜色在图片模式中生效；`render_mode=text` 时只能显示纯文本，但格式仍保留。

### 属性术语

神器/装备属性统一使用以下中文名：

| 英文 | 中文 |
| --- | --- |
| Psyonics / Psy-emissions | 精神辐射 |
| Bleeding | 流血 |
| Laceration protection | 撕裂防护 |
| Bullet resistance | 子弹防护 |
| Explosion protection | 爆炸防护 |
| Healing effectiveness | 治疗效率 |
| Periodic healing | 周期性治疗 |
| Movement speed | 移动速度 |
| Running speed | 奔跑速度 |
| Carry weight | 负重 |
| Bleeding protection | 流血防护 |
| Psy-emission protection | 精神辐射防护 |
| Reload（神器） | 充能时间 |

## 物品查询详情与图标

`/sz item` 现在会显示：

- 中/英/俄名称、ID、类别、等级（有则显示）
- 神器/武器/护甲/消耗品等完整属性（神器会显示生命、耐力、辐射、温度、精神辐射、流血等词条）
- 中文描述（来自 `zh.lang`；没有中文时回退英文）
- 物品图标（武器/护甲/神器共 590 个离线图标；其他物品会按 CDN 下载并缓存到临时目录）

图标来源为 STALZONE WIKI 的物品 CDN（`cdn3.stalzone.wiki/exbo_item_parser/...`）。图片模式下图标会直接画进物品卡片；`render_mode=text` 时只发文本。

非神器物品名同样从 `zh.lang` 解析：除了精确 `item.*.name`，还会匹配 `display_name`、会员时长（`premium_token` + duration）、弹药变体后缀（`_sessions` / `_inside` / `_frontline`）和少量本地化拼写别名；无法直接匹配的 18 件已按候选和语义补全，全部 2615 件现在都有中文名。如需修正，可把中文名填入插件数据目录的 `item_name_overrides.json`，重启后生效，不需要重建索引。

物品卡片的装备等级会着色：Newbie 绿、Stalker 蓝、Veteran 粉、Master 红、Legend 金；Picklock/DEFAULT 为白色。拍卖中的非神器名称也使用这个固定颜色。物品名显示在「STALZONE · 物品」标题下方，英文名后用括号紧跟中文翻译，同一行显示，整行使用该物品的品质/等级颜色；像 AK-105 这种中英文同名的不重复显示翻译。

神器属性会按效果好坏着色：生命、治疗效率、移动速度、抗性/防护、撕裂/燃烧/电/化学灼烧反应等正面效果为绿色；生命降低、辐射/精神辐射升高、流血/感染/中毒升高、重量/后坐力升高等负面变化为红色。所有抗性统一为“+绿 -红”，词条名称和数值一起变色。例如 `生命 +2%` 绿色、`生命 -2%` 红色、`精神辐射 +20` 红色、`流血 -20` 绿色、`撕裂反应 +2%` 绿色。

武器配件/枪口也使用同一语义：后坐力、散布、晃动、换弹时间、瞄准时间、拔枪时间降低为绿色，升高为红色；伤害、稳定化、人体工学等提高为绿色。普通武器的基础面板属性不做好坏着色。

同名词条的基础值和附加值会合并到一行，例如 `移动速度：[+0.85%; +1%]（附加：[+0.28%; +0.35%]）`；只有附加属性才出现的词条会单独显示为 `治疗效率（附加）：...`。

`/sz 调整 <装备>` 先按物品索引解析到唯一物品（支持中文名/英文名/俄文名/ID，右上角显示该物品图标），再查本地 `balance_history.json`：中文长期索引 + 168 份含平衡段落的官方公告（2023-2026），按物品名抽取全部改动并把常见属性标签翻译为中文。`x95`、`FN IWI Tavor X95` 都会解析到基础武器 `IWI Tavor X95`，不会误配到 `X95 (A)`；输入不存在的物品会直接提示“物品不存在”，不再显示成“查不到调整记录”。有物品但确实没有历史时，卡片标题仍为 `STALZONE · 平衡调整`，正文说明未找到记录。神器/护甲的历史记录也能返回，例如 `/sz 调整 螺旋` 会列出 2026-06-03、2026-01-14、2025-11-12、2025-09-03、2023-12-20、2023-10-11 六条。

`/sz 通行证计算 <等级> <每日任务>[+超载] <剩余天数> [每周天数=7]` 使用官方赛季通行证规则本地计算，不请求游戏 API。三参数 `<等级> <每日任务> <剩余天数>` 表示不用超载；四参数 `<等级> <每日任务> <超载> <剩余天数>` 表示使用超载，例如 `15 15 3 20` 等价于 `15 15+3 20`；四参数加 `+` 时最后一个数是每周天数；五参数 `<等级> <每日任务> <超载> <剩余天数> <每周天数>` 中最后一个数才是每周天数，超载可以填 0。三参数和无 `+` 的四参数默认每周 7 天；有效超载为 0 时，等级预测只显示“不用超载”一行，不再重复“使用超载”。每日任务 1–7 个 500 经验、8–15 个 250、16–45 个 75、46+ 个 25；超载只对每天前 15 个任务生效，每个 250 经验。周任务 15/45/100 个分别累计到 3/8/20 级奖励；1000 经验一级。每周三 12:00、每日 12:00（UTC+8）重置。

## 输出样式与图片字体

默认 `render_mode=auto`：

- 拍卖、角色、战队、物品、爆发、战队列表、行动记录、区服会尝试生成 **深色卡片图片**，使用低透明度官方壁纸背景，价格/属性区域保持高对比度；
- 普通拍卖查询在售和成交各最多取 **100 条**；只有带日期的查询才启用翻页（正常 200 条/页，接口异常时自动降为 100 条/页）；
- 没有 Pillow 或没有中文字体时，自动退回 **卡片式纯文本**（不是原来的长行）；
- `/sz help` 使用完整图片菜单，首次生成后缓存在 AstrBot 数据目录；只有 Pillow/中文字体不可用或图片发送失败时才回退文本。

Linux 服务器建议装中文字体：

```bash
# Debian / Ubuntu
apt-get update && apt-get install -y fonts-noto-cjk

# Alpine
apk add font-noto-cjk
```

装完重启 AstrBot。也可以把 `font_path` 指向已有字体，例如：

```text
/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc
```

Windows 会自动找 `msyh.ttc`（微软雅黑）。如果图片发送失败（NapCat 文件路径/权限），把 `render_mode` 改成 `text` 即可，文本卡片仍然比原来的单行输出更易读。

图片通过 base64 消息段发送，避免 AstrBot 与 NapCat 分容器时的本地文件路径问题。

## 阵营图标

查询玩家或战队时，图片右上角会按阵营显示对应徽记：

- 自由 Freedom
- 纪律 Duty
- 佣兵 Mercenary（兼容 `merc`/`mercenaries`）
- 契约 Covenant
- 潜行者 Stalker（兼容 `stalkers`/`loners`）
- 强盗 Bandit（兼容 `bandits`）

前期未选阵营的玩家会按接口返回的 Stalker/Bandit 显示对应徽记。图标随插件离线打包，不依赖外网；文本模式下只显示阵营中文名。

## 角色资料与 K/D / 战斗分说明

官方公开 API 的 `profile/stats` 只返回有限的公开统计，**不提供完整的 PvP 对战/战斗分数据**。插件会：

1. 展示官方 API 返回的全部统计（等级、游戏时长、击杀/死亡等，如果有）；
2. 如果官方只给击杀/死亡，自动计算一个 K/D；
3. 在 `lunar_enrich=true` 时，额外请求 Lunar 的公开战队战报接口，补充 **K/D、KDA、战斗分、场次、最近比赛**，并标注「Lunar 第三方」；
4. Lunar 未返回该玩家时，给出链接并说明“未收录或服务不可达”，不编造数字。

所以如果你在 Lunar 页面看到详细 K/D，而本插件只显示官方统计，通常是因为 Lunar 那边有战队战报/OCR 数据，而官方 API 没有。把 `lunar_enrich` 保持开启即可获得这部分补充。

### StalzoneHQ 开放世界 PvP 分数

插件按 StalzoneHQ 公开公式计算：

```text
((击杀 + 助攻 × 0.5) / (估算死亡 × 0.33)) × 1000
```

- 击杀/助攻来自官方统计的 `kil`、`ast`；
- 估算死亡 = 子弹、爆炸、出血、近战死亡之和（`bul-dea`、`exp-dea`、`ble-to-dea`、`col-dea`）；
- 异常/环境死亡不计入；
- 结果标注为“StalzoneHQ 公式”，同时显示 K/D 和 HQ 角色页链接。

HQ 页面上的 `Open World PvP Score` 是 HQ 自己保存的缓存值，更新节奏和官方统计不同；同一时刻用官方 API 实时 stats 计算，可能与页面显示值不同。插件不再维护手工分数缓存，避免每次 HQ 更新都要改数据；需要核对页面值请以 HQ 链接为准。

### 玩家简介 / PDA 富文本

玩家资料里的 `status` 是游戏内 PDA 简介，不是简单的在线状态。图片模式会单独渲染“简介 / STATUS”面板，支持：

- `§0`–`§F`：游戏预设颜色；
- `§R`：重置为白色；
- `§#RRGGBB`：自定义颜色；
- 渐变：格式化工具会为每个字符写入 `§#RRGGBB`，插件会逐字解析；
- ASCII 艺术字、换行和缩进会保留，并自动使用等宽字体；简介含中文时会自动切换到支持中文的等宽/宋体字体，不会出现方框；
- 深色（包括 `§0` 黑）会加浅色描边，避免在深色卡片上看不见；
- 纯文本回退会自动移除 `§` 代码，不会把控制码直接显示给用户。

如系统没有可用的等宽字体，可设置环境变量 `STALZONE_MONO_FONT` 指向 TTF/OTF 字体文件。玩家页同时把阵营、PvP、统计数值分区着色，避免整页同一种颜色。

### 不启动 AstrBot 的演示服冒烟测试

先向 EXBO 申请演示应用凭证([应用管理 — STALZONE API 文档](https://eapi.stalzone.com/registration.html))（或使用官方文档中的演示应用凭证，**不要把 secret 提交到仓库**），然后：

```powershell
$env:SZ_CID="你的演示 Client-Id"
$env:SZ_SECRET="你的演示 Client-Secret"
# 默认请求 dapi.stalzone.com / EU；可用 STALZONE_API_BASE、STALZONE_REGION 覆盖
python tests/demo_smoke.py
```

会输出 `y1q9` 的拍卖在售/成交和当前辐射爆发。演示服 `profile` 可能返回 404（示例数据不完整），这是数据问题，不是解析问题；用单测里的 profile fixture 验证，或切生产后用真实角色名验证。

## 国内服务器 pip 安装（重要）

如果出现：

```text
ERROR: Could not find a version that satisfies the requirement httpx<1.0.0,>=0.27.0
(from versions: 0.6.7 ... 0.22.0)
```

说明当前 pip 指向的是**阿里云内网 PyPI 镜像** `mirrors.cloud.aliyuncs.com`，它的 httpx 版本很旧（只到 0.22.0）。换用阿里云公网镜像或清华镜像：

```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
# 或
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

如果容器内已有新版 httpx，可以不重复安装，先确认：

```bash
python -c "import httpx; print(httpx.__version__)"
```

注意：如果你现在是在**宿主机**执行 pip，而 AstrBot 在 Docker 里，宿主机的包不会被容器使用。应在容器内安装：

```bash
docker exec -it astrbot pip install -r /AstrBot/data/plugins/astrbot_plugin_stalzone/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

安装后重启/重载 AstrBot。本项目按 `httpx >= 0.27` 测试；0.22 太旧，不建议用于新版 Python/AstrBot。

## 阿里云 Docker 部署

假设 AstrBot 容器名为 `astrbot`，数据目录挂载到容器的 `/AstrBot/data`（以你的 compose 实际路径为准）。

### 方式 A：docker cp

```bash
# 在 Windows 上把整个插件目录传到服务器后，在服务器执行：
docker cp astrbot_plugin_stalzone astrbot:/AstrBot/data/plugins/
docker exec -it astrbot pip install -r /AstrBot/data/plugins/astrbot_plugin_stalzone/requirements.txt
docker restart astrbot
```

### 方式 B：宿主机目录挂载（推荐）

把 `astrbot_plugin_stalzone/` 放到 compose 映射的宿主机 `data/plugins/` 下，然后：

```bash
docker exec -it astrbot pip install -r /AstrBot/data/plugins/astrbot_plugin_stalzone/requirements.txt
docker restart astrbot
```

AstrBot 通常也会在插件加载时按 `requirements.txt` 安装依赖；如果 WebUI 已显示插件但启动报 `ModuleNotFoundError: httpx`，手动执行上面的 pip 命令。

### 启用

1. 打开 AstrBot WebUI → 插件，确认 `STALZONE 数据查询` 已加载。
2. 进入插件配置，填 `client_id`、`client_secret`，`region` 设为 `eu`（或你的群所在区服）。
3. 先把 `api_base` 设为演示环境，保存并重载插件。
4. 在 QQ 群发 `/sz help`、`/sz auction y1q9`、`/sz emission`。
5. 演示通过后把 `api_base` 切回生产，填正式应用凭证，重启/重载插件。
6. 如果 NapCat 有全局唤醒前缀或命令权限限制，确认 `/sz` 能到达 AstrBot；必要时在群管理里给机器人命令权限。

## 性能与缓存

- **物品搜索**：启动时预计算每件物品的规范化别名缓存；模糊匹配先用 `SequenceMatcher` 的理论上界预筛，避免对 2,615 件物品做无意义的相似度计算。常用查询从约 20ms 降到约 2ms，复杂模糊查询约 20-40ms；搜索在线程池执行，不阻塞事件循环。
- **图片与发送**：拍卖/物品/玩家/风暴/候选卡渲染和 base64 编码全部走 `asyncio.to_thread`，图片较大时也不会卡住其他群的消息处理；帮助图本来就在线程池生成并缓存。
- **HTTP**：所有官方 API 请求共用一个 `httpx.AsyncClient` 连接池（按 `api_base` 复用，`terminate` 时关闭），避免每条命令重新建连接；普通拍卖的在售和成交仍是并发请求。
- **循环**：日期历史必须按官方分页顺序向前翻（最多 40 页/4000 条），其余热点循环均限制结果数或并发度；候选图标最多 20 个、并发 16。
- **缓存上限**：候选选择按群/会话保存 10 分钟，最多 200 个会话；SC CORE 物品键最多 4096 条；物品图标临时缓存超过 30 天自动清理（每天最多检查一次）；临时卡片图超过 24 小时清理；帮助图只保留当前版本/区服/环境的一份，版本升级会删除旧图。

## 常见问题

| 现象 | 排查 |
| --- | --- |
| 提示“未配置 Client-Id / Client-Secret” | WebUI 插件配置未填或保存后未重载 |
| 401/403 | 应用未获批、凭证错误，或拿演示凭证访问生产 |
| 演示有数据、生产为空 | **先检查 `region`**；再确认物品/角色属于该区服 |
| 400 | 物品 ID 无效、物品不可交易、角色名格式不对 |
| 404 | 角色名/物品 ID 不存在；演示服 profile 本身可能没数据 |
| 429 | 官方 API 频率限制；稍后再试，不要连续刷 |
| 超时/连接失败 | 服务器出网、DNS、代理；插件超时为 10 秒 |
| 价格和游戏里不一样 | API 有延迟、同名物品品质/强化不同；以游戏内挂单为准 |

## 设计决策

1. **只用 httpx**：AstrBot 事件循环是异步的，`requests` 会阻塞；客户端统一 10 秒超时。
2. **凭证只从配置读**：`api_client.py` 不写死任何 secret；请求头按请求注入，不打印。
3. **直接应用认证**：官方支持 `Client-Id`/`Client-Secret` 头，省掉 OAuth token 的刷新状态。
4. **api_client 与 formatter 分离**：handler 只做编排；格式化函数可单测，API 字段缺失不会让插件崩溃。
5. **宽容解析**：所有响应字段用 `.get()`；未知附加字段忽略，缺字段显示“API 未返回”。
6. **错误分级**：400/401/403/404/429/5xx/超时/非 JSON 分别给用户友好提示，技术细节只进日志。
7. **只做缓存、不存业务数据**：帮助图写到 AstrBot 的 `data/` 目录（拿不到时回退系统临时目录），物品图标写系统临时目录；索引和平衡历史只读，不保存玩家账号、实时价格或聊天内容。
8. **不把实时数据写回知识库**：知识库只存静态/历史快照；价格、爆发、玩家资料统一走本插件。

## 已实现 / 未实现

**已实现（AppAuth / 公开数据）**：拍卖在售与成交、辐射爆发、角色资料（名字/UUID）、战队搜索与详情、战队列表、行动记录、区服列表、双语物品索引。

**未实现（需要 UserAuth 用户 token）**：角色列表 `/characters`、好友列表 `/friends`、战队成员列表 `/clan/{id}/members`。本插件不保存玩家账号，也不做 OAuth 用户授权；这三类接口如果以后要做，需要单独的 User token 流程。

**后续可选**：短 TTL 内存缓存（拍卖 15-30 秒、爆发 10 秒），降低 429 风险；物品 `/sz item` 自动带出最低在售。

## 官方资料

- API 文档：<https://eapi.stalzone.com/reference>
- 认证说明：<https://eapi.stalzone.com/auth.html>
- 演示环境：<https://dapi.stalzone.com>
- AstrBot 插件文档：<https://docs.astrbot.app/dev/star/plugin-new.html>
