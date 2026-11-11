# 数据维护指南

插件的数据分三层，更新方式不同：

| 数据 | 位置 | 更新方式 |
| --- | --- | --- |
| 玩家自定义别名 | AstrBot 插件数据目录 `item_aliases.json` | 运行时读取，重载插件即可，无需重建索引 |
| 官方平衡调整 | `balance_history.json` | 拉取官方 Steam 公告后重新生成，随版本发布 |
| 物品名称/属性/图标 | `item_index.json`、`item_details.json`、`item_icons/` | 从官方/ WIKI 快照重新生成，随版本发布 |
| 实时行情/角色/战队 | 官方 API | 查询时实时请求，不写入以上文件 |

## 1. 给物品加别名

适用场景：群友习惯用绰号、缩写或错别字称呼某件物品，但不想改插件代码或重建索引。

1. 用 `/sz 物品 <名称>` 找到物品 ID。例如原子是 `wg53`。
2. 在 AstrBot 插件数据目录创建 `item_aliases.json`（通常为 `data/plugin_data/astrbot_plugin_stalzone/item_aliases.json`）：

```json
{
  "wg53": ["核弹", "Atom", "原子弹"],
  "vjr1n": ["AK74", "AK-74"]
}
```

3. 保存后在 WebUI 重载插件。别名不区分大小写，空格和连字符会被归一化。

示例文件见 [`item_aliases.example.json`](item_aliases.example.json)。

注意事项：

- 键必须是物品 ID，不是中文名；同名物品较多时用 ID 最稳。
- 别名只在本机生效，不修改仓库里的 `item_index.json`。
- 如果别名和别的物品重名，搜索结果会同时出现两个候选，不会静默覆盖。
- 别名文件损坏或格式不对时会被忽略，不会导致插件启动失败。

## 2. 官方再次调整武器/神器

`balance_history.json` 由脚本生成，不建议手工编辑。维护者工作区（插件目录的上一级）需要：

```text
kb/04_武器与装备/枪械与装备平衡调整历史.md   # 中文长期索引
data/steam_news_all.json                      # 官方 Steam 公告归档
scripts/build_balance_history.py              # 生成器
```

更新步骤：

1. 拉取官方 Steam 公告（appid `1818450`），按 `gid` 合并进 `data/steam_news_all.json`，保留旧公告。
2. 运行：

```bash
python scripts/build_balance_history.py
```

3. 检查 `balance_history.json` 的 diff：新增日期、公告标题、涉及物品和改动是否符合原文。
4. 跑测试、更新 CHANGELOG、提升补丁版本，构建 release。

说明：

- 官方公告是主来源，中文长期索引只补公告没覆盖的日期。
- 抽取依赖物品名匹配，自动生成后需要人工抽查，尤其是同名武器、配件和神器。
- 不要把“公告里提到物品名”的说明性长句当成改动；生成器已有过滤，但新格式仍建议抽查。
- 新公告的 Steam 接口示例：

```text
https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=1818450&count=200&maxlength=0
```

后续可以加一个定时 GitHub Action：发现新公告就自动生成并开 PR，人工审核后合并。1.0 前先保证脚本和审核流程稳定，不要直接让 Action 推 master。

## 3. 官方新增神器/物品

物品 ID、英文/俄文名、品质色、类别和图标以 **EXBO 官方物品库**为准（<https://github.com/EXBO-Studio/stalzone-database>）。中文名由本项目维护在 `translations/zh_items.json`。完整说明见 [`official-item-database.md`](official-item-database.md)。

维护流程：

1. 下载官方快照（基础物品 JSON + 图标，自动跳过 `_variants` 皮肤）：

```bash
python tools/fetch_official_database.py --dest ../stalzone-official-db
```

2. 重新生成索引，并刷新市场包内置的常用图标：

```bash
python tools/sync_official_items.py --source ../stalzone-official-db \
    --sync-icons item_icons
```

3. 查看输出里的未翻译数量；新物品若回退成英文，在 `translations/zh_items.json` 的 `names` 中补 `{物品ID: 中文名}` 后重新运行第 2 步。社区 `zh.lang` 仍是主要译名来源，但需要人工校对。
4. 生成完整图标目录（官方图标优先 + 旧补充条目图标）：

```bash
python tools/sync_official_items.py --source ../stalzone-official-db \
    --full-icons-out ../full_icons_official/item_icons \
    --seed-icons ../full_icons_tmp/item_icons
```

5. 基础包只按 `tools/build_package.py` 的常用分类选图标；完整图标放在 `icons-full` 分支供用户下载，master 只保留常用图标。如果新增一整个常用分类，把前缀加进 `BASE_CATEGORY_PREFIXES`，并同步更新 master 与 `icons-full` 分支。
6. 跑测试、检查新物品的 `/sz 物品` 和 `/sz 拍卖`，再发版。

为什么不能完全自动：

- 官方数据库不包含中文；中文名依赖社区汉化 + 人工校对，新版本可能暂时回退英文。
- 官方数据库只收录当前基础物品；旧活动皮肤等历史条目会保留为 `supplemental`，不要因为官方库没有就删除。
- 物品属性/描述仍来自 WIKI/客户端快照（`item_details.json`），必须和索引同版本，否则会出现“名字有了但属性是旧的”。

可以自动化的部分：检测官方新增 ID、生成未翻译清单、下载官方图标、开 PR。最终译名确认和发版仍建议人工审核。

## 4. 发布检查清单

- [ ] `python -m unittest discover -s tests` 全部通过
- [ ] `metadata.yaml` / `main.py` 版本一致
- [ ] README 版本徽章、CHANGELOG 已更新
- [ ] 新增/变更数据已抽查
- [ ] 运行 `python tools/build_package.py --output-dir .`，插件 zip 小于 16 MiB
- [ ] 插件 zip 不包含 `.git`、`__pycache__`、`.pyc`、`tests/`、`tools/`
- [ ] 验证从 `icons-full` 分支的 `item_icons/` 复制图标到 `data/plugin_data/astrbot_plugin_stalzone/` 后能读取
- [ ] Release 上传插件 zip 和 `SHA256SUMS`
- [ ] 干净 AstrBot 环境安装 release zip，填写凭证后可查询
- [ ] 图片卡在 QQ 缩略图和点开查看都正常
- [ ] Release 附 SHA256，PR 目标分支为 `master`
