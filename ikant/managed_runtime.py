from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable

from .component_manifest import load_manifest
from .component_store import atomic_json
from .engine_supervisor import EngineSupervisor
from .model_broker import LocalModelBroker
from .model_manager import ModelManager

MANAGED_RUNTIME_SCHEMA = "ikant-managed-local-runtime/v0.23-test"


class ManagedRuntimeError(RuntimeError):
    pass


def _binding_digest(binding: dict[str, Any]) -> str:
    material = {
        "manifest_sha256": binding["manifest_sha256"],
        "engine": {
            "id": binding["engine"]["id"],
            "version": binding["engine"]["version"],
            "platform": binding["engine"]["platform"],
            "artifact_sha256": binding["engine"]["artifact_sha256"],
        },
        "model": {
            "id": binding["model"]["id"],
            "revision": binding["model"]["revision"],
            "sha256": binding["model"]["sha256"],
        },
    }
    raw = json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class ManagedLocalRuntime:
    def __init__(
        self,
        root: str | Path,
        *,
        manifest_path: str | Path | None = None,
        component_root: str | Path | None = None,
        manager_factory: Callable[..., ModelManager] = ModelManager,
        supervisor_factory: Callable[..., EngineSupervisor] = EngineSupervisor,
    ):
        self.root = Path(root).resolve()
        self.state_dir = self.root / ".ikant"
        self.manifest_path = Path(manifest_path).resolve() if manifest_path else self.root / "MODEL_RUNTIME.json"
        self.component_root = Path(component_root).resolve() if component_root else None
        self.manager_factory = manager_factory
        self.supervisor_factory = supervisor_factory
        self.supervisor: EngineSupervisor | None = None
        self.binding: dict[str, Any] | None = None
        self.binding_digest: str | None = None

    @property
    def projection_path(self) -> Path:
        return self.state_dir / "model-runtime.json"

    def _persist(self, status: str, **extra: Any) -> None:
        payload: dict[str, Any] = {
            "schema": MANAGED_RUNTIME_SCHEMA,
            "status": status,
            "managed": True,
            "browser_model_transport": False,
            "api_key_persisted": False,
            "model_output_is_authority": False,
            "component_presence_is_authority": False,
            "runtime_readiness_is_authority": False,
            "epistemic_authority": 0.0,
            "execution_authority": 0.0,
        }
        payload.update(extra)
        atomic_json(self.projection_path, payload)

    def start(self, *, progress=None, readiness_timeout: float = 45.0) -> LocalModelBroker:
        if self.supervisor is not None:
            raise ManagedRuntimeError("managed runtime already started")
        try:
            manifest = load_manifest(self.manifest_path)
            self._persist("PREPARING", manifest_sha256=hashlib.sha256(self.manifest_path.read_bytes()).hexdigest())
            manager = self.manager_factory(manifest, component_root=self.component_root)
            binding = manager.ensure(progress=progress)
            digest = _binding_digest(binding)
            supervisor = self.supervisor_factory(self.state_dir)
            session = supervisor.start(binding, timeout=readiness_timeout)
            if session.get("status") != "READY" or session.get("browser_model_transport") is not False:
                supervisor.stop()
                raise ManagedRuntimeError("managed engine did not reach constrained readiness")
            self.supervisor = supervisor
            self.binding = binding
            self.binding_digest = digest
            self._persist(
                "READY",
                manifest_sha256=binding["manifest_sha256"],
                binding_sha256=digest,
                engine={
                    "id": binding["engine"]["id"],
                    "version": binding["engine"]["version"],
                    "platform": binding["engine"]["platform"],
                    "artifact_sha256": binding["engine"]["artifact_sha256"],
                },
                model={
                    "id": binding["model"]["id"],
                    "revision": binding["model"]["revision"],
                    "sha256": binding["model"]["sha256"],
                },
            )
            return LocalModelBroker(
                str(session["endpoint"]),
                model=str(session["model_id"]),
                api_key=str(session["api_key"]),
                runtime_binding_digest=digest,
                managed_runtime=True,
            )
        except Exception as exc:
            self._persist("BLOCKED", error=type(exc).__name__)
            self.stop(persist=False)
            if isinstance(exc, ManagedRuntimeError):
                raise
            raise ManagedRuntimeError("managed local runtime failed closed") from exc

    def stop(self, *, persist: bool = True) -> None:
        supervisor, self.supervisor = self.supervisor, None
        if supervisor is not None:
            supervisor.stop()
        if persist and self.projection_path.exists():
            extra: dict[str, Any] = {}
            if self.binding_digest:
                extra["binding_sha256"] = self.binding_digest
            self._persist("STOPPED", **extra)
