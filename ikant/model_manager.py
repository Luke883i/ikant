from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Callable

from .component_manifest import manifest_digest, select_engine_artifact
from .component_store import ComponentStoreError, default_component_root, find_unique_regular, safe_extract_tar, verify_file
from .download_manager import download_verified

MODEL_BINDING_SCHEMA = "ikant-managed-model-binding/v0.23-test"


class ModelManagerError(RuntimeError):
    pass


class ModelManager:
    def __init__(
        self,
        manifest: dict[str, Any],
        *,
        component_root: str | Path | None = None,
        platform: str | None = None,
        downloader: Callable[..., Path] = download_verified,
    ):
        self.manifest = manifest
        self.manifest_sha256 = manifest_digest(manifest)
        self.root = Path(component_root).resolve() if component_root else default_component_root()
        self.platform, self.engine_artifact = select_engine_artifact(manifest, key=platform)
        self.downloader = downloader

    @property
    def engine_version(self) -> str:
        return str(self.manifest["engine"]["release_tag"])

    @property
    def model(self) -> dict[str, Any]:
        return dict(self.manifest["model"])

    def _download(self, url: str, target: Path, sha256: str, progress=None) -> Path:
        return self.downloader(url, target, sha256, progress=progress)

    def ensure_model(self, *, progress=None) -> Path:
        spec = self.model
        target = self.root / "models" / str(spec["id"]) / str(spec["file"])
        if verify_file(target, str(spec["sha256"])):
            return target
        if target.exists():
            target.unlink()
        return self._download(str(spec["url"]), target, str(spec["sha256"]), progress=progress)

    def ensure_engine(self, *, progress=None) -> Path:
        spec = self.engine_artifact
        install = self.root / "engines" / self.engine_version / self.platform
        marker = install / ".ikant-artifact-sha256"
        if install.is_dir() and marker.is_file() and marker.read_text(encoding="utf-8").strip() == spec["sha256"]:
            try:
                server = find_unique_regular(install, str(spec["server_basename"]))
                if os.access(server, os.X_OK):
                    return server
            except ComponentStoreError:
                pass
            shutil.rmtree(install, ignore_errors=True)
        archive_name = Path(str(spec["url"]).split("?", 1)[0]).name
        archive = self.root / "downloads" / archive_name
        self._download(str(spec["url"]), archive, str(spec["sha256"]), progress=progress)
        if install.exists():
            shutil.rmtree(install)
        safe_extract_tar(archive, install)
        server = find_unique_regular(install, str(spec["server_basename"]))
        server.chmod(server.stat().st_mode | 0o100)
        marker.write_text(str(spec["sha256"]) + "\n", encoding="utf-8")
        with marker.open("rb") as fh:
            os.fsync(fh.fileno())
        return server

    def ensure(self, *, progress=None) -> dict[str, Any]:
        engine_path = self.ensure_engine(progress=progress)
        model_path = self.ensure_model(progress=progress)
        return {
            "schema": MODEL_BINDING_SCHEMA,
            "manifest_sha256": self.manifest_sha256,
            "engine": {
                "id": self.manifest["engine"]["id"],
                "version": self.engine_version,
                "platform": self.platform,
                "artifact_sha256": self.engine_artifact["sha256"],
                "path": str(engine_path),
            },
            "model": {
                "id": self.model["id"],
                "revision": self.model["revision"],
                "sha256": self.model["sha256"],
                "path": str(model_path),
            },
            "model_output_is_authority": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
