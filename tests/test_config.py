"""Tests for reading and validating the config file."""

import re
from pathlib import Path

import pytest
from conftest import UUID_A, UUID_B

from healthchecks_linux import (
    ConfigError,
    Credentials,
    config_search_paths,
    find_config,
    load_config,
)

EXAMPLE = Path(__file__).resolve().parent.parent / "healthchecks.example.toml"


def check(
    name: str = "app", uuid: str = UUID_A, probes: str = '{ url = "http://example.test/" }', extra: str = ""
) -> str:
    return f'[[check]]\nname = "{name}"\nuuid = "{uuid}"\n{extra}\nprobes = [{probes}]\n'


def test_defaults(tmp_path: Path) -> None:
    path = tmp_path / "healthchecks.toml"
    path.write_text(check(), encoding="utf-8")
    config = load_config(path, {})
    assert config.path == path
    assert config.ping_url == "https://hc-ping.com"
    assert config.lock_dir == Path("/tmp")
    assert config.timeout == 10
    assert config.workers == 8
    assert config.send_details is True
    (only,) = config.checks
    assert only.enabled and only.kind == "http"
    (probe,) = only.probes
    assert probe.url == "http://example.test/"
    assert probe.expect == frozenset({200})
    assert not probe.follow_redirects and probe.verify_tls and not probe.send_token and probe.auth is None


def test_general_settings_and_placeholders(tmp_path: Path) -> None:
    text = (
        '[general]\nping_url = "https://hc.example.test/ping/"\nlock_dir = "/var/lock/hcl"\n'
        "timeout = 2.5\nworkers = 3\nsend_details = false\n\n"
        '[hosts]\ndomain = "example.test"\nprimary = "10.0.0.5:8080"\n\n'
        + check(
            uuid=UUID_A.upper(),
            probes='{ url = "https://{domain}/app/", expect = [200, 401], send_token = true }, '
            '{ url = "http://{primary}/x", follow_redirects = true, verify_tls = false }',
        )
    )
    config = load_config(_write(tmp_path, text), {})
    assert config.ping_url == "https://hc.example.test/ping"
    assert config.lock_dir == Path("/var/lock/hcl")
    assert (config.timeout, config.workers, config.send_details) == (2.5, 3, False)
    (only,) = config.checks
    assert only.uuid == UUID_A
    external, internal = only.probes
    assert external.url == "https://example.test/app/"
    assert external.expect == frozenset({200, 401}) and external.send_token
    assert internal.url == "http://10.0.0.5:8080/x"
    assert internal.follow_redirects and not internal.verify_tls


def test_lock_dir_expands_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    config = load_config(_write(tmp_path, '[general]\nlock_dir = "~/locks"\n' + check()), {})
    assert config.lock_dir == tmp_path / "locks"


def test_credentials_come_from_the_environment(tmp_path: Path) -> None:
    text = '[auth.nagios]\nuser = "admin"\npassword_env = "NAGIOS_PW"\n\n' + check(
        probes='{ url = "http://example.test/", auth = "nagios" }'
    )
    config = load_config(_write(tmp_path, text), {"NAGIOS_PW": "hunter2"})
    credentials = config.checks[0].probes[0].auth
    assert credentials == Credentials("admin", "hunter2")
    assert "hunter2" not in repr(credentials)


def test_statuspage_check(tmp_path: Path) -> None:
    text = (
        f'[[check]]\nname = "plex_auth"\nuuid = "{UUID_A}"\nkind = "statuspage"\n'
        'url = "https://status.example.test/api/v2/components.json"\ncomponent = "Authentication"\n'
    )
    (only,) = load_config(_write(tmp_path, text), {}).checks
    assert only.kind == "statuspage" and only.component == "Authentication"
    assert only.probes[0].url == "https://status.example.test/api/v2/components.json"


