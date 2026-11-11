# 官方物品库与图标同步

插件内置的 `item_index.json` 现在以 **EXBO 官方物品库** 为权威来源：

- 仓库：<https://github.com/EXBO-Studio/stalzone-database>
- 物品 JSON：`ru/items/<类别>/<物品ID>.json`
- 图标：`ru/icons/<类别>/<物品ID>.png`
- 官方数据库会随游戏版本更新，物品 ID、英文/俄文名、品质色、类别和图标都由 EXBO 维护。

官方数据库不包含中文。中文名继续由本项目维护在 `translations/zh_items.json`（来源：社区 `zh.lang` + 人工校对），同步时会自动套用；官方新增、尚未翻译的物品先回退英文名，之后在 overlay 里补译即可。

当前内置快照：2026-11-11 抓取，官方 commit `5dd1cc97f2c1`，2,367 个基础物品、2,361 个官方图标（6 个界面占位物品无图标）；`item_index.json` 的 `official_commit` 记录同一版本。

## 为什么还需要补充条目

官方库只收录当前版本的基础物品，不收录旧活动皮肤等历史条目。插件会把「旧索引里有、官方库没有」的物品保留为 `source: "supplemental"`，因此原有查询、别名和候选不会因为迁移而消失。当前快照为 2,367 个官方基础物品 + 269 个补充条目。

## 运行时检查/补全

管理员可在聊天里直接发送：

```text
/sz 检查
/sz 物品库检查
/sz 物品库更新
```

三个别名执行同一流程：

1. 按当前 `item_index.json` 检查 `item_icons/` 覆盖率；低于 90% 或缺失超过 24 个时下载项目最新 Release 的 `astrbot_plugin_stalzone_full.zip`，只提取 `item_icons/*.png` 到插件数据目录；
2. 先查官方 commit；有变化才下载 EXBO `stalzone-database` 快照，保留现有中文和 `supplemental` 条目，补全官方 ID/英文/俄文/品质色/类别/图标；commit 未变化时跳过官方压缩包，只刷新未翻译占位；
3. 未翻译条目写入插件数据目录的 `item_name_overrides.json`，值为空字符串；文件为 JSONC，每条后面带 `// en: 官方英文名 | key: 官方键值`，本身是英文的物品可留空；
4. 索引更新前备份到 `item_db_backups/`（保留最近 3 份），成功后立即重载内存索引。

这个指令不会更新 `item_details.json` 的属性/描述，也不会把官方英文当成中文；中文仍由社区/使用者维护。

## 更新流程

```bash
# 1. 下载官方快照（只取基础物品 JSON 与图标，不含 _variants 皮肤）
python tools/fetch_official_database.py --dest ../stalzone-official-db

# 2. 重新生成索引，并刷新市场包内置的常用图标
python tools/sync_official_items.py --source ../stalzone-official-db \
    --sync-icons item_icons

# 3. 生成完整图标目录（官方图标 + 旧补充图标），供完整包使用
python tools/sync_official_items.py --source ../stalzone-official-db \
    --full-icons-out ../full_icons_official/item_icons \
    --seed-icons ../full_icons_tmp/item_icons

# 4. 打包
python tools/build_package.py --output-dir .. \
    --full-icon-source ../full_icons_official/item_icons
```

`fetch_official_database.py` 会把 commit、文件数和下载时间写入 `official_snapshot.json`，便于复现。网络受限时它会自动尝试 `gh-proxy.com` / `v4.gh-proxy.org`。

## 插件停更后，用户自行更新与核对

发布包通常不包含 `tools/`（源码仓库才有），所以不要直接在已安装插件目录里找脚本。请先取得**同版本的源码仓库**（`git clone` 或 GitHub 的源码归档，不是 Release 里的插件 zip），在源码目录运行工具，再把生成物复制回已安装插件。

