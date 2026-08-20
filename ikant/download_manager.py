from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .component_store import fsync_dir, sha256_file


class DownloadError(RuntimeError):
    pass


def _status(response: Any) -> int:
    return int(getattr(response, "status", getattr(response, "code", 200)))


def download_verified(
    url: str,
    destination: str | Path,
    expected_sha256: str,
    *,
    opener: Callable[..., Any] = urlopen,
    progress: Callable[[dict[str, int | str]], None] | None = None,
    chunk_size: int = 1024 * 1024,
) -> Path:
    parsed = urlparse(str(url))
    if parsed.scheme != "https" or not parsed.netloc:
        raise DownloadError("component download requires HTTPS")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and sha256_file(target) == expected_sha256:
        return target
    partial = target.with_name(target.name + ".partial")
    offset = partial.stat().st_size if partial.is_file() else 0
    headers = {"Accept": "application/octet-stream", "User-Agent": "iKant/0.23 managed-runtime"}
    if offset:
        headers["Range"] = f"bytes={offset}-"
    request = Request(url, method="GET", headers=headers)
    try:
        response = opener(request, timeout=60)
    except Exception as exc:
        raise DownloadError("component download failed") from exc
    with response:
        status = _status(response)
        if status not in {200, 206}:
            raise DownloadError(f"component download HTTP {status}")
        append = bool(offset and status == 206)
        if offset and status == 200:
            offset = 0
        mode = "ab" if append else "wb"
        written = offset
        with partial.open(mode) as fh:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                fh.write(chunk)
                written += len(chunk)
                if progress:
                    progress({"phase": "DOWNLOADING", "bytes": written, "target": target.name})
            fh.flush()
            os.fsync(fh.fileno())
    actual = sha256_file(partial)
    if actual != expected_sha256:
        try:
            partial.unlink()
        finally:
            raise DownloadError("component digest mismatch")
    os.replace(partial, target)
    fsync_dir(target.parent)
    if progress:
        progress({"phase": "VERIFIED", "bytes": target.stat().st_size, "target": target.name})
    return target
