from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Protocol

from collab.models import DemoState


class StateStore(Protocol):
    def load(self) -> DemoState: ...

    def save(self, state: DemoState) -> None: ...

    def check_writable(self) -> None: ...

    def locked(self) -> AbstractContextManager[None]: ...


class JsonStateStore:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = RLock()

    def load(self) -> DemoState:
        with self._lock:
            if not self._path.exists():
                return DemoState()
            return DemoState.model_validate_json(self._path.read_text(encoding="utf-8"))

    def save(self, state: DemoState) -> None:
        with self._lock:
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

    def check_writable(self) -> None:
        with self._lock:
            self.save(self.load())

    @contextmanager
    def locked(self) -> Iterator[None]:
        """Serialize local read-modify-write state transitions."""
        with self._lock:
            yield
