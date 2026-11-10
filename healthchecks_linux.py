#!/usr/bin/env python3
"""Test self-hosted applications and report each result to Healthchecks.

Each check sends one or more GET requests, usually one through the reverse proxy and one straight to the
application, and pings its Healthchecks check with success when every answer is as expected, or with fail
otherwise. The checks and settings come from a TOML file. Secrets come from the same file, which must then be
readable only by its owner, or from environment variables, which win over the file.
"""

import argparse
import base64
import difflib
import fcntl
import functools
import http.client
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any, TextIO

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError:
        _version = ".".join(str(part) for part in sys.version_info[:3])
        if sys.version_info[:2] == (3, 10):
            print(
                f"healthchecks-linux: Python {_version} needs the tomli package; install it "
                "(sudo apt install python3-tomli, or python3 -m pip install --user tomli) or use Python 3.11 or newer",
                file=sys.stderr,
            )
        else:
            print(f"healthchecks-linux: Python 3.10 or newer is needed, but this is Python {_version}", file=sys.stderr)
        sys.exit(2)

__version__ = "2.0.0"

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

ENV_CONFIG = "HCL_CONFIG"
ENV_TOKEN = "HCL_ORGANIZR_TOKEN"

DEFAULT_PING_URL = "https://hc-ping.com"
# Shared with Tronitor, which creates and removes the lock files here by default.
DEFAULT_LOCK_DIR = "/tmp"  # nosec B108
GLOBAL_LOCK_NAME = "healthchecks.lock"
RUN_LOCK_NAME = ".healthchecks-linux.run"
USER_AGENT = f"healthchecks-linux/{__version__}"

# Healthchecks keeps the first 100 kB of a ping body.
PING_BODY_LIMIT = 100_000
STATUSPAGE_BODY_LIMIT = 5_000_000
PING_RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)

PASS = "pass"
FAIL = "fail"
LOCKED = "locked"

UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
HOST_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
HOST_VALUE_RE = re.compile(r"[A-Za-z0-9.:\[\]-]+")
PLACEHOLDER_RE = re.compile(r"\{([^{}]*)\}")

TOP_KEYS = ("general", "hosts", "auth", "check")
GENERAL_KEYS = ("ping_url", "lock_dir", "timeout", "workers", "send_details", "organizr_token")
AUTH_KEYS = ("user", "password", "password_env")
CHECK_KEYS = ("name", "uuid", "enabled", "kind", "probes", "url", "component")
PROBE_KEYS = ("url", "expect", "follow_redirects", "verify_tls", "send_token", "auth")
KINDS = ("http", "statuspage")


"""Configuration: the TOML file, and the environment variables that can override its secrets."""


class ConfigError(Exception):
    """The config file is missing or invalid, or a setting it needs cannot be used."""


@dataclass(frozen=True)
class AuthEntry:
    """One [auth.<name>] table: a user name, a password, and an environment variable that overrides the password."""

    user: str
    password_env: str = ""
    password: str = field(default="", repr=False)


@dataclass(frozen=True)
class Credentials:
    """A user name and password for HTTP basic authentication."""

    user: str
    password: str = field(repr=False)


@dataclass(frozen=True)
class Probe:
    """One GET request, and the status codes that make it pass."""

    url: str
    expect: frozenset[int] = frozenset({200})
    follow_redirects: bool = False
    verify_tls: bool = True
    send_token: bool = False
    auth: Credentials | None = None


@dataclass(frozen=True)
class Check:
    """One application check and the Healthchecks check it reports to.

    The probes of a disabled check keep their URLs as written, because their hosts may not be set.
    """

    name: str
    uuid: str
    enabled: bool
    kind: str
    probes: tuple[Probe, ...]
    component: str = ""


@dataclass(frozen=True)
class Config:
    """The complete configuration."""

    path: Path
    ping_url: str
    lock_dir: Path
    timeout: float
    workers: int
    send_details: bool
    checks: tuple[Check, ...]
    organizr_token: str = field(default="", repr=False)


def _suggest(name: str, known: Sequence[str]) -> str:
    """Return a did-you-mean hint for name, or an empty string."""
    match = difflib.get_close_matches(name, known, n=1, cutoff=0.6)
    return f" (did you mean '{match[0]}'?)" if match else ""