def test_disabled_check_needs_no_uuid_host_or_password(tmp_path: Path) -> None:
    text = (
        '[hosts]\nunraid = ""\n\n[auth.nas]\nuser = ""\npassword_env = "UNSET"\n\n'
        '[[check]]\nname = "off"\nenabled = false\n'
        'probes = [{ url = "http://{unraid}/login", auth = "nas" }, { url = "http://{nowhere}/" }]\n'
    )
    (only,) = load_config(_write(tmp_path, text), {}).checks
    assert not only.enabled and only.uuid == ""
    assert only.probes[0].url == "http://{unraid}/login"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("[gneral]\n", "unknown key 'gneral' (did you mean 'general'?)"),
        ('[general]\nping_ur = "x"\n', "[general]: unknown key 'ping_ur' (did you mean 'ping_url'?)"),
        ("general = 1\n", "[general] must be a table"),
        ('check = "x"\n', "check must be a list of tables"),
        ('[general]\nping_url = "ftp://hc.example.test"\n', "ping_url must start with http:// or https://"),
        ('[general]\nlock_dir = "locks"\n', "lock_dir must be an absolute path"),
        ("[general]\ntimeout = 0\n", "timeout must be a number from 1 to 300"),
        ("[general]\nworkers = true\n", "workers must be a whole number from 1 to 64"),
        ("[general]\nworkers = 2.5\n", "workers must be a whole number"),
        ("[general]\nsend_details = 1\n", "send_details must be true or false"),
        ('[hosts]\nbad = "a/b"\n', "[hosts]: bad must be a host name or an IP address"),
        ('[hosts]\n1st = "a"\n', "'1st' must start with a letter"),
        ('[auth.x]\nuser = "u"\n', "[auth.x]: password_env is required"),
        ('[auth.x]\nuser = "u"\npassword_env = "P"\npass = "p"\n', "[auth.x]: unknown key 'pass'"),
        ('[[check]]\nuuid = "x"\n', "check #1: name is required"),
        ('[[check]]\nname = "a b"\n', "check #1: name must start with a letter or digit"),
        (check(extra="enabeld = true"), "check 'app': unknown key 'enabeld' (did you mean 'enabled'?)"),
        (check(uuid=""), "check 'app': an enabled check needs a uuid"),
        (check(uuid="not-a-uuid"), "check 'app': uuid must look like"),
        (check(extra='kind = "tcp"'), 'kind must be "http" or "statuspage"'),
        (check(extra='component = "x"'), 'component is only for kind = "statuspage"'),
        (check(probes=""), "probes must be a list with at least one probe"),
        (check(probes='{ urll = "http://x.test/" }'), "probe 1: unknown key 'urll' (did you mean 'url'?)"),
        (check(probes='{ url = "" }'), "probe 1: url is required"),
        (check(probes='{ url = "ftp://x.test/" }'), "url must start with http:// or https://"),
        (check(probes='{ url = "http://x .test/" }'), "url contains a space or a control character"),
        (check(probes='{ url = "http://x.test:99999/" }'), "url is not a valid URL"),
        (check(probes='{ url = "http://{nope}/" }'), "unknown host '{nope}'; add it to [hosts]"),
        (check(probes='{ url = "http://x.test/", expect = [] }'), "expect must be a list of HTTP status codes"),
        (check(probes='{ url = "http://x.test/", expect = [true] }'), "expect must be a list of HTTP status codes"),
        (check(probes='{ url = "http://x.test/", expect = [999] }'), "expect must be a list of HTTP status codes"),
        (check(probes='{ url = "http://x.test/", follow_redirects = "yes" }'), "follow_redirects must be true"),
        (check(probes='{ url = "http://x.test/", auth = 1 }'), "auth must be a string"),
        (check(probes='{ url = "http://x.test/", auth = "nagois" }'), "no [auth.nagois] table"),
        (check() + check(uuid=UUID_B), "two checks are named 'app'"),
        (check() + check(name="other"), "checks 'app' and 'other' have the same uuid"),
        (
            f'[[check]]\nname = "s"\nuuid = "{UUID_A}"\nkind = "statuspage"\nurl = "https://x.test/"\n',
            "component is required",
        ),
        (
            (
                f'[[check]]\nname = "s"\nuuid = "{UUID_A}"\nkind = "statuspage"\nurl = "https://x.test/"\n'
                'component = "c"\nprobes = []\n'
            ),
            'probes are not used with kind = "statuspage"',
        ),
    ],
)
def test_invalid_config(tmp_path: Path, text: str, message: str) -> None:
    with pytest.raises(ConfigError) as error:
        load_config(_write(tmp_path, text), {})
    assert message in str(error.value)
    assert str(tmp_path) in str(error.value)


def test_host_suggestion(tmp_path: Path) -> None:
    text = '[hosts]\nprimary = "10.0.0.1"\n\n' + check(probes='{ url = "http://{primray}/" }')
    with pytest.raises(ConfigError, match=r"did you mean 'primary'\?"):
        load_config(_write(tmp_path, text), {})


