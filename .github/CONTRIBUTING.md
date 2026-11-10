# 🤝 Contributing

Thanks for wanting to help! Bug reports, ideas, new applications and pull requests are all welcome.

## 🐛 Reporting a bug

Found a security vulnerability? Please don't open an issue: see the [security policy](SECURITY.md).

[Open an issue](https://github.com/tronyx/HealthChecks-Linux/issues/new) with:

- The command you ran and everything it printed. `--dry-run` output is ideal, because it shows the status code of each probe.
- The `[[check]]` table of the check that fails, and any `[general]` settings you changed. Remove `organizr_token`, every `password`, and any UUID you don't want to share.
- Your operating system, and the output of `python3 --version` and `python3 healthchecks_linux.py --version`.
- Whether you use healthchecks.io or a Healthchecks server you host yourself.

## 💡 Suggesting a feature or an application

- **A new application:** [open an application request](https://github.com/tronyx/HealthChecks-Linux/issues/new?template=application-request.md) with its name and its GitHub or Docker Hub page. A URL that answers `200` without a login, such as a login page or a status page, helps a lot.
- **Anything else:** [open an issue](https://github.com/tronyx/HealthChecks-Linux/issues/new) describing what you'd like to do and why. For anything bigger than a small fix, please do this before writing code, so we can agree on the approach and your time isn't wasted.

## 🛠️ Making a change

1. Fork the repository, then clone your fork:

   ```bash
   git clone https://github.com/<your_name>/HealthChecks-Linux.git
   cd HealthChecks-Linux
   ```

2. Create a branch from `develop`:

   ```bash
   git checkout -b my-new-feature develop
   ```

3. Make your change. Keep each pull request to one change.

4. Install the dev requirements, then run the tests and the checks:

   ```bash
   pip install -r requirements-dev.txt
   python -m pytest
   python -m ruff check .
   python -m ruff format --check .
   python -m mypy
   ```

   The tests run the script against a fake server (`tests/fake_server.py`), a small local web server that plays both your applications and Healthchecks, so they need no account and no network. To see which lines your tests reach, run `python -m coverage run -m pytest` and then `python -m coverage report`.

   `ruff` is a linter and formatter, and `mypy` checks the type hints. Both are set up in `pyproject.toml`, and GitHub runs them on every push too, along with `shellcheck -S warning application_healthchecks_generic.sh` for the Bash script.

5. Commit, push, and open a pull request against `develop`:

   ```bash
   git add -A
   git commit -m "Add some feature"
   git push origin my-new-feature
   ```

## 📋 Adding an application

Every application is a `[[check]]` table in `healthchecks.example.toml`. The script itself has no code for any one application.

1. Add the table in alphabetical order, with `uuid = ""` and `enabled = false`, like the others. Use `{domain}` and `{primary}` for the hosts, and the application's default port.
2. Prefer a URL that answers `200` without a login. If the application only answers `401`, set `expect = [401]`, as `rutorrent` does.
3. Add the application to the table in the **Supported applications** section of the README.
4. Update the number of checks in `test_example_config_loads_with_every_check_disabled` in `tests/test_config.py`.
5. Test the table against a real copy of the application with `--dry-run --only <name>`, and say in the pull request which version you tested.

## 🐚 The Bash script

`application_healthchecks_generic.sh` is deprecated, and a future release removes it. It only gets fixes for bugs and security problems. New applications and features go in the Python script and `healthchecks.example.toml`.

## 📏 Code style

- **One file, standard library only.** People install this by copying a single script, so keep it that way: no new modules, and no new required packages. The one exception is `tomli` on Python 3.10, which stands in for the standard library's `tomllib`.
- **Python 3.10 and newer.** GitHub tests on 3.10 and on the newest release. Avoid syntax and library features newer than 3.10, such as reusing the same quote inside an f-string (3.12+). `mypy` checks the script as 3.10, so it catches a newer library feature.
- **Linux and macOS.** The script uses `fcntl` for its run lock, so it doesn't run on Windows. Use `pathlib` for paths, and don't run other programs: the script talks HTTP with the standard library.
- **Docstrings first.** Explain code in the docstring of the function or class it belongs to. Use a `#` comment only for what the code can't show on its own, and keep it to one short line.
- **Lines up to 120 characters, formatted by `ruff format`.**
- **Type hints on every function.** `mypy` checks them in strict mode. If it objects to something, fix the code rather than silencing it with `# type: ignore`.
- **Never show a secret.** The Organizr API key and the passwords must never appear in output, error messages, the ping body or a `repr()`, and must never be sent to Healthchecks or to another host after a redirect. Add a test when you touch that code.
- **Add or update tests** for any change in behavior, against the fake server, so they run anywhere without an account. Tests of the config file go in `tests/test_config.py`, of the probes and pings in `tests/test_http.py`, of the command line in `tests/test_cli.py`, and of `--migrate` in `tests/test_migrate.py`.
- **Update the README** if you add an option or a setting, or change what the script does.
