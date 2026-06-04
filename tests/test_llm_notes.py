from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from data_quality_investigation_workflow import cli
from data_quality_investigation_workflow.llm_notes import (
    FORBIDDEN_TERMS,
    build_safe_input_summary,
    generate_llm_notes,
    parse_and_validate_notes,
)
from data_quality_investigation_workflow.llm_prompt import build_llm_notes_prompt


class FakeClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.prompts: list[str] = []

    def create_notes(
        self,
        *,
        model: str,
        prompt: str,
        max_output_tokens: int | None = None,
    ) -> str:
        self.prompts.append(prompt)
        return self.response


def _run_default_artifacts(output_dir: Path, *, baseline: bool = False) -> None:
    args = [
        "--input",
        "examples/customer_quality_snapshot.csv",
        "--issue",
        "Customer IDs have started duplicating",
        "--output-dir",
        str(output_dir),
    ]
    if baseline:
        args.extend(["--baseline", "examples/customer_quality_snapshot_baseline.csv"])
    assert cli.main(args) == 0


def _load_artifacts(output_dir: Path) -> dict[str, Any]:
    names = {
        "investigation_case": "investigation_case.json",
        "dataset_profile": "dataset_profile.json",
        "evidence_ledger": "evidence_ledger.json",
        "hypothesis_tracker": "hypothesis_tracker.json",
        "investigation_findings": "investigation_findings.json",
    }
    return {
        key: json.loads((output_dir / filename).read_text(encoding="utf-8"))
        for key, filename in names.items()
    }


def _source_artifacts(output_dir: Path) -> dict[str, str]:
    return {
        "investigation_case": (output_dir / "investigation_case.json").as_posix(),
        "dataset_profile": (output_dir / "dataset_profile.json").as_posix(),
        "investigation_plan": (output_dir / "investigation_plan.json").as_posix(),
        "evidence_ledger": (output_dir / "evidence_ledger.json").as_posix(),
        "hypothesis_tracker": (output_dir / "hypothesis_tracker.json").as_posix(),
        "investigation_findings": (output_dir / "investigation_findings.json").as_posix(),
        "investigation_report": (output_dir / "investigation_report.md").as_posix(),
    }


def _valid_notes_response() -> str:
    return json.dumps(
        {
            "review_summary": "Review the deterministic evidence and keep human review in control.",
            "suggested_follow_up_questions": ["Which upstream process owns the relevant key field?"],
            "suggested_human_checks": ["Confirm the expected uniqueness rule for the selected column."],
            "communication_notes": ["Describe the aggregate signal without final confirmation."],
            "limitations_to_keep_visible": ["Human review remains required."],
        }
    )


def test_default_run_does_not_write_llm_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "default_run"

    _run_default_artifacts(output_dir)

    assert not (output_dir / "llm_safe_input_summary.json").exists()
    assert not (output_dir / "llm_investigation_notes.json").exists()
    assert not (output_dir / "llm_investigation_notes.md").exists()
    trace = json.loads((output_dir / "investigation_trace.json").read_text(encoding="utf-8"))
    assert "llm" not in trace
    assert (output_dir / "investigation_report.md").exists()