def _table(value: object, where: str) -> dict[str, Any]:
    """Return value if it is a TOML table, else raise ConfigError."""
    if not isinstance(value, dict):
        raise ConfigError(f"{where} must be a table")
    return value


def _known(table: Mapping[str, Any], known: Sequence[str], where: str) -> None:
    """Raise ConfigError for the first key of table that is not in known."""
    for key in table:
        if key not in known:
            prefix = f"{where}: " if where else ""
            raise ConfigError(f"{prefix}unknown key '{key}'{_suggest(key, known)}")


def _get_str(table: Mapping[str, Any], key: str, where: str, default: str | None = None) -> str:
    """Return the stripped string at table[key], or default; a missing key with no default raises ConfigError."""
    value = table.get(key, default)
    if value is None:
        raise ConfigError(f"{where}: {key} is required")
    if not isinstance(value, str):
        raise ConfigError(f"{where}: {key} must be a string")
    return value.strip()


def _get_bool(table: Mapping[str, Any], key: str, where: str, default: bool) -> bool:
    """Return the boolean at table[key], or default."""
    value = table.get(key, default)
    if not isinstance(value, bool):
        raise ConfigError(f"{where}: {key} must be true or false")
    return value


def _get_number(table: Mapping[str, Any], key: str, where: str, default: float, low: float, high: float) -> float:
    """Return the number at table[key], or default; it must be from low to high."""
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ConfigError(f"{where}: {key} must be a number from {low:g} to {high:g}")
    return float(value)


def _get_int(table: Mapping[str, Any], key: str, where: str, default: int, low: int, high: int) -> int:
    """Return the whole number at table[key], or default; it must be from low to high."""
    value = table.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ConfigError(f"{where}: {key} must be a whole number from {low} to {high}")
    return value


def _check_url(url: str, where: str, what: str) -> str:
    """Return url if it is an http or https URL with a host and no user name or password, else raise ConfigError.

    The message for a URL with a user name leaves the URL out, because it may hold a password.
    """
    if re.search(r"[\s\x00-\x1f\x7f]", url):
        raise ConfigError(f"{where}: {what} contains a space or a control character")
    try:
        parts = urllib.parse.urlsplit(url)
        _ = parts.port
    except ValueError:
        raise ConfigError(f"{where}: {what} is not a valid URL: {url}") from None
    if "@" in parts.netloc:
        raise ConfigError(f"{where}: {what} must not contain a user name or password; use an [auth] table")
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise ConfigError(f"{where}: {what} must start with http:// or https:// and name a host: {url}")
    return url


