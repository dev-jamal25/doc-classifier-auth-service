from __future__ import annotations

import socket
import subprocess
import time
from collections.abc import Iterator
from contextlib import contextmanager

import httpx


def docker_available() -> bool:
    result = subprocess.run(
        ["docker", "version"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_port(host: str, port: int, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1.0):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for {host}:{port} to accept TCP connections.")


def wait_for_http(url: str, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code < 500:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for HTTP endpoint `{url}`.")


@contextmanager
def run_container(
    *,
    image: str,
    ports: dict[int, int],
    env: dict[str, str] | None = None,
    command: list[str] | None = None,
) -> Iterator[str]:
    args: list[str] = ["docker", "run", "-d", "--rm"]
    for host_port, container_port in ports.items():
        args.extend(["-p", f"{host_port}:{container_port}"])
    if env is not None:
        for key, value in env.items():
            args.extend(["-e", f"{key}={value}"])
    args.append(image)
    if command is not None:
        args.extend(command)

    result = subprocess.run(args, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start container `{image}`. stderr: {result.stderr.strip()}")
    container_id = result.stdout.strip()

    try:
        yield container_id
    finally:
        subprocess.run(
            ["docker", "rm", "-f", container_id],
            capture_output=True,
            text=True,
            check=False,
        )
