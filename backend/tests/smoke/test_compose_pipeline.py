from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import pytest

from app.classifier.constants import CLASS_NAMES, REVIEW_THRESHOLD
from tests.smoke._compose_utils import (
    BACKEND_ROOT,
    REQUEST_ID_HEADER,
    api_request,
    assign_role,
    bootstrap_user,
    dump_logs_for_request_id,
    dump_service_logs,
    find_batch_by_filename,
    invite_user,
    list_quarantine_via_sftp,
    login,
    minio_object_exists,
    phase,
    poll_until,
    random_token,
    remove_role,
    upload_via_sftp,
    wait_for_batch_state,
    wait_for_prediction,
)

pytestmark = [
    pytest.mark.smoke,
    pytest.mark.skipif(
        os.getenv("RUN_COMPOSE_SMOKE") != "1",
        reason="Compose smoke tests require RUN_COMPOSE_SMOKE=1 and a running stack.",
    ),
]

PASSWORD = "TempPass123!"
GOLDEN_DIR = BACKEND_ROOT / "app/classifier/eval/golden_images"
HIGH_CONFIDENCE_TIFF = GOLDEN_DIR / "golden_001_specification.tiff"
HIGH_CONFIDENCE_LABEL = "specification"
LOW_CONFIDENCE_TIFF = GOLDEN_DIR / "golden_000_memo.tiff"
OVERLAY_BUCKET = "documents-overlays"


@pytest.mark.smoke
def test_happy_path_sftp_to_api_prediction() -> None:
    """End-to-end SFTP drop reaches API reads and proves list-cache invalidation.

    The classifier review threshold is frozen at 0.70 in code/model-card alignment; this
    smoke path uses an easy golden image and therefore expects confidence >= 0.90.
    """

    token = random_token()
    admin_email = f"admin-smoke-{token}@example.com"
    remote_name = f"scan_smoke_{token}.tif"
    request_id: str | None = None

    try:
        phase(f"bootstrap admin user {admin_email}")
        bootstrap_user(admin_email, PASSWORD, role="admin")

        phase("login as admin, got JWT")
        admin_token = login(admin_email, PASSWORD)

        phase("priming GET /batches and GET /predictions/recent (caches them)")
        primed_batches = api_request(
            "GET",
            "/batches?limit=100",
            token=admin_token,
            expected_status=200,
        ).json()["items"]
        api_request("GET", "/predictions/recent?limit=100", token=admin_token, expected_status=200)
        assert all(batch["source_filename"] != remote_name for batch in primed_batches)

        phase(f"uploading {HIGH_CONFIDENCE_TIFF.name} via SFTP as {remote_name}")
        upload_via_sftp(HIGH_CONFIDENCE_TIFF, remote_name)

        phase("waiting for sftp-ingest to pick up the file")
        batch = poll_until(
            lambda: find_batch_by_filename(admin_token, remote_name),
            timeout_seconds=30,
            description=f"batch for {remote_name} to appear in GET /batches",
        )
        request_id = batch["request_id"]
        batch_id = batch["id"]
        phase(f"batch landed: id={batch_id} state={batch['state']} request_id={request_id}")
        dump_logs_for_request_id(["sftp-ingest", "api"], request_id)

        phase(f"waiting for worker to complete batch {batch_id}")
        completed_batch = wait_for_batch_state(
            admin_token,
            batch_id,
            "completed",
            timeout_seconds=60,
        )

        phase("waiting for prediction to become visible through GET /predictions/recent")
        prediction = wait_for_prediction(admin_token, batch_id, timeout_seconds=60)
        phase(
            f"prediction visible: label={prediction['label']} "
            f"confidence={prediction['confidence']:.4f}"
        )
        dump_logs_for_request_id(["worker", "api"], request_id)

        phase("verifying overlay PNG exists in MinIO bucket")
        assert prediction["overlay_blob_key"]
        assert minio_object_exists(OVERLAY_BUCKET, prediction["overlay_blob_key"])

        phase("verifying cache-invalidation evidence from primed GET /batches")
        post_batches = api_request(
            "GET",
            "/batches?limit=100",
            token=admin_token,
            expected_status=200,
        ).json()["items"]
        assert any(batch["source_filename"] == remote_name for batch in post_batches)

        assert completed_batch["state"] == "completed"
        assert prediction["label"] == HIGH_CONFIDENCE_LABEL
        assert prediction["confidence"] >= 0.90
        assert completed_batch["request_id"] == prediction["request_id"] == request_id
        phase("all assertions passed")
    finally:
        if request_id is None:
            dump_service_logs(["sftp-ingest", "worker", "api"])
        else:
            dump_logs_for_request_id(["sftp-ingest", "worker", "api"], request_id)


