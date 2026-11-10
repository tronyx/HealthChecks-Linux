# 📜 Changelog

The notable changes to HealthChecks Linux, newest first.

The project doesn't use version numbers. Each entry is one merge into `master`, which always has the latest release, and links to its pull request for the full details. `--version` prints the date of the release instead. Changes waiting on `develop` are listed under **Unreleased**.

## Unreleased

HealthChecks Linux is rewritten in Python. The checks are mostly the same, but you must move your settings to a new configuration file. Read the lines marked **Breaking** before you update.

### Changed

- **Breaking:** the script is now `healthchecks_linux.py`, a Python script. It needs Python 3.11 or newer and nothing else, or Python 3.10 with the `tomli` package. It runs on Linux and macOS. The Bash script, `application_healthchecks_generic.sh`, is deprecated. It still works, but a future release removes it.
- **Breaking:** the settings are in a configuration file, `healthchecks.toml`, instead of in the script. Each application is a `[[check]]` table with a list of probes, instead of a function. Copy `healthchecks.example.toml` to `healthchecks.toml`, or run `--migrate` to write it from your Bash script. See [Configuration](README.md#%EF%B8%8F-configuration).
- **Breaking:** each probe sends a GET request. The Bash script sent a HEAD request for some applications, which some applications answer with an error. So the `radarr_v4` and `sonarr_v4` checks are now the same as `radarr` and `sonarr`, and the example configuration has 57 checks instead of 59.
- The external Plex probe in the example configuration uses `https`. The Bash script used `http`.
- The `plex_auth` check reads the JSON data of the Plex status page. The Bash script read its HTML page, so a change to the page broke the check.
- The secrets can be in `healthchecks.toml`: the Organizr API key in `organizr_token`, and the HTTP basic auth passwords in `[auth.<name>]` tables. If other users can open a file that holds a secret, the script stops and shows the `chmod 600` command. The environment variables `HCL_ORGANIZR_TOKEN` and those that `password_env` names win over the file. See [Secrets](README.md#-secrets).
- The script sends the Organizr API key and the passwords only to the URL of the probe. It never sends them to Healthchecks, and after a redirect it sends them only to the same host.

### Added

- `--dry-run` tests the applications and shows the status code of each probe, but sends no pings. It replaces `bash -x`.
- `--list` shows each check with its UUID and its state: enabled, disabled, or paused by a lock file.
- `--only NAME[,NAME...]` runs only some checks, and `--verbose` shows the result of each check.
- `--migrate PATH` writes `healthchecks.toml` from a configured copy of the Bash script. It reads the script as text, and it does not run it. The new file is readable only by you. `--force` lets it replace a file that exists. See [Migrating your settings](README.md#-migrating-your-settings).
- Each probe can list the status codes that pass, for example `expect = [401]`. Before, only `200` passed, so some checks set a response to `200` by hand.
- Each ping includes the URL and the result of each probe, so Healthchecks shows which probe failed. `send_details = false` sends empty pings.
- The checks run at the same time, 8 by default. If a run is still busy when the next run starts, the next run stops, so two runs from cron never overlap.
- The script checks the whole configuration before it runs. For an unknown name, it suggests the closest known name.
- Exit codes: `0` if each ping was sent, `1` if a ping was not sent, and `2` for an error in the configuration or the command line. See [Command line](README.md#-command-line).

### Project

- 141 tests run the script against a local fake server, so they need no account and no network. GitHub runs them on each push, on Python 3.10 and 3.14 on Linux and 3.14 on macOS, with ruff, mypy, and shellcheck for the Bash script.
- The README shows the same badges as Tronitor and Set-Stereo-Default: tests, coverage, Python 3.10+, and license. GitHub combines the coverage of the tests on Linux and macOS for the coverage badge.
- A contributing guide, a pull request template, a security policy, and a code of conduct, in `.github`.
- A `develop` branch. Pull requests go to `develop`, and each release merges `develop` into `master`. A `sync-develop` workflow fast-forwards `develop` to `master` after each release.
- A changelog (this file), linked from the README. The contributing guide and the pull request template ask for a line under **Unreleased** with each change.

## 2026-11-10

These fixes to the Bash script were pushed to `master` without a pull request.

### Security

- The Bash script sent your Organizr API key to Healthchecks in a `token` header, with each success and fail ping. Healthchecks does not need the key. Now the pings send no token.

### Fixed

- The Forgejo, Gitea, and Immich checks added a subfolder to their external URL that they did not set. The Petio check did the same to its internal URL. The Bash script shares its variables between all the checks, so these checks used the subfolder of the check that ran before them, for example `/dozzle/`, and failed.
- The ruTorrent check sent no ping when the external response was `200` and the internal response was `401`. Now each result that does not pass sends a fail ping.
- A ping had no time limit, so a slow Healthchecks server stopped the whole run. Now each ping waits at most 10 seconds.

### Documentation

- The README and the Bash script told you to set `tempDir='/tmp/tronitor/'` for Tronitor. That was for the old Bash version of Tronitor. Tronitor now uses `/tmp` by default, the same as the Bash script, so the two work together with no change.

## Older changes

The changes before 2026-11-10 are in the [commit history](https://github.com/tronyx/HealthChecks-Linux/commits/master).
