"""Tests for --migrate: writing healthchecks.toml from a configured copy of the Bash script."""

import stat
from pathlib import Path

import pytest
from conftest import UUID_A, UUID_B

from healthchecks_linux import Credentials, load_config, main, migrate_bash

REPO_SCRIPT = Path(__file__).resolve().parent.parent / "application_healthchecks_generic.sh"
UUID_C = "5e2f8c1a-7b3d-4f9e-a6c0-1d2e3f4a5b6c"
UUID_D = "6f3a9d2b-8c4e-4a0f-b7d1-2e3f4a5b6c7d"

CONFIGURED = f"""#!/usr/bin/env bash
domain='example.test'
orgAPIKey='org-s3cret'
dockerServerAddress='10.0.0.5'
unifiNVRAddress='10.0.0.6'
emptyServerAddress=''
badServerAddress='a/b'
tempDir='/tmp/tronitor/'
healthchecksLockFile="${{tempDir}}healthchecks.lock"
hcPingDomain='https://hc.example.test/ping/'

check_lock_file() {{
    main
}}

check_sonarr() {{
    appPort='9898'
    subDir='/sonarr/'
    hcUUID='{UUID_A.upper()}'
    extResponse=$(curl -w "%{{http_code}}\\n" -sIL -o /dev/null --connect-timeout 10 -m 10 https://"${{domain}}${{subDir}}" -H "token: ${{orgAPIKey}}")
    #extResponse=$(curl -s https://old.example.test)
    intResponse=$(curl -w "%{{http_code}}\\n" -sIk -o /dev/null --connect-timeout 10 -m 20 http://"${{dockerServerAddress}}":"${{appPort}}""${{subDir}}")
    appLockFile="${{tempDir}}${{hcUUID}}".lock
    if [ -e "${{appLockFile}}" ]; then
        :
    else
        if [[ "${{extResponse}}" = '200' ]] && [[ "${{intResponse}}" = '200' ]]; then
            ping_healthchecks
        fi
    fi
}}

check_nvr() {{
    appPort='7443'
    hcUUID='{UUID_B}'
    extResponse='200'
    intResponse=$(curl -w "%{{http_code}}\\n" -sLk -o /dev/null https://"${{unifiNVRAddress}}":"${{appPort}}")
    if [[ "${{extResponse}}" = '200' ]] && [[ "${{intResponse}}" = '200' ]]; then
        ping_healthchecks
    fi
}}

check_rutorrent() {{
    hcUUID='{UUID_C}'
    extResponse=$(curl -w "%{{http_code}}\\n" -s -o /dev/null https://rutorrent."${{domain}}" -H "token: ${{orgAPIKey}}")
    intResponse=$(curl -w "%{{http_code}}\\n" -s -o /dev/null http://"${{dockerServerAddress}}":9080)
    if [[ "${{extResponse}}" = '401' ]] && [[ "${{intResponse}}" = '401' ]]; then
        ping_healthchecks
    fi
}}

check_nagios() {{
    nagUser='nagiosadmin'
    nagPass='nag-s3cret'
    hcUUID='{UUID_D}'
    extResponse=$(curl -u "${{nagUser}}:${{nagPass}}" -w "%{{http_code}}\\n" -sI -o /dev/null https://nagios."${{domain}}""${{subDir}}")
    if [[ "${{extResponse}}" = '200' ]]; then
        ping_healthchecks
    fi
}}

check_plex_auth() {{
    hcUUID='7a4b0e3c-9d5f-4b1a-8c2e-3f4a5b6c7d8e'
    plexAuthStatus=$(curl -s https://status.plex.tv/ | grep -B4 'Authentication and API server')
}}

check_no_uuid() {{
    hcUUID=''
    extResponse=$(curl -s -o /dev/null https://nouuid."${{domain}}")
}}

check_same_uuid() {{
    hcUUID='{UUID_B}'
    extResponse=$(curl -s -o /dev/null https://same."${{domain}}")
}}

check_empty_host() {{
    hcUUID='8b5c1f4d-0e6a-4c2b-9d3f-4a5b6c7d8e9f'
    extResponse=$(curl -s -o /dev/null http://"${{emptyServerAddress}}"/x)
}}

check_bad_quotes() {{
    hcUUID='9c6d2a5e-1f7b-4d3c-8e4a-5b6c7d8e9fa0'
    extResponse=$(curl -s "https://unclosed.example.test)
}}

check_undefined_host() {{
    hcUUID='0d7e3b6f-2a8c-4e4d-9f5b-6c7d8e9fa0b1'
    extResponse=$(curl -s -o /dev/null http://"${{nowhereServerAddress}}"/x)
}}

main() {{
    check_sonarr
    check_nvr
    check_rutorrent
    check_nagios
    check_plex_auth
    check_no_uuid
    check_same_uuid
    check_empty_host
    check_bad_quotes
    check_undefined_host
    check_missing
    check_sonarr
    #check_radarr
    #check_lidarr
}}

check_lock_file
"""


