"""Fail-closed exact-commit/source checks for the existing Vercel projects."""

import base64
import hashlib
import os
import subprocess

import httpx
from cloud_credentials import github_token

REPOSITORY = "prolificintelligence/loveworld-care"


def committed_source(root):
    git = ["git", "-c", "safe.directory=" + root.as_posix()]
    for arguments in (["diff", "--exit-code"], ["diff", "--cached", "--exit-code"]):
        if subprocess.run(git + arguments, cwd=root, capture_output=True, check=False).returncode:
            raise ValueError("Commit tracked changes before release")
    pending = subprocess.check_output(
        git + ["ls-files", "--others", "--exclude-standard"], cwd=root, text=True
    ).splitlines()
    if any(path != "docs/New Recording 20.m4a" for path in pending):
        raise ValueError("Untracked release inputs require explicit reconciliation")
    commit = subprocess.check_output(git + ["rev-parse", "HEAD"], cwd=root, text=True).strip()
    if os.environ.get("GITHUB_SHA", commit) != commit:
        raise ValueError("Runner and checkout commits differ")
    return commit


def successful_ci(commit):
    credential = os.environ.get("GITHUB_TOKEN") or github_token()
    with httpx.Client(headers={"Authorization": "Bearer " + credential}, timeout=45) as client:
        response = client.get(
            f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/ci.yml/runs",
            params={"head_sha": commit, "per_page": 20},
        )
        response.raise_for_status()
        runs = response.json()["workflow_runs"]
        # A later failed/cancelled attempt must not be hidden by an earlier pass.
        if not runs or runs[0]["head_sha"] != commit or runs[0]["conclusion"] != "success":
            raise ValueError("The exact source commit must have successful CI")
        run = runs[0]
        response = client.get(run["jobs_url"])
        response.raise_for_status()
        jobs = response.json()["jobs"]
        validate_jobs(jobs)
        return {
            "commit": commit,
            "run_id": run["id"],
            "url": run["html_url"],
            "conclusion": "success",
        }


def validate_jobs(jobs):
    completed = {
        job["name"]
        for job in jobs
        if job["status"] == "completed" and job["conclusion"] == "success"
    }
    if not {"python", "web", "secrets-scan"}.issubset(completed):
        raise ValueError("Python, web and secret-scan jobs must all pass")


def manifest(files):
    return [
        {
            "file": entry["file"],
            "sha1": hashlib.sha1(base64.b64decode(entry["data"])).hexdigest(),
            "sha256": hashlib.sha256(base64.b64decode(entry["data"])).hexdigest(),
        }
        for entry in files
    ]


def walk(nodes, parent=""):
    for node in nodes:
        path = parent + node["name"]
        yield path, node
        yield from walk(node.get("children", []), path + "/")


def verify_source_tree(expected, tree):
    nodes = dict(walk(tree if isinstance(tree, list) else tree["files"]))
    for item in expected:
        node = nodes.get("src/" + item["file"]) or nodes.get(item["file"])
        if not node or node.get("uid") != item["sha1"]:
            raise ValueError("Deployment source inventory does not match committed release inputs")
    return len(expected)
