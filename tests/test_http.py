"""Tests for the probes, the Statuspage check and the pings."""

import base64
import json
import ssl
from pathlib import Path

import pytest
from conftest import UUID_A
from fake_server import Answer, FakeServer

import healthchecks_linux
from healthchecks_linux import (
    Check,
    Config,
    Credentials,
    PingError,
    Probe,
    ProbeFailed,
    fetch,
    ping_body,
    run_check,
    run_probe,
    run_statuspage,
    send_ping,
)

TOKEN = "org-s3cret"


def config(server: FakeServer, lock_dir: Path, send_details: bool = True) -> Config:
    return Config(Path("x.toml"), f"{server.url}/ping", lock_dir, 5, 2, send_details, ())


def test_probe_passes_on_expected_status(server: FakeServer) -> None:
    server.answer("/ok", Answer(200))
    result = run_probe(Probe(f"{server.url}/ok"), "", 5)
    assert (result.passed, result.detail) == (True, "200")
    assert server.requests[0].method == "GET"


def test_probe_fails_on_other_status(server: FakeServer) -> None:
    server.answer("/bad", Answer(502))
    result = run_probe(Probe(f"{server.url}/bad"), "", 5)
    assert (result.passed, result.detail) == (False, "502, expected 200")


def test_probe_with_several_expected_codes(server: FakeServer) -> None:
    server.answer("/auth", Answer(401))
    assert run_probe(Probe(f"{server.url}/auth", expect=frozenset({401})), "", 5).passed
    result = run_probe(Probe(f"{server.url}/missing", expect=frozenset({401, 200})), "", 5)
    assert result.detail == "404, expected 200 or 401"


def test_redirect_is_not_followed_by_default(server: FakeServer) -> None:
    server.answer("/old", Answer(302, headers={"Location": "/new"}))
    server.answer("/new", Answer(200))
    result = run_probe(Probe(f"{server.url}/old"), "", 5)
    assert result.detail == "302, expected 200"
    assert [request.path for request in server.requests] == ["/old"]


def test_redirect_is_followed_when_asked(server: FakeServer) -> None:
    server.answer("/old", Answer(302, headers={"Location": "/new"}))
    server.answer("/new", Answer(200))
    assert run_probe(Probe(f"{server.url}/old", follow_redirects=True), "", 5).passed


@pytest.mark.parametrize(
    ("send_token", "token", "sent"), [(True, TOKEN, True), (False, TOKEN, False), (True, "", False)]
)
def test_token_header(server: FakeServer, send_token: bool, token: str, sent: bool) -> None:
    server.answer("/", Answer(200))
    run_probe(Probe(f"{server.url}/", send_token=send_token), token, 5)
    assert server.requests[0].headers.get("token") == (TOKEN if sent else None)


def test_secrets_follow_a_redirect_to_the_same_host(server: FakeServer) -> None:
    server.answer("/old", Answer(301, headers={"Location": "/new"}))
    server.answer("/new", Answer(200))
    probe = Probe(f"{server.url}/old", follow_redirects=True, send_token=True, auth=Credentials("u", "p"))
    run_probe(probe, TOKEN, 5)
    new = server.requests_to("/new")[0]
    assert new.headers["token"] == TOKEN
    assert new.headers["authorization"].startswith("Basic ")


def test_secrets_do_not_follow_a_redirect_to_another_host(server: FakeServer, other_server: FakeServer) -> None:
    server.answer("/old", Answer(302, headers={"Location": f"{other_server.url}/landing"}))
    other_server.answer("/landing", Answer(200))
    probe = Probe(f"{server.url}/old", follow_redirects=True, send_token=True, auth=Credentials("u", "p"))
    assert run_probe(probe, TOKEN, 5).passed
    assert server.requests[0].headers["token"] == TOKEN
    landing = other_server.requests[0]
    assert "token" not in landing.headers
    assert "authorization" not in landing.headers


