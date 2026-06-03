"""Minimal PEP 660 build backend for the scaffold project.

This backend exists so the scaffold can be installed in constrained local
sandboxes without downloading packaging build dependencies. It builds a simple
editable wheel that adds ``src`` to Python's import path and exposes the console
script declared in ``pyproject.toml``.
"""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import pathlib
import tomllib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _project() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]


def _normalized_name(name: str) -> str:
    return name.replace("-", "_").replace(".", "_")


def _dist_info_name() -> str:
    project = _project()
    return f"{_normalized_name(project['name'])}-{project['version']}.dist-info"


def _metadata() -> str:
    project = _project()
    lines = [
        "Metadata-Version: 2.2",
        f"Name: {project['name']}",
        f"Version: {project['version']}",
        f"Summary: {project.get('description', '')}",
        f"Requires-Python: {project.get('requires-python', '')}",
        "License: MIT",
    ]
    for classifier in project.get("classifiers", []):
        lines.append(f"Classifier: {classifier}")
    for keyword in project.get("keywords", []):
        lines.append(f"Keywords: {keyword}")
    for extra, requirements in project.get("optional-dependencies", {}).items():
        lines.append(f"Provides-Extra: {extra}")
        for requirement in requirements:
            lines.append(f"Requires-Dist: {requirement}; extra == '{extra}'")
    lines.append("")
    return "\n".join(lines)


def _entry_points() -> str:
    scripts = _project().get("scripts", {})
    if not scripts:
        return ""
    lines = ["[console_scripts]"]
    lines.extend(f"{name} = {target}" for name, target in scripts.items())
    lines.append("")
    return "\n".join(lines)


def _wheel() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: data-quality-investigation-workflow-build-backend",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def _hash(data: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=")
    return f"sha256={digest.decode('ascii')}"


def _write_wheel(wheel_directory: str) -> str:
    project = _project()
    name = _normalized_name(project["name"])
    version = project["version"]
    wheel_name = f"{name}-{version}-py3-none-any.whl"
    wheel_path = pathlib.Path(wheel_directory) / wheel_name
    dist_info = _dist_info_name()
    pth_name = f"{name}.pth"
    src_path = (ROOT / "src").as_posix()

    files = {
        pth_name: f"{src_path}\n".encode("utf-8"),
        f"{dist_info}/METADATA": _metadata().encode("utf-8"),
        f"{dist_info}/WHEEL": _wheel().encode("utf-8"),
        f"{dist_info}/entry_points.txt": _entry_points().encode("utf-8"),
    }

    record_rows = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for path, data in files.items():
            wheel.writestr(path, data)
            record_rows.append([path, _hash(data), str(len(data))])

        record_path = f"{dist_info}/RECORD"
        record_rows.append([record_path, "", ""])
        record_buffer = io.StringIO()
        writer = csv.writer(record_buffer, lineterminator="\n")
        writer.writerows(record_rows)
        wheel.writestr(record_path, record_buffer.getvalue().encode("utf-8"))

    return wheel_name


def get_requires_for_build_wheel(config_settings=None):  # noqa: ANN001
    return []


def get_requires_for_build_editable(config_settings=None):  # noqa: ANN001
    return []


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):  # noqa: ANN001
    dist_info = pathlib.Path(metadata_directory) / _dist_info_name()
    dist_info.mkdir(parents=True, exist_ok=True)
    (dist_info / "METADATA").write_text(_metadata(), encoding="utf-8")
    (dist_info / "WHEEL").write_text(_wheel(), encoding="utf-8")
    (dist_info / "entry_points.txt").write_text(_entry_points(), encoding="utf-8")
    return dist_info.name


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):  # noqa: ANN001
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):  # noqa: ANN001
    return _write_wheel(wheel_directory)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):  # noqa: ANN001
    return _write_wheel(wheel_directory)
