"""Searchable weapon/artifact balance-history index."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_PROPERTY_LABELS = {
    "additional properties",
    "additional properties:",
    "bonus properties",
    "bonus properties:",
    "main properties",
    "main properties:",
}
_CHANGE_START_RE = re.compile(
    r"^(?:added|removed|increased|reduced|changed|now)\b", re.IGNORECASE
)


class BalanceHistory:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else Path(__file__).with_name("balance_history.json")
        self.weapon_rows: list[dict[str, Any]] = []
        self.patches: list[dict[str, Any]] = []
        self.historical_patches: list[dict[str, Any]] = []
        self.generated_at = ""
        self._load()

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        rows = payload.get("weapon_rows")
        patches = payload.get("patches")
        historical = payload.get("historical_patches")
        if isinstance(rows, list):
            self.weapon_rows = [row for row in rows if isinstance(row, dict)]
        if isinstance(patches, list):
            self.patches = [patch for patch in patches if isinstance(patch, dict)]
        if isinstance(historical, list):
            self.historical_patches = [
                patch for patch in historical if isinstance(patch, dict)
            ]
        self.generated_at = str(payload.get("generated_at") or "")

    @property
    def ready(self) -> bool:
        return bool(self.weapon_rows or self.patches or self.historical_patches)

    @staticmethod
    def _clean(value: str) -> str:
        return re.sub(r"[`*]", "", value).strip()

    @staticmethod
    def _contains(name: str, text: str) -> bool:
        name = str(name or "").strip()
        if not name:
            return False
        if re.search(r"[\u4e00-\u9fff]", name):
            return name in text
        pattern = r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])"
        return re.search(pattern, text, re.IGNORECASE) is not None

    @classmethod
    def _curated_changes(
        cls, patch: dict[str, Any], names: list[str]
    ) -> list[str]:
        found: list[str] = []
        for bullet in patch.get("bullets") or []:
            text = str(bullet)
            segments = re.split(r"[；。]", text)
            hits = [
                cls._clean(segment)
                for segment in segments
                if any(cls._contains(name, segment) for name in names)
            ]
            if not hits and any(cls._contains(name, text) for name in names):
                hits = [cls._clean(text)]
            for segment in hits:
                if segment and segment not in found:
                    found.append(segment)
        return found

    @staticmethod
    def _is_property_label(line: str) -> bool:
        return line.strip().lower() in _PROPERTY_LABELS

    @classmethod
    def _is_name_line(cls, line: str, names: list[str]) -> bool:
        text = re.sub(r"^[\s|•]+|[\s|]+$", "", line)
        normalized = re.sub(
            r"[^0-9a-zа-яё\u4e00-\u9fff]+", "", text.casefold()
        )
        if not normalized:
            return False
        for name in names:
            value = re.sub(
                r"[^0-9a-zа-яё\u4e00-\u9fff]+", "", str(name).casefold()
            )
            if value and normalized == value:
                return True
        return False

    @staticmethod
    def _looks_like_header(line: str) -> bool:
        text = line.strip("• ").strip()
        if not text or len(text) > 70:
            return False
        if re.search(r"[%:：→]|->", text):
            return False
        if _CHANGE_START_RE.search(text):
            return False
        if not re.search(r"[A-Za-zА-Яа-яЁё\u4e00-\u9fff]", text):
            return False
        if text.lower().startswith("similar to "):
            return True
        return bool(re.fullmatch(r"[A-Za-zА-Яа-яЁё0-9 .'’()\-+/]+", text))

    @staticmethod
    def _looks_like_change(line: str) -> bool:
        text = line.lstrip("• ").strip()
        if not text or len(text) > 160:
            return False
        if ":" in text or "：" in text:
            return bool(re.search(r"[0-9%→]|->", text))
        if re.search(r"→|->", text):
            return True
        if _CHANGE_START_RE.search(text):
            return bool(re.search(r"[0-9%]", text))
        return False

    @classmethod
    def _extract_snippets(cls, text: str, names: list[str]) -> list[str]:
        lines = [line.strip() for line in str(text or "").splitlines()]
        snippets: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            if (
                not line
                or line.startswith("Similar to ")
                or not any(cls._contains(name, line) for name in names)
            ):
                index += 1
                continue
            is_change = cls._looks_like_change(line)
            is_name_line = cls._is_name_line(line, names)
            # Prose that merely mentions the item (e.g. a patch comment) must
            # not start a block, or the next weapon's table would be attached.
            if not is_change and not is_name_line:
                index += 1
                continue
            changes: list[str] = []
            if is_change:
                changes.append(line.lstrip("• ").strip())
            cursor = index + 1
            while cursor < len(lines):
                candidate = lines[cursor]
                cursor += 1
                if not candidate or candidate in {"|", "•"}:
                    continue
                if cls._is_property_label(candidate):
                    changes.append(candidate.strip(":：").strip())
                    continue
                if cls._looks_like_header(candidate):
                    break
                if len(candidate) > 160 and not cls._looks_like_change(candidate):
                    break
                if cls._looks_like_change(candidate):
                    if candidate not in changes:
                        changes.append(candidate.lstrip("• ").strip())
                    continue
                if changes:
                    break
            if changes:
                snippet = "；".join(changes)
                if snippet not in snippets:
                    snippets.append(snippet)
            index = max(cursor, index + 1)
        return snippets

    def search(self, names: list[str]) -> dict[str, list[Any]]:
        names = [str(name).strip() for name in names if str(name or "").strip()]
        names = list(dict.fromkeys(names))
        if not names:
            return {"rows": [], "patches": []}
        rows = []
        for row in self.weapon_rows:
            haystack = f"{row.get('label', '')} {row.get('changes', '')}"
            if any(self._contains(name, haystack) for name in names):
                rows.append(
                    {
                        "label": self._clean(str(row.get("label") or "")),
                        "changes": self._clean(str(row.get("changes") or "")),
                    }
                )

        by_date: dict[str, dict[str, Any]] = {}
        # Prefer the official announcement text: it is the complete record for
        # a patch date. The curated Chinese index only fills dates that the
        # announcement extraction did not cover.
        for patch in self.historical_patches:
            date = str(patch.get("date") or "")
            if not date:
                continue
            changes = self._extract_snippets(
                str(patch.get("text") or ""), names
            )
            if changes:
                by_date[date] = {
                    "date": date,
                    "title": str(patch.get("title") or ""),
                    "url": str(patch.get("url") or ""),
                    "changes": changes,
                }

        for patch in self.patches:
            date = str(patch.get("date") or "")
            if not date or date in by_date:
                continue
            changes = self._curated_changes(patch, names)
            if not changes:
                continue
            by_date[date] = {
                "date": date,
                "title": str(patch.get("title") or ""),
                "url": str(patch.get("url") or ""),
                "changes": changes,
            }

        patches = sorted(
            by_date.values(), key=lambda row: str(row.get("date") or ""), reverse=True
        )
        return {"rows": rows, "patches": patches}
