#!/usr/bin/env python3
"""Download a pinned snapshot of the official EXBO item database.

Only ``ru/items/**/*.json`` (base items, not ``_variants`` skins) and
``ru/icons/**/*.png`` are fetched, which keeps the download far smaller than
the full repository archive.  The result can be passed to
``tools/sync_official_items.py --source <dest>``.

Example::

    python tools/fetch_official_database.py --dest ../stalzone-official-db
    python tools/sync_official_items.py --source ../stalzone-official-db
"""

from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API_ROOT = "https://api.github.com/repos/EXBO-Studio/stalzone-database"
RAW_ROOT = (
    "https://raw.githubusercontent.com/EXBO-Studio/stalzone-database"
)
USER_AGENT = "astrbot-plugin-stalzone-sync/1.0"
PROXIES = ("https://gh-proxy.com/", "https://v4.gh-proxy.org/")
ROUTE_PREFIXES = ("", *PROXIES)
_PREFERRED_PREFIX = ""


def _select_route() -> None:
    """Probe direct and both proxies once, then use the fastest for all files."""
    global _PREFERRED_PREFIX
    url = f"{API_ROOT}/commits/main"
    best_speed = -1.0
    best_prefix = ""
    print("probing GitHub routes (direct / gh-proxy / v4.gh-proxy)...")
    for prefix in ROUTE_PREFIXES:
        candidate = f"{prefix}{url}"
        started = time.monotonic()
        try:
            request = urllib.request.Request(
                candidate, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=8.0) as response:
                data = response.read(64 * 1024)
            elapsed = max(0.05, time.monotonic() - started)
            speed = len(data) / elapsed
            label = prefix or "direct"
            print(f"  {label}: {speed / 1024:.0f} KiB/s")
            if speed > best_speed:
                best_speed = speed
                best_prefix = prefix
        except Exception as exc:
            print(f"  {prefix or 'direct'}: failed ({exc})")
    _PREFERRED_PREFIX = best_prefix
    print(f"route selected: {best_prefix or 'direct'}")


def _request(url: str, timeout: float = 20.0) -> bytes:
    last_error: Exception | None = None
    candidates: list[str] = []
    if _PREFERRED_PREFIX:
        candidates.append(f"{_PREFERRED_PREFIX}{url}")
    for prefix in ROUTE_PREFIXES:
        candidate = f"{prefix}{url}"
        if candidate not in candidates:
            candidates.append(candidate)
    for candidate in candidates:
        try:
            request = urllib.request.Request(
                candidate, headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                chunks: list[bytes] = []
                while True:
                    block = response.read(64 * 1024)
                    if not block:
                        break
                    chunks.append(block)
                return b"".join(chunks)
        except (
            urllib.error.URLError,
            TimeoutError,
            OSError,
            http.client.IncompleteRead,
        ) as exc:
            last_error = exc
    raise RuntimeError(f"download failed: {url}: {last_error}")


def _request_json(url: str) -> dict:
    return json.loads(_request(url).decode("utf-8"))


def _resolve_commit(ref: str) -> str:
    payload = _request_json(f"{API_ROOT}/commits/{ref}")
    return str(payload.get("sha") or "").strip()


def _list_paths(commit: str) -> list[str]:
    payload = _request_json(f"{API_ROOT}/git/trees/{commit}?recursive=1")
    if payload.get("truncated"):
        raise RuntimeError(
            "GitHub tree listing was truncated; pass --paths-file with a "
            "path list generated from a full git checkout instead"
        )
    paths: list[str] = []
    for entry in payload.get("tree") or []:
        if not isinstance(entry, dict) or entry.get("type") != "blob":
            continue
        path = str(entry.get("path") or "")
        if "_variants" in path.split("/"):
            continue
        if path.startswith("ru/items/") and path.endswith(".json"):
            paths.append(path)
        elif path.startswith("ru/icons/") and path.endswith(".png"):
            paths.append(path)
    return paths


def _read_paths_file(path: Path) -> list[str]:
    result: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#") or "_variants" in value.split("/"):
            continue
        if value.startswith("ru/items/") and value.endswith(".json"):
            result.append(value)
        elif value.startswith("ru/icons/") and value.endswith(".png"):
            result.append(value)
    return result


def _download_one(commit: str, path: str, dest: Path, force: bool) -> int:
    target = dest / path
    if target.is_file() and not force:
        return 0
    data = _request(f"{RAW_ROOT}/{commit}/{path}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.write_bytes(data)
    os.replace(temporary, target)
    return len(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, help="snapshot output directory")
    parser.add_argument("--ref", default="main", help="branch/tag/commit (default: main)")
    parser.add_argument(
        "--paths-file",
        help="newline-separated repo paths (from `git ls-tree`); skips the "
        "large GitHub tree API request",
    )
    parser.add_argument("--workers", type=int, default=12, help="parallel downloads")
    parser.add_argument("--force", action="store_true", help="re-download existing files")
    parser.add_argument(
        "--items-only", action="store_true", help="skip ru/icons downloads"
    )
    parser.add_argument(
        "--icons-only", action="store_true", help="skip ru/items downloads"
    )
    args = parser.parse_args(argv)
    _select_route()

    dest = Path(args.dest).resolve()
    commit = _resolve_commit(args.ref)
    if not commit:
        print(f"ERROR: could not resolve ref {args.ref}")
        return 1
    paths = (
        _read_paths_file(Path(args.paths_file))
        if args.paths_file
        else _list_paths(commit)
    )
    if args.items_only:
        paths = [path for path in paths if path.startswith("ru/items/")]
    if args.icons_only:
        paths = [path for path in paths if path.startswith("ru/icons/")]
    if not paths:
        print("ERROR: no item/icon paths found")
        return 1

    totals = {"items": 0, "icons": 0}
    for path in paths:
        totals["items" if path.startswith("ru/items/") else "icons"] += 1
    print(
        f"commit {commit[:12]}: {totals['items']} item JSON, "
        f"{totals['icons']} icons -> {dest}"
    )

    started = time.time()
    downloaded = 0
    done = 0
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=max(1, args.workers)
    ) as executor:
        futures = {
            executor.submit(_download_one, commit, path, dest, args.force): path
            for path in paths
        }
        for future in concurrent.futures.as_completed(futures):
            path = futures[future]
            try:
                downloaded += future.result()
            except Exception as exc:  # noqa: BLE001 - report and continue
                print(f"WARN {path}: {exc}")
            done += 1
            if done % 250 == 0 or done == len(paths):
                elapsed = max(0.1, time.time() - started)
                print(
                    f"  {done}/{len(paths)}  "
                    f"{downloaded / 1024 / 1024:.1f} MiB  "
                    f"{downloaded / 1024 / elapsed:.0f} KiB/s"
                )

    manifest = {
        "repository": "EXBO-Studio/stalzone-database",
        "commit": commit,
        "ref": args.ref,
        "item_json": totals["items"],
        "icons": totals["icons"],
        "downloaded_bytes": downloaded,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    (dest / "official_snapshot.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    print(f"snapshot manifest: {dest / 'official_snapshot.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
