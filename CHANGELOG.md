# Changelog

All notable changes to this project are documented here.
The project follows [Semantic Versioning](https://semver.org/).

## 1.10.2 - 2026-10-30

### Changed

- `/sz 拍卖历史` now follows the simpler rule: page 1 reads the latest 200 official records; page 2 and later read SC CORE's `before` cursor directly. The official offset/100-item retry detection was removed, because deployments may ignore offset and it produced repeated pages.
- Added optional quality to `/sz 拍卖历史 <物品> [页码] [品质]`; quality-filtered pages use SC CORE's `qlt` parameter and are labeled as third-party.
- Added `stalzone_auction_history` LLM tool for natural-language history paging.
- `sz 1` is now a shorthand for `sz 候选 1`.

### Tests

- Updated history page tests for page-1 official/page-2 SC CORE and quality filtering; 254 tests and 14 visual signatures pass.

## 1.10.1 - 2026-10-29

### Fixed

- `/sz 拍卖历史` no longer shows page 1 for every page when the deployment ignores the official `offset`. The plugin detects the repeated page signature, retries with 100-item offsets, then fills the requested page from SC CORE's `before` cursor; SC CORE pages are labeled as third-party and capped at 4,000 records for safety.
- An ignored offset with no SC CORE fallback now shows an explicit error card instead of silently presenting page 1 again.

### Tests

- Added an ignored-offset/SC CORE cursor regression; 253 tests and 14 visual signatures pass.

## 1.10.0 - 2026-10-29

### Added

- `/sz 拍卖历史 <物品> [页码]` browses official auction sale history newest-first, 200 records per page. The official endpoint limits `limit` to 200 per request but has an unbounded `offset` and returns `total`, so pages can keep going back until an empty page. The card shows page/page-size/total and a paging hint; candidates from ambiguous item names replay the same page.
- `/sz 拍卖历史` also reports an out-of-range page with the maximum available page instead of a generic empty result.
- A unique English weapon prefix now resolves directly (`KS-12` -> `KS-12 Komrad`), while parenthesized variants still require a candidate choice.

### Tests

- Added history paging/offset, out-of-range page and KS-12 prefix resolution coverage; 252 tests and 14 visual signatures pass.

## 1.9.0 - 2026-10-29

### Added

- `/sz 物品` accepts optional trailing quality and category filters in either order: `准镜 红`, `准镜 红 瞄具`, `准镜 瞄具`. Quality accepts 白/绿/蓝/粉/红/金 and English aliases; category accepts labels such as 武器/瞄具/弹匣/护甲/神器/消耗品, plus aliases like 瞄准镜/红点/全息/弹夹/皮肤.
- Filtering is applied during the single catalog scan before alias ranking, so adding filters does not trigger repeated full searches. Raw IDs also respect a contradictory filter; an empty filtered result shows a filter-specific notice instead of a generic "item not found" card.

### Tests

- Added parser, single-pass narrowing, out-of-range filter and missing-result coverage; 251 tests and 14 visual signatures pass.

## 1.8.1 - 2026-10-29

### Changed

- Storm subscriber notifications are grouped by session: when several users in the same group subscribed, the storm alert now sends one message mentioning all of them instead of one message per user. Private chats still receive one direct message. Failed grouped sends keep all affected subscriptions for retry.

### Tests

- Added a grouped-mention regression with two subscribers in the same group; 248 tests and 14 visual signatures pass.

## 1.8.0 - 2026-10-29

### Added

- `/sz 风暴订阅` (also `/sz 订阅风暴`) subscribes the current user in the current group or private chat to the next storm. Group success replies use a real @ mention; private chats reply directly.
- After the allow-list group image is sent, each subscriber is notified in the session where they subscribed: groups get an @ mention, private chats get a direct message. The notice includes the official start time and reminds the user that the next storm needs a new subscription.
- Subscriptions are one-shot, persist in `emission_auto_state.json` across reloads/restarts, and are only removed after a successful notice. Subscribe during an active storm waits for the next one. `/sz 风暴订阅 状态` and `/sz 风暴订阅 取消` are supported.
- Subscription polling works even when the group allow-list is empty; group image alerts remain disabled in that case. Official QQ bots are rejected because they cannot push unsolicited mentions.

### Tests

- Added subscription mention/private/persistence, one-shot notification, active-storm deferral and no-whitelist polling coverage; 247 tests and 14 visual signatures pass.

## 1.7.4 - 2026-10-29

### Fixed

- Chinese queries no longer resolve to a skin when the bare translated name is an exact skin name and a weapon base has a prefix. For example `蜜獾` now resolves to `AAC 蜜獾` (weapon) instead of the `Ratel` skin; the skin remains reachable via `Ratel` or its item ID. When several weapon bases match, the plugin shows candidates instead of picking one.

### Tests

- Added a Honey Badger/skin resolution regression; 242 tests and 14 visual signatures pass.

## 1.7.3 - 2026-10-29

### Added

- Six AstrBot LLM tools for natural-language queries: `stalzone_auction`, `stalzone_item`, `stalzone_player`, `stalzone_emission`, `stalzone_balance` and `stalzone_pass`. The model extracts parameters from chat and the plugin sends the normal image card directly, without returning the image to the model or producing a duplicate text answer.
- `llm_tools_enabled` config switch (default on) and documentation for enabling function calling in AstrBot. Tools can also be managed with AstrBot's `/tool` commands.

### Tests

- Added all-tool image routing, auction parameter composition and disabled-tool coverage; 241 tests and 14 visual signatures pass.

## 1.7.2 - 2026-10-29

### Changed

- Missing-argument help is now sent as a rendered command-guide card instead of plain text, so QQ's newline handling cannot break the layout. The card follows the shared STALZONE visual style: accent label, syntax box with colored `<required>` / `[optional]` placeholders, aligned parameter table, permission strip and a terminal-style example block.
- Usage cards are generated once per command and cached next to the help image; text output remains the fallback when rendering is disabled or Pillow/CJK fonts are unavailable. This also covers handlers that return their usage block for malformed arguments.

### Tests

- Added usage-card caching/routing and all-command rendering tests, plus a 14th Windows visual signature; 238 tests and 14 visual signatures pass.

## 1.7.1 - 2026-10-29

### Changed

- Commands that require arguments now return a detailed usage block when the argument is missing: purpose, parameter table and examples, with consistent formatting. This covers auction, item, player, balance, pass, clan, candidate, storm-alert whitelist, default region and auction display mode. `/sz emission` was added as an explicit alias in the storm usage text.

### Tests

- Added missing-argument usage coverage; 236 tests and 13 visual signatures pass.

## 1.7.0 - 2026-10-29

### Added

- `/sz 风暴提醒 白名单 <群号>` / `/sz 风暴提醒 黑名单 <群号>`: edit the same `emission_group_whitelist` used by the WebUI. The blacklist form only removes the group from the whitelist (it does not add it to the deny-list), so adding it back works; adding a whitelist group also clears an old blacklist entry.
- `/sz 区服切换 <ru/eu/na/sea/nea>` (or `/sz 默认区服`) and `/sz 拍卖显示模式 <0/1/聚合/全部>`: persist their changes to the plugin config; the auction-mode command accepts `0`/`聚合` for aggregate and `1`/`全部` for full rendering.
- These setting commands, `/sz diag` and `/sz 更新` now require AstrBot admin, QQ group owner or QQ group admin. `/sz 版本` remains unrestricted.
- `sz` replies now mark the event as handled and stop its propagation, preventing AstrBot from answering the same command again as plain text after the image/text reply.

### Tests

- Added whitelist/region/auction-mode, permission and event-stop coverage; 235 tests and 13 visual signatures pass.

## 1.6.8 - 2026-10-29

### Changed

- Manual self-update messages are reduced to avoid platform anti-spam limits: one start notice with the current/target version and package type, then one post-hot-reload completion or failure notice. Intermediate download/backup/unzip steps are no longer sent; errors still surface in the final reply.

### Tests

- Updated update-flow expectations; 231 tests and 13 visual signatures pass.

## 1.6.7 - 2026-10-29

### Added

- GitHub fallback proxy support for release API, item-index and package downloads: direct URLs are tried first, then `https://gh-proxy.com/`, then `https://v4.gh-proxy.org/`. This covers hosts that cannot reach GitHub directly or time out mid-download; proxy URLs use the `proxy/https://github.com/...` form.
- Downloaded archives are checked with `zipfile.is_zipfile` before backup/overwrite, so a proxy error page cannot replace the plugin.

### Tests

- Added proxy URL construction coverage; 231 tests and 13 visual signatures pass.

## 1.6.6 - 2026-10-29

### Added

- Weapon-module auction names now draw each of the three affixes in its own component quality color (white/green/blue/pink/red/gold), so a module with blue/white/green parts shows three colors while the row's overall quality still drives the quality filter and row color. Missing component quality falls back to the module's overall `qlt`.

### Tests

- Added per-component affix color coverage; 230 tests and 13 visual signatures pass.

## 1.6.5 - 2026-10-29

### Added

- Check-only version commands: `/sz 版本`, `/sz 检查版本`, `/sz 检查更新` (also `version`/`check`). They query the GitHub latest Release, compare it with the running version, and report either "up to date" or the newer version. They never download, back up or update anything, and have no administrator restriction.

### Tests

- Added parser aliases and a no-update version-check test; 229 tests and 13 visual signatures pass.

## 1.6.4 - 2026-10-29

### Changed

- Update backups are now capped at the latest three copies. Pruning runs at plugin startup and after each new backup, so repeated updates no longer accumulate dozens of 40 MB directories. The current backup is always retained for rollback.

### Tests

- Added backup-retention coverage; 228 tests and 13 visual signatures pass.

## 1.6.3 - 2026-10-29

### Changed

- Automatic updates are silent again: no group notices and no coupling to the emission allow-list; the hourly task only checks, updates and writes logs.
- Manual `/sz 更新` now sends a separate completion message to the initiating session after the hot reload finishes (or a failure message asking for a manual reload if the reload fails). The removed `update_notify_target` option is no longer used.
- Icon-completeness checks ignore the four catalog entries that have no icon in the official full package (`1rk6g`, `5lrg1`, `96jyz`, `3gp95`), so an installation already using the full package no longer downloads the full package on every update.

### Tests

- Updated the update-flow test to assert the post-reload notice targets the command event; 227 tests and 13 visual signatures pass.

## 1.6.2 - 2026-10-29

### Added

- Automatic updates now send a post-reload group notice: "STALZONE 插件已自动更新到 vX，热重载完成。" The new `update_notify_target` option accepts one or more group numbers/UMOs; when empty it reuses the emission allow-list groups, and if that is also empty the update only writes logs.
- If the post-update hot reload fails, the configured notification groups receive a failure notice asking for a manual reload.

### Tests

- Added explicit update-notification target coverage; 228 tests and 13 visual signatures pass.

## 1.6.1 - 2026-10-29

### Changed

- Auction rows for any item with multiple qualities (artifacts, module cores, weapon modules, and other quality-tiered items) no longer show the "最低单价/最低价" badge; quality color/grouping already conveys the cheap row. Single-quality items keep the existing badge.

### Tests

- Updated weapon-module coverage for badge suppression; 227 tests and 13 visual signatures pass.

## 1.6.0 - 2026-10-29

### Added

- Self-update commands: `/sz 插件更新`, `/sz 更新插件`, `/sz 更新`, `/sz update` (also `插件 更新`). The plugin queries the GitHub latest Release, compares `tag_name`, downloads the full or light zip, backs up the current plugin directory, applies the update asynchronously, and hot-reloads through AstrBot's plugin manager.
- The updater checks the release `item_index.json` against local `item_icons`: missing common item icons select `astrbot_plugin_stalzone_full.zip`; otherwise the light package is used. A light overlay keeps existing extra icons.
- Every step (version check, icon check, download, backup, unzip/overwrite, reload) is reported in the chat when triggered by a user. Download/backup/copy operations run off the event loop.
- New config `auto_update` (default false): an hourly background check updates automatically when a newer Release exists; the loop stays alive so the WebUI toggle needs no reload. New config `update_admin_only` (default true) restricts manual updates to administrators.
- On GitHub timeout/network/API errors the bot reports a friendly message and leaves the current version untouched. Failed overwrites restore the backup and report the backup path.

### Tests

- Added command aliases, latest-version/admin guard, package-selection, zip install/rollback and update-flow coverage; 227 tests and 13 visual signatures pass.

## 1.5.1 - 2026-10-29

### Added

- New WebUI option `auction_display_mode`: `aggregate` (default, same quantity/quality grouping and 30-row limits as before) or `full` (render every fetched active lot, skipping aggregation, quality grouping and head/tail truncation). The mode can be switched at any time and applies to the next auction query.
- Full mode fetches up to 200 lots, keeps buyout-descending order, shows the unit-price column for stackable items, and keeps the recent-trades limits unchanged.

### Performance

- Full-mode cards reuse the wallpaper/background and normalized-icon caches, keep `compress_level=1`, and cap the canvas at 12000px; a 200-row card renders in about 0.25s warm on the test machine.

### Tests

- Added full-display aggregation/truncation coverage and handler wiring; 222 tests and 13 visual signatures pass.

## 1.5.0 - 2026-10-29

### Added

- Synced the item database with the 2026-10-28 game update: 21 new official items, including Athame (`阿萨梅`), Modified Colt Walker (`改装版柯尔特沃克`), PTRD-M tranquilizer rounds, CR-380 Battery, 5.45 Extended Magazine and the autumn26 motifs/tokens/crates.
- Item names were regenerated from `zh_new.lang`; new items carry Chinese names, English/Russian names, categories, official icons and item details (descriptions, stats) from the official EXBO database.
- Added official icons for the new items to both the bundled icon set (828) and the full icon set (2,621).

### Balance history

- Added the 2026-10-28 Patch Notes to `/sz 调整`: AR/sniper/MG/SMG/pistol/shotgun/attachment/armor changes, event reward randomization, and the Detector Components sale-limit adjustment. Queries such as `/sz 调整 FN Scar-H` and `/sz 调整 SR-3M` now surface the 10-28 values.

### Tests

- Added new-item resolution/icon coverage and a 2026-10-28 balance regression; 220 tests and 13 visual signatures pass.

## 1.4.4 - 2026-10-28

### Fixed

- Automatic storm alerts no longer stop checking after the old 2–4h window. The plugin keeps a three-minute slow probe outside the window (and still polls every minute inside it), so a game update that shifts the storm cadence no longer leaves `last_check` frozen and misses every storm.
- Diag now shows the slow-probe state (`每 3 分钟预检` / `每 3 分钟探测`) so a stale check time is distinguishable from a stopped task.
- Successful probes with an empty payload now update `last_check_at` as well, instead of leaving an old timestamp.

### Tests

- Updated the outside-window test and added a regression that catches a storm after an old 4h+ window; 218 tests and 13 visual signatures pass.

## 1.4.3 - 2026-10-28

### Changed

- Help menu now documents affix filtering for weapon modules and quality filtering for module cores, in both the image cards and the plain-text fallback. The auction card shows `/sz 拍卖 <物品> [品质] [词条]` with the new examples.

## 1.4.2 - 2026-10-28

### Added

- `/sz 拍卖 模块核心 蓝` now applies the quality filter. Without a filter the recent list stays at three rows per quality; with a quality filter it shows up to ten rows of that quality, keeps the quality group header, drops the lowest-price badge, and labels the filter under the active table.

### Performance

- Wallpaper resize/brighten/blur results are cached per background and card size, and normalized item icons are cached per icon file; warm auction renders drop to roughly 0.04s from about 0.10s on the test machine.
- Module-core history fetches shrink to 30 rows (10 when a quality is selected) instead of 100; module lots fetch 200 only when a filter needs the extra coverage.

### Tests

- Added module-core quality-filter/history-limit coverage; 217 tests and 13 visual signatures pass.

## 1.4.1 - 2026-10-28

### Changed

- Module-core (`模块核心`, `9yow`) recent/history trades now show at most three rows per quality, grouped from gold to white, matching the artifact history layout. The date walk fetches extra rows so six quality groups can still be represented.
- The per-quality limit applies only to module cores; other stackable items keep the ten-row total list, and multi-quality non-stackables such as weapon modules are unchanged.

### Tests

- Added per-quality recent-limit coverage for module cores and its handler wiring; 216 tests and 13 visual signatures pass.

## 1.4.0 - 2026-10-28

### Added

- Weapon modules (`武器模块`, `1pyq`) are named by their three rolled affixes with Chinese translations, e.g. `瞬间 后退 猎人`. The order is add-on, deviation, concept; unknown ids fall back to their readable English key.
- Module auctions are sorted by buyout price from high to low, keep the existing 30-row head/tail limit, and are not treated as stackable quantity groups.
- `/sz 拍卖 武器模块` accepts a quality filter, a fuzzy affix filter, or both: `武器模块 粉`, `武器模块 抑制器`, `武器模块 粉 抑制器`. The affix filter matches Chinese, English and definition ids.
- The card shows the applied quality/affix filter under the active table; text output shows the same filter.

### Tests

- Added module parser, naming, quality/affix filtering and end-to-end handler coverage; 214 tests and 13 visual signatures pass.

## 1.3.15 - 2026-10-27

### Changed

- Recent trades for multi-quality stackables are grouped by quality as well (gold to white), with colored group headers and a "按品质分组，组内时间倒序" heading; the global ten-row cap still applies before grouping.
- The "最低单价" badge is no longer shown in these quality-grouped recent lists, since the per-quality groups already make the cheap rows obvious. Single-quality items keep the badge and the old flat list.
- Long quantity notes can use two lines instead of being clipped.

### Tests

- Extended module-core coverage for grouped recent trades and badge suppression; 210 tests and 13 visual signatures pass.

## 1.3.14 - 2026-10-27

### Changed

- Multi-quality stackable non-artifacts now group by quality from gold down to white, with a colored quality header per group; unit price is the sort order only inside each group. A cheap white listing can no longer push every other quality below it. Single-quality and non-stacked items keep the previous ordering.

### Tests

- Extended module-core coverage for quality grouping and header order; 210 tests and 13 visual signatures pass.

## 1.3.13 - 2026-10-27

### Added

- Quality-tiered non-artifacts such as module cores now color each auction row by its own `qlt` (white / green / blue / pink / red / gold), while rank-colored items keep their catalog rank color.
- Quantity aggregation now groups by amount **and** quality, so the same stack size listed at several qualities stays visible; each combination still keeps its lowest buyout, plus a cheaper auction row when one exists. Names and columns are unchanged; text output adds a short quality label when more than one quality is present.

### Tests

- Added module-core quality coverage; 210 tests and 13 visual signatures pass.

## 1.3.12 - 2026-10-27

### Fixed

- Short auction names are no longer clipped in the recent-trades table: the name column now budgets active and recent rows separately, including the recent list's 16px indent. A five-character artifact such as `伊里奇 灯泡` keeps its full name and `＋15`.
- Name-fit samples now use real catalog items instead of synthetic long labels, so the layout result matches what a group actually sees.

### Tests

- Added name-column budget coverage; 209 tests and 13 visual signatures pass.

## 1.3.11 - 2026-10-25

### Fixed

- Long auction names now truncate only the base name while keeping the trailing `＋level` visible; `伊里奇灯泡…` can no longer hide `＋15`.
- Stacked item names likewise keep `×amount` when the base name is shortened, in both the active table and recent trades.

### Tests

- Added suffix-preserving name-fit coverage; 208 tests and 13 visual signatures pass.

## 1.3.10 - 2026-10-25

### Fixed

- OneBot `unique_session` UMOs such as `aiocqhttp:GroupMessage:111222_333444` are now parsed to the group id `333444`, and proactive targets are normalized back to `platform:GroupMessage:group` instead of the sender-specific session.
- Automatic alerts again accept custom OneBot adapter IDs. Instead of requiring an `aiocqhttp`/`onebot` prefix, only clearly non-QQ platforms (Telegram, Discord, Slack, Matrix, Feishu/Lark, WeChat/WeCom, DingTalk and Mattermost) are rejected.

### Tests

- Added unique-session normalization and custom-adapter coverage; 207 tests and 13 visual signatures pass.

## 1.3.9 - 2026-10-25

### Changed

- Updated the help card's clan entry: it now shows the parenthesized-tag priority and arbitrary tag length instead of the old `4-letter tag` wording.
- Help/footer now says the background wallpaper is configurable.
- Updated the text help line for clan lookup to match the new tag behavior.

### Tests

- Regenerated the 13 visual signatures; 206 tests pass.

## 1.3.8 - 2026-10-25

### Changed

- Clan lookup now prioritizes the tag inside the clan name's parentheses, then an exact full name, then the official tag field, and finally partial matches. Tags are no longer restricted to four letters.
- Clan not-found messages now say `战队名称错误或战队资料未公开`, covering private clan profiles instead of implying a query bug.
- Clan directory reads are faster: the first page is fetched once, remaining pages (up to 600 clans) are fetched in parallel, and the directory is cached for five minutes.
- Clan descriptions now strip PDA colour codes like player bios and keep their line breaks.

### Tests

- Added arbitrary tag length, parenthesized-tag priority, directory cache, private-profile message and PDA-description coverage; 206 tests and 13 visual signatures pass.

## 1.3.7 - 2026-10-25

### Changed

- Temporary API failures now use more formal wording: `官方数据服务暂时未响应，请稍后重试；连续失败请等待约 30 秒。` Rate-limit, timeout and response-error messages were formalized too.
- API failures in image mode now render a dedicated dark `服务提示` card with a subtle `RETRY` watermark, amber accent, original query and retry guidance, instead of a generic text card.
- The bottom-left hint now reads `更多功能：/sz help 获取菜单`; its position, size, color and the creator-watermark switch are unchanged.

### Tests

- Added the error-card visual signature (13 total); 203 tests pass.

## 1.3.6 - 2026-10-25

### Changed

- Temporary API failures now use friendly, actionable messages instead of `官方 API 暂时不可用`: users are told to send the query again, and to wait about half a minute after repeated failures. Rate-limit and timeout messages were softened too.
- No extra retry sleep was added: the client already makes up to 3 attempts with non-blocking 0.5s/1.0s backoff (plus jitter); 429 honors `Retry-After` up to 2s, and the circuit opens for 30s after repeated failures.

### Tests

- Added user-facing error message coverage; 203 tests and 12 visual signatures pass.

## 1.3.5 - 2026-10-25

### Fixed

- Exact Chinese names shared by a weapon and another item (for example `逆变器` and `清道夫的AKS`) no longer silently resolve to the non-weapon entry; they now show candidates. A unique exact name such as `冰霜` still resolves directly.
- Automatic storm alerts now accept only known QQ-compatible OneBot adapters (`aiocqhttp`, `onebot`, `qq`, `napcat`, `llonebot`, `lagrange`, `cqhttp`, `go-cqhttp`) instead of every non-official platform, preventing a numeric QQ whitelist from being sent through Telegram or another adapter.

### Tests

- Audited all 352 weapon and 104 artifact names for wrong auto-resolution; added duplicate Chinese name and non-QQ platform coverage. 202 tests and 12 visual signatures pass.

## 1.3.4 - 2026-10-25

### Fixed

- A unique exact Chinese base name now wins before the mixed-category candidate check: `冰霜` resolves directly to the Frost artifact (`gyln`), while true duplicates such as `变压器` still show candidates. Weapon variants keep the existing base-weapon behavior (`x95`), and `mk47`/`mp7` still show candidates including skins.

### Tests

- Added exact-Chinese artifact vs duplicate-name coverage; 201 tests and 12 visual signatures pass.

## 1.3.3 - 2026-10-25

### Changed

- Short ambiguous weapon tokens now show candidates instead of silently choosing the base weapon. `mk47` lists MK47 Mutant, its parts and Melted MK47; `mp7` lists Melted MP7, HK MP7A2 and related matches.
- Same-category variants still auto-resolve when unambiguous (for example `x95` → IWI Tavor X95); explicit skin names still resolve directly.
- Fuzzy matching no longer uses raw item IDs, removing unrelated candidates such as Zombie Eye (`m2k7`) from an `mk47` search.

### Tests

- Updated resolver integration coverage to use a real catalog item; 200 tests and 12 visual signatures pass.

## 1.3.2 - 2026-10-25

### Fixed

- Short weapon tokens now resolve to the base weapon instead of a skin: `mk47` → `MK47 突变体`, `mp7` → `HK MP7A2`. When matches contain exactly one weapon, that weapon wins before suffix matching; explicit skin names such as `熔融 MK47` still resolve to the skin.
- Ambiguous two-character tokens such as `m4` now return candidates instead of an arbitrary suffix match.

### Tests

- Added MK47/MP7/skin/ambiguous-token resolver coverage; 200 tests and 12 visual signatures pass.

## 1.3.1 - 2026-10-25

### Fixed

- Artifact balance-history search now starts only at an exact item header. Short artifact names such as `Frost`/`冰霜` no longer match stat lines, `Frost Troopers`, `Frost Razor` or `frost consumables`; property-only labels are skipped and the weapon-only curated index is not used for artifacts.
- Expanded English balance-term translation: singular `Psy-emission`, Frost/thermal/bioinfection/bleeding/radiation resistance, instant healing, new-property phrases, nested values after arrows, and ASCII colons normalized to Chinese punctuation.

### Tests

- Added Frost false-positive and stat-translation coverage; 199 tests and 12 visual signatures pass.

## 1.3.0 - 2026-10-25

### Added

- Global card background configuration: `card_background` selects one of 16 bundled official wallpapers (or `default`), `card_background_custom` accepts a custom image path, and `card_panel_opacity` controls the shared card panel opacity from 0 to 1.
- The selected wallpaper is used by normal cards, the help card and the emission poster; the help and storm posters keep their own dark/red treatments.
- Help-image cache keys now include the selected background file and opacity.

### Tests

- Added background preset/custom-path/opacity and plugin-config application coverage; 197 tests and 12 visual signatures pass.

## 1.2.2 - 2026-10-25

### Fixed

- Automatic storm alerts no longer require the platform ID to start with `aiocqhttp`/`onebot`. Any non-official adapter (including custom OneBot IDs such as `qq`, `napcat` or `aiocqhttp_1`) is accepted again; only `qq_official`/`qq_official_webhook` are excluded.
- `_platform_prefix()` now reads the bare platform name stored in `emission_auto_state.json`, so numeric whitelists work after restart even when no target UMO has been cached yet.
- Added regression coverage for custom OneBot adapter IDs and state-only platform prefixes; 195 tests pass.

## 1.2.1 - 2026-10-25

### Fixed

- `metadata.yaml` declared only `aiocqhttp` in `support_platforms`, so the plugin page still showed OneBot v11 as the sole supported platform. Added `qq_official` and `qq_official_webhook` (and mirrored them in `platforms`).

### Tests

- 193 tests and 12 visual signatures pass.

## 1.2.0 - 2026-10-25

### Added

- QQ Official Bot support for both AstrBot adapters: WebSocket (`qq_official`) and Webhook (`qq_official_webhook`). AstrBot handles official image uploads; commands and image replies use the same dispatch path as OneBot.
- Group target parsing now recognizes official `GROUP-...` openids and combined `USER-..._GROUP-...` sessions, in addition to numeric OneBot group IDs.

### Changed

- Automatic storm alerts are explicitly OneBot-only. QQ Official groups are skipped from the allow-list, do not trigger API polling when no OneBot target remains, and show `无可用 OneBot 群` in diagnostics. This avoids relying on official bots' passive-reply window and cached `msg_id` for unsolicited alerts.
- Config hints and README now document the OneBot/official platform split.

### Tests

- Added official UMO parsing, mixed allow-list, official-only polling skip, and official command-path coverage; 193 tests and 12 visual signatures pass.

## 1.1.30 - 2026-10-24

### Changed

- Candidate-list icons now sit on a subtle neutral gradient frame and receive a gentle shadow-lift, contrast and rim-glow treatment. Dark weapons such as AK-74M and M4A1 are readable without brightening the whole card or shifting icon hues.
- Small candidate icons are normalized to the 76px inner frame, matching the top-right icon treatment.

### Tests

- Candidate visual case now uses real dark weapon icons; 188 tests and 12 visual signatures pass.

## 1.1.29 - 2026-10-24

### Fixed

- Artifact lots/history entries whose API payload omits `additional.qlt` now default to 常见（白） instead of showing `品质未标注`. Valid qlt 1–5 values are still preserved, and filtering by 白 includes these missing-quality records.

### Tests

- Added missing-quality artifact coverage; 188 tests and 12 visual signatures pass.

## 1.1.28 - 2026-10-24

### Fixed

- `api_client.py` now imports `logger` only from `astrbot.api` (matching `main.py`) and no longer uses the Python stdlib `logging` module. Tests and the manual demo smoke script provide a minimal AstrBot logger stub when run outside AstrBot.

### Tests

- 187 tests and 12 visual signatures pass.

## 1.1.27 - 2026-10-24

### Changed

- Top-right item icons now use one 124px frame, measured from Snake Eye: larger icons are downscaled, small 74×76 icons are upscaled with LANCZOS, and non-square artwork is centered without distortion.
- Applied to auction, quantity auction, empty auction and item/text cards; the empty-auction title keeps extra clearance for the larger frame.

### Tests

- Extended icon coverage to assert a 64px source fills the 124px frame; 187 tests and 12 visual signatures pass.

## 1.1.26 - 2026-10-24

### Performance

- Replaced the expensive PNG `optimize=True` encoder with `compress_level=1` for every rendered card. The image pixels are unchanged; only encoding is faster and files are slightly larger.
- Local benchmark (render only, Windows): 4-lot artifact card 0.46s → 0.08s; 100-lot artifact reduced to 17 displayed rows 0.69s → 0.10s; 100-lot artifact with all rows 1.39s → 0.25s; 100-quantity/200-row quantity card 2.27s → 0.51s. View construction stays under 1ms.

### Tests

- 187 tests and 12 visual signatures pass; visual pixels are unchanged.

## 1.1.25 - 2026-10-24

### Fixed

- The signature and the `更多功能` hint now stay inside the rounded card border; the signature clamp reserves the 12px border inset plus a small margin, and auction cards keep enough bottom space for the shared baseline.

### Tests

- Regenerated the 12 Windows visual signatures; 187 tests pass.

## 1.1.24 - 2026-10-24

### Changed

- Missing or zero start/buyout prices now render as `—` everywhere instead of `\`.
- The `更多功能：sz help 获取菜单` footer hint is larger (15px instead of 12px).
- Auction card heights now match their content, removing the extra empty strip below the signature while keeping a small bottom margin.

### Tests

- Added missing-price coverage; regenerated the 12 Windows visual signatures; 187 tests pass.

## 1.1.23 - 2026-10-24

### Changed

- Rolled the quantity-mode image layout back to the earlier single-column auction table: `名称 / 起拍 / 买断 / 单价 / 剩余时间`.
- Removed the two-column quantity table, its divider and the recent-trades centering experiments. Every aggregated quantity row is rendered in one column, however tall the card becomes.
- Quantity aggregation logic is unchanged: one lowest-buyout row per amount, plus a cheaper auction row when applicable. The item icon and recent-trades table remain.

### Tests

- Regenerated the 12 Windows visual signatures; 186 tests pass.

## 1.1.22 - 2026-10-24

### Changed

- Recent trades are left-aligned again; the section now uses its own larger 20px body / 17px headers and 32px rows, so it can grow downward independently of the two-column quantity table.
- Single-column quantity cards widen when needed to fit full recent-trade names instead of truncating them.

### Tests

- Regenerated the 12 Windows visual signatures; 187 tests pass.

## 1.1.21 - 2026-10-24

### Changed

- The two-column quantity divider now uses the same border color as the horizontal separators.
- Recent trades below a two-column quantity table are now an independent centered block with 19px names/prices and 16px headers/time, instead of stretching the small columns across the full card width.

### Tests

- Regenerated the 12 Windows visual signatures; 187 tests pass.

## 1.1.20 - 2026-10-24

### Fixed

- Restored the item thumbnail in the top-right corner of quantity-mode auction cards; the icon was previously bypassed when the renderer switched to the quantity table.
- Single-column quantity cards now size themselves to the content, so the unit price sits next to the name instead of leaving a large empty middle.
- Two-column quantity tables now draw a visible vertical divider between the columns.
- Kept the same 18px font for unit prices, totals and auction annotations; overlap is avoided with measured columns, not smaller text.

### Tests

- Added item-icon and two-column-divider render coverage; 187 tests and 12 visual signatures pass.

## 1.1.19 - 2026-10-24

### Fixed

- Quantity-table total prices now use the same 18px font as unit prices; overlap is handled by measured column widths and by dropping the remaining-time column in two-column mode instead of shrinking the total font.

### Tests

- Regenerated the 12 Windows visual signatures; 185 tests pass.

## 1.1.18 - 2026-10-24

### Fixed

- The two-column quantity table no longer overlaps unit price, total and `竞拍 · x` for long item names or 7-digit prices; column widths now follow the actual text, and two-column mode drops the remaining-time column.
- Quantity rows keep their `×N` suffix visible even when the item name is truncated.
- The `更多功能` hint now shares the signature baseline instead of dropping below the watermark.

### Tests

- Added the `auction_quantity_many` stress signature (12 visual signatures total); 185 tests pass.

## 1.1.17 - 2026-10-24

### Changed

- Non-stackable non-artifact auction rows (guns, equipment, detectors, etc.) no longer show a unit-price column; they show start and buyout prices only.
- The quantity table moves the unit-price column closer to the total, removing the wide empty middle.
- Restored the `名称 / 成交价 / 单价 / 时间` header for the recent-trades table in the quantity card.

### Tests

- Updated non-stackable table/header coverage; 185 tests and 11 visual signatures pass.

## 1.1.16 - 2026-10-24

### Changed

- The stackable quantity section is now titled `按数量汇总` with an explicit subtitle: each quantity shows the lowest buyout, adding an auction row when its price is lower.
- Auction rows show `竞拍 · 100,000` immediately after the unit price; the redundant `总价` wording and parentheses were removed.

### Tests

- Updated the quantity heading/annotation assertions; 185 tests and 11 visual signatures pass.

## 1.1.15 - 2026-10-24

### Changed

- Auction offer metadata moved from the item name to the price column: auction rows now show `单价 (竞拍·总价xx)`, while buyout rows remain unlabeled.
- Quantity table header uses `总价` for the buyout/auction total column.

### Tests

- Updated the quantity annotation assertion; 185 tests and 11 visual signatures pass.

## 1.1.14 - 2026-10-24

### Fixed

- Stackable quantity rows now use the item quality color instead of the neutral text color.
- Only auction offers get a `竞拍` label; buyout rows no longer repeat a redundant `买断` label in the image or text.
- Fixed the quantity table's bottom divider overlapping the final row by accounting for the section header offset in the card height.

### Tests

- Updated quantity-label assertions; 185 tests and 11 visual signatures pass.

## 1.1.13 - 2026-10-24

### Changed

- Per stack quantity, the card now shows the cheapest buyout offer and, when the cheapest auction/start price is lower than that buyout, an additional auction row (maximum two rows per quantity).
- If the lowest auction price is greater than or equal to the lowest buyout, the auction row is omitted.
- Both offer types are labeled `买断` / `竞拍` in the image and text, and all offers are sorted by unit price ascending.

### Tests

- Added auction-vs-buyout omission and duplicate-offer coverage; 185 tests and 11 visual signatures pass.

## 1.1.12 - 2026-10-24

### Changed

- Stackable non-artifact quantity rows are ordered by unit price ascending (cheapest first) after keeping one cheapest listing per actual amount. Amounts are only a tie-breaker.

### Tests

- Updated the quantity-order assertion; 184 tests and 11 visual signatures pass.

## 1.1.11 - 2026-10-24

### Added

- Stackable non-artifact auctions are now grouped by the actual stack amounts. Each distinct quantity shows only its cheapest-unit listing, computed with one O(n) dictionary pass over the returned lots (no 1..max loop). More than 30 distinct quantities use a compact two-column table.
- The auction card and text output show the number of distinct quantities and total listings.

### Tests

- Added quantity aggregation coverage and an `auction_quantity` visual signature; 184 tests and 11 visual signatures pass.

## 1.1.10 - 2026-10-24

### Changed

- Red and gold artifacts no longer count toward the 30-lot artifact limit and are always shown in full. The limit is evaluated only against other qualities.
- When artifact grouping is triggered, rows inside each quality section are sorted by price descending; red/gold sections show every listing, while other qualities keep one cheapest lot per +0/+N level.
- If 30 or fewer non-red/gold artifact lots exist, every artifact lot is shown without grouping, even when red/gold raises the total above 30.

### Tests

- Added red/gold exemption, full red/gold display and price-order coverage; 183 tests and 10 visual signatures pass.

## 1.1.9 - 2026-10-24

### Fixed

- Excluded the CI-only `full_icons/` staging directory from the marketplace package. The v1.1.8 release build copied the full icon source into the small zip, pushed it over 16 MiB and failed at the package-size check.
- Both release assets are now generated successfully: the marketplace zip (826 icons) and the GitHub full zip (2,600 icons).

### Tests

- No runtime changes; 181 tests and 10 visual signatures pass.

## 1.1.8 - 2026-10-24

### Added

- GitHub releases now publish two zips: the marketplace-safe `astrbot_plugin_stalzone.zip` with 826 common icons, and `astrbot_plugin_stalzone_full.zip` with all 2,600 icons for GitHub/source users.
- The full zip is built in CI from the current master code plus the `icons-full` branch's icon set, so GitHub users can install the complete version in one step without a separate icon pack.

### Tests

- Both zips are generated and size-checked; 181 tests and 10 visual signatures pass.

## 1.1.7 - 2026-10-24

### Fixed

- Added `tests/__init__.py` so the release workflow's `unittest discover -s tests` can import the test package reliably. The v1.1.6 release job stopped at test discovery; runtime code and the slimmed marketplace archive are unchanged.

### Tests

- `python -m unittest discover -s tests` now runs all 181 tests and 10 visual signatures.

## 1.1.6 - 2026-10-24

### Changed

- Slimmed the `master` tree to 826 common icons and moved the complete 2,600-icon set plus README preview images to the `icons-full` branch. This keeps GitHub source archives/plugin-market builds below 16 MiB while the runtime package still ships common icons.
- Added `.gitattributes` export-ignore rules for `.github`, `tests`, `tools` and development requirements.
- README preview images now load from the `icons-full` branch; full-icon installation instructions point to that branch.

### Tests

- No runtime behavior changes; 181 tests and 10 visual signatures pass.

## 1.1.5 - 2026-10-24

### Changed

- Removed the separate lowest-buyout and lowest-start badges/forced rows. Only the lowest unit-price row is marked and preserved for non-artifact stacks.
- Artifact quality/level sections remain as-is and intentionally carry no "lowest" badge; every displayed per-level row is already the lowest for that quality and level.

### Tests

- Removed the obsolete buyout/start special-row coverage; 181 tests and 10 visual signatures pass.

## 1.1.4 - 2026-10-24

### Fixed

- The auction display limit now applies only when more than 30 active lots exist; normal auctions show every listing.
- When the display is reduced, the global lowest-buyout and lowest-start lots are always included even if they fall outside the head/tail or quality/level selection. Non-artifact rows get explicit badges; artifact sections omit the badge because every displayed per-level row is already the lowest.

### Tests

- Added lowest-buyout/lowest-start retention coverage; 183 tests and 10 visual signatures pass.

## 1.1.3 - 2026-10-24

### Changed

- Artifact auctions are now grouped by quality first, then by +0/+N upgrade level. Each quality section shows one cheapest lot per level, with the lot count and level count in the section header.
- Artifact rows are ordered by level inside each quality section; +0 uses the base item name, +1 and above use `＋N`.
- Updated the auction preview and Windows visual baseline.

### Tests

- Adjusted the artifact grouping, quality-section and ordering assertions; 181 tests and 10 visual signatures pass.

## 1.1.2 - 2026-10-24

### Changed

- High-volume single-quality/non-artifact auction lists now show the first 15 rows, an ellipsis row with the omitted count, and the last 15 rows. The lowest unit-price row is kept in the tail.
- Artifact auctions still preserve the cheapest lot per +0/+N level.

### Tests

- Updated the high-volume auction assertions; 181 tests and 10 visual signatures pass.

## 1.1.1 - 2026-10-24

### Fixed

- High-volume artifact auctions now keep the cheapest lot for every upgrade level (+0/+N) before applying the 30-row display cap. This preserves each level instead of taking an arbitrary price slice; the card notes the total lot count and the number of levels shown. Non-artifact stacking still keeps the lowest unit-price row.
- A 100-lot artifact sample renders as roughly 700×993 instead of a multi-thousand-pixel card.

### Tests

- Added artifact per-level cap coverage; 181 tests and 10 visual signatures pass.

## 1.1.0 - 2026-10-24

### Added

- API health tracking with request totals, failures, last status/path/latency, average latency and the last error. Repeated 5xx/network failures open a 30-second circuit breaker so commands fail fast instead of hammering the official API.
- `/sz diag` now shows API health, circuit state, last response, automatic-alert status/window, whitelist recipient count and the latest broadcast result.
- Windows visual-regression snapshots for 10 main cards (profile, auction, candidate, notice, diag, pass, emission, automatic alert, item and help). Baselines can be regenerated with `tools/build_visual_baselines.py`.
- High-volume auction results are capped at the first 30 active lots with a total-count note (the cheapest/lowest-unit row is kept), preventing multi-thousand-pixel cards and extremely long text output.

### Changed

- API failure logs now include the request path, status and latency; retries are still limited to two with backoff.

### Tests

- Added circuit-breaker, diagnostics and visual-signature coverage; 181 tests and 10 visual signatures pass.

## 1.0.42 - 2026-10-24

### Changed

- Player-card labels now state both scopes explicitly: `子弹死亡（含团竞）` and `大世界 PvP 死亡（估算）`; the combat summary uses `PvP 死亡`.
- A player with no clan now shows a dash for the clan, rank and clan-level fields instead of `无 / API 未返回`. The text profile uses the same dash-only clan section.

### Tests

- Updated the HQ/profile assertions for the new labels and no-clan display; 177 tests pass.

## 1.0.41 - 2026-10-24

### Changed

- Icon delivery now matches the repository layout: the release package contains only the 826 common icons, while users download the complete `item_icons/` folder directly from GitHub and place it under `data/plugin_data/astrbot_plugin_stalzone/`.
- The release workflow no longer publishes the 35 MiB icon-pack asset; it uploads only the under-16-MiB plugin zip and `SHA256SUMS`. `tools/build_package.py` can still build an icon pack locally with `--with-icon-pack` when needed.

### Tests

- Packaging and extension-icon lookup coverage remains at 177 passing tests.

## 1.0.40 - 2026-10-24

### Changed

- Split the release package: it now includes 826 common icons and stays under the plugin marketplace's 16 MiB limit. The full 2,600-icon set is published as the separate `stalzone_icons_full.zip` release asset.
- Added support for reading user-installed icons from the plugin data directory at `data/plugin_data/astrbot_plugin_stalzone/item_icons/`, after bundled icons and before the CDN cache.
- Added `tools/build_package.py`, which builds the size-checked plugin zip, the full icon pack and SHA256SUMS. The release workflow now uploads all three assets.

### Tests

- Added an extension-icon-directory lookup regression; 177 tests pass.

## 1.0.39 - 2026-10-24

### Added

- Added the `hide_creator_watermark` switch (default off). When enabled, every generated image omits the bottom-right `Created By @Sakura_Akira` signature. The help-image cache key includes the setting, so toggling it does not reuse an image with the wrong watermark state.

### Tests

- Added watermark toggle, cache-key and signature-suppression coverage; 176 tests pass.

## 1.0.38 - 2026-10-24

### Changed

- An empty group allow-list now does nothing: no automatic sends and no emission API polling. The previous single-target fallback (configured target or latest group) has been removed; `emission_notify_target` is now only an optional platform-prefix seed for numeric allow-list entries.
- Sending now treats `send_message()` returning `False` as a delivery failure. Failures log the target with a hint to check the group number and bot membership; other groups continue and failed groups are retried while the storm is active.

### Tests

- Added empty-allow-list no-send/no-poll and false-return failure coverage; 173 tests pass.

## 1.0.37 - 2026-10-24

### Changed

- A non-empty group allow-list is now the recipient list: the alert is rendered once and sent to every allow-listed QQ group, with the deny-list taking priority. An empty allow-list keeps the previous single-target fallback.
- Delivery is tracked per group in `emission_auto_state.json`. If one group fails, the next check retries only that group and does not duplicate alerts in groups that already succeeded.

### Tests

- Added broadcast, render-once, per-group retry and fallback coverage; 171 tests pass.

## 1.0.36 - 2026-10-24

### Added

- Automatic emission alerts now accept only QQ group chats. Private sessions are never remembered or used as proactive targets.
- Added `emission_group_whitelist` and `emission_group_blacklist` list settings. Both support adding multiple group numbers in the WebUI; an empty allow-list permits every QQ group, and the deny-list always takes priority.

### Tests

- Added regression coverage for private-target rejection, allow/deny filtering and deny-list precedence; 169 tests pass.

## 1.0.35 - 2026-10-24

### Changed

- Moved the radiation trefoil watermark from the right edge to the card centre, enlarged it moderately and faded it behind the content on both emission cards.
- The automatic alert now uses the official `currentStart` as the displayed storm start, even when detection happens a minute later, and its elapsed line no longer says "检测时".
- Added the post-storm artifact notice above the "请尽快上线" prompt and a small spawn-location tip at the bottom of the automatic alert.
- Added a subtle, card-matched "更多功能：sz help 获取菜单" line in the bottom-left corner of every generated card except the help menu.

### Tests

- Added an actual-start-time regression; 166 tests pass.

## 1.0.34 - 2026-10-24

### Fixed

- Proactive alerts now use AstrBot's documented `MessageChain().file_image(...)` builder instead of passing raw components to the chain constructor. The temporary alert image is still removed after sending, and text fallback remains.

## 1.0.33 - 2026-10-24

### Added

- Automatic default-region emission alerts, enabled by default. The plugin probes once on startup, then polls the official emission endpoint at most once a minute only during the 2–4 hour window after the previous emission. Outside that window it does not poll every minute.
- A dedicated "风暴已开始" alert card: same doomsday emission style as `/sz 风暴`, but focused on the start time and immediate action instead of elapsed time.
- `emission_auto_notify` and `emission_notify_target` configuration keys. If no target is configured, the latest `/sz` session is remembered automatically.
- Persistent `emission_auto_state.json`: previous end time, active state, last alerted start and target survive plugin reloads and bot restarts; the same storm is never alerted twice.

### Fixed

- Consolidated the duplicated `terminate()` hook so shared HTTP cleanup runs and the background reminder task stops cleanly on unload.
- The automatic reminder handles API/window boundaries, a missing target and image-rendering failures without stopping the task.

### Tests

- Added alert view/renderer tests and window, deduplication, startup-probe and restart-persistence tests; 165 tests pass.

## 1.0.32 - 2026-10-23

### Fixed

- Auction queries now check the local item catalog first. A fabricated or unknown item gets the item-not-found card instead of an auction “unsupported” message.
- Only catalog items whose auction endpoints still return 400/404 produce the “暂不支持拍卖查询” auction card.

### Tests

- Added the missing-auction-item regression; 154 tests pass.

## 1.0.31 - 2026-10-23

### Changed

- Merged the separate PvP-details panel into the official statistics table, removing the duplicated section.
- Added PvP summary rows to that single table: total kills, battlefield kills/deaths, open-world kills, total/PvP deaths, anomaly deaths, total/PvP K/D, duel wins, win rate and battlefield record.
- Renamed the battlefield stats from “争锋/竞技场” to “团竞” throughout the player card.

## 1.0.30 - 2026-10-23

### Changed

- Removed the outer achievement container; each achievement is now a separate rounded 44px row with 10px spacing and 16px text, using the neutral dark panel palette.

## 1.0.29 - 2026-10-23

### Changed

- Unified the achievement list and PvP-detail panel with the dark slate palette used by the combat/stat panels; removed the brown/gold borders and gold achievement dots.

## 1.0.28 - 2026-10-23

### Changed

- Moved showcase achievements from the right column into the empty lower-left rail, with a larger framed list and gold accents.
- Achievement height is included in the card layout calculation so the source block cannot overlap; right-side statistics regain the freed space.

## 1.0.27 - 2026-10-23

### Changed

- Updated Open World PvP scoring to the current STALZONEHQ formula: subtract `kills-bf` from `kil`, subtract `deaths-bf` from the bullet/melee/explosion/bleeding deaths, and floor the result.
- Added full PvP breakdown to the player card/text: total kills/deaths, battlefield kills/deaths, anomaly deaths, total and PvP K/D, duel wins (personal/equal), win rate, and battlefield win/loss record.
- Restored the `kil` spelling in the official-stat label; only the PvP/duel fields use the new labels.

### Tests

- Added the user-provided HQ example (score 3,286) and field checks; 153 tests pass.

## 1.0.26 - 2026-10-23

### Fixed

- Reverted auction item IDs to the official catalog casing; no lowercase rewriting.
- Live API verification showed `rz6ZNaDw` (and its lowercase form) is rejected by the auction endpoints with `Invalid item id`, while a marketable item such as `gdj6` returns lots and history. The plugin now labels such items as “暂不支持拍卖查询”, not as “没有成交记录” or a generic parameter error.
- The unsupported state is carried into both the direct auction card and candidate replay; no misleading empty-history text is shown.

### Tests

- Updated mixed-case ID and unsupported-auction regressions; 152 tests pass.

## 1.0.25 - 2026-10-23

### Fixed

- Auction requests now normalize catalog item IDs to lowercase before calling the official auction endpoints. Mixed-case catalog IDs such as `rz6ZNaDw` (also searched as `rz6znadw`) are accepted by the market API instead of returning a false “参数无效”.
- Added a regression that verifies mixed-case inputs are sent to the auction API in lowercase.

### Tests

- 152 tests pass.

## 1.0.24 - 2026-10-23

### Fixed

- Auction queries for catalog items that are not marketable (for example the mixed-case `rz6ZNaDw` device, queried as `rz6znadw`) no longer surface the raw “参数无效” API error. When both official auction endpoints return 400/404, the plugin now renders an empty auction card explaining that the item may not be tradable.
- Candidate replay for such items now keeps the auction image rendering path instead of falling back to plain text.
- Unavailable auction results are not cached, so a later retry can still succeed if the API state changes.

### Tests

- Added direct and candidate-replay regressions for a non-marketable item; 151 tests pass.

## 1.0.23 - 2026-10-23

### Changed

- Removed the player online/offline inference entirely; the official API does not expose a reliable presence field, so the card no longer guesses from `lastLogin`.
- The region badge is now a single centered pill under the player name.

## 1.0.22 - 2026-10-23

### Fixed

- Removed the old 14-row statistics cap so all readable official stats are shown; “另有 3 项统计未展示” no longer appears.
- Fixed the `击杀（kil）` label to `击杀（kill）`.
- The card height and two-column split adapt to the full stats list.

## 1.0.21 - 2026-10-23

### Fixed

- Removed the redundant `UTC+8` suffix from the player-card “最后登录” value, preventing the enlarged label and timestamp from colliding.

## 1.0.20 - 2026-10-23

### Fixed

- Enlarged and brightened the gray labels for player metadata, combat metrics and official statistics, not just the white values. Adjusted the metadata column width so “最后登录” no longer overlaps its value.

## 1.0.19 - 2026-10-23

### Changed

- Enlarged player-card metadata labels/values (clan, rank, level, last login), combat metrics (kills/assists/deaths/KD) and official-stat labels/values for readability.
- Increased stat row spacing to match the larger type.

## 1.0.18 - 2026-10-23

### Changed

- Removed the redundant “估算值” caption under the player PvP score; the larger `PvP SCORE` label already identifies it.

## 1.0.17 - 2026-10-23

### Changed

- Moved the player-card faction emblem up slightly.
- Enlarged the `PvP SCORE` label from 13px to 18px, brightened it, and adjusted the panel height so the score and “估算值” do not collide.

## 1.0.16 - 2026-10-23

### Fixed

- Item and balance not-found cards now show `全服` instead of the configured region, matching their global catalogs; the N2 header uses a CJK-capable font so `全服` does not render as boxes.

## 1.0.15 - 2026-10-23

### Changed

- Replaced the not-found card with the selected N2 banner layout: a large query headline, dark 404 watermark, compact metadata, suggestion block and signature.
- Query names now shrink and wrap within a safe width; long names/notes expand the card height instead of crossing the frame or the watermark.
- Kept the card fully dark and consistent with the player/diagnostic cards.

### Tests

- Existing not-found rendering regressions pass; 151 tests total.

## 1.0.14 - 2026-10-23

### Fixed

- `玩家 <名字> NEA` and `战队 <名字> NEA` now consume the trailing region token; `NEA` was missing from the player whitelist, and the shared parser now treats region tokens case-insensitively. Names containing internal spaces are preserved; only one trailing region token is consumed.
- Help text, image help and README now list `NEA` for player/clan region selection and clarify the trailing-token rule.
- Rebuilt the not-found card with a wrapped query block and dynamic height, so long names, notes and metadata stay inside the frame. The card also links users to `/sz diag` or `/sz 状态`.

### Tests

- Added NEA player/clan region regressions; 151 tests pass.

## 1.0.13 - 2026-10-23

### Changed

- Renamed the season-pass note heading from “等级口径” to the clearer “预测说明”.

## 1.0.12 - 2026-10-23

### Changed

- The level-gain label (`+168 级` / `+158 级` / `+… 级`) now sits at the lower-right of its forecast level, in smaller, lighter type instead of a chip at the far edge of the card.
- The prediction-methodology note now sits in a centered panel in the empty right side of the hero, with larger body text; the “预测结果” heading is larger and no longer crowds the overload label.
- The current and forecast levels share one baseline; labels sit directly above their own `Lv` values, and both overload rows use the same 34/40 type scale.

## 1.0.11 - 2026-10-23

### Fixed

- Pass current/forecast levels now share one baseline; labels sit directly above their own `Lv` values instead of both being rendered above the forecast.
- Fixed the overload card's second row showing the overloaded prediction instead of the non-overloaded prediction.
- Reduced the forecast number from 82px to 40px (current 34px) and tightened the hero height, so the result stays prominent without leaving large gaps against the surrounding text. Both overload and non-overload rows use the same 34/40 sizes.

## 1.0.10 - 2026-10-23

### Changed

- Season-pass results now open with the forecast as a dedicated hero card: current level → predicted level, with the level gain in green and a colored delta chip.
- When no overload is used, no “不使用超载” wording appears anywhere. When overload is used, both overloading and non-overloading forecasts are shown.
- The explanatory note now sits directly under the forecast: the prediction comes only from daily/weekly task XP and excludes seasonal/periodic events, main quests and side quests.
- Supporting daily, weekly and season totals were moved below the result in a two-column layout.

### Tests

- Added a season-pass image regression; 150 tests pass.

## 1.0.9 - 2026-10-23

### Fixed

- Diagnostic health chips now use equal-width cells, so long font names or OS details cannot push the row past the card edge.
- Diagnostic footer text reserves space for the signature, preventing overlap on narrow labels.
- Profile achievement chips now contribute their wrapped row count to the card height, avoiding collisions with the footer for long achievement IDs.
- Diagnostics always report UTC+8 instead of the host process timezone.

## 1.0.8 - 2026-10-23

### Added

- `/sz 状态` is listed alongside `/sz diag` in text and image help; the alias resolves to the same command.
- Diagnostics now render as a full dashboard image: system/runtime, API and safety status, data assets, cache/queues, storage/render status, health checks and a conclusion panel. Text mode carries the same detailed sections as fallback.
- Diagnostics include Python implementation, OS/arch, uptime, PID, timezone, API base, retry/timeout/concurrency, Lunar/SC CORE flags, alias/balance/icon counts, cache hit rate, SC keys, cooldown scopes, help/icon/temp cache sizes, font and Pillow versions. Secrets and player data are excluded.

### Tests

- Added the `/sz 状态` parser case and a diagnostic image regression; 149 tests pass.

## 1.0.7 - 2026-10-23

### Fixed

- Section accent bars (简介, 战斗概览, 官方统计, 展示成就) now use the actual font glyph bounding box instead of a fixed vertical offset, so the gold bar aligns with each heading.

## 1.0.6 - 2026-10-23

### Changed

- Removed the gold rule from the identity rail entirely.
- Tightened the faction emblem, faction label, player name and presence chips into one upper cluster after measuring the real emblem's transparent bounds.
- Removed the duplicate PvP score block from the left rail; only the right combat summary remains.
- Replaced the right PvP block's gold fill and border with a dark neutral panel, keeping the score text as the only highlight.

## 1.0.5 - 2026-10-23

### Fixed

- Moved the faction emblem down inside the identity rail and replaced the full-height left gold stripe with a gold rule along the top edge of the rail.
- Increased the gap between the player name and the region/presence chips.
- Presence chips now switch between a green treatment for online and a gray treatment for offline; unknown remains neutral.
- Long player names automatically shrink down to 22px and only then ellipsize, preventing overflow outside the identity rail.

### Tests

- Added a long-name render regression and presence color/layout coverage; 148 tests pass.

## 1.0.4 - 2026-10-23

### Added

- Selected the tactical-dossier player card: faction emblem and identity rail on the left, bio, PvP summary, official stats and achievements on the right.
- The player name now has a dedicated region and presence row directly underneath. Presence shows 在线/离线; the official profile schema has no online flag, so the plugin uses an optional `online` field when present, explicit `status`, or infers from `lastLogin` with a 3-minute window.
- The card notes when presence was inferred from the last login, and text mode includes the same explanation.

### Changed

- Cleaned up the dossier rules and alignment: the left accent stops with the identity block, stats no longer use misaligned row rules, and the bio section has its own heading.
- The last-login value now keeps its UTC+8 label instead of being truncated.

### Tests

- Added presence-inference tests at the 3-minute boundary; 147 tests pass.

## 1.0.3 - 2026-10-23

### Fixed

- The not-found card no longer wraps the enlarged query in normal-sized brackets, which could collide with the query text.
- “未查到关于” and “的…信息” now use the same text color; only the query remains highlighted.
- All-uppercase query names are displayed in lowercase on the not-found card, while mixed-case user input is preserved. Successful queries continue to use the name returned by the API.
- Clan tag misses now show the lowercase tag instead of forcing uppercase.

### Tests

- Added casing coverage for not-found queries; 146 tests pass.

## 1.0.2 - 2026-10-23

### Added

- Bundled 2,600 item icons at 160×160, covering nearly the full 2,615-item catalog; candidates and item cards no longer depend on the CDN for common queries.
- Added a prominent player-name and region strip at the top of the profile body, with a larger name and a dedicated region badge.
- Added a query-specific “not found” card for player, item, auction, clan and balance queries. The card repeats the queried name/ID and explains how to fix the query.

### Changed

- Empty auction cards now read “未查到关于「物品」的成交记录” instead of a generic “没有找到…成交记录”.
- Missing icon slots show “暂无图标” instead of a bare question mark. Fifteen catalog IDs still return 404 from the official icon CDN and fall back to this placeholder.

### Tests

- Added coverage for missing-item/missing-player notice cards, the notice-card renderer, plugin routing and the offline icon library; 145 tests pass.

## 1.0.1 - 2026-10-23

### Fixed

- `7.62` ammunition/attachment candidates could show only question marks when their icons were not bundled and the CDN was slow or unavailable.
- Cached icon files are now validated by image signature; corrupt/HTML cache entries are discarded and refetched instead of rendering as `?`.
- Added 441 offline ammunition and attachment icons (1,031 bundled icons total), so common ammo/attachment candidate queries render without network access.

### Tests

- Added a regression test for `7.62` candidate icons and image-signature validation; 140 tests pass.

## 1.0.0 - 2026-10-23

First stable release. Public commands, configuration keys and data source labels are frozen for the 1.x series.

### Added

- Auction in-sale and sold-history cards with quality grouping, stacked items, unit prices and date pagination.
- Emission count-up card with region parameter and `fb` alias.
- Player profile cards with faction emblem, PDA formatting, PvP estimate and optional Lunar enrichment.
- Clan search/list, item encyclopedia with 2,615 bilingual entries, balance history and season-pass calculator.
- Two-column candidate cards with runtime item aliases (`item_aliases.json`).
- `/sz diag` diagnostics without credentials or player data.
- Short TTL cache for auction (20s) and emission (10s), bounded API concurrency and retry/backoff for 429/5xx/timeouts.
- GitHub Actions CI on Windows/Linux and Python 3.10/3.12, with coverage gate.
- English README, maintenance guide, issue/PR templates, security policy and MIT license.

### Changed

- Item Chinese names are explicitly sourced from the community-maintained `zh.lang` (unofficial; the game has no official Chinese localization).
- Help descriptions only describe what a command does, not how the card looks.
- Candidate lists show at most the 20 closest matches to keep responses fast.
- HTTP connections are reused and image rendering/base64 work runs outside the event loop.

### Fixed

- Auction signature could be clipped below the canvas on cards with no recent trades.
- All image cards now clamp the signature inside the canvas.
- Region override for player profiles is applied to the request, card, Lunar and HQ links.
- Cache and pending-choice storage are bounded; old help/icon/temp files are pruned.

### Notes

- Public API data is real-time and may change; Lunar and SC CORE data are third-party and are labeled in output.
- UserAuth endpoints (character list, friends, clan members) are intentionally not implemented.
- `zh.lang` is community-maintained and may lag behind new items; English fallback and manual overrides are supported.
