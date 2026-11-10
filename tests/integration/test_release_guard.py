"""Local Git and source/CI rejection cases; no provider success is simulated."""

import base64
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from release_guard import committed_source, manifest, validate_jobs, verify_source_tree


def test_release_source_rejects_dirty_or_untracked_code_but_preserves_recording(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("GITHUB_SHA", raising=False)

    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=tmp_path, stderr=subprocess.STDOUT, text=True
        ).strip()

    git("init")
    git("config", "user.name", "Synthetic release test")
    git("config", "user.email", "release@synthetic.invalid")
    source = tmp_path / "app.py"
    source.write_text("COMMITTED_SOURCE = True\n")
    git("add", "app.py")
    git("commit", "-m", "Synthetic release fixture")
    folder = tmp_path / "docs"
    folder.mkdir()
    recording = folder / "New Recording 20.m4a"
    recording.write_bytes(b"SYNTHETIC_RECORDING_PRESERVATION")
    assert committed_source(tmp_path) == git("rev-parse", "HEAD")
    source.write_text("UNREVIEWED_SOURCE = True\n")
    with pytest.raises(ValueError):
        committed_source(tmp_path)
    git("checkout", "--", "app.py")
    extra = tmp_path / "unexpected.py"
    extra.write_text("UNTRACKED = True\n")
    with pytest.raises(ValueError):
        committed_source(tmp_path)
    extra.unlink()
    monkeypatch.setenv("GITHUB_SHA", "0" * 40)
    with pytest.raises(ValueError):
        committed_source(tmp_path)
    assert recording.read_bytes() == b"SYNTHETIC_RECORDING_PRESERVATION"


@pytest.mark.parametrize(
    "state,conclusion",
    [("completed", "failure"), ("completed", "cancelled"), ("in_progress", None)],
)
def test_ci_guard_rejects_incomplete_or_failed_required_job(state, conclusion):
    jobs = [
        {"name": name, "status": "completed", "conclusion": "success"}
        for name in ("python", "web", "secrets-scan")
    ]
    jobs[0].update(status=state, conclusion=conclusion)
    with pytest.raises(ValueError):
        validate_jobs(jobs)
    with pytest.raises(ValueError):
        validate_jobs(jobs[1:])


def test_source_guard_detects_missing_and_changed_dependency_inputs():
    files = [
        {"file": name, "data": base64.b64encode(data).decode()}
        for name, data in [("app.py", b"QUALIFIED_SOURCE"), ("requirements.txt", b"PINNED_GRAPH")]
    ]
    expected = manifest(files)
    tree = [
        {
            "name": "src",
            "children": [{"name": item["file"], "uid": item["sha1"]} for item in expected],
        }
    ]
    assert verify_source_tree(expected, tree) == 2
    tree[0]["children"][1]["uid"] = "0" * 40
    with pytest.raises(ValueError):
        verify_source_tree(expected, tree)
    with pytest.raises(ValueError):
        verify_source_tree(expected, [])
