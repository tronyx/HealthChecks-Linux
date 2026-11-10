"""Shared pytest fixtures for the healthchecks_linux tests."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fake_server import FakeServer

import healthchecks_linux

UUID_A = "31365bce-8da9-4729-8ff3-aaa71d56b712"
UUID_B = "4b1d9a2e-6c3f-4e8a-9b7d-2f1e0c5a8d41"

WriteConfig = Callable[..., Path]


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep proxies out of the way of the local servers, and make ping retries instant."""
    for name in ("http_proxy", "https_proxy", "all_proxy", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setattr(healthchecks_linux, "PING_RETRY_DELAYS", (0.0, 0.0, 0.0))


@pytest.fixture
def server() -> Iterator[FakeServer]:
    """Yield a started fake server for the applications and the pings."""
    with FakeServer() as fake:
        yield fake


@pytest.fixture
def other_server() -> Iterator[FakeServer]:
    """Yield a second fake server: another origin, for redirect tests."""
    with FakeServer() as fake:
        yield fake


@pytest.fixture
def lock_dir(tmp_path: Path) -> Path:
    """Return an empty lock folder."""
    path = tmp_path / "locks"
    path.mkdir()
    return path


@pytest.fixture
def write_config(tmp_path: Path, server: FakeServer, lock_dir: Path) -> WriteConfig:
    """Return a function that writes a config file around the given [[check]] tables and returns its path.

    Pings go to the fake server under /ping, and {app} is the fake server's host:port.
    """

    def write(checks: str, general: str = "", tables: str = "") -> Path:
        path = tmp_path / "healthchecks.toml"
        path.write_text(
            f'[general]\nping_url = "{server.url}/ping"\nlock_dir = "{lock_dir}"\n{general}\n\n'
            f'[hosts]\napp = "{server.host}"\n\n{tables}\n\n{checks}\n',
            encoding="utf-8",
        )
        return path

    return write


def http_check(name: str, uuid: str, *probes: str, enabled: bool = True) -> str:
    """Return a [[check]] table with the given inline probe tables."""
    return (
        f'[[check]]\nname = "{name}"\nuuid = "{uuid}"\nenabled = {str(enabled).lower()}\n'
        f"probes = [{', '.join(probes)}]\n"
    )
