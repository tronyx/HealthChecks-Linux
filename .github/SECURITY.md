# 🔒 Security policy

## ✅ Supported versions

The project doesn't use version numbers. Only the latest release is supported: the `master` branch. Fixes aren't made to older copies, so update to the latest before reporting (`git pull`, or download `healthchecks_linux.py` again).

The `develop` branch is the next release in progress. A vulnerability there is welcome too, since fixing it early keeps it out of the next release.

The Bash script, `application_healthchecks_generic.sh`, is deprecated. It gets fixes for serious problems until a future release removes it, but the Python script is the supported way to run the checks.

## 📮 Reporting a vulnerability

**Please don't open a public issue.** Report it privately instead, through GitHub: on the [Security tab](https://github.com/tronyx/HealthChecks-Linux/security), choose **Report a vulnerability**, or go straight to the [form](https://github.com/tronyx/HealthChecks-Linux/security/advisories/new). Only you and the maintainer can see the report.

It helps to include:

- what an attacker could do, and what they'd need first (for example, an account on the same computer, or control of a server that a probe tests);
- how to reproduce it: the command, and your `healthchecks.toml` with `organizr_token` and every `password` removed;
- your operating system and your Python version (`python3 --version`).

If you can't use the form, [open an issue](https://github.com/tronyx/HealthChecks-Linux/issues) asking for a private way to get in touch, with no details of the problem.

## ⏱️ What to expect

This project is maintained by one volunteer in their spare time, so please allow for that:

- You'll get a reply within **7 days** saying whether the report is accepted.
- An accepted report is fixed privately, then released, with an advisory on the [Security tab](https://github.com/tronyx/HealthChecks-Linux/security) that credits you, unless you'd rather not be named. The aim is a release within **90 days** of the report, sooner for something serious, and you'll be kept up to date along the way.
- Please keep it private until the fix is released and the advisory published.

## 🎯 Scope

The script can hold your Organizr API key and passwords for your applications, often runs from cron as root, sends requests to your applications and to Healthchecks, and reads lock files from a folder that other users may share. These are in scope:

- **The script:**
  - **The secrets.** `healthchecks.toml` can hold the Organizr API key (`organizr_token`) and the HTTP basic auth passwords (`password` in each `[auth.<name>]` table). The environment variables `HCL_ORGANIZR_TOKEN` and those that `password_env` names can hold them too. The script refuses to run if a file that holds a secret can be opened by other users. A probe sends the API key or a password only to its own URL, and again after a redirect only to the same scheme, host and port. In scope is anything that makes the script reveal a secret: in its output, its error messages, the ping body, a file that other users can read, a request to Healthchecks, or a request to another host.
  - **Lock files.** [Tronitor](https://github.com/tronyx/tronitor) creates and removes lock files that tell the script to skip checks: `healthchecks.lock` skips every check, and `<UUID>.lock` skips one. The script reads them from the folder that `lock_dir` sets (`/tmp` by default), and keeps its run lock, `.healthchecks-linux.run`, in the same folder. In scope is a trick in that folder that makes the script create, change or delete a file it shouldn't, or follow a link to another file.
  - **What a server sends back.** An answer from an application, from the Plex status page or from a Healthchecks server that makes the script write a file, run a command, put terminal control codes in its output, or send your secrets or data anywhere else.
  - **`--migrate`.** It reads a configured copy of the Bash script as text, and must never run any of it. In scope is a Bash script that makes `--migrate` run a command, write outside the file it names, or write a file that other users can read.
- **The repository's workflows:** anything that could expose their token, let someone else's code run with their permissions, or push to the repository or its `badges` branch.

**Known limitations.** These are known, so please don't report them:

- Every user on the computer can write to `/tmp`. So any local user can create or delete `/tmp/healthchecks.lock`, or a check's lock file, and so stop or restart the pings for your checks. To prevent it on a shared computer, set `lock_dir` in `healthchecks.toml`, and in `tronitor.toml` if you use Tronitor, to the same folder, one that only you can write to.
- A probe with `verify_tls = false` accepts any HTTPS certificate, so someone on your network could answer in place of the application. Use it only for addresses on your own network.
- With `send_details = true`, the default, each ping sends the URL and the result of each probe to Healthchecks. These URLs can show your domain and the IP addresses on your network. Set `send_details = false` to send empty pings.
- The Bash script keeps its secrets in the script itself, and `curl -u` shows a password to other users in the process list. Move to the Python script, which does neither.

Out of scope:

- vulnerabilities in Healthchecks, Organizr, Tronitor, the applications you monitor or Python themselves; please report those to their own projects;
- anything that needs an attacker who can already run commands as the user that runs the script;
- a check that passes or fails when it shouldn't: that's a bug, for an [issue](https://github.com/tronyx/HealthChecks-Linux/issues).