def test_empty_host_in_enabled_check(tmp_path: Path) -> None:
    text = '[hosts]\nunraid = ""\n\n' + check(probes='{ url = "http://{unraid}/login" }')
    with pytest.raises(ConfigError, match=r"url uses \{unraid\}, but \[hosts\] unraid is empty"):
        load_config(_write(tmp_path, text), {})


def test_password_in_url_is_refused_without_showing_it(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as error:
        load_config(_write(tmp_path, check(probes='{ url = "http://admin:s3cret@x.test/" }')), {})
    assert "must not contain a user name or password" in str(error.value)
    assert "s3cret" not in str(error.value)


def test_missing_password_variable(tmp_path: Path) -> None:
    text = '[auth.nas]\nuser = "admin"\npassword_env = "NAS_PW"\n\n' + check(
        probes='{ url = "http://x.test/", auth = "nas" }'
    )
    with pytest.raises(ConfigError, match="the environment variable NAS_PW is not set"):
        load_config(_write(tmp_path, text), {})


def test_empty_auth_user(tmp_path: Path) -> None:
    text = '[auth.nas]\nuser = ""\npassword_env = "NAS_PW"\n\n' + check(
        probes='{ url = "http://x.test/", auth = "nas" }'
    )
    with pytest.raises(ConfigError, match=r"\[auth.nas\] user is empty"):
        load_config(_write(tmp_path, text), {"NAS_PW": "pw"})


def test_invalid_toml(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as error:
        load_config(_write(tmp_path, "[general\n"), {})
    assert str(tmp_path) in str(error.value)


def test_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="No such file"):
        load_config(tmp_path / "missing.toml", {})


def test_example_config_loads_with_every_check_disabled() -> None:
    config = load_config(EXAMPLE, {})
    names = [check.name for check in config.checks]
    assert len(names) == len(set(names)) == 57
    assert not any(check.enabled for check in config.checks)
    assert "plex_auth" in names and "rutorrent" in names


def test_example_config_loads_with_every_check_enabled(tmp_path: Path) -> None:
    text = EXAMPLE.read_text(encoding="utf-8")
    counter = iter(range(1, 1000))
    text = re.sub(r'uuid = ""', lambda _: f'uuid = "00000000-0000-4000-8000-{next(counter):012d}"', text)
    text = text.replace("enabled = false", "enabled = true").replace('user = ""', 'user = "admin"')
    text = re.sub(r'^(\w+) = ""$', r'\1 = "10.0.0.9"', text, flags=re.MULTILINE)
    env = {"HCL_NAGIOS_PASSWORD": "pw", "HCL_READYNAS_PASSWORD": "pw"}
    config = load_config(_write(tmp_path, text), env)
    assert all(check.enabled for check in config.checks)
    for item in config.checks:
        for probe in item.probes:
            assert "{" not in probe.url, (item.name, probe.url)


def test_find_config_explicit(tmp_path: Path) -> None:
    path = _write(tmp_path, "")
    assert find_config(path, {}, []) == path
    with pytest.raises(ConfigError, match="config file does not exist"):
        find_config(tmp_path / "missing.toml", {}, [])


def test_find_config_from_environment(tmp_path: Path) -> None:
    path = _write(tmp_path, "")
    assert find_config(None, {"HCL_CONFIG": str(path)}, []) == path


def test_find_config_search_order(tmp_path: Path) -> None:
    first, second = tmp_path / "a.toml", tmp_path / "b.toml"
    second.write_text("", encoding="utf-8")
    assert find_config(None, {}, [first, second]) == second
    first.write_text("", encoding="utf-8")
    assert find_config(None, {}, [first, second]) == first


def test_find_config_none_found(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match=r"copy healthchecks\.example\.toml to"):
        find_config(None, {}, [tmp_path / "a.toml"])


def test_config_search_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "bin" / "healthchecks_linux.py"
    assert config_search_paths(script, {"XDG_CONFIG_HOME": "/xdg"}) == [
        tmp_path / "bin" / "healthchecks.toml",
        Path("/xdg/healthchecks-linux/healthchecks.toml"),
    ]
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config_search_paths(script, {"XDG_CONFIG_HOME": "relative"})[1] == (
        tmp_path / ".config" / "healthchecks-linux" / "healthchecks.toml"
    )


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "healthchecks.toml"
    path.write_text(text, encoding="utf-8")
    return path
