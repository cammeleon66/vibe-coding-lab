from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path
from threading import RLock
from typing import Any, Protocol, cast


class DocumentStore(Protocol):
    """Key/value document store owned by exactly one service."""

    def read(self, key: str) -> bytes | None: ...

    def write(self, key: str, data: bytes) -> None: ...

    def create(self, key: str, data: bytes) -> bool:
        """Create-only write. Returns False when the key already exists."""
        ...

    def list(self, prefix: str) -> list[str]: ...

    def delete_prefix(self, prefix: str) -> int: ...


def _check_key(key: str) -> str:
    parts = key.split("/")
    if not key or key.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"Invalid store key: {key!r}")
    return key


class MemoryDocumentStore:
    def __init__(self) -> None:
        self._items: dict[str, bytes] = {}
        self._lock = RLock()

    def read(self, key: str) -> bytes | None:
        with self._lock:
            return self._items.get(_check_key(key))

    def write(self, key: str, data: bytes) -> None:
        with self._lock:
            self._items[_check_key(key)] = data

    def create(self, key: str, data: bytes) -> bool:
        with self._lock:
            if _check_key(key) in self._items:
                return False
            self._items[key] = data
            return True

    def list(self, prefix: str) -> list[str]:
        with self._lock:
            return sorted(key for key in self._items if key.startswith(prefix))

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [key for key in self._items if key.startswith(prefix)]
            for key in keys:
                del self._items[key]
            return len(keys)


class FileDocumentStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._lock = RLock()

    def _path(self, key: str) -> Path:
        return self._root.joinpath(*_check_key(key).split("/"))

    def read(self, key: str) -> bytes | None:
        path = self._path(key)
        with self._lock:
            return path.read_bytes() if path.is_file() else None

    def write(self, key: str, data: bytes) -> None:
        path = self._path(key)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_name(f".{path.name}.tmp")
            temporary.write_bytes(data)
            for attempt in range(5):
                try:
                    temporary.replace(path)
                    return
                except PermissionError:
                    # Windows refuses to replace a file another process has open.
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))

    def create(self, key: str, data: bytes) -> bool:
        path = self._path(key)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                descriptor = os.open(path, flags)
            except FileExistsError:
                return False
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            return True

    def list(self, prefix: str) -> list[str]:
        if not self._root.exists():
            return []
        keys = (
            path.relative_to(self._root).as_posix()
            for path in self._root.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        )
        return sorted(key for key in keys if key.startswith(prefix))

    def delete_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = self.list(prefix)
            for key in keys:
                self._path(key).unlink(missing_ok=True)
            return len(keys)


class _Blob(Protocol):
    def download_blob(self) -> Any: ...

    def upload_blob(self, data: bytes, **kwargs: Any) -> Any: ...

    def delete_blob(self, **kwargs: Any) -> Any: ...


class _BlobItem(Protocol):
    name: str


class BlobContainer(Protocol):
    def get_blob_client(self, blob: str) -> _Blob: ...

    def list_blobs(self, *, name_starts_with: str | None = None) -> Iterator[_BlobItem]: ...


class BlobDocumentStore:
    """Azure Blob container scoped to one service (see the identity matrix)."""

    def __init__(self, container: BlobContainer) -> None:
        self._container = container

    def read(self, key: str) -> bytes | None:
        from azure.core.exceptions import ResourceNotFoundError

        blob = self._container.get_blob_client(_check_key(key))
        try:
            return cast(bytes, blob.download_blob().readall())
        except ResourceNotFoundError:
            return None

    def write(self, key: str, data: bytes) -> None:
        self._container.get_blob_client(_check_key(key)).upload_blob(data, overwrite=True)

    def create(self, key: str, data: bytes) -> bool:
        from azure.core.exceptions import ResourceExistsError

        try:
            self._container.get_blob_client(_check_key(key)).upload_blob(data, overwrite=False)
        except ResourceExistsError:
            return False
        return True

    def list(self, prefix: str) -> list[str]:
        return sorted(item.name for item in self._container.list_blobs(name_starts_with=prefix))

    def delete_prefix(self, prefix: str) -> int:
        keys = self.list(prefix)
        for key in keys:
            self._container.get_blob_client(key).delete_blob()
        return len(keys)


def create_blob_store(
    account_url: str, container_name: str, client_id: str | None
) -> BlobDocumentStore:
    """The container is provisioned by infrastructure; the app identity cannot create it."""
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import ContainerClient

    credential = DefaultAzureCredential(
        managed_identity_client_id=client_id,
        exclude_interactive_browser_credential=True,
    )
    container = ContainerClient(
        account_url=account_url, container_name=container_name, credential=credential
    )
    return BlobDocumentStore(cast(BlobContainer, container))
