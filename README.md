<div align="center">

# STALZONE 数据查询

**把 STALZONE 的实时数据查询搬进 QQ 群。**

拍卖 · 风暴 · 玩家 · 战队 · 物品 · 候选卡 · 通行证计算

![AstrBot](https://img.shields.io/badge/AstrBot-plugin-5865F2?style=flat-square)
![Version](https://img.shields.io/badge/version-1.10.1-22c55e?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)
![Platform](https://img.shields.io/badge/platform-QQ%20%2F%20OneBot-F97316?style=flat-square)
![API](https://img.shields.io/badge/data-Official%20STALZONE%20API-0EA5E9?style=flat-square)
[![Stars](https://img.shields.io/github/stars/sakura426649/astrbot_plugin_stalzone?style=flat-square&color=F59E0B)](https://github.com/sakura426649/astrbot_plugin_stalzone)
[![Tests](https://github.com/sakura426649/astrbot_plugin_stalzone/actions/workflows/tests.yml/badge.svg)](https://github.com/sakura426649/astrbot_plugin_stalzone/actions/workflows/tests.yml)
![License](https://img.shields.io/badge/license-MIT-3B82F6?style=flat-square)

[English](README.en.md) · [GitHub](https://github.com/sakura426649/astrbot_plugin_stalzone)

<br>

<img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/help.png" alt="STALZONE 查询菜单" width="92%">

</div>

面向 AstrBot 的 STALZONE 公开数据查询插件。发送一条 `/sz`，直接得到排版好的图片卡片：拍卖在售与成交、距上次风暴时间、玩家档案、战队资料、物品详情和候选列表。

实时数据全部来自官方 API；凭证只保存在 AstrBot 配置中，不写入代码、不提交仓库、不需要玩家账号或 OAuth 登录。

## 目录

- [界面预览](#界面预览)
- [功能亮点](#功能亮点)
- [快速开始](#快速开始)
- [常用指令](#常用指令)
- [输出与卡片](#输出与卡片)
- [配置](#配置)
- [部署](#部署)
- [数据与缓存](#数据与缓存)
- [项目结构](#项目结构)
- [开发与测试](#开发与测试)
- [常见问题](#常见问题)
- [数据来源与致谢](#数据来源与致谢)
- [Roadmap](#roadmap)
- [贡献](#贡献)

## 界面预览

| 玩家档案 | 辐射风暴 |
| :---: | :---: |
| <img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/player.png" alt="玩家档案" width="100%"> | <img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/emission.png" alt="辐射风暴" width="100%"> |
| **候选卡** | **拍卖行** |
| <img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/candidates.png" alt="候选卡" width="100%"> | <img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/auction.png" alt="拍卖行" width="100%"> |
| **物品详情** | **战队候选** |
| <img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/item.png" alt="物品详情" width="100%"> | <img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/clan.png" alt="战队候选" width="100%"> |

> 图片在 QQ 缩略图和点开查看时颜色一致；所有卡片均为不透明 RGB PNG，不依赖外部图床。

**自动风暴提醒**（后台检测到爆发时主动发送，与手动查询的计时卡区分）：

<img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/emission_alert.png" alt="自动风暴提醒" width="82%">

## 功能亮点

| 模块 | 能力 |
| --- | --- |
| **拍卖行** | 当前在售、最近成交与按日期查询；神器只对非红/金品质应用 30 条限制，红/金全部显示，触发时按品质分组、其他品质每个 +0/+N 等级显示最低价且组内价格倒序；可堆叠非神器按实际数量聚合，每个数量显示最低买断价；若最低竞拍价更低则再并列一条（买断列显示「—」）；按旧版单列显示名称/起拍/买断/单价/剩余时间，全部渲染，不再分双列；非堆叠非神器不显示单价，只显示起拍/买断；超过 30 条显示前 15 条和后 15 条；武器模块按三个词条命名（如「瞬间 后退 猎人」），三个词条按各自品质着色；按买断价从高到低，并可用品质或词条模糊筛选；模块核心支持品质筛选（如「模块核心 蓝」），不筛选时最近成交每品质最多 3 条，筛选后该品质最多 10 条；`/sz 拍卖历史` 可按 200 条一页一直翻到更早的成交 |
| **辐射风暴** | 以「距离上次风暴」为主视觉的大字计时卡，同时展示当前风暴状态、上次开始/结束时间 |
| **自动风暴提醒** | 仅 OneBot 群可用；上一场结束后的 2–4 小时窗口内每分钟查询，其他时间每 3 分钟低频率探测，检测到新风暴后向白名单内每个 QQ 群发送「风暴已开始」警报图，黑名单优先；白名单为空时不发群图，但若存在风暴订阅仍会轮询并提醒订阅用户。QQ 官方机器人受被动回复限制，不参与自动提醒 |
| **AI 函数调用** | 注册 6 个 LLM 工具（拍卖、物品、玩家、风暴、调整、通行证），模型可从自然语言中自行提取参数并直接发送查询图片；需模型支持函数调用，可在配置中关闭 |
| **插件自更新** | `/sz 插件更新` / `/sz 更新` / `/sz update`：检查 GitHub Release，按本地图标缺失情况自动选择完整包或轻量包，异步下载、备份、覆盖并热重载；可选每小时自动检查 |
| **平台适配** | 查询指令与图片回复支持 OneBot（`aiocqhttp`）和 QQ 官方机器人（`qq_official` / `qq_official_webhook`）；自动风暴提醒目前只支持 OneBot |
| **玩家档案** | 战术档案卡、阵营徽记、战队/职位、PvP 估算分和完整统计；区服胶囊居中显示，不推断在线状态 |
| **战队** | 按名称、标签或 UUID 查询；优先匹配名称括号内的标签，标签长度不限、不区分大小写；支持战队列表 |
| **物品图鉴** | 2,636 件物品的中/英/俄/ID 索引，1,359 件详情；支持品质与类型筛选（如 `准镜 红`、`准镜 红 瞄具`、`准镜 瞄具`）；基础包内置 828 个常用图标，完整 2,621 图标通过扩展包安装 |
| **候选卡** | 模糊匹配最多展示前 20 个，两列卡片显示序号、品质色名称、ID/类别和物品图标；`sz 候选 <序号>` 直接重放原查询 |
| **平衡调整** | 合并 171 份 2023–2026 官方补丁公告（含 2026-10-28），按物品列出全部改动，支持武器、神器与配件 |
| **通行证计算** | 本地计算每日/每周经验、超载与剩余天数；预测等级置顶大字展示，等级变化用颜色区分，不请求游戏 API |
| **指令说明** | 必须带参数的指令缺参时不再回一段易被 QQ 换行打乱的纯文本，而是发送同风格说明图：`<必填>` / `[可选]` 语法高亮、参数对齐表、权限条和可直接发送的示例；说明图按指令缓存 |
| **查无结果** | 玩家/物品/拍卖/战队/调整未命中时发送提示图，重复查询名与区服，并给出修改建议 |

### 平台适配

- **OneBot（`aiocqhttp`）**：全部功能，包括自动风暴提醒。
- **QQ 官方机器人 WebSocket（`qq_official`）** / **Webhook（`qq_official_webhook`）**：查询指令和图片回复正常；官方群标识是 `GROUP-...` openid，不是数字群号。
- 官方机器人以被动回复为主（群聊约 5 分钟 / 5 次），主动推送受平台权限和会话缓存限制，无法保证风暴这类不定时主动消息。因此自动风暴提醒只接受 OneBot 数字群号，官方群不会进入发送队列，也不会触发轮询。

## 快速开始

1. 安装本插件：
   - **GitHub 用户**：从 [最新 Release](https://github.com/sakura426649/astrbot_plugin_stalzone/releases/latest) 下载 [`astrbot_plugin_stalzone_full.zip`](https://github.com/sakura426649/astrbot_plugin_stalzone/releases/latest/download/astrbot_plugin_stalzone_full.zip)（含全部 2,621 个图标），直接导入插件页；
   - **插件市场用户**：使用市场内的小包 `astrbot_plugin_stalzone.zip`（16 MiB 内，828 个常用图标）。
2. 在 [STALZONE API 应用管理](https://eapi.stalzone.com/registration.html) 获取 `Client-Id` 与 `Client-Secret`。
3. 进入插件配置，填写凭证，并把 `region` 设为你的群所在区服（EU 群填 `eu`）。
4. 保存并重启/重载 AstrBot，在群里发送：

```text
/sz help
/sz 拍卖 原子
/sz 风暴 ru
/sz 玩家 Sakura_Akira eu
```

> [!IMPORTANT]
> **凭证安全**：`Client-Id` / `Client-Secret` 只填写在 AstrBot WebUI 配置中。不要发到群里、不要提交到 Git、不要写进截图。仓库和日志都不会保存 secret。
>
> **API 状态**：官方 API 仍处于 Beta，字段可能调整；插件对缺失字段做了容错，但生产环境需要已获批的应用凭证。

> [!TIP]
> `/sz` 的斜杠可以省略，但 `sz` 后必须加一个空格才会触发：`sz 拍卖 原子` 等价于 `/sz 拍卖 原子`。单独发 `sz` 不会触发。
>
> **自动风暴提醒**向群发送图片前需要填写群白名单；白名单为空时不会向群发图。用户仍可用 `/sz 风暴订阅` 单独订阅下一场风暴，订阅提醒不依赖白名单。填写白名单后，插件会向名单内每个群发送同一张警报图，黑名单优先。窗口、已成功发送的群与去重状态保存在插件数据目录，重启 Bot 不会丢失。

## 常用指令

| 指令 | 作用 | 示例 |
| --- | --- | --- |
| `/sz auction <物品> [品质] [词条] [日期] [数量]` | 在售 + 成交；支持品质、日期和数量筛选；武器模块支持词条模糊筛选 | `/sz 拍卖 原子 粉 6.11 20`；`/sz 拍卖 武器模块 粉 抑制器` |
| `/sz 拍卖历史 <物品> [页码]` | 按官方成交历史倒序翻页；每页 200 条，可一直向前翻 | `/sz 拍卖历史 KS-12 2` |
| `/sz 版本` / `/sz 检查更新` / `/sz 检查版本` | 只检查 GitHub 最新版本，不执行更新，无管理员限制 | `/sz 版本` |
| `/sz 风暴提醒 白名单/黑名单 <群号>` | 修改自动风暴提醒白名单，与 WebUI 配置共享 | `/sz 风暴提醒 白名单 123456789` |
| `/sz 区服切换 <ru/eu/na/sea/nea>` | 修改默认查询区服 | `/sz 区服切换 eu` |
| `/sz 拍卖显示模式 <0/1/聚合/全部>` | 切换拍卖聚合/全部显示 | `/sz 拍卖显示模式 1` |
| `/sz 插件更新` / `/sz 更新` / `/sz update` | 通过 GitHub Release 检查并自更新；管理员默认可用 | `/sz 插件更新` |
| `/sz emission [区服]` | 距上次风暴时间与当前状态 | `/sz 风暴 ru` |
| `/sz 风暴订阅 [取消/状态]` | 订阅下一场风暴（一次性；群聊 @、私聊直发） | `/sz 风暴订阅` |
| `/sz player <角色名/UUID> [区服]` | 玩家公开资料、战队、PvP 估算分 | `/sz 玩家 Sakura_Akira eu` |
| `/sz item <中文名/英文名/ID> [品质] [类型]` | 物品属性、描述、类别和图标；支持品质/类型筛选 | `/sz 物品 准镜 红 瞄具` |
| `/sz 候选 <序号>` | 使用最近一次候选继续原查询 | `/sz 候选 1` |
| `/sz 调整 <装备>` | 官方平衡调整历史 | `/sz 调整 螺旋` |
| `/sz 通行证计算 <等级> <每日任务> [天数]` | 通行证经验与等级预测 | `/sz 通行证计算 15 15+2 20` |
| `/sz clan <名称/标签/UUID>` | 战队资料；优先匹配名称括号内的标签，标签长度不限 | `/sz 战队 RSHT` |
| `/sz clans [页码]` | 战队列表 | `/sz 战队列表 2` |
| `/sz operations [地图ID]` | 最近行动记录 | `/sz 行动 operation_bigcleanup` |
| `/sz regions` | 官方区服列表 | `/sz 区服` |
| `/sz diag` / `/sz 状态` | 运行环境、API 健康与熔断、自动提醒状态、数据资产、缓存、存储和渲染状态（不含凭证；需管理员/群主/群管理员） | `/sz 状态` |
| `/sz help` | 图片帮助菜单 | `/sz help` |

常用中文别名：`拍卖行`、`风暴`/`爆发`、`玩家`/`角色`、`物品`、`战队`、`行动`、`区服`。风暴查询还支持简写 `fb`。

`/sz 风暴提醒 白名单/黑名单`、`/sz 区服切换`、`/sz 拍卖显示模式`、`/sz diag` 和 `/sz 更新` 仅 AstrBot 管理员、QQ 群主或 QQ 群管理员可用；白名单/区服/显示模式的修改会写回 WebUI 配置。

**日期与区服**

- 日期支持 `6.11`、`6/11`（当前年份）和 `25.6.11`、`25/6/11`；按 UTC+8 自然日计算。
- 区服参数支持 `EU`、`RU`、`NA`、`SEA`、`NEA`，不区分大小写；省略时使用插件配置的默认区服。玩家、战队和风暴命令会把末尾完整的区服缩写识别为区服参数，名字中间的空格会保留。
- 所有展示时间统一为 **UTC+8（北京时间）**。
- 物品名/ID 匹配忽略大小写，`ak-308`、`AK-308` 都能解析到同一物品。

## 输出与卡片

`render_mode` 控制输出方式：

| 模式 | 行为 |
| --- | --- |
| `auto`（默认） | 有 Pillow + 中文字体时发图片；否则自动回退文本卡片 |
| `text` | 始终发送卡片式纯文本，适合低配容器 |
| `image` | 强制图片；渲染失败时仍会回退文本，不影响指令可用性 |

`auction_display_mode` 控制拍卖在售列表：默认 `aggregate` 保持聚合与 30 条限制；切到 `full` 后跳过数量聚合、品质分组和前后 15 条截断，按买断价从高到低渲染所有查到的在售条目（接口单次最多返回 200 条，图片可能很长）；最近成交仍按原有上限显示。该开关可随时在 WebUI 切换，下一次拍卖查询生效。

图片卡片包括：帮助菜单、拍卖行、玩家档案、辐射风暴、物品详情、候选列表、战队资料和通行证预测。默认使用官方壁纸暗色背景，可在配置中切换 16 张内置官方壁纸、填写自定义背景图片，并调整卡片面板不透明度；所有卡片共享同一套背景设置。卡片使用品质色与语义色，署名位于右下角；可在配置中用 `hide_creator_watermark` 隐藏该署名。除帮助菜单外，左下角会附带一行与卡片风格一致的低调「更多功能：/sz help 获取菜单」提示。

候选列表为两列卡片，每行最多两个物品；行数按候选数量增长，最多展示最接近的前 20 个。基础包内置 828 个常用图标（武器/弹药/护甲/神器/容器/设备/背包），其余图标可安装完整扩展包；未安装时仍会尝试从 CDN 懒加载并缓存，源站没有图片的条目显示「暂无图标」而不是问号。

## AI 函数调用（LLM 工具）

插件向 AstrBot 注册了 6 个函数调用工具，模型支持 Function Calling 时，可以直接在聊天里说“帮我看看原子拍卖行情”“查一下 AK-308 的调整”“通行证 15 级每天 15 点还剩 20 天”，由模型自行抽取参数并调用：

| 工具名 | 对应查询 |
| --- | --- |
| `stalzone_auction` | 拍卖行行情，支持品质、词条、日期、数量 |
| `stalzone_item` | 物品图鉴 |
| `stalzone_player` | 玩家资料，支持区服 |
| `stalzone_emission` | 辐射风暴状态，支持区服 |
| `stalzone_balance` | 官方平衡调整历史 |
| `stalzone_pass` | 通行证等级与经验预测 |

工具会直接发送与 `/sz` 相同的图片，不会把图片交给模型二次转述，因此不会出现“图片 + 重复文字”的双回复。首次使用前需要在 AstrBot 的模型服务中开启函数调用；模型不支持时会提示 `tool call is not supported`。弱模型可能漏参数或填错参数，精确查询仍建议直接用 `/sz`。

配置项 `llm_tools_enabled` 默认开启，可在 WebUI 关闭；也可以在 AstrBot 用 `/tool ls` 查看工具、用 `/tool off <工具名>` 单独关闭。工具与 `/sz` 共用查询缓存、区服和冷却配置。

## 拍卖历史翻页

官方拍卖历史接口 `/{region}/auction/{item}/history` 的 `limit` 单次最多返回 **200 条**，但 `offset` 没有总上限，响应同时给出 `total`；因此历史并不是只有 200 条，而是需要按 offset 分页。

- `/sz 拍卖历史 <物品> [页码]` 直接按 200 条一页读取，页码从 1 开始，例如 `/sz 拍卖历史 KS-12 2`。
- 卡片会显示当前页、每页条数、总条数和 `翻页：/sz 拍卖历史 <物品> <页码>`；可以一直向后翻，直到官方返回该页没有记录。
- 少数部署会忽略官方 `offset`，每次都返回第一页。插件会先检测重复签名，再用 100 条分页重试；仍重复时改用 SC CORE 的 `before` 游标补页（卡片标注「SC CORE 第三方存档」，最多回翻 4,000 条保护）。
- 普通 `/sz 拍卖` 仍只展示最近成交，避免每次查询都拉取全部历史；带日期的查询会在内部逐页扫描，最多检查 4,000 条作为安全上限。
- 该功能只读取官方成交历史，不上传或缓存完整历史到第三方。

## 插件自更新

发送 `/sz 版本`、`/sz 检查版本` 或 `/sz 检查更新` 只查询 GitHub Release 并对比版本，不下载、不备份、不更新，也没有管理员限制。发送 `/sz 插件更新`、`/sz 更新插件`、`/sz 更新` 或 `/sz update` 才会执行自更新：

- 已是最新版：直接提示当前版本。
- 有新版本：先比较本地 `item_icons` 与新版 `item_index.json`；常用物品图标有缺失才下载 `astrbot_plugin_stalzone_full.zip`（完整包），否则下载 `astrbot_plugin_stalzone.zip`（轻量包）。轻量包覆盖不会删除本地已有的额外图标。
- 下载、备份、解压、覆盖均异步执行。为避免短时间消息过多触发风控，聊天里只在开始更新时提示一次“当前版本 → 新版本（完整/轻量包）”，热重载完成后提示“已更新到 vX，热重载完成”；中间步骤不逐条播报，只有连接超时、下载失败等错误才补发提示。
- 直连 GitHub 的 API、图标清单或安装包失败/超时/无法连接时，会自动改走 `https://gh-proxy.com/`，再失败再尝试 `https://v4.gh-proxy.org/`，无需手动切换。
- 覆盖前会把旧插件目录备份到插件数据目录的 `update_backups/<版本>-<时间>/`；只保留最近 3 份，启动时和每次新备份后自动清理更旧的，避免几十次更新累积几百 MB。覆盖失败会自动用备份回滚。GitHub API/下载超时会提示网络错误，并保留旧版本。
- 手动更新固定需要 AstrBot 管理员、QQ 群主或群管理员权限。打开 `auto_update` 后，插件每小时自动检查一次，发现新版会走同一套备份/更新/热重载流程；默认关闭。自动更新本身保持静默，只写日志；手动 `/sz 更新` 会在热重载完成后向发起会话补发「已更新到 vX，热重载完成」提醒。

## 配置

在 AstrBot WebUI → 插件 → `STALZONE 数据查询` 中配置：

| 配置项 | 默认 | 说明 |
| --- | --- | --- |
| `client_id` | 空 | STALZONE API 应用 Client-Id |
| `client_secret` | 空 | STALZONE API 应用 Client-Secret；UI 会掩码 |
| `region` | `ru` | `ru` / `eu` / `na` / `sea` / `nea`；EU 群建议 `eu` |
| `api_base` | 生产 | 默认 `https://eapi.stalzone.com`；可切 `https://dapi.stalzone.com` 演示环境 |
| `render_mode` | `auto` | `auto` / `text` / `image` |
| `auction_display_mode` | `aggregate` | `aggregate`（聚合显示，同数量同品质只留最低买断，沿用 30 条限制）或 `full`（全部显示，跳过聚合与截断，渲染所有查到的在售条目） |
| `llm_tools_enabled` | `true` | 允许大模型通过函数调用主动查询并发送图片；需在 AstrBot 模型服务中启用函数调用 |
| `auto_update` | `false` | 开启后每小时检查一次 GitHub Release；有新版自动异步更新并热重载 |
| `font_path` | 空 | Linux 中文字体路径；留空自动查找 Noto CJK / 文泉驿 / 微软雅黑 |
| `card_background` | `default` | 全局卡片背景；可选内置官方壁纸 `01 仓库小队` … `16 爆炸战场`，所有卡片共享 |
| `card_background_custom` | 空 | 自定义背景图片绝对路径（或以插件目录为基准的相对路径），支持 jpg/png/webp；非空且文件存在时优先于预设 |
| `card_panel_opacity` | `0.9` | 卡片面板不透明度 `0–1`；`0` 背景最透，`1` 面板完全不透明；所有普通卡片共享 |
| `hide_creator_watermark` | `false` | 隐藏右下角 `Created By @Sakura_Akira` 水印；默认关闭（显示水印），开启后所有图片都不再绘制 |
| `lunar_enrich` | `true` | 玩家资料追加 Lunar 第三方 K/D、KDA、战斗分；关闭后不请求第三方 |
| `sc_core_fallback` | `true` | 官方成交历史翻页失效时用 SC CORE 第三方存档补全旧成交；结果会标注来源 |
| `command_cooldown` | `1.0` | 同一群两次查询的最小间隔（秒）；`0` 为关闭 |
| `emission_auto_notify` | `true` | 自动风暴提醒开关；2–4 小时窗口内每分钟查询，其他时间每 3 分钟低频率探测 |
| `emission_notify_target` | 空 | 平台前缀种子（可选）；仅用于给纯群号白名单提供平台前缀，不会单独成为收件群 |
| `emission_group_whitelist` | 空 | QQ 群白名单；每项一个群号，可点“添加更多”继续添加。留空则完全不发送自动提醒；填写后向名单内每个群发送 |
| `emission_group_blacklist` | 空 | QQ 群黑名单；每项一个群号，可点“添加更多”继续添加。优先级高于白名单 |

### 自动风暴提醒

游戏通常不会在风暴结束后的 0–2 小时内再次爆发，2–4 小时内随机爆发；但游戏更新可能调整周期。插件默认开启 `emission_auto_notify`，采用“窗口内高频 + 窗口外低频”的策略：

- 启动时先探测一次官方风暴接口，恢复上次结束时间；进入「上次结束 + 2 小时」到「上次结束 + 4 小时」的窗口后每分钟查询一次；窗口外每 3 分钟低频率探测一次，避免游戏调整风暴周期后完全漏报。
- 检测到 `currentStart` 后立即向提醒目标发送自动警报图，图中突出「风暴已开始」和开始时间；同一场风暴对同一个群只提醒一次。
- 风暴进行中按分钟确认结束状态；结束后更新保存的结束时间，再进入下一轮 2–4 小时窗口。
- `emission_auto_state.json` 保存在 AstrBot 插件数据目录，记录上次结束时间、是否进行中、已提醒的开始时间、已成功发送的群和最近会话；重启后据此恢复，不会因重启丢失窗口或重复提醒。
- 发送目标只接受 QQ 群聊：私聊会话不会被记住，也不会收到自动警报。
- 白名单为空时不会向任何群发送自动警报；但如果有用户订阅了风暴，插件仍会为订阅用户轮询并发送一次性提醒。不会回退到最近群或 `emission_notify_target`。
- 白名单非空时只认白名单：名单里有几个群就发几个（黑名单排除）。警报图只渲染一次，然后依次发送到所有目标；某个群发送失败时只重试失败的群，不会给已成功的群重复发图。
- 黑名单优先级高于白名单，命中黑名单的群永不发送。两个列表都支持在 WebUI 点“添加更多”逐个添加群号；不在白名单内的会话不会被记住。
- 白名单里的纯群号会复用 `emission_notify_target` 或最近群会话的平台前缀；如果还没用过任何群聊指令，先在群里发一次 `/sz`，或直接填完整群聊 UMO。
- 插件无法预检机器人是否已经在某个群。群号填错或机器人未入群时，该群发送会失败并记录日志（会提示检查群号/是否入群），其他群继续发送；失败群在风暴持续期间会重试，但不会回退到别的群。

自动警报使用与 `/sz 风暴` 相同的末日风卡片，但主视觉是「风暴已开始」+ 大字实际开始时间，而不是检测时间或持续时长；图中同时提示「风暴结束后 30 分钟内将伴随神器爆发」，底部标注神器生成位置。图片渲染不可用时会退回文字提醒。

### 风暴订阅（一次性）

任何群成员或私聊用户都可以发送 `/sz 风暴订阅`，订阅**下一场**风暴：

- 订阅成功时，群聊会 @ 订阅者并提示「已成功订阅下一场风暴，届时会在当前会话提醒您」；私聊直接回复，不 @。
- 风暴到来时，先向白名单群发送警报图，再提醒订阅用户：同一个群会话有多人订阅时，合并成一条消息同时 @ 所有订阅者；私聊直接发消息。提示包含实际开始时间，并说明「下一场风暴需重新订阅」。
- 订阅是一次性的：成功提醒后自动删除；如果在风暴已经开始后才订阅，不会立刻收到当前风暴的提醒，而是等下一场。
- 订阅只对 OneBot 等支持主动推送的平台开放；QQ 官方机器人无法主动 @ 或私聊推送，会拒绝订阅。
- 订阅记录与已提醒状态保存在 `emission_auto_state.json`，插件重载或 Bot 重启后继续有效；发送失败的订阅会保留，在风暴持续期间重试。白名单为空时订阅仍可工作。
- `/sz 风暴订阅 状态` 查看当前会话的订阅，`/sz 风暴订阅 取消` 退订。订阅命令不需要管理员权限，但仍受 `emission_auto_notify` 总开关控制。

### 自定义物品别名（无需重建索引）

在 AstrBot 插件数据目录（通常是 `data/plugin_data/astrbot_plugin_stalzone/`）新建 `item_aliases.json`：

```json
{
  "wg53": ["核弹", "Atom", "原子弹"],
  "vjr1n": ["AK74", "AK-74"]
}
```

键是物品 ID（用 `/sz 物品 原子` 可看到），值是别名数组。别名不区分大小写，空格和连字符会归一化；保存后在 WebUI 重载插件即可生效。别名只在本机生效，不会修改或重写 `item_index.json`。可参考 [`docs/item_aliases.example.json`](docs/item_aliases.example.json)。

平衡公告、新物品/神器和新图标的维护流程见 [`docs/maintenance.md`](docs/maintenance.md)。

**认证方式**：使用 `Client-Id` + `Client-Secret` 请求头，不需要 OAuth 用户授权。角色列表、好友列表、战队成员列表属于 UserAuth 端点，本插件不提供。

> [!WARNING]
> 如果使用演示环境 `dapi.stalzone.com`，角色资料和行动记录可能没有数据；这是演示数据不完整，不是插件解析失败。正式使用请切换到生产环境并填写已获批凭证。

## 部署

### 安装插件

推荐在插件市场或 [最新 Release](https://github.com/sakura426649/astrbot_plugin_stalzone/releases/latest) 导入 `astrbot_plugin_stalzone.zip`；发布包已控制在 16 MiB 内。开发时可克隆仓库：

```bash
# 在 AstrBot 的 data/plugins 目录下
git clone git@github.com:sakura426649/astrbot_plugin_stalzone.git
cd astrbot_plugin_stalzone
pip install -r requirements.txt
```

### 图标扩展（可选）

如果是从 GitHub 安装，直接下载 [`astrbot_plugin_stalzone_full.zip`](https://github.com/sakura426649/astrbot_plugin_stalzone/releases/latest/download/astrbot_plugin_stalzone_full.zip) 即可，已经包含全部 2,621 个图标。

插件市场的小包只内置 **828 个常用物品图标**，避免超过市场的 16 MiB 限制。使用小包又想要完整图标时，可以从独立的 [`icons-full` 分支](https://github.com/sakura426649/astrbot_plugin_stalzone/tree/icons-full/item_icons) 下载：

1. 打开 [`item_icons/` 文件夹](https://github.com/sakura426649/astrbot_plugin_stalzone/tree/icons-full/item_icons)，或直接下载 [icons-full 分支 ZIP](https://github.com/sakura426649/astrbot_plugin_stalzone/archive/refs/heads/icons-full.zip)；
2. 解压后只取 `astrbot_plugin_stalzone-icons-full/item_icons/`；
3. 把整个 `item_icons/` 放到 AstrBot 插件数据目录：

```text
data/plugin_data/astrbot_plugin_stalzone/item_icons/<物品ID>.png
```

4. 在 WebUI 重载插件。

Windows 下同样放在 `AstrBot/data/plugin_data/astrbot_plugin_stalzone/item_icons/`。未安装完整图标时，缺失图标会尝试 CDN 懒加载；若仍无图会显示「暂无图标」。

`icons-full` 分支包含完整图标和预览图；`master` 只保留 828 个常用图标，保证插件市场能从源码归档正常构建。

Linux 容器如果缺少中文字体，安装 Noto CJK：

```bash
apt-get update && apt-get install -y fonts-noto-cjk
```

然后在 AstrBot WebUI 重载插件，填写配置。首次发 `/sz help` 会生成帮助图并缓存。

### Docker

假设容器名为 `astrbot`，数据目录挂载到 `/AstrBot/data`：

```bash
docker cp astrbot_plugin_stalzone astrbot:/AstrBot/data/plugins/
docker exec -it astrbot pip install -r /AstrBot/data/plugins/astrbot_plugin_stalzone/requirements.txt
docker restart astrbot
```

如果 WebUI 已显示插件但启动报 `ModuleNotFoundError: httpx`，按上面的 `docker exec` 命令在容器内手动安装依赖。

### 国内网络

如果 pip 指向阿里云内网镜像导致找不到新版 `httpx`，改用公网镜像：

```bash
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
# 或
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

## 数据与缓存

- **实时数据**：拍卖、风暴、玩家、战队、行动记录、区服全部来自官方 API，不写入知识库。
- **静态数据**：物品索引、物品详情、常用图标和 2023–2026 平衡公告随插件打包；完整 2,621 图标保留在 GitHub 仓库 `item_icons/`，可按需手动安装，离线可查。
- **第三方数据**：Lunar 只用于玩家资料的 K/D/KDA 补充；SC CORE 只用于官方历史翻页失效时的旧成交补全；两者都会在输出中标注来源。
- **性能**：物品搜索使用别名缓存和模糊匹配预筛；搜索、图片渲染和 base64 编码在线程池执行；官方 API 复用同一个 `httpx.AsyncClient` 连接池。
- **API 缓存、重试与并发**：普通拍卖在售/成交缓存 20 秒，风暴状态缓存 10 秒；429/5xx/超时最多重试 2 次并指数退避；同一时刻最多 6 个查询进入 API 处理；同一群默认 1 秒查询冷却。带日期的历史查询不缓存，保证翻页结果准确。
- **缓存上限**：候选按群/会话保存 10 分钟，最多 200 个会话；SC CORE 物品键最多 4096 条；物品图标超过 30 天清理；临时卡片图超过 24 小时清理；帮助图只保留当前版本/区服/环境的一份。

> 实时价格和排行榜会随时变化，历史查询结果可能受官方 API 可查范围限制；以游戏内实际数据为准。

## 项目结构

```text
astrbot_plugin_stalzone/
├── main.py                  # AstrBot 入口：指令解析、API 编排、回复发送
├── api_client.py            # httpx.AsyncClient 封装、认证、超时与错误分类
├── formatters.py            # 文本与共享视图模型
├── image_renderer.py        # Pillow 卡片渲染
├── command_parser.py        # /sz 指令与别名解析
├── item_index.py            # 中/英/俄物品名 → item_id
├── item_index.json          # 2,615 件物品双语索引
├── item_details.json        # 1,338 件物品属性/描述
├── item_icons/              # 828 个随包常用图标（完整图标在仓库中按需下载）
├── balance_history.py       # 官方平衡公告索引
├── season_pass.py           # 通行证计算
├── pda_format.py            # PDA §颜色/渐变解析
├── lunar_client.py          # Lunar 第三方战报（可选）
├── sc_core_client.py        # SC CORE 第三方历史补全（可选）
├── assets/                  # 壁纸、署名字体、阵营徽记
├── docs/                    # 文档（预览图在 icons-full 分支）
├── tools/build_package.py   # 16 MiB 插件包构建（可选图标扩展包）
├── tests/                   # 单元测试与集成测试
├── _conf_schema.json
├── metadata.yaml
└── requirements.txt
```

## 开发与测试

测试不需要真实 API 凭证，使用 mock HTTP 与 AstrBot stub；Windows 下会额外跑 14 张主要卡片的视觉快照（Linux 自动跳过）：

```bash
python -m unittest discover -s tests -v
```

当前测试覆盖 API 客户端、熔断与诊断、格式化、物品索引、PDA 富文本、图片渲染与视觉快照、候选卡、区服参数、缓存与主流程，共 **253 个测试**；GitHub Actions 在 Windows / Linux、Python 3.10 / 3.12 上自动跑测试，并执行覆盖率门槛（当前 80%，门槛 75%）。

演示服冒烟测试（需要演示应用凭证）：

```powershell
$env:SZ_CID="你的演示 Client-Id"
$env:SZ_SECRET="你的演示 Client-Secret"
python tests/demo_smoke.py
```

开发约定：

- 只使用 `httpx` / `aiohttp` 等异步 HTTP 客户端，不使用 `requests`。
- 图片渲染、搜索和编码等 CPU 操作放入线程池，避免阻塞 AstrBot 事件循环。
- 凭证只从配置读取，不写死、不打印、不提交。
- 修改图片布局后同时更新 `tests/snapshots/`；README 预览图从 `icons-full` 分支读取。

默认分支为 **master**，Pull Request 也请提交到 `master`。

## 常见问题

| 现象 | 排查 |
| --- | --- |
| 提示“未配置 Client-Id / Client-Secret” | WebUI 插件配置未填，或保存后未重载插件 |
| 401 / 403 | 应用未获批、凭证错误，或用演示凭证访问生产 |
| 演示有数据、生产为空 | 检查 `region`；再确认物品/角色是否属于该区服 |
| 400 | 物品 ID 无效、物品不可交易、角色名格式不对 |
| 404 | 角色名/物品 ID 不存在；演示服部分资料本身没有数据 |
| 429 | 官方 API 频率限制；稍后重试，不要连续刷 |
| 图片没有发送 | 确认 Pillow 已安装、存在中文字体；可先设 `render_mode=text` 验证 |
| Linux 中文变方框 | 安装 `fonts-noto-cjk`，或在 `font_path` 指定字体文件 |
| `sz ...` 不触发 | `sz` 后必须有空格；也可以直接用 `/sz ...` |
| HQ PvP 分对不上 | HQ 页面显示的是其自身缓存分；插件只按实时官方统计计算并标注公式 |
| 历史成交查不到 | 官方只保留有限历史；插件会标注 SC CORE 存档起点，不能保证更早数据 |

## 数据来源与致谢

| 来源 | 用途 |
| --- | --- |
| [STALZONE 官方 API](https://eapi.stalzone.com/reference) | 拍卖、风暴、玩家、战队、行动记录、区服 |
| [STALZONE WIKI](https://stalzone.wiki/) | 物品英文名称、属性、图标 |
| 社区汉化 `zh.lang` | 物品中文名（玩家社区维护，非官方；官方不支持中文） |
| [StalzoneHQ](https://stalzonehq.com/) | 阵营图标与开放世界 PvP 公式参考 |
| [Lunar Zone](https://lunar-zone.com/) | 可选的第三方战队战报 K/D/KDA |
| [SC CORE](https://sccore.ru/) | 可选的第三方成交历史补全 |
| [AstrBot](https://github.com/AstrBotDevs/AstrBot) | 插件运行框架 |

物品中文名来自玩家社区维护的 `zh.lang` 汉化文件（**非官方**；游戏官方不支持中文，翻译可能滞后于新物品）；英文名与物品属性来自 STALZONE WIKI。平衡历史来自官方 Steam 公告。Playfair Display Italic 字体按 SIL Open Font License 1.1 随包分发，许可证见 `assets/PlayfairDisplay-OFL.txt`。

> 本项目是非官方工具，与 EXBO / STALZONE 没有隶属关系。游戏名称、图标和数据的版权归各自权利人所有；第三方数据仅作补充并在输出中标注。

## Roadmap

| 方向 | 说明 | 状态 |
| --- | --- | --- |
| 拍卖短 TTL 缓存 | 降低重复查询的 API 压力与 429 风险 | 计划中 |
| 更多卡片主题 | 为不同群提供可切换的视觉样式 | 计划中 |
| 配装分享/导入 | 把候选与物品组合成可分享的配装卡 | 讨论中 |
| 可观测性 | 更细的请求耗时、缓存命中和失败日志 | 持续 |

## 贡献

欢迎提交 Issue 和 Pull Request。

- **Bug**：附上插件版本、AstrBot 版本、区服、复现指令和脱敏日志。
- **功能建议**：说明使用场景、期望输出和与现有指令的关系。
- **PR**：目标分支为 `master`；提交前运行 `python -m unittest discover -s tests`，并同步更新 README / 预览图。
- **安全**：不要在 Issue、PR、截图或日志中暴露 `Client-Id` / `Client-Secret`。

如果这个插件对你有帮助，欢迎点一个 Star。
