"""Read timeline Markdown without changing the source notes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import re
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Event:
    path: Path
    date: date
    title: str
    category: str
    body: str

    def narration(self, read_year: bool = True) -> str:
        prefix = f"Year {self.date.year}. " if read_year else ""
        return f"{prefix}{self.title}.\n\n{self.body}"


@dataclass
class Timeline:
    events: list[Event]
    parents: dict[str, str | None]
    warnings: list[str]

    def category_path(self, category: str) -> str:
        parts = [category]
        while parent := self.parents.get(parts[0]):
            if parent in parts:
                break
            parts.insert(0, parent)
        return " / ".join(parts)

    def includes(self, category: str, selected: str) -> bool:
        seen = set()
        while category and category not in seen:
            if category == selected:
                return True
            seen.add(category)
            category = self.parents.get(category) or ""
        return False

    def select(self, category: str | None, start: int, end: int) -> list[Event]:
        return [
            event for event in self.events
            if start <= event.date.year <= end
            and (category is None or self.includes(event.category, category))
        ]


def load_timeline(folder: Path) -> Timeline:
    """Load direct .md children, YAML dates, and optional category hierarchy."""
    files = sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".md"),
        key=lambda p: p.name.casefold(),
    )
    parents: dict[str, str | None] = {}
    warnings = []
    by_id = {}
    settings = folder / ".settings" / "categories.json"
    if settings.exists():
        try:
            categories = json.loads(settings.read_text(encoding="utf-8-sig"))
            if not isinstance(categories, list) or any(
                not isinstance(c, dict) or not isinstance(c.get("name"), str)
                or not c["name"].strip() for c in categories
            ):
                raise ValueError("Expected a list of named categories")
            by_id = {str(c["id"]): c["name"] for c in categories if c.get("id")}
            parents = {c["name"]: by_id.get(str(c.get("parent_id"))) for c in categories}
        except (OSError, UnicodeError, ValueError) as exc:
            warnings.append(f"Category hierarchy unavailable: {exc}")
    events = []
    for path in files:
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            if not lines or lines[0].strip() != "---":
                raise ValueError("Missing YAML metadata")
            end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
            if end is None:
                raise ValueError("Unclosed YAML metadata")
            try:
                metadata = yaml.safe_load("\n".join(lines[1:end]))
            except yaml.YAMLError:
                # Timeline exports can contain unescaped quotes in titles or
                # unindented multi-line labels. Recover the scalar fields used
                # by this reader rather than discarding an otherwise valid note.
                metadata = {}
                for line in lines[1:end]:
                    match = re.match(r"^(date|title|category|cat|category_id):\s*(.*)$", line)
                    if match:
                        value = match[2].strip()
                        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                            value = value[1:-1]
                        metadata[match[1]] = value
                warnings.append(f"{path.name}: Recovered non-standard YAML metadata")
            if not isinstance(metadata, dict):
                raise ValueError("Expected YAML metadata fields")
            raw_date = metadata.get("date")
            if isinstance(raw_date, datetime):
                event_date = raw_date.date()
            elif isinstance(raw_date, date):
                event_date = raw_date
            else:
                event_date = date.fromisoformat(str(raw_date).strip()[:10])
            category = by_id.get(str(metadata.get("category_id"))) or str(
                metadata.get("cat") or metadata.get("category") or "Uncategorized"
            ).strip()
            parents.setdefault(category, None)
            body = "\n".join(lines[end + 1:]).strip()
            title = str(metadata.get("title") or path.stem).strip()
            events.append(Event(path, event_date, title, category, body))
        except (OSError, UnicodeError, ValueError, yaml.YAMLError) as exc:
            warnings.append(f"{path.name}: {exc}")
    events.sort(key=lambda event: (event.date, event.path.name.casefold()))
    return Timeline(events, parents, warnings)