def _fill(template: str, hosts: Mapping[str, str], where: str) -> str:
    """Replace each {name} in template with its value from [hosts]."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in hosts:
            raise ConfigError(f"{where}: unknown host '{{{name}}}'{_suggest(name, list(hosts))}; add it to [hosts]")
        if not hosts[name]:
            raise ConfigError(f"{where}: url uses {{{name}}}, but [hosts] {name} is empty")
        return hosts[name]

    return PLACEHOLDER_RE.sub(replace, template)


def _hosts(raw: object) -> dict[str, str]:
    """Return the [hosts] table: names that URLs can use as {name}, and their values (which may be empty)."""
    table = _table(raw, "[hosts]")
    hosts: dict[str, str] = {}
    for name in table:
        if not HOST_NAME_RE.fullmatch(name):
            raise ConfigError(f"[hosts]: '{name}' must start with a letter and use only letters, digits and '_'")
        value = _get_str(table, name, "[hosts]")
        if value and not HOST_VALUE_RE.fullmatch(value):
            raise ConfigError(f"[hosts]: {name} must be a host name or an IP address, with an optional :port")
        hosts[name] = value
    return hosts


def _get_secret(table: Mapping[str, Any], key: str, where: str) -> str:
    """Return the string at table[key] as written, or an empty string; the value never appears in an error."""
    value = table.get(key, "")
    if not isinstance(value, str):
        raise ConfigError(f"{where}: {key} must be a string")
    return value


def _auths(raw: object) -> dict[str, AuthEntry]:
    """Return the [auth.<name>] tables."""
    table = _table(raw, "[auth]")
    auths: dict[str, AuthEntry] = {}
    for name, value in table.items():
        where = f"[auth.{name}]"
        entry = _table(value, where)
        _known(entry, AUTH_KEYS, where)
        auths[name] = AuthEntry(
            user=_get_str(entry, "user", where),
            password_env=_get_str(entry, "password_env", where, ""),
            password=_get_secret(entry, "password", where),
        )
    return auths


def _credentials(name: str, entry: AuthEntry, env: Mapping[str, str], where: str) -> Credentials:
    """Return the user name and password of [auth.<name>]; the password_env variable, when set, wins."""
    if not entry.user:
        raise ConfigError(f"{where}: [auth.{name}] user is empty")
    password = (env.get(entry.password_env, "") if entry.password_env else "") or entry.password
    if not password:
        if entry.password_env:
            raise ConfigError(
                f"{where}: the environment variable {entry.password_env} is not set, and [auth.{name}] has no password"
            )
        raise ConfigError(f"{where}: [auth.{name}] needs a password, or password_env to name an environment variable")
    return Credentials(entry.user, password)


def _check_private(path: Path) -> None:
    """Raise ConfigError if users other than the owner can read or change path, which holds a secret."""
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise ConfigError(f"cannot read the permissions of the file: {exc.strerror or exc}") from None
    if mode & 0o077:
        raise ConfigError(f"the file holds a secret, but other users can open it; make it private: chmod 600 {path}")


def _expect(value: object, where: str) -> frozenset[int]:
    """Return the expected status codes of a probe."""
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(code, int) and not isinstance(code, bool) and 100 <= code <= 599 for code in value)
    ):
        raise ConfigError(f"{where}: expect must be a list of HTTP status codes, such as [200] or [200, 401]")
    return frozenset(value)


def _probe(
    raw: object,
    where: str,
    hosts: Mapping[str, str],
    auths: Mapping[str, AuthEntry],
    env: Mapping[str, str],
    live: bool,
) -> Probe:
    """Build one probe; live resolves the {host} names and the credentials, which only enabled checks need."""
    table = _table(raw, where)
    _known(table, PROBE_KEYS, where)
    url = _get_str(table, "url", where)
    if not url:
        raise ConfigError(f"{where}: url is required")
    auth_name = table.get("auth")
    if auth_name is not None and not isinstance(auth_name, str):
        raise ConfigError(f"{where}: auth must be a string")
    if auth_name is not None and auth_name not in auths:
        raise ConfigError(f"{where}: no [auth.{auth_name}] table{_suggest(auth_name, list(auths))}")
    credentials = None
    if live:
        url = _check_url(_fill(url, hosts, where), where, "url")
        if auth_name is not None:
            credentials = _credentials(auth_name, auths[auth_name], env, where)
    return Probe(
        url=url,
        expect=_expect(table.get("expect", [200]), where),
        follow_redirects=_get_bool(table, "follow_redirects", where, False),
        verify_tls=_get_bool(table, "verify_tls", where, True),
        send_token=_get_bool(table, "send_token", where, False),
        auth=credentials,
    )


def _check(
    raw: object, index: int, hosts: Mapping[str, str], auths: Mapping[str, AuthEntry], env: Mapping[str, str]
) -> Check:
    """Build one [[check]]."""
    where = f"check #{index}"
    table = _table(raw, where)
    name = _get_str(table, "name", where)
    if not NAME_RE.fullmatch(name):
        raise ConfigError(f"{where}: name must start with a letter or digit and use only letters, digits, . _ and -")
    where = f"check '{name}'"
    _known(table, CHECK_KEYS, where)
    enabled = _get_bool(table, "enabled", where, True)
    uuid = _get_str(table, "uuid", where, "").lower()
    if uuid and not UUID_RE.fullmatch(uuid):
        raise ConfigError(f"{where}: uuid must look like 31365bce-8da9-4729-8ff3-aaa71d56b712")
    if enabled and not uuid:
        raise ConfigError(f"{where}: an enabled check needs a uuid; set it, or set enabled = false")
    kind = _get_str(table, "kind", where, "http")
    if kind not in KINDS:
        raise ConfigError(f'{where}: kind must be "http" or "statuspage"')
    if kind == "http":
        for key in ("url", "component"):
            if key in table:
                raise ConfigError(f'{where}: {key} is only for kind = "statuspage"; put the URLs in probes')
        probes_raw = table.get("probes")
        if not isinstance(probes_raw, list) or not probes_raw:
            raise ConfigError(f"{where}: probes must be a list with at least one probe")
        probes = tuple(
            _probe(item, f"{where} probe {number}", hosts, auths, env, enabled)
            for number, item in enumerate(probes_raw, 1)
        )
        return Check(name, uuid, enabled, kind, probes)
    if "probes" in table:
        raise ConfigError(f'{where}: probes are not used with kind = "statuspage"; set url and component')
    url = _get_str(table, "url", where)
    component = _get_str(table, "component", where)
    if not url or not component:
        raise ConfigError(f'{where}: kind = "statuspage" needs both url and component')
    if enabled:
        url = _check_url(_fill(url, hosts, where), where, "url")
    return Check(name, uuid, enabled, kind, (Probe(url),), component)


def _lock_dir(value: str) -> Path:
    """Return the lock folder with ~ expanded; it must be an absolute path, because cron runs in another folder."""
    path = Path(value)
    try:
        path = path.expanduser()
    except RuntimeError:
        pass
    if not path.is_absolute():
        raise ConfigError("[general]: lock_dir must be an absolute path, such as /tmp")
    return path


def _build_config(path: Path, doc: Mapping[str, Any], env: Mapping[str, str]) -> Config:
    """Validate the parsed TOML document and build the configuration."""
    _known(doc, TOP_KEYS, "")
    general = _table(doc.get("general", {}), "[general]")
    _known(general, GENERAL_KEYS, "[general]")
    ping_url = _check_url(_get_str(general, "ping_url", "[general]", DEFAULT_PING_URL), "[general]", "ping_url")
    file_token = _get_secret(general, "organizr_token", "[general]").strip()
    hosts = _hosts(doc.get("hosts", {}))
    auths = _auths(doc.get("auth", {}))
    if file_token or any(entry.password for entry in auths.values()):
        _check_private(path)
    checks_raw = doc.get("check", [])
    if not isinstance(checks_raw, list):
        raise ConfigError("check must be a list of tables; start each one with [[check]]")
    checks = tuple(_check(raw, index, hosts, auths, env) for index, raw in enumerate(checks_raw, 1))
    seen_names: set[str] = set()
    seen_uuids: dict[str, str] = {}
    for check in checks:
        if check.name in seen_names:
            raise ConfigError(f"two checks are named '{check.name}'")
        seen_names.add(check.name)
        if check.uuid and check.uuid in seen_uuids:
            raise ConfigError(f"checks '{seen_uuids[check.uuid]}' and '{check.name}' have the same uuid")
        if check.uuid:
            seen_uuids[check.uuid] = check.name
    return Config(
        path=path,
        ping_url=ping_url.rstrip("/"),
        lock_dir=_lock_dir(_get_str(general, "lock_dir", "[general]", DEFAULT_LOCK_DIR)),
        timeout=_get_number(general, "timeout", "[general]", 10, 1, 300),
        workers=_get_int(general, "workers", "[general]", 8, 1, 64),
        send_details=_get_bool(general, "send_details", "[general]", True),
        checks=checks,
        organizr_token=env.get(ENV_TOKEN, "").strip() or file_token,
    )


def load_config(path: Path, env: Mapping[str, str]) -> Config:
    """Read and validate the config file at path; the secrets in env win over the ones in the file."""
    try:
        doc = tomllib.loads(path.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError, UnicodeDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from None
    try:
        return _build_config(path, doc, env)
    except ConfigError as exc:
        raise ConfigError(f"{path}: {exc}") from None


def config_search_paths(script: Path, env: Mapping[str, str]) -> list[Path]:
    """Return the places to look for the config file, in order: next to the script, then the user's config folder."""
    paths = [script.parent / "healthchecks.toml"]
    xdg = env.get("XDG_CONFIG_HOME", "").strip()
    if xdg and Path(xdg).is_absolute():
        paths.append(Path(xdg) / "healthchecks-linux" / "healthchecks.toml")
    else:
        try:
            paths.append(Path.home() / ".config" / "healthchecks-linux" / "healthchecks.toml")
        except RuntimeError:
            pass
    return paths


