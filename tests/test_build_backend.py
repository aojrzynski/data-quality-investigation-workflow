from __future__ import annotations

import importlib.util
from pathlib import Path


def test_build_backend_metadata_includes_runtime_dependencies(tmp_path: Path) -> None:
    backend_path = Path("build_backend/_build_backend.py")
    spec = importlib.util.spec_from_file_location("local_build_backend", backend_path)
    assert spec is not None
    assert spec.loader is not None
    backend = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)

    dist_info_name = backend.prepare_metadata_for_build_wheel(str(tmp_path))
    metadata = (tmp_path / dist_info_name / "METADATA").read_text(encoding="utf-8")

    assert "Requires-Dist: pandas>=2.2" in metadata
    assert "Requires-Dist: openpyxl>=3.1" in metadata
    assert "Provides-Extra: llm" in metadata
    assert "Requires-Dist: openai>=1.0; extra == 'llm'" in metadata
