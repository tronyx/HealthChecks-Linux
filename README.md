# HealthChecks Linux
[![CodeFactor](https://www.codefactor.io/repository/github/christronyxyocum/healthchecks-linux/badge)](https://www.codefactor.io/repository/github/christronyxyocum/healthchecks-linux) [![made-with-bash](https://img.shields.io/badge/Made%20with-Bash-1f425f.svg)](https://www.gnu.org/software/bash/) [![GitHub](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/christronyxyocum/healthchecks-linux/blob/develop/LICENSE.md) [![Average time to resolve an issue](http://isitmaintained.com/badge/resolution/christronyxyocum/healthchecks-linux.svg)](http://isitmaintained.com/project/christronyxyocum/healthchecks-linux "Average time to resolve an issue") [![Percentage of issues still open](http://isitmaintained.com/badge/open/christronyxyocum/healthchecks-linux.svg)](http://isitmaintained.com/project/christronyxyocum/healthchecks-linux "Percentage of issues still open")

Script to test various application reverse proxies, as well as their internal pages, and report to their respective [Healthchecks.io](https://healthchecks.io) checks. This is meant to work with [Organizr](https://github.com/causefx/Organizr) Authentication, leveraging the Organizr API key to check the reverse proxies.

## Setting it up

There are variables at the top that are used throughout the script to do the tests. You'll want to fill in your domain, Organizr API key, and server IP(s). If you are self-hosting Healthchecks, you can change the `hcPingDomain` variable. You'll also need to go to each of the `check_application` functions and edit the UUID for the Healthcheck and the ports and/or subdomains or subdirectories on those. Lastly, uncomment (remove the `#` from the beginning of the line) the checks that you wish to run in the main function at the bottom of the script.

Once you have all of the checks configured as you need, you can run the script with `bash -x application_healthchecks_generic.sh` to make sure that all the responses are returning what's expected, an HTTP response code of `200`.

:warning: **NOTE:** You may need to tweak some of the URLs that are being used to check the applications depending on your setup and you might be using a subfolder configuration where I'm using a subdomain or vice versa. Point is, this won't work 100% for everyone, so you might need to do some trial and error to get everything working.

## Scheduling

Now that you have it configured so that everything is working properly, you can use a cronjob to schedule the script to run automatically and perform the checks.

Here's an example of running the script every two minutes:

```bash
## Run application healthchecks script for Healthchecks.io
*/2 * * * * /home/tronyx/scripts/application_healthchecks.sh
```

My HC.io checks are setup with a two minute period and a three minute grace. You can adjust all of that according to your needs.

## Tronitor

This script partners up with my [Tronitor](https://github.com/christronyxyocum/tronitor) script that allows you to pause and unpause your monitors manually or via a cronjob for scheduled maintenance, etc. If you wish to use this script with Tronitor you will need to uncomment the Tronitor temp directory line and then comment out or remove the original one.

## Thanks

Big thanks to [HalianElf](https://github.com/HalianElf) for creating the Powershell version of the script for Windows users.

## Questions

If you have any questions, you can find me on the [Organizr Discord](https://organizr.app/discord).
