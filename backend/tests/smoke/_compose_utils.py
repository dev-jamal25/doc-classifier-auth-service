from __future__ import annotations

import os
import secrets
import subprocess
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
API_BASE_URL = os.getenv("SMOKE_API_BASE_URL", "http://127.0.0.1:8000")
REQUEST_ID_HEADER = "X-Request-ID"

SFTP_HOST = os.getenv("SFTP_HOST", "127.0.0.1")
SFTP_PORT = os.getenv("SFTP_PORT", "2222")
SFTP_USERNAME = os.getenv("SFTP_USERNAME", "sftp-user")
SFTP_PASSWORD = os.getenv("SFTP_PASSWORD", "dev-sftp-password")


def phase(message: str) -> None:
    print(f"\n=== [smoke {_current_test_name()}] {message} ===", flush=True)


def random_token() -> str:
    return secrets.token_hex(4)


def bootstrap_user(email: str, password: str, role: str | None = None) -> None:
    _run_compose(
        [
            "exec",
            "-T",
            "api",
            "uv",
            "run",
            "python",
            "-m",
            "app.entrypoints.bootstrap_admin",
            "--email",
            email,
            "--password",
            password,
        ],
        timeout=120,
    )
    if role is None:
        return
    if role != "admin":
        raise ValueError(
            "bootstrap_user can only grant the admin role; use the API for other roles"
        )
    _run_compose(
        [
            "exec",
            "-T",
            "api",
            "uv",
            "run",
            "python",
            "-m",
            "app.entrypoints.bootstrap_admin_role",
            "--email",
            email,
        ],
        timeout=120,
    )


def login(email: str, password: str) -> str:
    response = httpx.post(
        f"{API_BASE_URL}/auth/login",
        data={"username": email, "password": password},
        timeout=10,
    )
    _assert_status(response, 200, "login")
    return str(response.json()["access_token"])


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def api_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    headers: dict[str, str] | None = None,
    expected_status: int | tuple[int, ...] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    request_headers = dict(headers or {})
    if token is not None:
        request_headers.update(auth_headers(token))
    response = httpx.request(
        method,
        f"{API_BASE_URL}{path}",
        headers=request_headers,
        timeout=10,
        **kwargs,
    )
    if expected_status is not None:
        _assert_status(response, expected_status, f"{method.upper()} {path}")
    return response


def invite_user(admin_token: str, email: str, password: str) -> dict[str, Any]:
    response = api_request(
        "POST",
        "/admin/users/invite",
        token=admin_token,
        json={"email": email, "temporary_password": password},
        expected_status=201,
    )
    return dict(response.json())


