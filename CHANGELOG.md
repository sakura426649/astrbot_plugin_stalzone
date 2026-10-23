# Changelog

All notable changes to this project are documented here.
The project follows [Semantic Versioning](https://semver.org/).

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