def find_config(explicit: Path | None, env: Mapping[str, str], search_paths: Sequence[Path]) -> Path:
    """Return the config file to read: --config, else HCL_CONFIG, else the first search path that exists."""
    if explicit is None and env.get(ENV_CONFIG, "").strip():
        explicit = Path(env[ENV_CONFIG].strip())
    if explicit is not None:
        try:
            explicit = explicit.expanduser()
        except RuntimeError:
            pass
        if not explicit.is_file():
            raise ConfigError(f"{explicit}: config file does not exist")
        return explicit
    for path in search_paths:
        if path.is_file():
            return path
    raise ConfigError(
        f"no config file found; copy healthchecks.example.toml to {search_paths[0]} and edit it, or use --config"
    )


"""HTTP: the probes, the Statuspage check and the pings."""


class ProbeFailed(Exception):
    """A probe got no HTTP answer: the connection failed or timed out."""


class PingError(Exception):
    """A ping could not be delivered to Healthchecks."""


@dataclass(frozen=True)
class ProbeResult:
    """The outcome of one probe."""

    url: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one check: pass, fail or locked, and the ping error if the ping was not delivered."""

    check: Check
    state: str
    probes: tuple[ProbeResult, ...] = ()
    ping_error: str = ""


def _origin(url: str) -> tuple[str, str]:
    """Return the scheme and the host:port of url, lowercased."""
    parts = urllib.parse.urlsplit(url)
    return parts.scheme.lower(), parts.netloc.lower()


class _Redirects(urllib.request.HTTPRedirectHandler):
    """Follow redirects only when asked, and send the secret headers again only to the same scheme, host and port.

    urllib copies normal headers to every redirect target, including other hosts, so the secrets are added as
    unredirected headers and copied here by hand.
    """

    def __init__(self, follow: bool, secret_headers: Mapping[str, str]) -> None:
        super().__init__()
        self._follow = follow
        self._secret_headers = dict(secret_headers)

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: IO[bytes],
        code: int,
        msg: str,
        headers: http.client.HTTPMessage,
        newurl: str,
    ) -> urllib.request.Request | None:
        """Return the request for the new URL, or None to report the redirect's own status code."""
        if not self._follow:
            return None
        new = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new is not None and _origin(new.full_url) == _origin(req.full_url):
            for name, value in self._secret_headers.items():
                new.add_unredirected_header(name, value)
        return new


