<div align="center">

# STALZONE Data Query

**STALZONE data queries inside your QQ group.**

Auction · Emissions · Players · Clans · Items · Candidates · Season Pass

![AstrBot](https://img.shields.io/badge/AstrBot-plugin-5865F2?style=flat-square)
![Version](https://img.shields.io/badge/version-1.0.35-22c55e?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square)
![Platform](https://img.shields.io/badge/platform-QQ%20%2F%20OneBot-F97316?style=flat-square)
![API](https://img.shields.io/badge/data-Official%20STALZONE%20API-0EA5E9?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-3B82F6?style=flat-square)

[中文 README](README.md) · [Repository](https://github.com/sakura426649/astrbot_plugin_stalzone)

<img src="docs/images/help.png" alt="STALZONE help menu" width="92%">

</div>

An AstrBot plugin for public STALZONE data. Send one `/sz` command and get a formatted image card for auction listings, time since the last emission, player profiles, clans, items or candidates.

Real-time data comes from the official API. Credentials stay in AstrBot configuration and are never committed, logged or sent to the chat.

## Features

| Module | Capability |
| --- | --- |
| Auction | Active lots and sold history, quality groups, stacked items with unit price and lowest-price marker |
| Emission | Time since the last emission, current status and region selection |
| Auto emission alert | Enabled by default; polls once a minute only in the 2–4h window and pushes a distinct "emission started" alert image with the artifact window |
| Player | Tactical dossier, faction emblem, clan, PvP estimate and full stats; the region badge is centered and no online inference is made |
| Clan | Search by name, tag or UUID; exact 4-letter tag matching; clan list |
| Item | 2,615 bilingual entries, 1,338 detail records, 2,600 bundled icons, semantic stat colors |
| Candidates | Two-column cards with index, quality-colored name, ID/category and icon; top 20 only |
| Balance | 168 official patch notes from 2023–2026, extracted per item |
| Season Pass | Local XP/level prediction, no game API request |
| Not found | A query-specific card repeats the name/ID and region, with a short correction hint |

## Quick start

1. Install the plugin in AstrBot:
   - clone this repository into `data/plugins/`, or
   - download the ZIP and place the `astrbot_plugin_stalzone/` directory under `data/plugins/`.
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
| `/sz auction <item> [quality] [date] [count]` | Active lots and sold history; date queries walk history pages |
| `/sz emission [region]` | Time since the last emission and current status |
| `/sz player <name/UUID> [region]` | Public profile, clan, PvP estimate and optional Lunar data |
| `/sz item <name/ID>` | Item stats, description, category and icon |
| `/sz candidate <number>` | Replay the previous query with a candidate |
| `/sz balance <item>` | Official balance-change history |
| `/sz pass <level> <daily> [overload] <days>` | Season-pass level prediction |
| `/sz clan <name/tag/UUID>` | Clan profile; 4-letter tags are exact matches |
| `/sz clans [page]` | Clan list |
| `/sz operations [map]` | Recent operation sessions |
| `/sz regions` | Official region list |
| `/sz diag` / `/sz 状态` | Runtime, API, data, cache, storage and render status (no secrets) |
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
| `font_path` | empty | Optional CJK font path for Linux |
| `lunar_enrich` | `true` | Add Lunar third-party K/D and battle score |
| `sc_core_fallback` | `true` | Use SC CORE for older auction history when official pagination fails |
| `command_cooldown` | `1.0` | Minimum seconds between queries in the same group; `0` disables |
| `emission_auto_notify` | `true` | Automatic emission alert; polls once a minute only during the 2–4h window |
| `emission_notify_target` | empty | Fixed `unified_msg_origin`; when empty, the latest `/sz` session is remembered |

### Automatic emission alerts

The game does not start a new emission in the first 2 hours after one ends; the next one is random within 2–4 hours. The plugin uses that rule instead of polling all day:

- On startup it probes the official emission endpoint once to restore the previous end time. It then polls once a minute only between `previousEnd + 2h` and `previousEnd + 4h`; idle time outside that window is not polled.
- A new `currentStart` triggers one "emission started" image for the configured target. The same start time is never alerted twice.
- While the storm is active the plugin keeps confirming its end once a minute; the saved end time is then refreshed and the next 2–4h window begins.
- State is stored in `emission_auto_state.json` under the plugin data directory, including the previous end, active flag, last alerted start and latest target, so a restart neither loses the window nor repeats an alert.
- Target precedence: `emission_notify_target` → the latest `/sz` session. If no target exists yet, set the config value or run one query in the group first.

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

Tests use AstrBot stubs and mock HTTP, so no real credentials are needed. CI runs on Windows/Linux and Python 3.10/3.12.

The default branch is `master`; pull requests target `master`.

## License

MIT for the plugin code. Game assets, icons, wallpapers and third-party data remain the property of their respective owners. See [LICENSE](LICENSE).
