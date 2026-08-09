from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .models import Metadata


class MetadataError(ValueError):
    """Raised when metadata files are empty or malformed."""


def _non_empty_lines(path: Path) -> list[str]:
    if not path.exists():
        raise MetadataError(f"Metadata file does not exist: {path}")
    values = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [value for value in values if value and not value.startswith("#")]


def _description_options(path: Path) -> list[str]:
    if not path.exists():
        raise MetadataError(f"Metadata file does not exist: {path}")
    raw = path.read_text(encoding="utf-8").strip()
    blocks = [block.strip() for block in raw.split("\n---\n")]
    blocks = [block for block in blocks if block and not block.startswith("#")]
    if not blocks:
        raise MetadataError(f"Description file has no usable entries: {path}")
    return blocks


def _tag_sets(path: Path) -> list[list[str]]:
    if not path.exists():
        raise MetadataError(f"Metadata file does not exist: {path}")
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetadataError(f"Tags file must be valid JSON: {path}") from exc
    if not isinstance(payload, list):
        raise MetadataError("Tags JSON must be an array of arrays or strings")

    result: list[list[str]] = []
    for entry in payload:
        if isinstance(entry, str):
            tags = [tag.strip() for tag in entry.split(",")]
        elif isinstance(entry, list):
            tags = [str(tag).strip() for tag in entry]
        else:
            raise MetadataError("Each tags entry must be a string or an array")
        cleaned = list(dict.fromkeys(tag for tag in tags if tag))
        if cleaned:
            result.append(cleaned)
    if not result:
        raise MetadataError(f"Tags file has no usable tag sets: {path}")
    return result


class MetadataPool:
    def __init__(self, directory: str, *, rng: random.Random | None = None) -> None:
        root = Path(directory)
        self.titles = _non_empty_lines(root / "titles.txt")
        self.descriptions = _description_options(root / "descriptions.txt")
        self.tag_sets = _tag_sets(root / "tags.json")
        self.rng = rng or random.SystemRandom()

    def choose(self) -> Metadata:
        title = self.rng.choice(self.titles)
        description = self.rng.choice(self.descriptions)
        tags = self.rng.choice(self.tag_sets)
        if len(title) > 100:
            raise MetadataError("Selected title exceeds YouTube's 100-character limit")
        if len(description) > 5000:
            raise MetadataError("Selected description exceeds YouTube's 5,000-character limit")
        if sum(len(tag) + 1 for tag in tags) > 500:
            raise MetadataError("Selected tag set exceeds YouTube's 500-character limit")
        return Metadata(title=title, description=description, tags=tags)