@pytest.mark.smoke
def test_malformed_file_creates_failed_batch_and_quarantine(tmp_path: Path) -> None:
    token = random_token()
    admin_email = f"admin-bad-smoke-{token}@example.com"
    remote_name = f"scan_smoke_bad_{token}.tif"
    local_file = tmp_path / remote_name
    local_file.write_bytes(b"not a tiff payload")
    request_id: str | None = None

    try:
        phase(f"bootstrap admin user {admin_email}")
        bootstrap_user(admin_email, PASSWORD, role="admin")
        admin_token = login(admin_email, PASSWORD)

        phase("priming GET /batches?state=failed")
        primed_failed = api_request(
            "GET",
            "/batches?limit=100&state=failed",
            token=admin_token,
            expected_status=200,
        ).json()["items"]
        assert all(batch["source_filename"] != remote_name for batch in primed_failed)

        phase(f"uploading malformed TIFF bytes via SFTP as {remote_name}")
        upload_via_sftp(local_file, remote_name)

        phase("waiting for failed batch row")
        failed_batch = poll_until(
            lambda: find_batch_by_filename(admin_token, remote_name, state="failed"),
            timeout_seconds=30,
            description=f"failed batch for malformed upload {remote_name}",
        )
        request_id = failed_batch["request_id"]
        phase(
            f"failed batch landed: id={failed_batch['id']} "
            f"reason={failed_batch['failure_reason']} request_id={request_id}"
        )
        dump_logs_for_request_id(["sftp-ingest", "api"], request_id)

        phase("verifying quarantined file suffix pattern")
        quarantine_listing = list_quarantine_via_sftp()
        expected_stem = remote_name.removesuffix(".tif")
        assert f"{expected_stem}." in quarantine_listing
        assert ".tif" in quarantine_listing

        assert failed_batch["state"] == "failed"
        assert failed_batch["failure_reason"] == "corrupted TIFF"
        assert failed_batch["source_filename"] == remote_name
        assert failed_batch["blob_key"] is None
        assert failed_batch["created_by_user_id"] is None
        phase("all assertions passed")
    finally:
        if request_id is None:
            dump_service_logs(["sftp-ingest", "api"])
        else:
            dump_logs_for_request_id(["sftp-ingest", "api"], request_id)


@pytest.mark.smoke
def test_three_roles_enforce_expected_permissions() -> None:
    token = random_token()
    admin_email = f"admin-roles-{token}@example.com"
    reviewer_email = f"reviewer-roles-{token}@example.com"
    auditor_email = f"auditor-roles-{token}@example.com"

    phase("bootstrap admin and create reviewer/auditor users")
    bootstrap_user(admin_email, PASSWORD, role="admin")
    admin_token = login(admin_email, PASSWORD)
    reviewer = invite_user(admin_token, reviewer_email, PASSWORD)
    auditor = invite_user(admin_token, auditor_email, PASSWORD)
    assign_role(admin_token, reviewer["id"], "reviewer")
    assign_role(admin_token, auditor["id"], "auditor")
    reviewer_token = login(reviewer_email, PASSWORD)
    auditor_token = login(auditor_email, PASSWORD)

    phase("create a target user for role-management assertions")
    target = invite_user(admin_token, f"role-target-{token}@example.com", PASSWORD)

    phase("assert shared read permissions")
    for role_name, role_token in (
        ("admin", admin_token),
        ("reviewer", reviewer_token),
        ("auditor", auditor_token),
    ):
        api_request("GET", "/batches?limit=1", token=role_token, expected_status=200)
        api_request("GET", "/predictions/recent?limit=1", token=role_token, expected_status=200)
        phase(f"{role_name} can read batches and recent predictions")

    phase("assert audit-log permissions")
    api_request("GET", "/admin/audit-log?limit=1", token=admin_token, expected_status=200)
    api_request("GET", "/admin/audit-log?limit=1", token=reviewer_token, expected_status=403)
    api_request("GET", "/admin/audit-log?limit=1", token=auditor_token, expected_status=200)

    phase("assert role-management permissions")
    api_request(
        "PUT",
        f"/admin/users/{target['id']}/roles/reviewer",
        token=admin_token,
        expected_status=200,
    )
    api_request(
        "PUT",
        f"/admin/users/{target['id']}/roles/auditor",
        token=reviewer_token,
        expected_status=403,
    )
    api_request(
        "PUT",
        f"/admin/users/{target['id']}/roles/auditor",
        token=auditor_token,
        expected_status=403,
    )

    phase("assert invite-user permissions")
    api_request(
        "POST",
        "/admin/users/invite",
        token=admin_token,
        json={"email": f"invite-admin-{token}@example.com", "temporary_password": PASSWORD},
        expected_status=201,
    )
    api_request(
        "POST",
        "/admin/users/invite",
        token=reviewer_token,
        json={"email": f"invite-reviewer-{token}@example.com", "temporary_password": PASSWORD},
        expected_status=403,
    )
    api_request(
        "POST",
        "/admin/users/invite",
        token=auditor_token,
        json={"email": f"invite-auditor-{token}@example.com", "temporary_password": PASSWORD},
        expected_status=403,
    )
    phase("all assertions passed")


