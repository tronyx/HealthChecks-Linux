# 🩺 HealthChecks Linux

[![CodeFactor](https://www.codefactor.io/repository/github/tronyx/healthchecks-linux/badge)](https://www.codefactor.io/repository/github/tronyx/healthchecks-linux)
[![Tests](https://github.com/tronyx/HealthChecks-Linux/actions/workflows/tests.yml/badge.svg)](https://github.com/tronyx/HealthChecks-Linux/actions/workflows/tests.yml)
[![Made with Python](https://img.shields.io/badge/made%20with-Python-3776ab.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE.md)
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/tronyx/healthchecks-linux.svg)](http://isitmaintained.com/project/tronyx/healthchecks-linux "Average time to resolve an issue")
[![Percentage of issues still open](http://isitmaintained.com/badge/open/tronyx/healthchecks-linux.svg)](http://isitmaintained.com/project/tronyx/healthchecks-linux "Percentage of issues still open")

HealthChecks Linux tests your self-hosted applications and reports the result of each test to [Healthchecks.io](https://healthchecks.io).

> [!IMPORTANT]
> The Bash script, `application_healthchecks_generic.sh`, is deprecated. It still works, but a future release removes it. See [The Bash script](#-the-bash-script-deprecated) to move your settings to the Python script.

`healthchecks_linux.py` is a Python script. For each application, it sends one or more HTTP requests, called probes. Usually there are two probes:

- The external probe goes to the reverse proxy URL of the application, for example `https://domain.com/sonarr/`. A reverse proxy is a web server that makes an internal application available on your domain.
- The internal probe goes directly to the IP address and the port of the application, for example `http://192.168.1.103:8989`.

If each probe returns the expected status code, the script sends a success ping to the Healthchecks.io check of the application. If a probe returns a different code, or no answer, the script sends a fail ping. Healthchecks.io then sends you an alert. Each ping includes the result of each probe, so you can see in Healthchecks.io which probe failed.

The external probes can send your [Organizr](https://github.com/causefx/Organizr) API key in a `token` header. Thus, the probes get through the Organizr authentication on your reverse proxy.

> [!NOTE]
> Each setup is different. You can use a subfolder where the example configuration uses a subdomain, or the opposite. Thus, you will probably need to change some URLs before all the checks pass. See [Troubleshooting](#-troubleshooting).

## ✨ Features

The script has these features:

- 🌐 It tests the reverse proxy URL and the internal URL of each application.
- 📋 Its example configuration has checks for 57 applications and services, for example Plex, Sonarr, Radarr, Organizr, and Unifi. See [Supported applications](#-supported-applications).
- 🔐 It works with Organizr authentication. It sends your Organizr API key only to your applications, never to Healthchecks.io. You can also use it without Organizr.
- 🏠 It works with Healthchecks.io and with a self-hosted Healthchecks server.
- ⚡ It runs several checks at the same time. If a run is still busy when the next run starts, the next run stops, so two runs never overlap.
- ⏸️ It skips a check when a lock file for that check exists. It skips all the checks when the global lock file exists. Thus, you can pause the checks for maintenance.
- 🤝 It works with [Tronitor](https://github.com/tronyx/tronitor), which creates and removes the lock files for you.
- 🧪 Its `--dry-run` option tests your applications and shows the results, but sends no pings.

## 📦 Requirements

You must have these tools on the host that runs the script:

| Tool | Why the script needs it |
| --- | --- |
| Python 3.11 or newer | The script is a Python script. Python 3.10 also works if you install the `tomli` package (`sudo apt install python3-tomli`, or `python3 -m pip install --user tomli`) |
| Linux or macOS | The script uses file locks that Windows does not have |
| cron | Optional. Runs the script on a schedule. See [Scheduling](#%EF%B8%8F-scheduling) |

The script uses only the Python standard library. You do not have to install other packages.

You must also have a [Healthchecks.io](https://healthchecks.io) account, or a self-hosted Healthchecks server. Create one check for each application that you want to monitor.

## 🚀 Quick start

1. Download the script:

   ```bash
   git clone https://github.com/tronyx/HealthChecks-Linux.git
   cd HealthChecks-Linux
   ```

2. Copy the example configuration file:

   ```bash
   cp healthchecks.example.toml healthchecks.toml
   ```

3. Open `healthchecks.toml` in a text editor. In the `[hosts]` table, set `domain` to your domain and `primary` to the IP address of your server. See [Configuration](#%EF%B8%8F-configuration).

4. For each application that you want to monitor, find its `[[check]]` table. Set `uuid` to the UUID of its Healthchecks.io check, and set `enabled = true`. If necessary, change the URLs of its probes.

5. If you use Organizr, put your Organizr API key in the `HCL_ORGANIZR_TOKEN` environment variable:

   ```bash
   export HCL_ORGANIZR_TOKEN='your-organizr-api-key'
   ```

6. Test the checks. The `--dry-run` option shows the status code of each probe, and sends no pings:

   ```bash
   python3 healthchecks_linux.py --dry-run
   ```

   Make sure that each check shows `PASS`.

7. Run the script on a schedule. See [Scheduling](#%EF%B8%8F-scheduling).

## ⚙️ Configuration

The configuration file uses [TOML](https://toml.io), a simple text format for configuration. `healthchecks.example.toml` has a comment for each setting.

The script reads the first configuration file that it finds, in this order:

1. The file that the `--config` option names.
2. The file that the `HCL_CONFIG` environment variable names.
3. `healthchecks.toml` in the folder of the script.
4. `~/.config/healthchecks-linux/healthchecks.toml`.

If the file has an error, the script shows the error and its location, and runs no checks. For an unknown name, it also suggests the closest known name.

### The general table

The `[general]` table applies to all the checks. All of its settings are optional:

| Setting | What it does | Default |
| --- | --- | --- |
| `ping_url` | The ping URL of Healthchecks. If you host Healthchecks yourself, set it to your own ping URL | `https://hc-ping.com` |
| `lock_dir` | The folder for the lock files. It must be an absolute path. See [Pausing checks](#%EF%B8%8F-pausing-checks) | `/tmp` |
| `timeout` | The number of seconds that a probe waits for each answer | `10` |
| `workers` | The number of checks that run at the same time | `8` |
| `send_details` | If `true`, each ping includes the URL and the result of each probe. If `false`, the pings are empty | `true` |

### The hosts table

Each name in the `[hosts]` table is a placeholder. In a probe URL, the script replaces `{name}` with the value of the name:

```toml
[hosts]
domain = "domain.com"
primary = "192.168.1.103"
nas = "192.168.1.20:5000"
```

With these values, `https://{domain}/sonarr/` becomes `https://domain.com/sonarr/`. You can add more names, for example for a second server or a second domain. A value can include a port.

### Checks

Each `[[check]]` table is one check:

| Setting | What it does |
| --- | --- |
| `name` | The name of the check. The `--only` option and the output use it |
| `uuid` | The UUID of the Healthchecks.io check. An enabled check must have one |
| `enabled` | If `false`, the script skips the check. The default is `true` |
| `probes` | The list of probes. The check passes only if each probe passes |

Each probe is one GET request. A probe has these settings:

| Setting | What it does | Default |
| --- | --- | --- |
| `url` | The URL. It can use the names from `[hosts]` | |
| `expect` | The list of status codes that pass, for example `[200, 401]` | `[200]` |
| `follow_redirects` | If `true`, the probe follows redirects and tests the final URL | `false` |
| `verify_tls` | If `false`, the probe accepts any HTTPS certificate. Use it for a self-signed certificate on your own network | `true` |
| `send_token` | If `true`, the probe sends your Organizr API key in a `token` header | `false` |
| `auth` | The name of an `[auth.<name>]` table. See [Secrets](#-secrets) | |

This check tests Sonarr through the reverse proxy and on the server:

```toml
[[check]]
name = "sonarr"
uuid = "31365bce-8da9-4729-8ff3-aaa71d56b712"
enabled = true
probes = [
  { url = "https://{domain}/sonarr/", send_token = true },
  { url = "http://{primary}:9898/sonarr/" },
]
```

The `plex_auth` check is different. Its `kind` is `"statuspage"`. It does not test your server. It reads the [Plex status page](https://status.plex.tv/), and it fails when the Plex authentication service is not operational.

### 🔐 Secrets

The configuration file does not hold secrets. The script reads them from environment variables:

| Environment variable | What it holds |
| --- | --- |
| `HCL_ORGANIZR_TOKEN` | Your Organizr API key. The probes that have `send_token = true` send it |
| The `password_env` of each `[auth.<name>]` table | The password for HTTP basic authentication, for example `HCL_NAGIOS_PASSWORD` |

HTTP basic authentication sends a user name and a password with each request. Some applications, for example Nagios, use it. An `[auth.<name>]` table holds the user name and the name of the environment variable:

```toml
[auth.nagios]
user = "nagiosadmin"
password_env = "HCL_NAGIOS_PASSWORD"
```

A probe with `auth = "nagios"` then sends this user name and password.

The script sends the API key and the passwords only to the URL of the probe. It never sends them to Healthchecks.io. If a probe follows a redirect to a different host, the script does not send them to that host.

### 🔓 Without Organizr

If you do not use Organizr, do not set `HCL_ORGANIZR_TOKEN`. Then the probes send no `token` header. You do not have to change `send_token`.

### 🚫 Without a reverse proxy

If an application has no reverse proxy (no external access), remove its external probe. Then the check has only the internal probe.

The `unraid`, `vcenter`, and `readynas` checks already have only an internal probe, because you must not put these admin pages on the internet. The `xbackbone` and `zipline` checks have only an external probe, because these applications redirect internal requests to their domain.

## 💻 Command line

```text
python3 healthchecks_linux.py [options]
```

| Option | What it does |
| --- | --- |
| `-c PATH`, `--config PATH` | Read this configuration file. See [Configuration](#%EF%B8%8F-configuration) |
| `-n`, `--dry-run` | Test the applications and show the results, but send no pings |
| `-l`, `--list` | Show each check with its UUID and its state: enabled, disabled, or paused |
| `--only NAME[,NAME...]` | Run only these checks |
| `-v`, `--verbose` | Show the result of each check |
| `-V`, `--version` | Show the version |

Without `--verbose` or `--dry-run`, the script shows output only for a problem, for example a ping that did not reach Healthchecks.io. The script stops with one of these exit codes:

| Exit code | Meaning |
| --- | --- |
| `0` | Each ping was sent. With `--dry-run`, each check passed |
| `1` | A ping was not sent. With `--dry-run`, a check failed |
| `2` | The configuration or the command line has an error |

## 📋 Supported applications

The example configuration has a check for each of these applications:

| | | | |
| --- | --- | --- | --- |
| AdGuard | Bazarr | Bitwarden | Chevereto |
| Dashbrr | Deluge | Dozzle | Filebrowser |
| Forgejo | Gitea | GitLab | Grafana |
| Guacamole | Immich | Jackett | Komodo |
| Lidarr | Logarr | Mediabutler | Monitorr |
| Nagios | Navidrome | Netdata | Netronome |
| Nextcloud | Notifiarr | NZBGet | NZBHydra / NZBHydra2 |
| Ombi | Organizr | Overseerr | Petio |
| Pi-hole | Plex | Plex authentication service (`plex_auth`) | PLPP (`library`) |
| Portainer | Prowlarr | qBittorrent | qui |
| Radarr | ReadyNAS | ruTorrent | SABnzbd |
| Snipe-IT | Sonarr | Tautulli | Tdarr |
| TheLounge | Tracearr | Transmission | Unifi Controller |
| Unifi Protect | Unraid | vCenter | XBackBone |
| Zipline | | | |

The name of each check is the name of the application in lowercase, for example `sonarr`.

To add an application, copy a `[[check]]` table that is similar. Then change its name, its UUID, and its probes.

## ⏱️ Scheduling

When all the checks pass, use cron to run the script automatically. This crontab entry runs the script every two minutes. The first line sets the environment variable for the script:

```bash
HCL_ORGANIZR_TOKEN=your-organizr-api-key
## Run application healthchecks script for Healthchecks.io
*/2 * * * * /usr/bin/python3 /home/tronyx/HealthChecks-Linux/healthchecks_linux.py
```

The crontab of each user is private to that user and to root. Thus, other users cannot read the API key in it.

The script shows output only when an error occurs, and cron sends you an email for each output. Thus, you get an email only when a ping fails or the configuration has an error.

Set the period and the grace time of each Healthchecks.io check to agree with the schedule. My checks use a period of two minutes and a grace time of three minutes.

## ⏸️ Pausing checks

The script uses lock files to pause checks, for example during maintenance. The lock files are in the `lock_dir` folder:

| Lock file | Result |
| --- | --- |
| `healthchecks.lock` | The script stops and runs no checks |
| `<uuid>.lock` | The script skips the check that has this UUID |

While a check is paused, the script sends no ping for it. If you also pause the check in Healthchecks.io, you get no alerts.

The script also keeps the file `.healthchecks-linux.run` in the `lock_dir` folder. It uses this file to make sure that only one run occurs at a time. Do not delete it while the script runs.

### 🤝 With Tronitor

[Tronitor](https://github.com/tronyx/tronitor) pauses and unpauses your Healthchecks.io checks, manually or on a schedule. It also creates and removes the lock files. Tronitor and the script both use `/tmp` by default. Thus, the two work together with no change.

If you use a different folder, set the same folder in both places: `lock_dir` in `tronitor.toml`, and `lock_dir` in `healthchecks.toml`. For example:

```toml
[general]
lock_dir = "/tmp/tronitor"
```

If the two folders are different, the script does not see the lock files, and it pings the paused checks.

All users on the computer can write to `/tmp`. Thus, other users can create or delete the lock files. On a computer that other people use, set both values to a folder that only you can write to.

> [!NOTE]
> Older versions of this README told you to set `tempDir='/tmp/tronitor/'` in the Bash script. That was for the old Bash version of Tronitor. If you made that change, change `tempDir` back to `'/tmp/'`, or set `lock_dir = "/tmp/tronitor"` in `tronitor.toml`.

## 🩺 Troubleshooting

> [!TIP]
> Run `python3 healthchecks_linux.py --dry-run` to see the status code of each probe. Add `--only <name>` to test one check.

| Problem | What to do |
| --- | --- |
| A probe returns `301` or `302` | The URL redirects to a different URL. Find the final URL with the command below, and use that URL in the probe. Or set `follow_redirects = true` |
| An Arr application with a login page fails | If you turned on the login page (authentication) in Sonarr, Radarr, Prowlarr, or another Arr application, add `login` to the URLs, for example `https://{domain}/sonarr/login` |
| An external probe fails, but the internal probe passes | Make sure that the subdomain or the subfolder in the probe agrees with your reverse proxy. If you use Organizr, make sure that `HCL_ORGANIZR_TOKEN` is correct and that the probe has `send_token = true` |
| A probe shows `error: timed out` or `Connection refused` | The script did not get an answer. Make sure that the address and the port are correct, and that the host that runs the script can connect to them |
| A probe shows `CERTIFICATE_VERIFY_FAILED` | The HTTPS certificate is not valid, for example because it is self-signed. If the address is on your own network, set `verify_tls = false` on the probe |
| The script shows `the previous run is still going, so this run is skipped` | A run takes longer than the time between two runs. Lower `timeout`, increase `workers`, or run the script less often |
| The script shows `an enabled check needs a uuid` | Set the `uuid` of the check, or set `enabled = false` |

This command shows the final URL after all the redirects. Replace `http://domain.com` with the URL of the application:

```bash
curl -Ls -o /dev/null -w %{url_effective} http://domain.com
```

## 🐚 The Bash script (deprecated)

`application_healthchecks_generic.sh` is the old Bash version. It still works, but a future release removes it. To move to the Python script, copy `healthchecks.example.toml` to `healthchecks.toml`, and move each setting:

| Bash script | `healthchecks.toml` |
| --- | --- |
| `domain` | `domain` in `[hosts]` |
| `primaryServerAddress` | `primary` in `[hosts]` |
| `unraidServerAddress`, `unifiControllerAddress`, `vCenterServerAddress`, `rNasServerAddress` | `unraid`, `unifi`, `vcenter`, `readynas` in `[hosts]` |
| `orgAPIKey` | The `HCL_ORGANIZR_TOKEN` environment variable |
| `hcPingDomain` | `ping_url` in `[general]` |
| `tempDir` | `lock_dir` in `[general]`, without the `/` at the end |
| `hcUUID` in `check_<application>` | `uuid` in the `[[check]]` table of the application |
| An uncommented `check_<application>` line in `main` | `enabled = true` in the `[[check]]` table of the application |
| `nagUser` and `nagPass` | `user` in `[auth.nagios]`, and the `HCL_NAGIOS_PASSWORD` environment variable |
| `rNasUser` and `rNasPass` | `user` in `[auth.readynas]`, and the `HCL_READYNAS_PASSWORD` environment variable |

The Python script also works differently in these ways:

- Each probe sends a GET request. The Bash script sent a HEAD request for some applications. Thus, the `radarr_v4` and `sonarr_v4` checks are now the same as `radarr` and `sonarr`.
- The external Plex probe uses `https`. The Bash script used `http`.
- The `plex_auth` check reads the JSON data of the Plex status page. The Bash script read its HTML page.

## 🪟 Windows

The Python script does not run on Windows. [HalianElf](https://github.com/HalianElf) made a PowerShell version of the Bash script for Windows users. Thank you!

## 💬 Questions

If you have questions, you can find me on the [Organizr Discord](https://organizr.app/discord). To report a bug, [open an issue](https://github.com/tronyx/HealthChecks-Linux/issues).

## 📄 License

The license is MIT. See [LICENSE.md](LICENSE.md).
