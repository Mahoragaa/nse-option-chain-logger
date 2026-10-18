from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class MarketConfig:
    symbol: str = "NIFTY"
    expiry: str | None = None
    strikes: list[int] = field(default_factory=lambda: [24500, 24600, 24700])
    interval_minutes: int = 3
    start_time: str = "09:15:00"
    end_time: str = "15:15:00"
    auto_atm: bool = False
    auto_atm_window: int = 2
    alert_oi_change: float = 0.0
    alert_pcr: float = 0.0
    output_dir: str = "output"
    data_dir: str = "data"

    @classmethod
    def from_yaml(cls, path: str | Path) -> "MarketConfig":
        config_path = Path(path)
        data: dict[str, Any] = {}
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        return cls(**{**cls().__dict__, **data})

    def to_yaml(self, path: str | Path) -> None:
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml.safe_dump(self.__dict__, sort_keys=False), encoding="utf-8")