def test_basic_auth_header(server: FakeServer) -> None:
    server.answer("/", Answer(200))
    run_probe(Probe(f"{server.url}/", auth=Credentials("admin", "pw:with:colons")), "", 5)
    value = server.requests[0].headers["authorization"]
    assert base64.b64decode(value.removeprefix("Basic ")) == b"admin:pw:with:colons"


def test_connection_refused() -> None:
    result = run_probe(Probe("http://127.0.0.1:1/"), "", 5)
    assert not result.passed
    assert result.detail.startswith("error: ")


def test_timeout(server: FakeServer) -> None:
    server.answer("/slow", Answer(200, delay=1.0))
    with pytest.raises(ProbeFailed, match="timed out"):
        fetch(Probe(f"{server.url}/slow"), "", 0.2)


def test_tls_context() -> None:
    strict = healthchecks_linux._tls_context(True)
    assert strict.verify_mode == ssl.CERT_REQUIRED and strict.check_hostname
    loose = healthchecks_linux._tls_context(False)
    assert loose.verify_mode == ssl.CERT_NONE and not loose.check_hostname


def statuspage(server: FakeServer, component: str = "Authentication and API server") -> Check:
    return Check("plex_auth", UUID_A, True, "statuspage", (Probe(f"{server.url}/components.json"),), component)


def components(*items: tuple[str, str]) -> bytes:
    return json.dumps({"components": [{"name": name, "status": state} for name, state in items]}).encode()


def test_statuspage_operational(server: FakeServer) -> None:
    body = components(("Plex website", "major_outage"), ("Authentication and API\nserver\n(plex.tv)", "operational"))
    server.answer("/components.json", Answer(200, body))
    result = run_statuspage(statuspage(server), 5)
    assert result.passed
    assert result.detail == "Authentication and API server (plex.tv): operational"


def test_statuspage_degraded(server: FakeServer) -> None:
    server.answer("/components.json", Answer(200, components(("Authentication and API server", "degraded"))))
    result = run_statuspage(statuspage(server), 5)
    assert (result.passed, result.detail) == (False, "Authentication and API server: degraded")


@pytest.mark.parametrize(
    ("answer", "detail"),
    [
        (Answer(200, components(("Other", "operational"))), "no component named 'Authentication and API server'"),
        (Answer(200, b"<html>"), "the answer is not JSON"),
        (Answer(200, b'["not", "an", "object"]'), "no component named"),
        (Answer(503), "503, expected 200"),
    ],
)
def test_statuspage_failures(server: FakeServer, answer: Answer, detail: str) -> None:
    server.answer("/components.json", answer)
    result = run_statuspage(statuspage(server), 5)
    assert not result.passed
    assert detail in result.detail


def test_statuspage_unreachable() -> None:
    check = Check("s", UUID_A, True, "statuspage", (Probe("http://127.0.0.1:1/c.json"),), "x")
    assert run_statuspage(check, 5).detail.startswith("error: ")


def test_success_ping(server: FakeServer) -> None:
    server.answer(f"/ping/{UUID_A}", Answer(200, b"OK"))
    send_ping(f"{server.url}/ping", UUID_A, True, "details", 5)
    (request,) = server.requests
    assert (request.method, request.path, request.body) == ("POST", f"/ping/{UUID_A}", b"details")
    assert request.headers["content-type"] == "text/plain; charset=utf-8"
    assert "token" not in request.headers


def test_fail_ping(server: FakeServer) -> None:
    server.answer(f"/ping/{UUID_A}/fail", Answer(200))
    send_ping(f"{server.url}/ping", UUID_A, False, "", 5)
    assert server.requests[0].path == f"/ping/{UUID_A}/fail"


def test_ping_retries_a_server_error(server: FakeServer) -> None:
    server.answer(f"/ping/{UUID_A}", Answer(500), Answer(429), Answer(200))
    send_ping(f"{server.url}/ping", UUID_A, True, "", 5)
    assert len(server.requests) == 3


