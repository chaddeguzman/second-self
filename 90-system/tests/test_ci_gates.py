"""Public CI policy tests for deterministic validation gates."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")


def test_public_validation_workflow_runs_each_required_gate_once():
    required = (
        "python -m pytest",
        "second_self validate --privacy",
        "second_self eval semantic --json",
        "second_self eval recall --json",
        "second_self eval safety --json",
        "certify_hermes.py --json",
        "generate-frontmatter-contract.py --check",
        "second_self wiki lint",
    )
    for command in required:
        assert WORKFLOW.count(command) == 1


def test_workflow_is_public_static_and_uses_python_312():
    assert 'python-version: "3.12"' in WORKFLOW
    assert "hermes-ready" not in WORKFLOW
    assert ".second-self.local.json" not in WORKFLOW
    assert "secrets." not in WORKFLOW
