# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 1.x | Yes |
| 0.x | No (please upgrade) |

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose credentials, player data, or allow remote code execution.

Use GitHub's **Security → Report a vulnerability** private advisory form for this repository. If private reporting is unavailable, open a minimal public issue asking the maintainer for a private contact channel; do not include the vulnerability details, logs, tokens or personal data in that issue.

## Scope

Relevant reports include:

- exposure of `Client-Id` / `Client-Secret` in logs, generated images, or repository files;
- SSRF or arbitrary URL fetching through item icons or external data sources;
- command injection, path traversal, or unsafe file writes;
- denial of service through unbounded input, caches or request loops;
- leaking player profile data or private chat content.

The following are not security issues:

- official API outages, rate limits or Beta field changes;
- inaccurate game data from the official API, Lunar or SC CORE;
- the absence of UserAuth-only features (character list, friends, clan members);
- third-party sites changing their public pages.
