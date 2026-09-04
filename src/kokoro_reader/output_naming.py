"""Collision-safe names for generated audio files."""

from __future__ import annotations

from pathlib import Path


def available_path(requested: Path) -> Path:
    """Return *requested* or the first available numbered variant."""
    if not requested.exists():
        return requested

    number = 2
    while True:
        candidate = requested.with_name(
            f"{requested.stem}-{number}{requested.suffix}"
        )
        if not candidate.exists():
            return candidate
        number += 1