```bash
# 1. 抓官方快照（建议固定 --ref；不写则取 main）
python tools/fetch_official_database.py --dest ../stalzone-official-db --ref main

# 或直接 git clone 一份官方库，后面把 --source 指向它
# git clone --depth 1 https://github.com/EXBO-Studio/stalzone-database

# 2. 复制一份自己的汉化 overlay，只改 names
cp translations/zh_items.json translations/zh_items.local.json

# 3. 生成索引；输出会列出 official / supplemental / untranslated / missing icons
python tools/sync_official_items.py     --source ../stalzone-official-db     --overlay translations/zh_items.local.json     --out item_index.json

# 4. 生成完整图标目录（官方图标优先，旧补充图标从当前 item_icons 或完整图标包 seed）
python tools/sync_official_items.py     --source ../stalzone-official-db     --full-icons-out ../updated_item_icons     --seed-icons item_icons
```

部署时：

- `item_index.json` 覆盖插件根目录的 `item_index.json`；
- `updated_item_icons/*.png` 复制到 AstrBot 插件数据目录的 `item_icons/`（通常是 `data/plugin_data/astrbot_plugin_stalzone/item_icons/`）。数据目录图标优先于插件内置图标，适合不想改插件目录的用户；
- 重新加载插件，或用 `/sz 物品 <新物品ID>` 验证。

### 怎么核对官方

- **ID/英文/俄文/品质色/类别/图标路径**：以官方文件为准。官方基础物品路径是 `ru/items/<类别>/<物品ID>.json`，物品 ID 就是文件名（去掉 `.json`）；名称看 `name.lines.en` / `name.lines.ru`，图标看 `ru/icons/<类别>/<物品ID>.png`（同步工具按这个约定生成，不依赖旧 WIKI 的 CDN URL）。
- **索引是否跟上官方**：看 `item_index.json` 顶部的 `official_commit` 是否等于 `../stalzone-official-db/official_snapshot.json` 里的 commit；`official_count` 应接近官方基础物品数。
- **官方没有的旧物品**：会保留为 `source: "supplemental"`，不会因为官方库没有而被删除。`supplemental` 变多通常表示官方删了/改了旧条目，属于保留历史，不一定是错误。
- **未翻译/图标缺失**：同步输出会打印 `untranslated` 和 `official icons missing`。未翻译项通常是新物品回退成了英文，在 `zh_items.local.json` 的 `names` 里补 `{物品ID: 中文名}` 后重跑第 3 步。
- **中文无法用官方核对**：EXBO 官方库不提供中文，`name.lines` 只有英文/俄文；中文名只能对照社区 `zh.lang`、游戏内文本或人工翻译。不要把官方英文名当成中文校验结果。
- **图标完整性**：`--sync-icons item_icons` 只刷新原本已经存在的图标，不会自动把新物品加进市场小包；要完整图标请用 `--full-icons-out`。官方仓库的 `_variants` 皮肤目录默认跳过，旧皮肤继续依赖补充条目。

### 自定义汉化索引格式

`translations/zh_items.local.json`：

```json
{
  "version": 1,
  "names": {
    "物品ID": "中文名"
  }
}
```

物品 ID 必须来自官方 JSON 文件名；没有翻译的物品会先回退英文，并在同步输出里计入 `untranslated`。同步时优先使用 overlay，其次保留旧索引里的中文，最后才回退英文/俄文/ID。

## 字段约定

| 字段 | 含义 |
| --- | --- |
| `source` | `official`（官方基础物品）或 `supplemental`（官方库未收录的历史条目） |
| `official_cat` | 官方类别路径，例如 `weapon/pistol`、`supply/food` |
| `cat` | 插件用于中文筛选的类别；已有物品保持原分类，新物品按映射表归类 |
| `official_icon` | 官方图标在官方仓库中的相对路径 |
| `icon` | 运行时网络兜底 URL；本地 `item_icons/<id>.png` 始终优先 |

## 类别映射

官方 `supply/*`、`bullet`、`grenade`、`medicine` 等会映射到插件现有的 `consumables/*` 筛选组；`misc` 映射到 `other/misc`；武器模块映射到 `weapon_modules/core|module|remover`。完整映射见 `tools/sync_official_items.py` 的 `CATEGORY_MAP`。

## 图标包策略

- 市场小包只内置常用类别（武器、弹药、护甲、神器、容器、设备、背包）的图标，保持源码归档低于 16 MiB。
- 完整包与 `icons-full` 分支使用 `--full-icons-out` 生成的完整图标目录，其中官方图标优先，补充条目沿用旧图标。
- 本地图标始终优先于网络下载；缺失时才会请求 `icon` URL。
