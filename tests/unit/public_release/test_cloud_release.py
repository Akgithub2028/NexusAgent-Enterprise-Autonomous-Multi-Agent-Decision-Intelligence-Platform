"""Release authorization, rollback and artifact gates without cloud mutations."""

import json

import pytest
from scripts import run_cloud_release as release
from scripts import verify_release_ci as ci
from scripts.add_live_demo_badge import badge

from decision_agent.ingestion.cloud_job import release_descriptor


@pytest.mark.parametrize("change", ["pending", "image", "gate", "measurement", "evidence"])
def test_incomplete_acceptance_cannot_promote(change):
    candidate = {"image": "digest", "measurement": {"status": "passed"}}
    accepted = {
        "schema_version": 1,
        "status": "approved",
        "image": "digest",
        "gates": {g: True for g in release.ACCEPTANCE_GATES},
        "evidence": ["recorded-results"],
    }
    release.require_acceptance(accepted, candidate)
    if change == "pending":
        accepted["status"] = "blocked"
    elif change == "image":
        accepted["image"] = "other"
    elif change == "gate":
        accepted["gates"]["sql_socket_and_denials"] = False
    elif change == "measurement":
        candidate["measurement"]["status"] = "failed"
    else:
        accepted["evidence"] = []
    with pytest.raises(ValueError):
        release.require_acceptance(accepted, candidate)


@pytest.mark.parametrize("failed", [False, True])
def test_ci_requires_exact_six_green_jobs(monkeypatch, failed):
    sha = "a" * 40
    monkeypatch.setenv("RELEASE_SHA", sha)
    jobs = [{"name": n, "conclusion": "success"} for n in ci.EXPECTED]
    if failed:
        jobs[0]["conclusion"] = "failure"
    values = iter(
        [
            json.dumps(
                [{"databaseId": 1, "headSha": sha, "event": "push", "conclusion": "success"}]
            ).encode(),
            json.dumps({"jobs": jobs}).encode(),
        ]
    )
    monkeypatch.setattr(ci.subprocess, "check_output", lambda *a, **kw: next(values))
    assert ci.main() == (2 if failed else 0)


@pytest.mark.parametrize("revision", ["old", None])
def test_rollback_uses_saved_revision_percentages(monkeypatch, revision):
    snapshot = {"metadata": {"name": "nexusagent"}, "status": {"traffic": []}}
    if revision:
        snapshot["status"]["traffic"] = [{"revisionName": revision, "percent": 100}]
    values = iter([snapshot, {"bindings": []}])
    monkeypatch.setattr(release, "capture", lambda *a: next(values))
    monkeypatch.setattr(release, "gcloud_json", lambda *a: {"bindings": []})
    calls = []
    monkeypatch.setattr(release, "command", lambda *a: calls.append(a))
    config = {
        "production_service": "nexusagent",
        "project": "project",
        "region": "us-west1",
        "release_bucket": "bucket",
    }
    if revision:
        release.rollback(config, "123")
        assert "old=100" in calls[0]
    else:
        with pytest.raises(ValueError):
            release.rollback(config, "123")
        assert calls == []


def test_blocked_public_record_makes_no_mutations(monkeypatch, tmp_path):
    manifest = {
        "corpus_release_id": "test",
        "collection": "nexus_test",
        "parents": 1,
        "children": 2,
    }
    image = "us-west1-docker.pkg.dev/project/repo/app@sha256:" + "a" * 64
    record = release_descriptor(manifest, image)
    monkeypatch.setattr(release, "capture", lambda *a: record)
    calls = []
    monkeypatch.setattr(release, "command", lambda *a: calls.append(a))
    with pytest.raises(ValueError):
        release.public_release(
            {"release_bucket": "bucket"}, image, manifest, tmp_path, "1", "2", {"status": "blocked"}
        )
    assert calls == []


def test_secret_snapshot_and_fake_badge_are_refused(tmp_path):
    snapshot = {
        "spec": {
            "template": {
                "spec": {
                    "containers": [
                        {"env": [{"name": "DECISION_AGENT_LLM_API_KEY", "value": "private"}]}
                    ]
                }
            }
        }
    }
    with pytest.raises(ValueError):
        release.save_snapshot(snapshot, tmp_path / "snapshot.json")
    assert not (tmp_path / "snapshot.json").exists()
    with pytest.raises(ValueError):
        badge('https://example.com/"bad')
    assert "Verified live synthetic demo" in badge("https://nexusagent-test.run.app")
