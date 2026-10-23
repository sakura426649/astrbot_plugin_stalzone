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

新物品不能只靠运行时“猜”，因为名称、属性、图标和中文翻译需要保持同一份快照。维护流程：

1. 更新 `data/category_all.json`（官方/WIKI 物品分类）和 `data/wiki_items.json`（属性/描述）。
2. 准备当前游戏版本的 `zh.lang`。
3. 重新生成索引：

```bash
python scripts/build_item_catalog.py --lang "路径/zh.lang"
```

4. 查看未翻译报告（`dist/导入参考/未翻译物品_待补全.tsv`）；能自动解析的会保留，无法解析的补到 `MANUAL_NAMES` 或运行时 `item_name_overrides.json`。
5. 新物品如果没有离线图标，运行时会按 `item.icon` 的 CDN 地址懒加载并缓存。要随包离线分发，就把图标下载为 `item_icons/{item_id}.png`。
6. 跑测试、检查新物品的 `/sz 物品` 和 `/sz 拍卖`，再发版。

为什么不能完全自动：

- `zh.lang` 是游戏本地化文件，不是公开 API；新版本需要从游戏文件更新。
- 物品属性/描述和图标来自 WIKI/官方快照，必须和索引同版本，否则会出现“名字有了但属性是旧的”。
- 未翻译名称需要人工判断，自动翻译容易把武器/神器译错。

可以自动化的部分：检测 WIKI 新增 ID、生成未翻译清单、下载新图标、开 PR。最终合并和发版仍建议人工确认。

## 4. 发布检查清单

- [ ] `python -m unittest discover -s tests` 全部通过
- [ ] `metadata.yaml` / `main.py` 版本一致
- [ ] README 版本徽章、CHANGELOG 已更新
- [ ] 新增/变更数据已抽查
- [ ] 插件 zip 不包含 `.git`、`__pycache__`、`.pyc`
- [ ] 干净 AstrBot 环境安装 release zip，填写凭证后可查询
- [ ] 图片卡在 QQ 缩略图和点开查看都正常
- [ ] Release 附 SHA256，PR 目标分支为 `master`
