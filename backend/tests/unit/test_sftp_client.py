from __future__ import annotations

from app.infra.sftp import SftpClient


def test_health_check_closes_failed_connection(monkeypatch) -> None:
    client = SftpClient(
        host="127.0.0.1",
        port=2222,
        username="user",
        password="password",
    )
    closed = False

    def _raise_connection_error():
        raise RuntimeError("banner not ready")

    def _close() -> None:
        nonlocal closed
        closed = True

    monkeypatch.setattr(client, "_client", _raise_connection_error)
    monkeypatch.setattr(client, "close", _close)

    assert client.health_check() is False
    assert closed is True
