"""Per-model token pricing and cost estimation.

Devin bills through ACUs/credits rather than published per-token prices,
so the numbers in ``prices.json`` are user-editable estimates.  Prices are
USD per 1M tokens, split into input / output / cache_read / cache_creation.
"""

from __future__ import annotations

import json
import os
import sys
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
        if cand and Path(cand).exists():
            return Path(cand)
    return _PROJECT_FILE

_KEYS = ("input", "output", "cache_read", "cache_creation")


@dataclass
class ModelPrice:
    input: float = 0.0
    output: float = 0.0
    cache_read: float = 0.0
    cache_creation: float = 0.0

    @classmethod
    def from_dict(cls, d: dict) -> "ModelPrice":
        return cls(**{k: float(d.get(k, 0.0)) for k in _KEYS})

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
            return float(self.settings.get("daily_budget", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    @property
    def language(self) -> str:
        lang = str(self.settings.get("language", "zh") or "zh")
        return lang if lang in ("zh", "en", "ja", "ko", "es", "vi") else "zh"

    @classmethod
    def load(cls, path: Path | None = None) -> "PriceTable":
        path = path or default_prices_path()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls(ModelPrice(), {})
        default = ModelPrice.from_dict(raw.get("default", {}))
        models = {
            name: ModelPrice.from_dict(p)
            for name, p in raw.get("models", {}).items()
        }
        return cls(default, models, raw.get("settings", {}))

    def update_settings(
        self, patch: dict, path: Path | None = None
    ) -> Path:
        """Merge ``patch`` into the ``settings`` block of prices.json."""
        path = path or default_prices_path()
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raw = {}
        except (OSError, json.JSONDecodeError):
            raw = {}
        settings = raw.setdefault("settings", {})
        settings.update(patch)
        path.write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
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
