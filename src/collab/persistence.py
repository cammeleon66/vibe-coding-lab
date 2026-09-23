from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from collab.models import DemoState


class JsonStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> DemoState:
        if not self._path.exists():
            return DemoState()
        return DemoState.model_validate_json(self._path.read_text(encoding="utf-8"))

    def save(self, state: DemoState) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self._path.parent,
            delete=False,
        ) as temporary:
            temporary.write(state.model_dump_json(indent=2))
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(self._path)
