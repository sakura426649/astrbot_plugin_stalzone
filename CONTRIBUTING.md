# Contributing

Thanks for improving STALZONE 数据查询. Please keep changes focused and include tests where behavior changes.

## Development setup

```bash
git clone git@github.com:sakura426649/astrbot_plugin_stalzone.git
cd astrbot_plugin_stalzone
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

The tests use AstrBot stubs and mock HTTP; no real API credentials are required.

```bash
python -m unittest discover -s tests -v
coverage run --source=. --omit="tests/*" -m unittest discover -s tests
coverage report
```

Coverage must stay at or above the threshold in `.coveragerc` (currently 75%). Please add tests for new branches and failure paths.

## Branches and PRs

- The default branch is `master`; PRs target `master`.
- Keep each PR to one topic. Do not mix data refreshes with feature changes.
- Run the full test suite and coverage before opening a PR.
- Update `README.md`, `README.en.md`, `CHANGELOG.md` and `docs/` when behavior changes.
- Do not commit `__pycache__`, `.pyc`, local data, logs or credentials.

## Code conventions

- Async HTTP only: use `httpx.AsyncClient` (or `aiohttp`), never `requests`.
- Do not block the event loop: use `asyncio.to_thread` for image rendering, large formatting and CPU work.
- Never log or commit `Client-Id` / `Client-Secret`; configuration is the only source of credentials.
- Keep API parsing defensive (`.get()` and friendly fallbacks) because the official API is beta.
- Label third-party data (Lunar, SC CORE, StalzoneHQ formula) in user-visible output.
- Keep image output as opaque RGB PNG for consistent QQ previews.

## Data updates

Aliases, official balance changes and new items have different workflows. Follow [docs/maintenance.md](docs/maintenance.md) before changing bundled JSON data.

## Reporting bugs

Use the issue templates and include:

- plugin version and AstrBot version;
- region and the exact command;
- expected vs. actual output;
- sanitized logs (never include secrets or private chat content).