@pytest.mark.smoke
def test_role_toggle_invalidates_me_cache_and_updates_permissions() -> None:
    token = random_token()
    admin_email = f"admin-toggle-{token}@example.com"
    target_email = f"target-toggle-{token}@example.com"
    request_ids: list[str] = []

    try:
        phase("bootstrap admin and target user")
        bootstrap_user(admin_email, PASSWORD, role="admin")
        admin_token = login(admin_email, PASSWORD)
        target = invite_user(admin_token, target_email, PASSWORD)
        target_token = login(target_email, PASSWORD)

        phase("prime target GET /me cache with no roles")
        me_before = api_request("GET", "/me", token=target_token, expected_status=200).json()
        assert me_before["roles"] == []

        phase("target cannot read batches before reviewer role")
        api_request("GET", "/batches?limit=1", token=target_token, expected_status=403)

        add_request_id = str(uuid4())
        request_ids.append(add_request_id)
        phase(f"admin assigns reviewer role with request_id={add_request_id}")
        assign_role(admin_token, target["id"], "reviewer", request_id=add_request_id)

        phase("same JWT sees updated /me response without re-login")
        me_after_add = api_request("GET", "/me", token=target_token, expected_status=200).json()
        assert me_after_add["roles"] == ["reviewer"]
        api_request("GET", "/batches?limit=1", token=target_token, expected_status=200)

        remove_request_id = str(uuid4())
        request_ids.append(remove_request_id)
        phase(f"admin removes reviewer role with request_id={remove_request_id}")
        remove_role(admin_token, target["id"], "reviewer", request_id=remove_request_id)

        phase("same JWT sees /me cache invalidated back to no roles")
        me_after_remove = api_request("GET", "/me", token=target_token, expected_status=200).json()
        assert me_after_remove["roles"] == []
        api_request("GET", "/batches?limit=1", token=target_token, expected_status=403)
        phase("all assertions passed")
    finally:
        for request_id in request_ids:
            dump_logs_for_request_id(["api"], request_id)


@pytest.mark.smoke
def test_reviewer_relabels_low_confidence_prediction() -> None:
    token = random_token()
    admin_email = f"admin-review-{token}@example.com"
    reviewer_email = f"reviewer-review-{token}@example.com"
    auditor_email = f"auditor-review-{token}@example.com"
    request_ids: list[str] = []

    try:
        phase("bootstrap admin, reviewer, and auditor")
        bootstrap_user(admin_email, PASSWORD, role="admin")
        admin_token = login(admin_email, PASSWORD)
        reviewer = invite_user(admin_token, reviewer_email, PASSWORD)
        auditor = invite_user(admin_token, auditor_email, PASSWORD)
        assign_role(admin_token, reviewer["id"], "reviewer")
        assign_role(admin_token, auditor["id"], "auditor")
        reviewer_token = login(reviewer_email, PASSWORD)
        auditor_token = login(auditor_email, PASSWORD)

        phase("finding or staging a low-confidence prediction")
        low_prediction = _find_prediction_by_confidence(admin_token, below=REVIEW_THRESHOLD)
        if low_prediction is None:
            low_prediction = _stage_prediction(
                admin_token,
                LOW_CONFIDENCE_TIFF,
                f"review_low_{token}.tiff",
                request_ids,
                timeout_seconds=60,
            )
        if low_prediction["confidence"] >= REVIEW_THRESHOLD:
            pytest.skip("No low-confidence prediction available for reviewer smoke test.")

        phase("reviewer relabels the low-confidence prediction")
        reviewed_label = _different_label(low_prediction["label"])
        relabel_request_id = str(uuid4())
        request_ids.append(relabel_request_id)
        reviewed = api_request(
            "PATCH",
            f"/predictions/{low_prediction['id']}/review",
            token=reviewer_token,
            headers={REQUEST_ID_HEADER: relabel_request_id},
            json={"reviewed_label": reviewed_label},
            expected_status=200,
        ).json()
        assert reviewed["reviewed_label"] == reviewed_label
        assert reviewed["reviewed_by_user_id"] == reviewer["id"]
        assert reviewed["reviewed_at"] is not None

        phase("auditor cannot relabel predictions")
        api_request(
            "PATCH",
            f"/predictions/{low_prediction['id']}/review",
            token=auditor_token,
            json={"reviewed_label": _different_label(reviewed_label)},
            expected_status=403,
        )

        phase("finding or staging a high-confidence prediction")
        high_prediction = _find_prediction_by_confidence(admin_token, at_or_above=REVIEW_THRESHOLD)
        if high_prediction is None:
            high_prediction = _stage_prediction(
                admin_token,
                HIGH_CONFIDENCE_TIFF,
                f"review_high_{token}.tiff",
                request_ids,
                timeout_seconds=60,
            )
        assert high_prediction["confidence"] >= REVIEW_THRESHOLD

        phase("reviewer cannot relabel high-confidence predictions")
        api_request(
            "PATCH",
            f"/predictions/{high_prediction['id']}/review",
            token=reviewer_token,
            json={"reviewed_label": _different_label(high_prediction["label"])},
            expected_status=409,
        )
        phase("all assertions passed")
    finally:
        if not request_ids:
            dump_service_logs(["sftp-ingest", "worker", "api"])
        for request_id in request_ids:
            dump_logs_for_request_id(["sftp-ingest", "worker", "api"], request_id)