@functools.lru_cache(maxsize=2)
def _tls_context(verify: bool) -> ssl.SSLContext:
    """Return a TLS context that checks certificates, or one that does not."""
    context = ssl.create_default_context()
    if not verify:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    return context


def _secret_headers(probe: Probe, token: str) -> dict[str, str]:
    """Return the Organizr token and basic auth headers that the probe sends."""
    headers: dict[str, str] = {}
    if probe.send_token and token:
        headers["token"] = token
    if probe.auth is not None:
        pair = f"{probe.auth.user}:{probe.auth.password}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(pair).decode("ascii")
    return headers


def fetch(probe: Probe, token: str, timeout: float, read_limit: int = 0) -> tuple[int, bytes]:
    """Send the probe's GET request; return the status code and up to read_limit bytes of the body.

    Any HTTP answer is returned, whatever its status; no answer at all raises ProbeFailed.
    """
    secrets = _secret_headers(probe, token)
    opener = urllib.request.build_opener(
        _Redirects(probe.follow_redirects, secrets),
        urllib.request.HTTPSHandler(context=_tls_context(probe.verify_tls)),
    )
    request = urllib.request.Request(probe.url, method="GET", headers={"User-Agent": USER_AGENT})
    for name, value in secrets.items():
        request.add_unredirected_header(name, value)
    try:
        with opener.open(request, timeout=timeout) as response:
            return int(response.status), response.read(read_limit) if read_limit else b""
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, b""
    except TimeoutError:
        raise ProbeFailed("timed out") from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise ProbeFailed("timed out") from None
        raise ProbeFailed(str(exc.reason)) from None
    except (OSError, http.client.HTTPException) as exc:
        raise ProbeFailed(str(exc) or type(exc).__name__) from None


def _codes(codes: frozenset[int]) -> str:
    """Return the status codes as "200" or "200 or 401"."""
    return " or ".join(str(code) for code in sorted(codes))


def run_probe(probe: Probe, token: str, timeout: float) -> ProbeResult:
    """Send one probe and compare its status code with the expected ones."""
    try:
        status, _ = fetch(probe, token, timeout)
    except ProbeFailed as exc:
        return ProbeResult(probe.url, False, f"error: {exc}")
    if status in probe.expect:
        return ProbeResult(probe.url, True, str(status))
    return ProbeResult(probe.url, False, f"{status}, expected {_codes(probe.expect)}")


