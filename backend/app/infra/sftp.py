from __future__ import annotations

import posixpath
import time
from datetime import UTC, datetime
from stat import S_ISREG

import paramiko

from app.domain.sftp import FileInfo


class SftpError(RuntimeError):
    """Raised when SFTP operations fail."""


class SftpClient:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        quarantine_dir: str = "/upload/quarantine",
        timeout_seconds: int = 10,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._quarantine_dir = quarantine_dir
        self._timeout_seconds = timeout_seconds
        self._ssh_client: paramiko.SSHClient | None = None
        self._sftp_client: paramiko.SFTPClient | None = None

    def close(self) -> None:
        """Release the SSH transport. Safe to call multiple times."""
        if self._sftp_client is not None:
            try:
                self._sftp_client.close()
            except Exception:
                pass
        if self._ssh_client is not None:
            try:
                self._ssh_client.close()
            except Exception:
                pass
        self._sftp_client = None
        self._ssh_client = None

    def _connect(self) -> None:
        if self._ssh_client is not None and self._sftp_client is not None:
            transport = self._ssh_client.get_transport()
            if transport is not None and transport.is_active():
                return

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=self._host,
            port=self._port,
            username=self._username,
            password=self._password,
            timeout=self._timeout_seconds,
            look_for_keys=False,
            allow_agent=False,
        )
        self._ssh_client = ssh_client
        self._sftp_client = ssh_client.open_sftp()

    def _client(self) -> paramiko.SFTPClient:
        try:
            self._connect()
        except Exception as exc:
            raise SftpError("Failed to establish SFTP connection.") from exc
        if self._sftp_client is None:
            raise SftpError("Failed to initialize SFTP client.")
        return self._sftp_client

    @staticmethod
    def _to_file_info(*, directory: str, attr: paramiko.SFTPAttributes) -> FileInfo:
        name = attr.filename
        path = posixpath.join(directory.rstrip("/") or "/", name)
        mtime_epoch = attr.st_mtime

        if mtime_epoch is None:
            raise SftpError(f"SFTP file `{attr.filename}` has no mtime; cannot dedup.")

        return FileInfo(
            name=name,
            path=path,
            size=attr.st_size,
            mtime=datetime.fromtimestamp(mtime_epoch, tz=UTC),
        )

    def list_new_files(self, remote_dir: str) -> list[FileInfo]:
        try:
            attrs = self._client().listdir_attr(remote_dir)
            files = [
                self._to_file_info(directory=remote_dir, attr=attr)
                for attr in attrs
                if S_ISREG(attr.st_mode)
            ]
            files.sort(key=lambda item: item.mtime)
            return files
        except Exception as exc:
            raise SftpError(f"Failed listing SFTP directory `{remote_dir}`.") from exc

    def stat(self, remote_path: str) -> FileInfo:
        try:
            attr = self._client().stat(remote_path)
            mtime_epoch = attr.st_mtime or 0
            return FileInfo(
                name=posixpath.basename(remote_path),
                path=remote_path,
                size=attr.st_size,
                mtime=datetime.fromtimestamp(mtime_epoch, tz=UTC),
            )
        except Exception as exc:
            raise SftpError(f"Failed stat for SFTP path `{remote_path}`.") from exc

    def download_file(self, remote_path: str) -> bytes:
        try:
            with self._client().open(remote_path, mode="rb") as file_obj:
                return file_obj.read()
        except Exception as exc:
            raise SftpError(f"Failed downloading SFTP path `{remote_path}`.") from exc

    def _ensure_remote_dir(self, remote_dir: str) -> None:
        sftp = self._client()
        path_parts = [part for part in remote_dir.strip("/").split("/") if part]
        current = "/"
        for part in path_parts:
            current = posixpath.join(current, part)
            try:
                sftp.stat(current)
            except FileNotFoundError:
                sftp.mkdir(current)

    def move_to_quarantine(self, remote_path: str, *, request_id: str | None = None) -> None:
        sftp = self._client()
        original_name = posixpath.basename(remote_path)
        quarantine_dir = self._quarantine_dir.rstrip("/") or "/quarantine"

        # Avoid filename collisions when the same bad filename arrives more than once.
        suffix = request_id if request_id else str(int(time.time()))
        stem, dot, ext = original_name.rpartition(".")
        if dot:
            target_name = f"{stem}.{suffix}.{ext}"
        else:
            target_name = f"{original_name}.{suffix}"

        try:
            self._ensure_remote_dir(quarantine_dir)
            target = posixpath.join(quarantine_dir, target_name)
            try:
                sftp.posix_rename(remote_path, target)
            except OSError:
                # Not all SFTP servers support OpenSSH posix_rename extension.
                sftp.rename(remote_path, target)
        except Exception as exc:
            raise SftpError(
                f"Failed moving `{remote_path}` to quarantine `{quarantine_dir}`."
            ) from exc

    def delete_file(self, remote_path: str) -> None:
        try:
            self._client().remove(remote_path)
        except Exception as exc:
            raise SftpError(f"Failed deleting SFTP path `{remote_path}`.") from exc

    def health_check(self) -> bool:
        try:
            self._client().listdir(".")
        except Exception:
            self.close()
            return False
        return True