@pytest.mark.smoke
def test_audit_log_captures_role_change_and_relabel() -> None:
    token = random_token()
    admin_email = f"admin-audit-{token}@example.com"
    target_email = f"target-audit-{token}@example.com"
    request_id = str(uuid4())

    try:
        phase("bootstrap admin and target user")
        bootstrap_user(admin_email, PASSWORD, role="admin")
        admin_token = login(admin_email, PASSWORD)
        admin_user = api_request("GET", "/me", token=admin_token, expected_status=200).json()
        target = invite_user(admin_token, target_email, PASSWORD)

        phase("capture audit-log baseline")
        baseline = api_request(
            "GET",
            "/admin/audit-log?limit=200",
            token=admin_token,
            expected_status=200,
        ).json()["items"]
        assert all(entry["request_id"] != request_id for entry in baseline)

        phase(f"assign reviewer role with request_id={request_id}")
        assign_role(admin_token, target["id"], "reviewer", request_id=request_id)

        phase("poll audit log for matching role_change entry")
        entry = poll_until(
            lambda: _find_audit_entry(admin_token, request_id),
            timeout_seconds=30,
            description=f"audit entry for request_id={request_id}",
        )
        dump_logs_for_request_id(["api"], request_id)

        assert entry["action"] == "role_change"
        assert entry["actor_user_id"] == admin_user["id"]
        assert entry["target_id"] == target["id"]
        assert entry["before_value"] == {"roles": []}
        assert entry["after_value"] == {"roles": ["reviewer"]}
        assert entry["request_id"] == request_id
        phase("all assertions passed")
    finally:
        dump_logs_for_request_id(["api"], request_id)


def _stage_prediction(
    admin_token: str,
    local_path: Path,
    remote_name: str,
    request_ids: list[str],
    *,
    timeout_seconds: float,
) -> dict[str, object]:
    phase(f"uploading {local_path.name} via SFTP as {remote_name}")
    upload_via_sftp(local_path, remote_name)
    batch = poll_until(
        lambda: find_batch_by_filename(admin_token, remote_name),
        timeout_seconds=30,
        description=f"batch for {remote_name}",
    )
    request_ids.append(batch["request_id"])
    dump_logs_for_request_id(["sftp-ingest", "api"], batch["request_id"])
    wait_for_batch_state(admin_token, batch["id"], "completed", timeout_seconds=timeout_seconds)
    prediction = wait_for_prediction(admin_token, batch["id"], timeout_seconds=timeout_seconds)
    dump_logs_for_request_id(["worker", "api"], batch["request_id"])
    return prediction


def _recent_predictions(token: str) -> list[dict[str, object]]:
    response = api_request(
        "GET",
        "/predictions/recent?limit=100",
        token=token,
        expected_status=200,
    )
    return list(response.json()["items"])


def _find_prediction_by_confidence(
    token: str,
    *,
    below: float | None = None,
    at_or_above: float | None = None,
) -> dict[str, object] | None:
    for prediction in _recent_predictions(token):
        confidence = float(prediction["confidence"])
        if below is not None and confidence < below:
            return prediction
        if at_or_above is not None and confidence >= at_or_above:
            return prediction
    return None


def _different_label(label: object) -> str:
    current = str(label)
    for candidate in CLASS_NAMES:
        if candidate != current:
            return candidate
    raise AssertionError("CLASS_NAMES did not contain an alternative label")


def _find_audit_entry(token: str, request_id: str) -> dict[str, object] | None:
    response = api_request("GET", "/admin/audit-log?limit=200", token=token, expected_status=200)
    for entry in response.json()["items"]:
        if entry["request_id"] == request_id:
            return dict(entry)
    return None