def test_ping_gives_up_after_the_retries(server: FakeServer) -> None:
    server.answer(f"/ping/{UUID_A}", Answer(503))
    delays: list[float] = []
    with pytest.raises(PingError, match=f"cannot ping Healthchecks for check {UUID_A}: HTTP 503"):
        send_ping(f"{server.url}/ping", UUID_A, True, "", 5, sleep=delays.append)
    assert len(server.requests) == 4
    assert delays == [0.0, 0.0, 0.0]


def test_ping_does_not_retry_a_client_error(server: FakeServer) -> None:
    with pytest.raises(PingError, match="HTTP 404"):
        send_ping(f"{server.url}/ping", UUID_A, True, "", 5)
    assert len(server.requests) == 1


def test_ping_network_error() -> None:
    with pytest.raises(PingError, match="cannot ping Healthchecks"):
        send_ping("http://127.0.0.1:1", UUID_A, True, "", 5)


def test_ping_body_is_cut_to_the_limit(server: FakeServer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(healthchecks_linux, "PING_BODY_LIMIT", 10)
    server.answer(f"/ping/{UUID_A}", Answer(200))
    send_ping(f"{server.url}/ping", UUID_A, True, "x" * 50, 5)
    assert server.requests[0].body == b"x" * 10


def test_run_check_pings_with_details(server: FakeServer, lock_dir: Path) -> None:
    server.answer("/ok", Answer(200))
    server.answer("/bad", Answer(500))
    server.answer(f"/ping/{UUID_A}/fail", Answer(200))
    check = Check("app", UUID_A, True, "http", (Probe(f"{server.url}/ok"), Probe(f"{server.url}/bad")))
    result = run_check(check, config(server, lock_dir), "", ping=True)
    assert result.state == "fail" and result.ping_error == ""
    body = server.requests_to(f"/ping/{UUID_A}/fail")[0].body.decode()
    assert f"PASS {server.url}/ok -> 200" in body
    assert f"FAIL {server.url}/bad -> 500, expected 200" in body


def test_run_check_without_details(server: FakeServer, lock_dir: Path) -> None:
    server.answer("/ok", Answer(200))
    server.answer(f"/ping/{UUID_A}", Answer(200))
    check = Check("app", UUID_A, True, "http", (Probe(f"{server.url}/ok"),))
    assert run_check(check, config(server, lock_dir, send_details=False), "", ping=True).state == "pass"
    assert server.requests_to(f"/ping/{UUID_A}")[0].body == b""


def test_run_check_skips_a_locked_check(server: FakeServer, lock_dir: Path) -> None:
    (lock_dir / f"{UUID_A}.lock").touch()
    check = Check("app", UUID_A, True, "http", (Probe(f"{server.url}/ok"),))
    assert run_check(check, config(server, lock_dir), "", ping=True).state == "locked"
    assert server.requests == []


def test_run_check_reports_a_ping_error(server: FakeServer, lock_dir: Path) -> None:
    server.answer("/ok", Answer(200))
    check = Check("app", UUID_A, True, "http", (Probe(f"{server.url}/ok"),))
    result = run_check(check, config(server, lock_dir), "", ping=True)
    assert result.state == "pass"
    assert "HTTP 404" in result.ping_error


def test_run_check_statuspage(server: FakeServer, lock_dir: Path) -> None:
    server.answer("/components.json", Answer(200, components(("Authentication and API server", "operational"))))
    result = run_check(statuspage(server), config(server, lock_dir), TOKEN, ping=False)
    assert result.state == "pass"
    assert "token" not in server.requests[0].headers


def test_ping_body() -> None:
    body = ping_body([healthchecks_linux.ProbeResult("http://a/", True, "200")])
    assert body.splitlines() == [f"healthchecks-linux {healthchecks_linux.__version__}", "PASS http://a/ -> 200"]
