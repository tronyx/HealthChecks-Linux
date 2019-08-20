# HealthChecks Linux
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/959bfd5ae28547b1985f7a2e6dbb7e83)](https://www.codacy.com/app/christronyxyocum/HealthChecks-Linux?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=christronyxyocum/HealthChecks-Linux&amp;utm_campaign=Badge_Grade)
[![made-with-bash](https://img.shields.io/badge/Made%20with-Bash-1f425f.svg)](https://www.gnu.org/software/bash/)
[![Beerpay](https://beerpay.io/christronyxyocum/HealthChecks-Linux/badge.svg)](https://beerpay.io/christronyxyocum/HealthChecks-Linux)

Script to test various application reverse proxies, as well as their internal pages, and report to their respective [Healthchecks.io](https://healthchecks.io) checks. This is meant to work with [Organizr](https://github.com/causefx/Organizr) Auth, leveraging the API key to check the reverse proxies.

## Setting it up

There are variables at the top that are used throughout the script to do the tests. You'll want to fill in your domain, Organizr API key, and server IP(s). If you are self-hosting Healthchecks, you can change the `hcPingDomain` variable. You'll also need to go to each of the `check_application` functions and edit the UUID for the Healthcheck and the ports and/or subdomains on those. Lastly, comment out any of the checks you don't need in the main function.

Once you have all of the checks configured as you need, you can run the script with `bash -x application_healthchecks_generic.sh` to make sure that all the responses are returning what's expected.

## Scheduling

Now that you have it so that everything is working properly, you can use a cronjob to schedule the script to run and perform the checks.

I have mine scheduled to run every two minutes:

```bash
## Run application healthchecks script for Healthchecks.io
*/2 * * * * /home/tronyx/scripts/application_healthchecks.sh
```

My checks are setup with a two minute period and a three minute grace. You can adjust all of that according to your needs.

## Tronitor

This script partners up with my [Tronitor](https://github.com/christronyxyocum/tronitor) script that allows you to pause and unpause your monitors manually or via a cronjob for scheduled maintenance, etc. If you wish to use this script with Tronitor you will need to uncomment the Tronitor temp directory line and then comment out or remove the original one.

## Thanks

Big thanks to [HalianElf](https://github.com/HalianElf) for creating the Powershell version of the script for Windows users.

## Questions

If you have any questions, you can find me on the [Organizr Discord](https://organizr.app/discord).