@pytest.fixture
def migrated(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> tuple[Path, str]:
    script = tmp_path / "application_healthchecks_generic.sh"
    script.write_text(CONFIGURED, encoding="utf-8")
    target = tmp_path / "healthchecks.toml"
    assert main(["--migrate", str(script), "-c", str(target)], {}) == 0
    return target, capsys.readouterr().out


def test_migrated_file_is_private_and_loads(migrated: tuple[Path, str]) -> None:
    target, _ = migrated
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    config = load_config(target, {})
    assert config.ping_url == "https://hc.example.test/ping"
    assert config.lock_dir == Path("/tmp/tronitor")
    assert config.timeout == 20
    assert config.organizr_token == "org-s3cret"


def test_migrated_checks(migrated: tuple[Path, str]) -> None:
    config = load_config(migrated[0], {})
    checks = {check.name: check for check in config.checks}
    assert list(checks) == [
        "sonarr",
        "nvr",
        "rutorrent",
        "nagios",
        "plex_auth",
        "no_uuid",
        "same_uuid",
        "empty_host",
        "undefined_host",
    ]
    external, internal = checks["sonarr"].probes
    assert checks["sonarr"].uuid == UUID_A
    assert external.url == "https://example.test/sonarr/"
    assert external.send_token and external.follow_redirects and external.verify_tls
    assert internal.url == "http://10.0.0.5:9898/sonarr/"
    assert not internal.send_token and internal.verify_tls
    (nvr,) = checks["nvr"].probes
    assert nvr.url == "https://10.0.0.6:7443"
    assert nvr.follow_redirects and not nvr.verify_tls
    assert all(probe.expect == frozenset({401}) for probe in checks["rutorrent"].probes)
    assert checks["rutorrent"].probes[1].url == "http://10.0.0.5:9080"
    (nagios,) = checks["nagios"].probes
    assert nagios.url == "https://nagios.example.test"
    assert nagios.auth == Credentials("nagiosadmin", "nag-s3cret")
    assert checks["plex_auth"].kind == "statuspage"
    assert checks["plex_auth"].component == "Authentication and API server"
    assert [name for name, check in checks.items() if not check.enabled] == [
        "no_uuid",
        "same_uuid",
        "empty_host",
        "undefined_host",
    ]


def test_migrated_hosts(migrated: tuple[Path, str]) -> None:
    text = migrated[0].read_text(encoding="utf-8")
    assert '[hosts]\ndomain = "example.test"\ndocker = "10.0.0.5"\nunifi_nvr = "10.0.0.6"\nempty = ""\n' in text


def test_migration_report(migrated: tuple[Path, str]) -> None:
    out = migrated[1]
    for line in (
        "Carried over: ping_url, lock_dir and 4 hosts",
        "Carried over: the Organizr API key, as organizr_token",
        "Skipped: badServerAddress (not a host name or an IP address)",
        "Note: check nagios uses ${subDir} without setting it; it is now empty",
        "Disabled: check no_uuid (hcUUID is empty); fix it, then set enabled = true",
        "Disabled: check same_uuid (check nvr has the same hcUUID)",
        "Disabled: check empty_host ([hosts] empty is empty); fix it, then set enabled = true",
        "Note: check undefined_host uses ${nowhereServerAddress} without setting it; it is now empty",
        "Disabled: check undefined_host (the URL http:///x is not valid)",
        "Skipped: a curl command in check bad_quotes (cannot read its quoting)",
        "Skipped: check bad_quotes (no curl probe to translate)",
        "Skipped: check missing (main runs it, but the script has no check_missing function)",
        "Carried over: 9 checks that main runs",
        "Carried over: the basic auth logins of nagios",
        "Not carried over: 2 checks that main does not run",
        "(readable only by you)",
    ):
        assert line in out
    assert "s3cret" not in out


def test_repo_bash_script() -> None:
    migration = migrate_bash(REPO_SCRIPT.read_text(encoding="utf-8"))
    assert migration.hosts == {
        "domain": "domain.com",
        "primary": "192.168.1.103",
        "unraid": "",
        "unifi": "",
        "vcenter": "",
        "readynas": "",
    }
    assert "Disabled: check organizr (hcUUID is empty); fix it, then set enabled = true" in migration.report
    assert "Not carried over: 58 checks that main does not run; copy them from healthchecks.example.toml" in (
        migration.report
    )


def test_existing_file_needs_force(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = tmp_path / "a.sh"
    script.write_text(CONFIGURED, encoding="utf-8")
    target = tmp_path / "healthchecks.toml"
    target.write_text("keep me\n", encoding="utf-8")
    assert main(["--migrate", str(script), "-c", str(target)], {}) == 2
    assert "already exists; pass --force to overwrite it" in capsys.readouterr().err
    assert target.read_text(encoding="utf-8") == "keep me\n"
    assert main(["--migrate", str(script), "-c", str(target), "--force"], {}) == 0
    assert "org-s3cret" in target.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("#!/usr/bin/env bash\necho hello\n", "does not look like the HealthChecks-Linux Bash script"),
        ("hcPingDomain='https://hc-ping.com/'\n", "does not look like the HealthChecks-Linux Bash script"),
    ],
)
def test_not_the_bash_script(tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str, message: str) -> None:
    script = tmp_path / "other.sh"
    script.write_text(text, encoding="utf-8")
    assert main(["--migrate", str(script), "-c", str(tmp_path / "out.toml")], {}) == 2
    assert message in capsys.readouterr().err
    assert not (tmp_path / "out.toml").exists()


def test_unreadable_script(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--migrate", str(tmp_path / "missing.sh"), "-c", str(tmp_path / "out.toml")], {}) == 2
    assert "cannot read the file" in capsys.readouterr().err


def test_migrate_is_exclusive_with_dry_run() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--migrate", "x.sh", "--dry-run"], {})
    assert exit_info.value.code == 2
