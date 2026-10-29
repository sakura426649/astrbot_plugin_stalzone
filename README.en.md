<div align="center">

# STALZONE Data Query

**STALZONE data queries inside your QQ group.**

Auction · Emissions · Players · Clans · Items · Candidates · Season Pass

![AstrBot](https://img.shields.io/badge/AstrBot-plugin-5865F2?style=flat-square)
![Version](https://img.shields.io/badge/version-1.6.3-22c55e?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)
![Platform](https://img.shields.io/badge/platform-QQ%20%2F%20OneBot-F97316?style=flat-square)
![API](https://img.shields.io/badge/data-Official%20STALZONE%20API-0EA5E9?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-3B82F6?style=flat-square)

[中文 README](README.md) · [Repository](https://github.com/sakura426649/astrbot_plugin_stalzone)

<img src="https://raw.githubusercontent.com/sakura426649/astrbot_plugin_stalzone/icons-full/docs/images/help.png" alt="STALZONE help menu" width="92%">

</div>

An AstrBot plugin for public STALZONE data. Send one `/sz` command and get a formatted image card for auction listings, time since the last emission, player profiles, clans, items or candidates.

Real-time data comes from the official API. Credentials stay in AstrBot configuration and are never committed, logged or sent to the chat.

## Features

| Module | Capability |
| --- | --- |
| Auction | Active lots and sold history, quality groups, stackable lots summarized per quantity with the lowest buyout and any cheaper auction offer; long non-stackable lists keep the first and last 15 rows |
| Emission | Time since the last emission, current status and region selection |
| Auto emission alert | OneBot only; inactive when the allow-list is empty; polls once a minute in the 2–4h window plus a slow three-minute probe outside it, and sends one alert to every allow-listed group, deny-list wins |
| Platform support | Queries and image replies work on OneBot (`aiocqhttp`) and QQ Official Bot (`qq_official` / `qq_official_webhook`); automatic storm alerts are OneBot-only |
| Player | Tactical dossier, faction emblem, clan, PvP estimate and full stats; the region badge is centered and no online inference is made |
| Clan | Search by name, parenthesized tag, tag field or UUID; tags of any length, case-insensitive; clan list |
| Item | 2,636 bilingual entries, 1,359 detail records, 828 bundled common icons plus an optional 2,621-icon extension pack |
| Candidates | Two-column cards with index, quality-colored name, ID/category and icon; top 20 only |
| Balance | 168 official patch notes from 2023–2026, extracted per item |
| Season Pass | Local XP/level prediction, no game API request |
| Not found | A query-specific card repeats the name/ID and region, with a short correction hint |

### Platform support

- **OneBot (`aiocqhttp`)**: all features, including automatic storm alerts.
- **QQ Official Bot WebSocket (`qq_official`)** / **Webhook (`qq_official_webhook`)**: queries and image replies work; official group IDs are `GROUP-...` openids, not numeric group numbers.
- Official bots are primarily passive-reply based (about 5 minutes / 5 replies per group message), and proactive delivery depends on platform permissions and cached session state. Automatic storm alerts therefore accept OneBot numeric groups only; official groups are skipped and do not trigger polling.

## Quick start

1. Install the plugin in AstrBot:
   - **GitHub users** download [`astrbot_plugin_stalzone_full.zip`](https://github.com/sakura426649/astrbot_plugin_stalzone/releases/latest/download/astrbot_plugin_stalzone_full.zip) (all 2,621 icons) and import it;
   - **Marketplace users** use the small `astrbot_plugin_stalzone.zip` (under 16 MiB, 828 common icons).
2. Get a `Client-Id` and `Client-Secret` from the [STALZONE API application page](https://eapi.stalzone.com/registration.html).
3. Configure the credentials and set `region` to your server (`eu`, `ru`, `na` or `sea`).
4. Reload/restart AstrBot and try:

```text
/sz help
/sz auction Atom
/sz emission ru
/sz player Sakura_Akira eu
```

> [!IMPORTANT]
> The official API is in beta. Keep credentials in the WebUI configuration only. Never paste a secret into an issue, screenshot or group chat.

## Commands

| Command | Purpose |
| --- | --- |
| `/sz auction <item> [quality] [affix] [date] [count]` | Active lots and sold history; weapon modules accept fuzzy affix filters and are named by their three rolled affixes |
| `/sz emission [region]` | Time since the last emission and current status |
| `/sz player <name/UUID> [region]` | Public profile, clan, PvP estimate and optional Lunar data |
| `/sz item <name/ID>` | Item stats, description, category and icon |
| `/sz candidate <number>` | Replay the previous query with a candidate |
| `/sz balance <item>` | Official balance-change history |
| `/sz pass <level> <daily> [overload] <days>` | Season-pass level prediction |
| `/sz clan <name/tag/UUID>` | Clan profile; parenthesized tags take priority and any tag length works |
| `/sz clans [page]` | Clan list |
| `/sz operations [map]` | Recent operation sessions |
| `/sz regions` | Official region list |
| `/sz diag` / `/sz 状态` | Runtime, API health/circuit breaker, auto-alert status, data, cache, storage and render status (no secrets) |
| `/sz help` | Image help menu |

The leading slash is optional, but a space is required after `sz`: `sz auction Atom` works, plain `sz` does not. All displayed times use UTC+8.

## Configuration

| Key | Default | Description |
| --- | --- | --- |
| `client_id` | empty | STALZONE API application Client-Id |
| `client_secret` | empty | STALZONE API application Client-Secret |
| `region` | `ru` | `ru` / `eu` / `na` / `sea` / `nea` |
| `api_base` | production | `https://eapi.stalzone.com`; use `https://dapi.stalzone.com` for the demo environment |
| `render_mode` | `auto` | `auto`, `text` or `image` |
| `auction_display_mode` | `aggregate` | `aggregate` (quantities grouped, 30-row limits) or `full` (render every fetched active lot, no aggregation/truncation) |
| `update_admin_only` | `true` | Only administrators may run the self-update command |
| `auto_update` | `false` | Check GitHub Releases hourly and update automatically when a newer version exists |
| `font_path` | empty | Optional CJK font path for Linux |
| `card_background` | `default` | Shared card wallpaper; choose one of the 16 bundled official wallpapers (`01`–`16`) |
| `card_background_custom` | empty | Optional custom background image path (absolute, or relative to the plugin directory); jpg/png/webp; takes priority when the file exists |
| `card_panel_opacity` | `0.9` | Shared card panel opacity from `0` (wallpaper most visible) to `1` (fully opaque) |
| `hide_creator_watermark` | `false` | Hide the bottom-right `Created By @Sakura_Akira` signature on every generated image; off by default |
| `lunar_enrich` | `true` | Add Lunar third-party K/D and battle score |
| `sc_core_fallback` | `true` | Use SC CORE for older auction history when official pagination fails |
| `command_cooldown` | `1.0` | Minimum seconds between queries in the same group; `0` disables |
| `emission_auto_notify` | `true` | Automatic emission alert; polls once a minute in the 2–4h window and every three minutes outside it |
| `emission_notify_target` | empty | Optional platform-prefix seed for numeric allow-list entries; never an extra recipient |
| `emission_group_whitelist` | empty | QQ group allow-list; add one group number per entry. Empty sends nothing; every listed group gets the alert |
| `emission_group_blacklist` | empty | QQ group deny-list; add one group number per entry. Takes priority over the allow-list |

### Automatic emission alerts

The game usually does not start a new emission in the first 2 hours after one ends; the next one is random within 2–4 hours, but game updates can shift that cadence. The plugin uses a fast window plus a slow fallback:

- On startup it probes the official emission endpoint once to restore the previous end time. It polls once a minute between `previousEnd + 2h` and `previousEnd + 4h`, and every three minutes outside that window so a changed cadence is still detected.
- A new `currentStart` triggers one "emission started" image for each recipient group. The same storm is never alerted twice to the same group.
- While the storm is active the plugin keeps confirming its end once a minute; the saved end time is then refreshed and the next 2–4h window begins.
- State is stored in `emission_auto_state.json` under the plugin data directory, including the previous end, active flag, last alerted start, successfully notified groups and latest session, so a restart neither loses the window nor repeats an alert.
- Only QQ group chats are accepted: private sessions are never remembered and never receive automatic alerts.
- An empty allow-list does nothing: no sending and no emission polling. There is no fallback to the latest group or `emission_notify_target`.
- A non-empty allow-list defines the recipients: every listed group receives the alert, excluding deny-listed groups. The image is rendered once and sent to each group; per-group delivery is tracked, so only failed groups are retried.
- The deny-list always wins. Both lists support adding more group numbers in the WebUI; groups outside the allow-list are not remembered.
- Numeric allow-list entries reuse the platform prefix from the configured seed or a remembered group. If the plugin has never seen a group command, run `/sz` once in a group or use a full group UMO entry.
- AstrBot cannot pre-check group membership. A wrong group number or a bot that is not in the group fails at send time and is logged with a hint to check the number/membership; other groups still receive the alert. Failed groups are retried while the storm is active, never redirected to another group.

The automatic card shares the doomsday emission style but leads with "风暴已开始" and the official start time (not the detection time). It also shows the 30-minute artifact window and where artifacts spawn. If image rendering is unavailable it falls back to text.

## Data notes

- Item Chinese names come from the **community-maintained `zh.lang`** file, not an official localization. The game has no official Chinese support; translations may lag behind new items. English fallback and manual overrides are supported.
- Balance history comes from official Steam announcements.
- Lunar and SC CORE are third-party sources and are labeled in output.
- PvP score is an estimate based on the public StalzoneHQ formula, not an official score.
- UserAuth-only endpoints (character list, friends, clan members) are intentionally not implemented.

See [docs/maintenance.md](docs/maintenance.md) for aliases, balance updates and new-item workflows.

## Development

```bash
python -m unittest discover -s tests -v
coverage run --source=. --omit="tests/*" -m unittest discover -s tests
coverage report
```

Tests use AstrBot stubs and mock HTTP, so no real credentials are needed. Windows also runs 13 visual-signature checks for the main cards; Linux skips them. CI runs on Windows/Linux and Python 3.10/3.12.

The default branch is `master`; pull requests target `master`.

## License

MIT for the plugin code. Game assets, icons, wallpapers and third-party data remain the property of their respective owners. See [LICENSE](LICENSE).