def assign_role(
    admin_token: str,
    user_id: str,
    role: str,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    headers = {REQUEST_ID_HEADER: request_id} if request_id is not None else None
    response = api_request(
        "PUT",
        f"/admin/users/{user_id}/roles/{role}",
        token=admin_token,
        headers=headers,
        expected_status=200,
    )
    return dict(response.json())


def remove_role(
    admin_token: str,
    user_id: str,
    role: str,
    *,
    request_id: str | None = None,
) -> dict[str, Any]:
    headers = {REQUEST_ID_HEADER: request_id} if request_id is not None else None
    response = api_request(
        "DELETE",
        f"/admin/users/{user_id}/roles/{role}",
        token=admin_token,
        headers=headers,
        expected_status=200,
    )
    return dict(response.json())


def upload_via_sftp(local_path: Path, remote_name: str) -> None:
    command = [
        "sshpass",
        "-p",
        SFTP_PASSWORD,
        "sftp",
        "-P",
        SFTP_PORT,
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        "UserKnownHostsFile=/dev/null",
        f"{SFTP_USERNAME}@{SFTP_HOST}",
    ]
    batch_input = f"put {local_path} /upload/{remote_name}\n"
    attempts: list[subprocess.CompletedProcess[str]] = []
    for attempt in range(1, 6):
        completed = _run_command(command, input_text=batch_input, timeout=60, check=False)
        if completed.returncode == 0:
            return
        attempts.append(completed)
        if attempt < 5:
            time.sleep(2)

    last_attempt = attempts[-1]
    if last_attempt.returncode != 0:
        raise AssertionError(
            "SFTP upload failed.\n"
            f"command: {' '.join(command)}\n"
            f"attempts: {len(attempts)}\n"
            f"stdout:\n{last_attempt.stdout}\n"
            f"stderr:\n{last_attempt.stderr}"
        )


def list_quarantine_via_sftp() -> str:
    completed = _run_compose(
        [
            "exec",
            "-T",
            "sftp",
            "find",
            f"/home/{SFTP_USERNAME}/upload/quarantine",
            "-maxdepth",
            "1",
            "-type",
            "f",
            "-printf",
            "%f\n",
        ],
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            "SFTP quarantine listing failed.\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return f"{completed.stdout}\n{completed.stderr}"


def poll_until[T](
    predicate: Callable[[], T | None],
    *,
    timeout_seconds: float,
    description: str,
    interval_seconds: float = 1.0,
) -> T:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result is not None:
            return result
        time.sleep(interval_seconds)
    raise TimeoutError(f"Timed out waiting for {description} after {timeout_seconds:.0f}s")


def find_batch_by_filename(
    token: str,
    source_filename: str,
    *,
    state: str | None = None,
) -> dict[str, Any] | None:
    query = "limit=100&offset=0"
    if state is not None:
        query = f"{query}&state={state}"
    response = api_request("GET", f"/batches?{query}", token=token, expected_status=200)
    for batch in response.json()["items"]:
        if batch["source_filename"] == source_filename:
            return dict(batch)
    return None


def wait_for_batch_state(
    token: str,
    batch_id: str,
    expected_state: str,
    *,
    timeout_seconds: float = 60,
) -> dict[str, Any]:
    def _predicate() -> dict[str, Any] | None:
        response = api_request("GET", f"/batches/{batch_id}", token=token)
        if response.status_code != 200:
            return None
        batch = dict(response.json())
        if batch["state"] == expected_state:
            return batch
        return None

    return poll_until(
        _predicate,
        timeout_seconds=timeout_seconds,
        description=f"batch {batch_id} to reach state={expected_state}",
    )


def wait_for_prediction(
    token: str,
    batch_id: str,
    *,
    timeout_seconds: float = 60,
) -> dict[str, Any]:
    def _predicate() -> dict[str, Any] | None:
        response = api_request("GET", "/predictions/recent?limit=100", token=token)
        if response.status_code != 200:
            return None
        for prediction in response.json()["items"]:
            if prediction["batch_id"] == batch_id:
                return dict(prediction)
        return None

    return poll_until(
        _predicate,
        timeout_seconds=timeout_seconds,
        description=f"prediction for batch {batch_id}",
    )


def minio_object_exists(bucket: str, key: str) -> bool:
    script = (
        'mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" '
        '> /dev/null && mc stat "local/$1/$2"'
    )
    completed = _run_compose(
        [
            "run",
            "--rm",
            "--entrypoint",
            "sh",
            "minio-init",
            "-c",
            script,
            "--",
            bucket,
            key.lstrip("/"),
        ],
        timeout=60,
        check=False,
    )
    return completed.returncode == 0


def dump_logs_for_request_id(
    services: list[str],
    request_id: str | None,
    *,
    tail: int = 200,
) -> None:
    if not request_id:
        return
    print(f"\n--- logs for request_id={request_id} ---", flush=True)
    for service in services:
        completed = _run_compose(
            ["logs", "--no-color", f"--tail={tail}", service],
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            print(f"[{service}] failed to read logs: {completed.stderr.strip()}", flush=True)
            continue
        for line in completed.stdout.splitlines():
            if request_id in line:
                print(f"[{service}] {line}", flush=True)


def dump_service_logs(services: list[str], *, tail: int = 120) -> None:
    print("\n--- recent service logs ---", flush=True)
    for service in services:
        completed = _run_compose(
            ["logs", "--no-color", f"--tail={tail}", service],
            timeout=30,
            check=False,
        )
        if completed.returncode != 0:
            print(f"[{service}] failed to read logs: {completed.stderr.strip()}", flush=True)
            continue
        print(f"===== {service} =====", flush=True)
        print(completed.stdout, flush=True)


def _run_compose(
    args: list[str],
    *,
    input_text: str | None = None,
    timeout: float = 60,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return _run_command(
        ["docker", "compose", *args],
        input_text=input_text,
        timeout=timeout,
        check=check,
        cwd=REPO_ROOT,
    )


def _run_command(
    command: list[str],
    *,
    input_text: str | None = None,
    timeout: float = 60,
    check: bool = True,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            input=input_text,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        raise AssertionError(f"Required CLI not found while running: {command[0]}") from exc

    if check and completed.returncode != 0:
        raise AssertionError(
            "Command failed.\n"
            f"command: {' '.join(command)}\n"
            f"returncode: {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    return completed


def _assert_status(
    response: httpx.Response,
    expected_status: int | tuple[int, ...],
    description: str,
) -> None:
    expected = (expected_status,) if isinstance(expected_status, int) else expected_status
    if response.status_code not in expected:
        raise AssertionError(
            f"Unexpected status for {description}: {response.status_code}, expected {expected}.\n"
            f"Response body:\n{response.text}"
        )


def _current_test_name() -> str:
    current = os.environ.get("PYTEST_CURRENT_TEST", "smoke")
    if "::" in current:
        current = current.rsplit("::", maxsplit=1)[-1]
    return current.split(" ", maxsplit=1)[0]
