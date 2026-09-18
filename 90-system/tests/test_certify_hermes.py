from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "90-system/.echo/runtime/certify_hermes.py"


def _module():
    runtime = str(MODULE_PATH.parent)
    if runtime not in sys.path:
        sys.path.insert(0, runtime)
    spec = importlib.util.spec_from_file_location("certify_hermes", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_static_readiness_passes_for_current_repository():
    report = _module().build_report(ROOT)

    assert report["version"] == "hermes-readiness/v1"
    assert report["static_ready"] is True
    assert report["runtime_certified"] is False
    assert report["runtime_smoke"] == "required"
    assert all(item["passed"] for item in report["checks"])


def test_missing_bundle_is_reported_without_private_paths(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    report = _module().build_report(root)

    assert report["static_ready"] is False
    details = " ".join(item["detail"] for item in report["checks"])
    assert str(root) not in details