def run_statuspage(check: Check, timeout: float) -> ProbeResult:
    """Read a Statuspage components.json and pass when the check's component is operational."""
    probe = check.probes[0]
    try:
        status, body = fetch(probe, "", timeout, STATUSPAGE_BODY_LIMIT)
    except ProbeFailed as exc:
        return ProbeResult(probe.url, False, f"error: {exc}")
    if status != 200:
        return ProbeResult(probe.url, False, f"{status}, expected 200")
    try:
        data = json.loads(body)
    except ValueError:
        return ProbeResult(probe.url, False, "the answer is not JSON")
    components = data.get("components") if isinstance(data, dict) else None
    for component in components if isinstance(components, list) else []:
        if not isinstance(component, dict):
            continue
        name = " ".join(str(component.get("name", "")).split())
        if name.startswith(check.component):
            state = str(component.get("status", "unknown"))
            return ProbeResult(probe.url, state == "operational", f"{name}: {state}")
    return ProbeResult(probe.url, False, f"no component named '{check.component}'")


def send_ping(
    ping_url: str, uuid: str, passed: bool, body: str, timeout: float, sleep: Callable[[float], None] = time.sleep
) -> None:
    """POST a success or fail ping with body; retry a network error, a 429 or a 5xx answer, then raise PingError."""
    url = f"{ping_url}/{uuid}" if passed else f"{ping_url}/{uuid}/fail"
    data = body.encode("utf-8")[:PING_BODY_LIMIT]
    headers = {"User-Agent": USER_AGENT, "Content-Type": "text/plain; charset=utf-8"}
    error = ""
    for delay in (*PING_RETRY_DELAYS, None):
        request = urllib.request.Request(url, data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response.read(1024)
            return
        except urllib.error.HTTPError as exc:
            with exc:
                error = f"HTTP {exc.code}"
            if exc.code < 500 and exc.code != 429:
                break
        except urllib.error.URLError as exc:
            error = "timed out" if isinstance(exc.reason, TimeoutError) else str(exc.reason)
        except (OSError, http.client.HTTPException) as exc:
            error = str(exc) or type(exc).__name__
        if delay is None:
            break
        sleep(delay)
    raise PingError(f"cannot ping Healthchecks for check {uuid}: {error}")


"""Running the checks."""


def ping_body(probes: Sequence[ProbeResult]) -> str:
    """Return the text sent with a ping: one line per probe."""
    lines = [f"healthchecks-linux {__version__}"]
    lines += [f"{'PASS' if probe.passed else 'FAIL'} {probe.url} -> {probe.detail}" for probe in probes]
    return "\n".join(lines)


def run_check(check: Check, config: Config, token: str, ping: bool) -> CheckResult:
    """Run one check unless its lock file exists, and ping its Healthchecks check when ping is True."""
    if (config.lock_dir / f"{check.uuid}.lock").exists():
        return CheckResult(check, LOCKED)
    if check.kind == "statuspage":
        probes: tuple[ProbeResult, ...] = (run_statuspage(check, config.timeout),)
    else:
        probes = tuple(run_probe(probe, token, config.timeout) for probe in check.probes)
    state = PASS if all(probe.passed for probe in probes) else FAIL
    ping_error = ""
    if ping:
        try:
            body = ping_body(probes) if config.send_details else ""
            send_ping(config.ping_url, check.uuid, state == PASS, body, config.timeout)
        except PingError as exc:
            ping_error = str(exc)
    return CheckResult(check, state, probes, ping_error)


def select_checks(config: Config, only: Sequence[str]) -> tuple[Check, ...]:
    """Return the enabled checks, or only the ones named in only (comma-separated names are split)."""
    enabled = tuple(check for check in config.checks if check.enabled)
    names = [name.strip() for item in only for name in item.split(",") if name.strip()]
    if not names:
        return enabled
    by_name = {check.name: check for check in config.checks}
    chosen: list[Check] = []
    for name in names:
        check = by_name.get(name)
        if check is None:
            raise ConfigError(f"--only: no check is named '{name}'{_suggest(name, list(by_name))}")
        if not check.enabled:
            raise ConfigError(f"--only: check '{name}' is not enabled")
        if check not in chosen:
            chosen.append(check)
    return tuple(chosen)


def acquire_run_lock(lock_dir: Path) -> int | None:
    """Return a file descriptor that holds the run lock, or None when another run holds it.

    O_NOFOLLOW keeps another user from pointing the name at a file of yours through a link in a shared /tmp.
    """
    try:
        lock_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(lock_dir / RUN_LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    except OSError as exc:
        raise ConfigError(f"cannot use the lock folder {lock_dir}: {exc.strerror or exc}") from None
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(descriptor)
        return None
    return descriptor


def format_result(result: CheckResult) -> str:
    """Return the lines that show one check result."""
    if result.state == LOCKED:
        return f"SKIP  {result.check.name} (its lock file exists)"
    lines = [f"{'PASS' if result.state == PASS else 'FAIL'}  {result.check.name}"]
    lines += [f"      {probe.url} -> {probe.detail}" for probe in result.probes]
    return "\n".join(lines)


def list_checks(config: Config, out: TextIO) -> None:
    """Print each check with its uuid and its state: enabled, disabled or paused (a lock file exists)."""
    all_locked = (config.lock_dir / GLOBAL_LOCK_NAME).exists()
    width = max([4, *(len(check.name) for check in config.checks)])
    print(f"{'NAME':<{width}}  {'UUID':<36}  STATE", file=out)
    for check in config.checks:
        if not check.enabled:
            state = "disabled"
        elif all_locked or (config.lock_dir / f"{check.uuid}.lock").exists():
            state = "paused"
        else:
            state = "enabled"
        print(f"{check.name:<{width}}  {check.uuid or '-':<36}  {state}", file=out)


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        prog="healthchecks_linux.py",
        description="Test self-hosted applications and report each result to Healthchecks.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="the config file (default: healthchecks.toml next to this script, then "
        f"~/.config/healthchecks-linux/healthchecks.toml; {ENV_CONFIG} also sets it)",
    )
    parser.add_argument("--only", action="append", default=[], metavar="NAME[,NAME...]", help="run only these checks")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "-n", "--dry-run", action="store_true", help="test the applications and show the results, but send no pings"
    )
    mode.add_argument("-l", "--list", action="store_true", help="list the checks in the config file, then stop")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the result of each check")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None) -> int:
    """Run the command line program and return its exit code."""
    args = parse_args(argv)
    env = os.environ if env is None else env
    try:
        path = find_config(args.config, env, config_search_paths(Path(__file__).resolve(), env))
        config = load_config(path, env)
        checks = select_checks(config, args.only)
    except ConfigError as exc:
        print(f"healthchecks-linux: {exc}", file=sys.stderr)
        return EXIT_USAGE
    if args.list:
        list_checks(config, sys.stdout)
        return EXIT_OK
    global_lock = config.lock_dir / GLOBAL_LOCK_NAME
    if global_lock.exists():
        if args.verbose or args.dry_run:
            print(f"Skipping all checks, because {global_lock} exists.")
        return EXIT_OK
    if not checks:
        print(f"healthchecks-linux: {config.path}: no check is enabled", file=sys.stderr)
        return EXIT_USAGE
    run_lock = None
    if not args.dry_run:
        try:
            run_lock = acquire_run_lock(config.lock_dir)
        except ConfigError as exc:
            print(f"healthchecks-linux: {exc}", file=sys.stderr)
            return EXIT_USAGE
        if run_lock is None:
            print("healthchecks-linux: the previous run is still going, so this run is skipped", file=sys.stderr)
            return EXIT_OK
    token = config.organizr_token
    try:
        with ThreadPoolExecutor(max_workers=min(config.workers, len(checks))) as pool:
            results = list(pool.map(lambda check: run_check(check, config, token, not args.dry_run), checks))
    finally:
        if run_lock is not None:
            os.close(run_lock)
    for result in results:
        if args.verbose or args.dry_run:
            print(format_result(result))
        if result.ping_error:
            print(f"healthchecks-linux: {result.ping_error}", file=sys.stderr)
    if args.dry_run:
        return EXIT_ERROR if any(result.state == FAIL for result in results) else EXIT_OK
    return EXIT_ERROR if any(result.ping_error for result in results) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
