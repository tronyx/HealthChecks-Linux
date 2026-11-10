"""Tests for the command line: main(), the lock files and the run lock."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import UUID_A, UUID_B, WriteConfig, http_check
from fake_server import Answer, FakeServer

from healthchecks_linux import GLOBAL_LOCK_NAME, __version__, acquire_run_lock, main

SCRIPT = Path(__file__).resolve().parent.parent / "healthchecks_linux.py"


def two_checks(write_config: WriteConfig, **kwargs: str) -> Path:
    return write_config(
        http_check("good", UUID_A, '{ url = "http://{app}/ok", send_token = true }')
        + http_check("bad", UUID_B, '{ url = "http://{app}/bad" }'),
        **kwargs,
    )


def script_answers(server: FakeServer) -> None:
    server.answer("/ok", Answer(200))
    server.answer("/bad", Answer(500))
    server.answer(f"/ping/{UUID_A}", Answer(200))
    server.answer(f"/ping/{UUID_B}/fail", Answer(200))


def pings(server: FakeServer) -> list[str]:
    return sorted(request.path for request in server.requests if request.path.startswith("/ping/"))


def test_run_pings_each_check_quietly(
    write_config: WriteConfig, server: FakeServer, capsys: pytest.CaptureFixture[str]
) -> None:
    script_answers(server)
    assert main(["-c", str(two_checks(write_config))], {}) == 0
    assert pings(server) == [f"/ping/{UUID_A}", f"/ping/{UUID_B}/fail"]
    assert capsys.readouterr().out == ""


def test_token_goes_to_the_probe_but_not_to_healthchecks(write_config: WriteConfig, server: FakeServer) -> None:
    script_answers(server)
    main(["-c", str(two_checks(write_config))], {"HCL_ORGANIZR_TOKEN": "s3cret"})
    assert server.requests_to("/ok")[0].headers["token"] == "s3cret"
    assert all("token" not in request.headers for request in server.requests if request.path.startswith("/ping/"))


def test_verbose_shows_results(
    write_config: WriteConfig, server: FakeServer, capsys: pytest.CaptureFixture[str]
) -> None:
    script_answers(server)
    assert main(["-c", str(two_checks(write_config)), "-v"], {}) == 0
    out = capsys.readouterr().out
    assert "PASS  good" in out and "FAIL  bad" in out
    assert f"{server.url}/bad -> 500, expected 200" in out


def test_dry_run_sends_no_pings(
    write_config: WriteConfig, server: FakeServer, capsys: pytest.CaptureFixture[str]
) -> None:
    script_answers(server)
    assert main(["-c", str(two_checks(write_config)), "--dry-run"], {}) == 1
    assert pings(server) == []
    assert "FAIL  bad" in capsys.readouterr().out


def test_dry_run_exit_code_when_all_pass(write_config: WriteConfig, server: FakeServer) -> None:
    script_answers(server)
    assert main(["-c", str(two_checks(write_config)), "-n", "--only", "good"], {}) == 0


def test_ping_failure_sets_the_exit_code(
    write_config: WriteConfig, server: FakeServer, capsys: pytest.CaptureFixture[str]
) -> None:
    server.answer("/ok", Answer(200))
    path = write_config(http_check("good", UUID_A, '{ url = "http://{app}/ok" }'))
    assert main(["-c", str(path)], {}) == 1
    assert f"cannot ping Healthchecks for check {UUID_A}: HTTP 404" in capsys.readouterr().err


def test_global_lock_skips_everything(
    write_config: WriteConfig, server: FakeServer, lock_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (lock_dir / GLOBAL_LOCK_NAME).touch()
    assert main(["-c", str(two_checks(write_config))], {}) == 0
    assert server.requests == []
    assert capsys.readouterr().out == ""
    assert main(["-c", str(two_checks(write_config)), "-v"], {}) == 0
    assert "Skipping all checks" in capsys.readouterr().out


def test_check_lock_skips_one_check(write_config: WriteConfig, server: FakeServer, lock_dir: Path) -> None:
    script_answers(server)
    (lock_dir / f"{UUID_B}.lock").touch()
    assert main(["-c", str(two_checks(write_config))], {}) == 0
    assert server.requests_to("/bad") == []
    assert pings(server) == [f"/ping/{UUID_A}"]


def test_overlapping_run_is_skipped(
    write_config: WriteConfig, server: FakeServer, lock_dir: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    held = acquire_run_lock(lock_dir)
    assert held is not None
    try:
        assert main(["-c", str(two_checks(write_config))], {}) == 0
        assert server.requests == []
        assert "the previous run is still going" in capsys.readouterr().err
        assert acquire_run_lock(lock_dir) is None
    finally:
        os.close(held)
    assert main(["-c", str(two_checks(write_config)), "--dry-run"], {}) == 1


def test_run_lock_folder_is_created(write_config: WriteConfig, server: FakeServer, tmp_path: Path) -> None:
    script_answers(server)
    lock_dir = tmp_path / "new" / "locks"
    path = write_config(http_check("good", UUID_A, '{ url = "http://{app}/ok" }'))
    path.write_text(path.read_text().replace(str(tmp_path / "locks"), str(lock_dir)), encoding="utf-8")
    assert main(["-c", str(path)], {}) == 0
    assert (lock_dir / ".healthchecks-linux.run").exists()


def test_unusable_lock_folder(write_config: WriteConfig, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    blocker = tmp_path / "file"
    blocker.touch()
    path = write_config(http_check("good", UUID_A, '{ url = "http://{app}/ok" }'))
    path.write_text(path.read_text().replace(str(tmp_path / "locks"), str(blocker / "locks")), encoding="utf-8")
    assert main(["-c", str(path)], {}) == 2
    assert "cannot use the lock folder" in capsys.readouterr().err


def test_only_runs_the_named_checks(write_config: WriteConfig, server: FakeServer) -> None:
    script_answers(server)
    assert main(["-c", str(two_checks(write_config)), "--only", "bad,bad"], {}) == 0
    assert pings(server) == [f"/ping/{UUID_B}/fail"]


@pytest.mark.parametrize(
    ("only", "message"),
    [("godo", "no check is named 'godo' (did you mean 'good'?)"), ("off", "check 'off' is not enabled")],
)
def test_only_errors(write_config: WriteConfig, capsys: pytest.CaptureFixture[str], only: str, message: str) -> None:
    path = write_config(
        http_check("good", UUID_A, '{ url = "http://{app}/" }')
        + http_check("off", UUID_B, '{ url = "http://{app}/" }', enabled=False)
    )
    assert main(["-c", str(path), "--only", only], {}) == 2
    assert message in capsys.readouterr().err


def test_no_enabled_check(write_config: WriteConfig, capsys: pytest.CaptureFixture[str]) -> None:
    path = write_config(http_check("off", UUID_A, '{ url = "http://{app}/" }', enabled=False))
    assert main(["-c", str(path)], {}) == 2
    assert "no check is enabled" in capsys.readouterr().err


def test_list(write_config: WriteConfig, lock_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = write_config(
        http_check("good", UUID_A, '{ url = "http://{app}/" }')
        + http_check("paused", UUID_B, '{ url = "http://{app}/" }')
        + '[[check]]\nname = "off"\nenabled = false\nprobes = [{ url = "http://{app}/" }]\n'
    )
    (lock_dir / f"{UUID_B}.lock").touch()
    assert main(["-c", str(path), "--list"], {}) == 0
    lines = [line.split() for line in capsys.readouterr().out.splitlines()]
    assert lines == [
        ["NAME", "UUID", "STATE"],
        ["good", UUID_A, "enabled"],
        ["paused", UUID_B, "paused"],
        ["off", "-", "disabled"],
    ]
    (lock_dir / GLOBAL_LOCK_NAME).touch()
    main(["-c", str(path), "--list"], {})
    assert "paused" in capsys.readouterr().out.splitlines()[1]


def test_config_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["-c", str(tmp_path / "missing.toml")], {}) == 2
    assert "config file does not exist" in capsys.readouterr().err


def test_config_from_environment(write_config: WriteConfig, server: FakeServer) -> None:
    script_answers(server)
    assert main([], {"HCL_CONFIG": str(two_checks(write_config))}) == 0
    assert len(pings(server)) == 2


def test_list_and_dry_run_are_exclusive() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--list", "--dry-run"], {})
    assert exit_info.value.code == 2


def test_script_runs_as_a_program(write_config: WriteConfig) -> None:
    version = subprocess.run([sys.executable, str(SCRIPT), "--version"], capture_output=True, text=True, check=True)
    assert version.stdout.strip() == f"healthchecks_linux.py {__version__}"
    path = write_config(http_check("good", UUID_A, '{ url = "http://{app}/" }'))
    listing = subprocess.run(
        [sys.executable, str(SCRIPT), "-c", str(path), "--list"], capture_output=True, text=True, check=False
    )
    assert listing.returncode == 0
    assert "good" in listing.stdout
