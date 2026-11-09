# 🩺 HealthChecks Linux

[![CodeFactor](https://www.codefactor.io/repository/github/tronyx/healthchecks-linux/badge)](https://www.codefactor.io/repository/github/tronyx/healthchecks-linux)
[![Made with Bash](https://img.shields.io/badge/made%20with-Bash-1f425f.svg)](https://www.gnu.org/software/bash/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE.md)
[![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/tronyx/healthchecks-linux.svg)](http://isitmaintained.com/project/tronyx/healthchecks-linux "Average time to resolve an issue")
[![Percentage of issues still open](http://isitmaintained.com/badge/open/tronyx/healthchecks-linux.svg)](http://isitmaintained.com/project/tronyx/healthchecks-linux "Percentage of issues still open")

HealthChecks Linux tests your self-hosted applications and reports the result of each test to [Healthchecks.io](https://healthchecks.io).

`application_healthchecks_generic.sh` is a Bash script. For each application, it sends two HTTP requests:

- The external request goes to the reverse proxy URL of the application, for example `https://domain.com/sonarr/`. A reverse proxy is a web server that makes an internal application available on your domain.
- The internal request goes directly to the IP address and the port of the application, for example `http://192.168.1.103:8989`.

If both requests return HTTP `200`, the script sends a success ping to the Healthchecks.io check of the application. If one of the requests returns a different code, the script sends a fail ping. Healthchecks.io then sends you an alert.

The external requests send your [Organizr](https://github.com/causefx/Organizr) API key in a `token` header. Thus, the requests get through the Organizr authentication on your reverse proxy.

> [!NOTE]
> Each setup is different. You can use a subfolder where the script uses a subdomain, or the opposite. Thus, you will probably need to change some URLs in the script before all the checks pass. See [Troubleshooting](#-troubleshooting).

## ✨ Features

The script has these features:

- 🌐 It tests the reverse proxy URL and the internal URL of each application.
- 📋 It has checks for 59 applications and services, for example Plex, Sonarr, Radarr, Organizr, and Unifi. See [Supported applications](#-supported-applications).
- 🔐 It works with Organizr authentication. You can also use it without Organizr.
- 🏠 It works with Healthchecks.io and with a self-hosted Healthchecks server.
- ⏸️ It skips a check when a lock file for that check exists. It skips all the checks when the global lock file exists. Thus, you can pause the checks for maintenance.
- 🤝 It works with [Tronitor](https://github.com/tronyx/tronitor), which creates and removes the lock files for you.

## 📦 Requirements

You must have these tools on the host that runs the script:

| Tool | Why the script needs it |
| --- | --- |
| Bash | The script is a Bash script |
| cURL | The script uses `curl` to test the applications and to send the pings |
| cron | Optional. Runs the script on a schedule. See [Scheduling](#-scheduling) |

You must also have a [Healthchecks.io](https://healthchecks.io) account, or a self-hosted Healthchecks server. Create one check for each application that you want to monitor.

## 🚀 Quick start

1. Download the script:

   ```bash
   git clone https://github.com/tronyx/HealthChecks-Linux.git
   cd HealthChecks-Linux
   ```

2. Open `application_healthchecks_generic.sh` in a text editor, and set the variables at the top of the script. See [Configuration](#%EF%B8%8F-configuration).

3. For each application that you want to monitor, edit its `check_<application>` function. Set the `hcUUID` variable to the UUID of the Healthchecks.io check. If necessary, change the port, the subdomain, or the subfolder.

4. In the `main` function at the bottom of the script, remove the `#` at the start of the line for each check that you want to run. Only `check_organizr` runs by default.

5. Run the script with tracing on. The `-x` option shows each command and each response code:

   ```bash
   bash -x application_healthchecks_generic.sh
   ```

   Make sure that each `extResponse` and each `intResponse` is `200`.

6. Run the script on a schedule. See [Scheduling](#-scheduling).

## ⚙️ Configuration

The variables at the top of the script apply to all the checks:

| Variable | What it does |
| --- | --- |
| `domain` | The primary domain of your reverse proxies, for example `domain.com` |
| `orgAPIKey` | Your Organizr API key. The external requests send it in the `token` header |
| `primaryServerAddress` | The IP address of the server that runs most of your applications |
| `hcPingDomain` | The ping URL of Healthchecks (default: `https://hc-ping.com/`). If you host Healthchecks yourself, set it to your own ping URL |
| `unraidServerAddress` | The IP address or the hostname of your Unraid server |
| `unifiControllerAddress` | The IP address or the hostname of your Unifi Controller |
| `vCenterServerAddress` | The IP address or the hostname of your vCenter server |
| `rNasServerAddress` | The IP address or the hostname of your ReadyNAS |
| `secondaryDomain` | A second domain, if some of your applications use one |
| `tempDir` | The folder for the lock files (default: `/tmp/`). See [Pausing checks](#%EF%B8%8F-pausing-checks) |

Each `check_<application>` function has its own variables:

| Variable | What it does |
| --- | --- |
| `hcUUID` | The UUID of the Healthchecks.io check for the application. You must set it |
| `appPort` | The port of the application on the internal address |
| `subDomain` | The subdomain of the application, for example `sonarr` for `sonarr.domain.com` |
| `subDir` | The subfolder of the application, for example `/sonarr/` for `domain.com/sonarr/` |

You can add more server variables. For example, if you have more than one server, add a variable for each server and use it in the functions.

### 🔓 Without Organizr

If you do not use Organizr, remove this text from the external `curl` command of each check that you use:

```bash
 -H "token: ${orgAPIKey}"
```

Remove the space at the start of the text too.

### 🚫 Without a reverse proxy

If an application has no reverse proxy (no external access), set the external response to `200` in its function. Then the external part of the check always passes:

```bash
extResponse='200'
```

The `check_unraid`, `check_vcenter`, and `check_readynas` functions already do this, because you must not put these admin pages on the internet. The `check_xbackbone` and `check_zipline` functions do the opposite. They set `intResponse='200'`, because these applications redirect internal requests to their domain.

## 📋 Supported applications

The script has a function for each of these applications:

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
| Pi-hole | Plex | Plex authentication service | PLPP (`check_library`) |
| Portainer | Prowlarr | qBittorrent | qui |
| Radarr | Radarr v4 | ReadyNAS | ruTorrent |
| SABnzbd | Snipe-IT | Sonarr | Sonarr v4 |
| Tautulli | Tdarr | TheLounge | Tracearr |
| Transmission | Unifi Controller | Unifi Protect | Unraid |
| vCenter | XBackBone | Zipline | |

The name of each function is `check_` and the name of the application in lowercase, for example `check_sonarr`. The `check_plex_auth` function does not test your server. It reads the [Plex status page](https://status.plex.tv/), and it fails when the Plex authentication service is not operational.

To add an application, copy a function that is similar, change the name and the variables, and add the function to `main`.

## ⏱️ Scheduling

When all the checks pass, use cron to run the script automatically. This crontab entry runs the script every two minutes:

```bash
## Run application healthchecks script for Healthchecks.io
*/2 * * * * /home/tronyx/scripts/application_healthchecks.sh
```

Set the period and the grace time of each Healthchecks.io check to agree with the schedule. My checks use a period of two minutes and a grace time of three minutes.

## ⏸️ Pausing checks

The script uses lock files to pause checks, for example during maintenance:

| Lock file | Result |
| --- | --- |
| `${tempDir}healthchecks.lock` | The script stops and runs no checks |
| `${tempDir}<hcUUID>.lock` | The script skips the check that has this UUID |

While a check is paused, the script sends no ping for it. If you also pause the check in Healthchecks.io, you get no alerts.

### 🤝 With Tronitor

[Tronitor](https://github.com/tronyx/tronitor) pauses and unpauses your Healthchecks.io checks, manually or on a schedule. It also creates the lock files in `/tmp/tronitor/`. To use the script with Tronitor, change the `tempDir` variable at the top of the script:

```bash
#tempDir='/tmp/'
tempDir='/tmp/tronitor/'
```

## 🩺 Troubleshooting

> [!TIP]
> Run `bash -x application_healthchecks_generic.sh` to see the response code of each request.

| Problem | What to do |
| --- | --- |
| A request returns `302` | The URL redirects to a different URL. Find the final URL with the command below, and use that URL in the function |
| An Arr application with a login page fails | If you turned on the login page (authentication) in Sonarr, Radarr, Prowlarr, or another Arr application, add `/login` to the URL |
| An external request fails, but the internal request passes | Make sure that the subdomain or the subfolder in the function agrees with your reverse proxy. If you use Organizr, make sure that `orgAPIKey` is correct |
| A request returns `000` | The script could not connect in 10 seconds. Make sure that the address and the port are correct, and that the host that runs the script can connect to them |
| A newer version of the application fails | Some functions, for example `check_lidarr` and `check_unifi_controller`, have a second `curl` command in a comment for newer versions. Use that command |

This command shows the final URL after all the redirects. Replace `http://domain.com` with the URL of the application:

```bash
curl -Ls -o /dev/null -w %{url_effective} http://domain.com
```

## 🪟 Windows

[HalianElf](https://github.com/HalianElf) made a PowerShell version of the script for Windows users. Thank you!

## 💬 Questions

If you have questions, you can find me on the [Organizr Discord](https://organizr.app/discord). To report a bug, [open an issue](https://github.com/tronyx/HealthChecks-Linux/issues).

## 📄 License

The license is MIT. See [LICENSE.md](LICENSE.md).
