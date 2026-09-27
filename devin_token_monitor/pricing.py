"""Per-model token pricing and cost estimation.

Devin bills through ACUs/credits rather than published per-token prices,
so the numbers in ``prices.json`` are user-editable estimates.  Prices are
USD per 1M tokens, split into input / output / cache_read / cache_creation.
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

_PROJECT_FILE = Path(__file__).resolve().parent.parent / "prices.json"
_USER_FILE = Path.home() / ".devin-token-monitor" / "prices.json"
_BUNDLED_FILE = (
    Path(sys.argv[0]).resolve().parent.parent / "Resources" / "prices.json"
)


def default_prices_path() -> Path:
    """First existing prices.json: env > user dir > bundled app > project."""
    for cand in (
        os.environ.get("DTM_PRICES"),
        _USER_FILE,
        _BUNDLED_FILE,
        _PROJECT_FILE,
    ):
        if cand:
            path = Path(cand).expanduser()
            if path.exists():
                return path
    return _PROJECT_FILE


def _read_prices_json(path: Path) -> dict:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("settings", {}), dict):
        raise ValueError(f"Price table must contain valid JSON settings: {path}")
    return raw


def _write_prices_json(path: Path, raw: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            json.dump(raw, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def editable_prices_path() -> Path:
    override = os.environ.get("DTM_PRICES")
    target = Path(override).expanduser() if override else _USER_FILE
    if not target.exists():
        _write_prices_json(target, _read_prices_json(default_prices_path()))
    return target


_KEYS = ("input", "output", "cache_read", "cache_creation")
_LANGUAGES = ("zh", "en", "ja", "ko", "es", "vi")
_THEMES = ("system", "midnight", "graphite", "paper", "ocean", "forest")


@dataclass
class ModelPrice:
    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_creation: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> "ModelPrice":
        values = {k: float(d.get(k, 0.0)) for k in _KEYS}
        if any(not math.isfinite(value) or value < 0 for value in values.values()):
            raise ValueError("Model prices must be finite and nonnegative")
        return cls(**values)

    def cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_creation_tokens: int,
    ) -> float:
        return (
            input_tokens * self.input
            + output_tokens * self.output
            + cache_read_tokens * self.cache_read
            + cache_creation_tokens * self.cache_creation
        ) / 1_000_000


class PriceTable:
    def __init__(
        self,
        default: ModelPrice,
        models: dict[str, ModelPrice],
        settings: dict | None = None,
    ):
        self.default = default
        self.models = models
        self.settings = settings or {}

    @property
    def daily_budget(self) -> float:
        try:
            value = float(self.settings.get("daily_budget", 0) or 0)
            return value if math.isfinite(value) and value >= 0 else 0.0
        except (TypeError, ValueError):
            return 0.0

    @property
    def language(self) -> str:
        lang = str(self.settings.get("language", "zh") or "zh")
        return lang if lang in _LANGUAGES else "zh"

    @classmethod
    def load(cls, path: Path | None = None) -> "PriceTable":
        primary = path or default_prices_path()
        for candidate in dict.fromkeys((primary, _BUNDLED_FILE, _PROJECT_FILE)):
            try:
                raw = _read_prices_json(candidate)
                default = ModelPrice.from_dict(raw.get("default", {}))
                models = {
                    name: ModelPrice.from_dict(price)
                    for name, price in raw.get("models", {}).items()
                }
                return cls(default, models, raw.get("settings", {}))
            except (OSError, ValueError, TypeError, AttributeError):
                if candidate == primary and candidate.exists():
                    print(f"warning: invalid price table at {candidate}; using bundled defaults", file=sys.stderr)
        return cls(ModelPrice(), {})

    def update_settings(
        self, patch: dict, path: Path | None = None
    ) -> Path:
        """Merge ``patch`` into the ``settings`` block of prices.json."""
        if not isinstance(patch, dict) or set(patch) - {"daily_budget", "language", "theme"}:
            raise ValueError("Unsupported price-table setting")
        values = dict(patch)
        if "daily_budget" in values:
            budget = float(values["daily_budget"])
            if not math.isfinite(budget) or budget < 0:
                raise ValueError("Daily budget must be finite and nonnegative")
            values["daily_budget"] = budget
        if "language" in values and values["language"] not in _LANGUAGES:
            raise ValueError("Unsupported language")
        if "theme" in values and values["theme"] not in _THEMES:
            raise ValueError("Unsupported theme")
        path = Path(path).expanduser() if path else editable_prices_path()
        raw = _read_prices_json(path if path.exists() else default_prices_path())
        settings = raw.setdefault("settings", {})
        if not isinstance(settings, dict):
            raise ValueError(f"Invalid settings in price table: {path}")
        settings.update(values)
        _write_prices_json(path, raw)
        return path

    def price_for(self, model: str) -> ModelPrice:
        if model in self.models:
            return self.models[model]
        m = model.lower()
        best: tuple[int, ModelPrice] | None = None
        for name, price in self.models.items():
            n = name.lower()
            if m.startswith(n) or n in m:
                if best is None or len(n) > best[0]:
                    best = (len(n), price)
        return best[1] if best else self.default
