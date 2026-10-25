# Changelog

All notable changes to this project are documented here.
The project follows [Semantic Versioning](https://semver.org/).

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
