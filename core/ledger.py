"""The sealed evaluation ledger: the one uneditable record.

Append-only JSONL, flushed per event. No in-world component may read it — the module
exposes only `record`. Researchers read the file after the run (see scoring.py).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Ledger:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = path.open("a", encoding="utf-8")
        self._seq = 0
        self.tick = 0

    def record(self, event: str, **data: Any) -> None:
        self._seq += 1
        row = {"seq": self._seq, "t": round(time.time(), 3), "tick": self.tick, "event": event, **data}
        self._fh.write(json.dumps(row, default=str) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()