def test_llm_notes_requires_input(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--llm-notes", "--issue", "Customer IDs", "--output-dir", str(tmp_path)])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "--llm-notes requires --input and --issue" in captured.err
    assert "Traceback" not in captured.err


def test_llm_notes_requires_issue(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as exc_info:
        cli.main(
            [
                "--llm-notes",
                "--input",
                "examples/customer_quality_snapshot.csv",
                "--output-dir",
                str(tmp_path),
            ]
        )

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "--llm-notes requires --issue" in captured.err
    assert "Traceback" not in captured.err


def test_safe_input_summary_excludes_forbidden_values(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "safe_summary"
    _run_default_artifacts(output_dir)
    artifacts = _load_artifacts(output_dir)

    summary = build_safe_input_summary(
        source_artifacts=_source_artifacts(output_dir),
        investigation_case=artifacts["investigation_case"],
        dataset_profile=artifacts["dataset_profile"],
        evidence_ledger=artifacts["evidence_ledger"],
        hypothesis_tracker=artifacts["hypothesis_tracker"],
        investigation_findings=artifacts["investigation_findings"],
    )

    assert summary["artifact_type"] == "llm_safe_input_summary"
    assert summary["issue"]["issue_type"] == "duplicate_key"
    assert "evidence_summary" in summary
    assert "hypothesis_summary" in summary
    assert "findings_summary" in summary
    serialized = json.dumps(summary)
    assert "avery@example.test" not in serialized
    assert "CUST-001" not in serialized
    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in serialized


def test_generate_llm_notes_with_fake_client_writes_valid_artifacts(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "fake_llm"
    _run_default_artifacts(output_dir)
    artifacts = _load_artifacts(output_dir)
    fake = FakeClient(_valid_notes_response())

    result = generate_llm_notes(
        output_dir=output_dir,
        model="fake-model",
        artifacts=_source_artifacts(output_dir),
        investigation_case=artifacts["investigation_case"],
        dataset_profile=artifacts["dataset_profile"],
        evidence_ledger=artifacts["evidence_ledger"],
        hypothesis_tracker=artifacts["hypothesis_tracker"],
        investigation_findings=artifacts["investigation_findings"],
        client=fake,
    )

    assert result["status"] == "completed"
    notes = json.loads((output_dir / "llm_investigation_notes.json").read_text(encoding="utf-8"))
    assert notes["llm_status"] == "completed"
    assert notes["validation"]["status"] == "passed"
    assert (output_dir / "llm_safe_input_summary.json").exists()
    markdown = (output_dir / "llm_investigation_notes.md").read_text(encoding="utf-8")
    assert "# Optional LLM Investigation Notes" in markdown
    assert fake.prompts


def test_cli_successful_mocked_llm_updates_case_and_trace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "cli_fake_llm"

    def fake_generate_llm_notes(**kwargs: Any) -> dict[str, Path | str | None]:
        out = kwargs["output_dir"]
        safe = out / "llm_safe_input_summary.json"
        notes = out / "llm_investigation_notes.json"
        md = out / "llm_investigation_notes.md"
        safe.write_text('{"artifact_type":"llm_safe_input_summary"}\n', encoding="utf-8")
        notes.write_text(
            '{"artifact_type":"llm_investigation_notes","llm_status":"completed","validation":{"status":"passed"}}\n',
            encoding="utf-8",
        )
        md.write_text("# Optional LLM Investigation Notes\n", encoding="utf-8")
        return {
            "status": "completed",
            "safe_input_summary_path": safe,
            "notes_json_path": notes,
            "notes_markdown_path": md,
        }

    monkeypatch.setattr(cli, "generate_llm_notes", fake_generate_llm_notes)

    assert cli.main(
        [
            "--input",
            "examples/customer_quality_snapshot.csv",
            "--issue",
            "Customer IDs have started duplicating",
            "--llm-notes",
            "--output-dir",
            str(output_dir),
        ]
    ) == 0

    case = json.loads((output_dir / "investigation_case.json").read_text(encoding="utf-8"))
    trace = json.loads((output_dir / "investigation_trace.json").read_text(encoding="utf-8"))
    assert case["workflow"]["status"] == "llm_notes_written"
    assert "llm_safe_input_summary" in case["artifacts"]
    assert trace["status"] == "llm_notes_written"
    assert trace["llm"]["requested"] is True
    assert trace["llm"]["status"] == "completed"
    assert (output_dir / "investigation_report.md").exists()


def test_cli_successful_mocked_baseline_llm_notes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "cli_fake_baseline_llm"

    def fake_generate_llm_notes(**kwargs: Any) -> dict[str, Path | str | None]:
        assert kwargs["baseline_profile"] is not None
        assert kwargs["baseline_comparison"] is not None
        out = kwargs["output_dir"]
        safe = out / "llm_safe_input_summary.json"
        notes = out / "llm_investigation_notes.json"
        md = out / "llm_investigation_notes.md"
        safe.write_text('{"run_context":{"baseline_available":true}}\n', encoding="utf-8")
        notes.write_text('{"llm_status":"completed","validation":{"status":"passed"}}\n', encoding="utf-8")
        md.write_text("# Optional LLM Investigation Notes\n", encoding="utf-8")
        return {
            "status": "completed",
            "safe_input_summary_path": safe,
            "notes_json_path": notes,
            "notes_markdown_path": md,
        }

    monkeypatch.setattr(cli, "generate_llm_notes", fake_generate_llm_notes)

    assert cli.main(
        [
            "--input",
            "examples/customer_quality_snapshot.csv",
            "--baseline",
            "examples/customer_quality_snapshot_baseline.csv",
            "--issue",
            "Nulls increased in the customer email field",
            "--llm-notes",
            "--output-dir",
            str(output_dir),
        ]
    ) == 0

    summary = json.loads((output_dir / "llm_safe_input_summary.json").read_text(encoding="utf-8"))
    trace = json.loads((output_dir / "investigation_trace.json").read_text(encoding="utf-8"))
    assert summary["run_context"]["baseline_available"] is True
    assert "baseline_profile" in trace["artifacts"]
    assert trace["llm"]["status"] == "completed"


def test_invalid_json_response_writes_safe_failure_artifact(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "invalid_json"
    _run_default_artifacts(output_dir)
    artifacts = _load_artifacts(output_dir)

    result = generate_llm_notes(
        output_dir=output_dir,
        model="fake-model",
        artifacts=_source_artifacts(output_dir),
        investigation_case=artifacts["investigation_case"],
        dataset_profile=artifacts["dataset_profile"],
        evidence_ledger=artifacts["evidence_ledger"],
        hypothesis_tracker=artifacts["hypothesis_tracker"],
        investigation_findings=artifacts["investigation_findings"],
        client=FakeClient("not-json with CUST-001"),
    )

    assert result["status"] == "failed_validation"
    notes = json.loads((output_dir / "llm_investigation_notes.json").read_text(encoding="utf-8"))
    assert notes["llm_status"] == "failed_validation"
    assert notes["validation"]["status"] == "failed"
    assert "CUST-001" not in json.dumps(notes)
    assert not (output_dir / "llm_investigation_notes.md").exists()


def test_forbidden_llm_output_fails_validation() -> None:
    notes, errors = parse_and_validate_notes(
        json.dumps(
            {
                "review_summary": "root cause identified for CUST-001",
                "suggested_follow_up_questions": [],
                "suggested_human_checks": [],
                "communication_notes": [],
                "limitations_to_keep_visible": [],
            }
        )
    )

    assert notes == {}
    assert any("blocked" in error for error in errors)


def test_llm_prompt_safety(tmp_path: Path) -> None:
    pytest.importorskip("pandas")
    output_dir = tmp_path / "prompt_safety"
    _run_default_artifacts(output_dir)
    artifacts = _load_artifacts(output_dir)
    summary = build_safe_input_summary(
        source_artifacts=_source_artifacts(output_dir),
        investigation_case=artifacts["investigation_case"],
        dataset_profile=artifacts["dataset_profile"],
        evidence_ledger=artifacts["evidence_ledger"],
        hypothesis_tracker=artifacts["hypothesis_tracker"],
        investigation_findings=artifacts["investigation_findings"],
    )

    prompt = build_llm_notes_prompt(summary)

    assert "avery@example.test" not in prompt
    assert "CUST-001" not in prompt
    assert "Do not identify root cause" in prompt
    assert "Return JSON only" in prompt


def test_openai_client_missing_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    from data_quality_investigation_workflow.errors import WorkflowUserError
    from data_quality_investigation_workflow.llm_client import OpenAIResponsesNotesClient

    def fake_import_module(name: str):
        if name == "openai":
            raise ImportError("missing")
        return importlib.import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(WorkflowUserError) as exc_info:
        OpenAIResponsesNotesClient()

    assert "Optional LLM notes require the 'openai' package" in str(exc_info.value)
    assert "llm extra" in str(exc_info.value)


def test_openai_client_missing_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib
    import types

    from data_quality_investigation_workflow.errors import WorkflowUserError
    from data_quality_investigation_workflow.llm_client import OpenAIResponsesNotesClient

    fake_openai = types.SimpleNamespace(OpenAI=lambda *args, **kwargs: object())

    def fake_import_module(name: str):
        if name == "openai":
            return fake_openai
        return importlib.import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(WorkflowUserError) as exc_info:
        OpenAIResponsesNotesClient()

    assert "OPENAI_API_KEY is required" in str(exc_info.value)
