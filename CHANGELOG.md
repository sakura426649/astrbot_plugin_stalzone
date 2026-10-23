# Changelog

All notable changes to this project are documented here.
The project follows [Semantic Versioning](https://semver.org/).

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
