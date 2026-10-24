# Changelog

All notable changes to this project are documented here.
The project follows [Semantic Versioning](https://semver.org/).

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
