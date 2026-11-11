# 官方物品库与图标同步

插件内置的 `item_index.json` 现在以 **EXBO 官方物品库** 为权威来源：

- 仓库：<https://github.com/EXBO-Studio/stalzone-database>
- 物品 JSON：`ru/items/<类别>/<物品ID>.json`
- 图标：`ru/icons/<类别>/<物品ID>.png`
- 官方数据库会随游戏版本更新，物品 ID、英文/俄文名、品质色、类别和图标都由 EXBO 维护。

官方数据库不包含中文。源码默认中文名继续由本项目维护在 `translations/zh_items.json`（来源：社区 `zh.lang` + 人工校对），同步时会自动套用；官方新增、尚未翻译的物品先回退英文名。玩家安装后可直接编辑数据目录的 `item_name_overrides.json`，无需改源码；具体流程见下文「玩家手动修改汉化」。

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
3. 所有条目写入插件数据目录的 `item_name_overrides.json`，已有中文预填、官方新增未翻译条目为空；文件为 JSONC，每条后面带 `// en: 官方英文名 | key: 官方键值`，可以直接改任意已有中文，本身是英文的物品可留空；
4. 索引更新前备份到 `item_db_backups/`（保留最近 3 份），成功后立即重载内存索引。完整包按项目定义会缺少少量官方/历史无图标条目（当前 15 个），检查结果仍显示「当前物品库图标：完整」并注明缺口。

这个指令只修改当前安装目录/数据目录，不持有 GitHub 写 token，也不会自动 push 仓库；需要同步 GitHub 时由维护者把生成的索引/图标提交到仓库或由 Actions 处理。它不会更新 `item_details.json` 的属性/描述，也不会把官方英文当成中文；中文仍由社区/使用者维护。

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

## 玩家手动修改汉化（推荐，无需源码）

普通使用者不需要源码仓库或 `tools/`，直接使用运行时指令：

1. 管理员发送 `/sz 物品库更新`（`/sz 物品库检查` 同义），等待检查完成；
2. 打开插件数据目录：
   `data/plugin_data/astrbot_plugin_stalzone/item_name_overrides.json`
3. 文件是**完整汉化表**：所有物品都会列出，已有中文自动预填，未翻译/英文-only 条目为空；每行后面有 `// en: 官方英文名 | key: 官方本地化键`；
4. 直接修改任意 `"物品ID": "中文名"`，保存为 UTF-8；
5. 在 AstrBot WebUI 重载 STALZONE 插件，或重启 Bot；新中文立即生效；
6. 再次运行更新指令会保留用户已填写的值和显式空白。

示例：

```jsonc
{
  // 物品 ID -> 中文名；留空表示使用内置/英文名
  // en: 官方英文名；key: 官方本地化键
  "dmjdn": "AK-308",  // en: AK-308 | key: item.wpn.ak308.name
  "food1": "食物",     // en: Food | key: item.food.food1.name
  "abc12": ""          // en: New Gun | key: item.wpn.abc12.name
}
```

说明：

- 文件是 **JSONC**，`//` 和 `/* */` 注释会被插件读取器自动忽略；用严格 JSON 工具校验可能提示注释不合法，这是正常的；
- 本身是英文、无需翻译的物品（如 `AK-308`）保持空白即可；
- 删除某个覆盖条目并重载，会回退到内置索引里的中文；留空同样使用内置中文/英文；
- 该文件在数据目录，不会被插件更新覆盖；请勿修改源码包里的 `translations/zh_items.json` 作为玩家日常汉化；
- 运行时指令只改本机，**不持有 GitHub 写 token，也不会自动 push**；需要同步仓库时由维护者提交。

## 停更后的源码维护流程（维护者/无指令时）

发布包通常不包含 `tools/`（源码仓库才有），所以不要直接在已安装插件目录里找脚本。只有维护者需要重新生成源码索引/完整包时才走这条流程；普通玩家优先用上面的运行时指令。

```bash
# 1. 抓官方快照（建议固定 --ref；不写则取 main）
python tools/fetch_official_database.py --dest ../stalzone-official-db --ref main

# 或直接 git clone 一份官方库，后面把 --source 指向它
# git clone --depth 1 https://github.com/EXBO-Studio/stalzone-database

# 2. 复制一份源码汉化 overlay，只改 names
cp translations/zh_items.json translations/zh_items.local.json

# 3. 生成索引；输出会列出 official / supplemental / untranslated / missing icons
python tools/sync_official_items.py \
    --source ../stalzone-official-db \
    --existing item_index.json \
    --overlay translations/zh_items.local.json \
    --out item_index.json

# 4. 生成完整图标目录（官方图标优先，旧补充图标从当前 item_icons 或完整图标包 seed）
python tools/sync_official_items.py \
    --source ../stalzone-official-db \
    --full-icons-out ../updated_item_icons \
    --seed-icons item_icons
```

部署时：

- `item_index.json` 覆盖插件根目录的 `item_index.json`；
- `updated_item_icons/*.png` 复制到 AstrBot 插件数据目录的 `item_icons/`（通常是 `data/plugin_data/astrbot_plugin_stalzone/item_icons/`）。数据目录图标优先于插件内置图标；
- 重新加载插件，或用 `/sz 物品 <新物品ID>` 验证。

### 怎么核对官方

- **ID/英文/俄文/品质色/类别/图标路径**：以官方文件为准。官方基础物品路径是 `ru/items/<类别>/<物品ID>.json`，物品 ID 就是文件名（去掉 `.json`）；名称看 `name.lines.en` / `name.lines.ru`，图标看 `ru/icons/<类别>/<物品ID>.png`（同步工具按这个约定生成）。
- **索引是否跟上官方**：看 `item_index.json` 顶部的 `official_commit` 是否等于 `../stalzone-official-db/official_snapshot.json` 里的 commit；`official_count` 应接近官方基础物品数。
- **官方没有的旧物品**：会保留为 `source: "supplemental"`，不会因为官方库没有而被删除。`supplemental` 变多通常表示官方删了/改了旧条目，属于保留历史，不一定是错误。
- **未翻译/图标缺失**：运行时检查会导出全部条目并把未翻译项留空；源码同步输出会打印 `untranslated` 和 `official icons missing`。未翻译项在 `item_name_overrides.json`（玩家）或 `translations/zh_items.local.json`（维护者源码）中补 `{物品ID: 中文名}`。
- **中文无法用官方核对**：EXBO 官方库不提供中文，`name.lines` 只有英文/俄文；中文名只能对照社区 `zh.lang`、游戏内文本或人工翻译。不要把官方英文名当成中文校验结果。
- **图标完整性**：`--sync-icons item_icons` 只刷新原本已经存在的图标，不会自动把新物品加进市场小包；要完整图标请用 `--full-icons-out`。官方仓库的 `_variants` 皮肤目录默认跳过，旧皮肤继续依赖补充条目。

### 两种汉化文件格式

**玩家运行时**：`data/plugin_data/astrbot_plugin_stalzone/item_name_overrides.json`，扁平 `{物品ID: 中文名}`，允许 JSONC 注释；全量条目，已有中文预填，空字符串表示使用内置/英文。

**维护者源码 overlay**：`translations/zh_items.json` 或 `translations/zh_items.local.json`，供 `tools/sync_official_items.py --overlay` 使用：

```json
{
  "version": 1,
  "names": {
    "物品ID": "中文名"
  }
}
```

物品 ID 必须来自官方 JSON 文件名；没有翻译的物品会先回退英文，并在同步输出里计入 `untranslated`。

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
