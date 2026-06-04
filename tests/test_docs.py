from __future__ import annotations

import re
from pathlib import Path


README_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((docs/[^)]+)\)")


def test_readme_uses_stable_v1_language() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    folded = readme.casefold()

    assert "pr #8 status" not in folded
    assert "pr #9 status" not in folded
    assert "pr #10 status" not in folded
    assert "repository is at pr" not in folded
    assert "pr #" not in folded[:1500]
    assert "What to open first" in readme
    assert "Why there are several artifacts" in readme
    assert "The output is review material, not a verdict" in readme
    assert "Optional LLM notes are disabled by default" in readme
    assert "Human review remains" in readme
    assert "No LLM is used unless" in readme
    assert "investigation_report.md" in readme
    assert "llm_safe_input_summary.json" in readme


def test_readme_doc_links_exist() -> None:
    assert Path("docs/design_principles.md").exists()
    readme = Path("README.md").read_text(encoding="utf-8")
    links = README_LINK_PATTERN.findall(readme)

    assert "docs/design_principles.md" in links
    for link in links:
        assert Path(link).exists(), f"README links to missing doc: {link}"
