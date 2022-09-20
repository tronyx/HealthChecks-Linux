#!/usr/bin/env bash
#
# Script to test various application reverse proxies, as well as their internal pages, and report to their respective Healthchecks.io checks
# Tronyx

# Define some variables
# Primary domain all of your reverse proxies are hosted on
domain='domain.com'

# Your Organizr API key to get through Org auth
orgAPIKey=''

# Primary Server IP address of the Server all of your applications/containers are hosted on
# You can add/utilize more Server variables if you would like, as I did below, and if you're running more than one Server like I am
primaryServerAddress='192.168.1.103'
hcPingDomain='https://hc-ping.com/'

# Additional hostname variables for other checks like Unraid, vCenter, Unifi Controler, Unifi Protect, etc.
unraidServerAddress=''
unifiControllerAddress=''
vCenterServerAddress=''
rNasServerAddress=''

# Location of the lock file that you can utilize to keep tests paused.
tempDir='/tmp/'
# The below temp dir is for use with the Tronitor script, uncomment the line if you wish to use it
# https://github.com/christronyxyocum/tronitor
#tempDir='/tmp/tronitor/'
healthchecksLockFile="${tempDir}healthchecks.lock"

# You will need to adjust the subDomain, appPort, subDir, and hcUUID variables for each application's function according to your setup
# I've left in some examples to show the expected format.

# Function to check for healthchecks lock file
check_lock_file() {
    if [ -e "${healthchecksLockFile}" ]; then
        echo "Skipping checks due to lock file being present."
        exit 0
    else
        main
    fi
}

# Function to check Organizr public Domain
check_organizr() {
    appPort='8889'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check AdGuard
check_adguard() {
    subDomain='adguard'
    appPort='80'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}"/login.html -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}"/login.html)
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Bazarr
check_bazarr() {
    appPort='6767'
    subDir='/bazarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}"system/status -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}"system/status)
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Bitwarden
check_bitwarden() {
    subDomain='bitwarden'
    appPort='8484'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}")
    intResponse=$(curl -w "%{http_code}\n" -sIk -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Chevereto
check_chevereto() {
    subDomain='gallery'
    appPort='9292'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}")
    intResponse=$(curl -w "%{http_code}\n" -sIk -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Deluge
check_deluge() {
    appPort='8112'
    subDir='/deluge/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Dozzle
check_dozzle() {
    appPort='8484'
    subDir='/dozzle/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Filebrowser
check_filebrowser() {
    subDomain='files'
    appPort='8585'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}" -s -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}")
    intResponse=$(curl -w "%{http_code}" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check GitLab
check_gitlab() {
    subDomain='gitlab'
    appPort='444'
    subDir='/users/sign_in'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sIk -o /dev/null --connect-timeout 10 -m 10 https://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Grafana
check_grafana() {
    subDomain='grafana'
    appPort='3000'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Guacamole
check_guacamole() {
    appPort='8080'
    subDir='/guac/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Jackett
check_jackett() {
    appPort='9117'
    subDir='/jackett/UI/Login'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check PLPP
check_library() {
    subDomain='library'
    appPort='8383'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Lidarr
check_lidarr() {
    appPort='8686'
    subDir='/lidarr/'
    hcUUID=''
    # For newer versions you need to drop the I from the curl command
    # Older
    #extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    #intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    # Newer
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Logarr
check_logarr() {
    appPort='8000'
    subDir='/logarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check TheLounge
check_thelounge() {
    appPort='9090'
    subDir='/thelounge/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Mediabutler
check_mediabutler() {
    appPort='9876'
    extSubDir='/mediabutler/version/'
    intSubDir='/version/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${extSubDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${intSubDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Monitorr
check_monitorr() {
    appPort='8001'
    subDir='/monitorr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Nagios
check_nagios() {
    subDomain='nagios'
    appPort='8787'
    subDir=''
    nagUser=''
    nagPass=''
    hcUUID=''
    extResponse=$(curl -u "${nagUser}:${nagPass}" -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -u "${nagUser}:${nagPass}" -w "%{http_code}\n" -sIk -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Netdata
check_netdata() {
    appPort='9999'
    extSubDir='/netdata/'
    intSubDir='/#menu_system;theme=slate;help=true'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sIL -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${extSubDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${intSubDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Nextcloud
check_nextcloud() {
    subDomain='nextcloud'
    appPort='9393'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sIL -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sILk -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Notifiarr
check_notifiarr() {
    appPort='5454'
    subDir='/notifiarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check NZBGet
check_nzbget() {
    appPort='6789'
    subDir='/nzbget/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check NZBHydra/NZBHydra2
check_nzbhydra() {
    appPort='5076'
    subDir='/nzbhydra/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Ombi
check_ombi() {
    appPort='3579'
    subDir='/ombi/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Overseerr
check_overseerr() {
    appPort='5055'
    subDomain='overseerr'
    subDir='/login'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}.${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Petio
# Comment out whichever one you do not use.
check_petio() {
    subDomain='petio'
    #subDir='/petio/'
    appPort='7777'
    hcUUID=''
    # Subdomain
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}" -H "token: ${orgAPIKey}")
    # Subdirectory
    #extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check PiHole
check_pihole() {
    subDomain='pihole'
    subDir='/admin/login.php'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Plex
check_plex() {
    subDir='/plex/'
    appPort='32400'
    hcUUID=''
    plexExtResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${domain}""${subDir}")
    plexIntResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}"/web/index.html)
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${plexExtResponse}" = '200' ]] && [[ "${plexIntResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${plexExtResponse}" != '200' ]] || [[ "${plexIntResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check status of Plex Auth Service
check_plex_auth() {
    hcUUID=''
    plexAuthStatus=$(curl -s https://status.plex.tv/ | grep -B4 'Authentication and API server' | grep status | awk -F= '{print $2}' | tr -d '"')
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${plexAuthStatus}" = 'operational' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${plexAuthStatus}" != 'operational' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Portainer
check_portainer() {
    appPort='9000'
    subDir='/portainer/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Prowlarr
check_prowlarr() {
    appPort='9696'
    subDir='/prowlarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check qBittorrent
check_qbittorrent() {
    appPort='8080'
    subDir='/qbit/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Radarr
check_radarr() {
    appPort='7878'
    subDir='/radarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Radarr v4
check_radarr() {
    appPort='7878'
    subDir='/radarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check ReadyNAS
# No external check because you should not reverse proxy your ReadyNAS panel
check_readynas() {
    subDir='/admin/'
    rNasUser=''
    rNasPass=''
    hcUUID=''
    extResponse='200'
    intResponse=$(curl -u "${rNasUser}:${rNasPass}" -w "%{http_code}\n" -sILk -o /dev/null --connect-timeout 10 -m 10 https://"${rNasServerAddress}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check ruTorrent
check_rutorrent() {
    subDomain='rutorrent'
    appPort='9080'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '401' ]] && [[ "${intResponse}" = '401' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '401' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check SABnzbd
check_sabnzbd() {
    appPort='8580'
    subDir='/sabnzbd/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Sonarr
check_sonarr() {
    appPort='9898'
    subDir='/sonarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Sonarr v4
check_sonarr_v4() {
    appPort='9898'
    subDir='/sonarr/'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}"login -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}"login)
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Tautulli
check_tautulli() {
    appPort='8181'
    subDir='/tautulli/status'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${domain}${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Tdarr
check_tdarr() {
    appPort='8265'
    subDomain='tdarr'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}.${domain}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Transmission
check_transmission() {
    appPort='9091'
    subDir='/transmission/web/index.html'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 https://"${domain}""${subDir}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -s -o /dev/null --connect-timeout 10 -m 10 http://"${primaryServerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Unifi Controller
check_unifi_controller() {
    subDomain='unifi'
    appPort='8443'
    subDir='/manage/account/login'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sIL -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sILk -o /dev/null --connect-timeout 10 -m 10 https://"${unifiControllerAddress}":"${appPort}""${subDir}")
    # With the 2.3.10 update it seems you have to drop the -I option with curl
    #intResponse=$(curl -w "%{http_code}\n" -sLk -o /dev/null --connect-timeout 10 -m 10 https://"${unifiControllerAddress}":"${appPort}""${subDir}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Unifi Protect
check_unifi_protect() {
    subDomain='nvr'
    appPort='7443'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sIL -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}" -H "token: ${orgAPIKey}")
    intResponse=$(curl -w "%{http_code}\n" -sILk -o /dev/null --connect-timeout 10 -m 10 https://"${unifiControllerAddress}":"${appPort}")
    # With the 1.21.0 update it seems you have to drop the -I option with curl
    #intResponse=$(curl -w "%{http_code}\n" -sLk -o /dev/null --connect-timeout 10 -m 10 https://"${unifiControllerAddress}":"${appPort}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check Unraid
# No external check because you should not reverse proxy your Unraid
check_unraid() {
    appPort='80'
    hcUUID=''
    extResponse='200'
    intResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 http://"${unraidServerAddress}"/login)
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check vCenter
# No external check because you should not reverse proxy your vCenter
check_vcenter() {
    hcUUID=''
    extResponse='200'
    intResponse=$(curl -w "%{http_code}\n" -sIk -o /dev/null --connect-timeout 10 -m 10 https://"${vCenterServerAddress}")
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Function to check XBackBone
# Internal check response set to 200 since XBackBone redirects you to the
# domain you have associated with it if you try to browse to it locally
check_xbackbone() {
    subDomain='sharex'
    hcUUID=''
    extResponse=$(curl -w "%{http_code}\n" -sI -o /dev/null --connect-timeout 10 -m 10 https://"${subDomain}"."${domain}"/login -H "token: ${orgAPIKey}")
    intResponse='200'
    appLockFile="${tempDir}${hcUUID}".lock
    if [ -e "${appLockFile}" ]; then
        :
    else
        if [[ "${extResponse}" = '200' ]] && [[ "${intResponse}" = '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}" >/dev/null
        elif [[ "${extResponse}" != '200' ]] || [[ "${intResponse}" != '200' ]]; then
            curl -fsS --retry 3 "${hcPingDomain}${hcUUID}"/fail >/dev/null
        fi
    fi
}

# Main function to run all other functions
# Uncomment (remove the # at the beginning of the line) to enable the checks you want
main() {
    check_organizr
    #check_adguard
    #check_bazarr
    #check_bitwarden
    #check_chevereto
    #check_deluge
    #check_filebrowser
    #check_gitlab
    #check_grafana
    #check_guacamole
    #check_jackett
    #check_library
    #check_lidarr
    #check_logarr
    #check_thelounge
    #check_monitorr
    #check_nagios
    #check_netdata
    #check_nextcloud
    #check_nzbget
    #check_nzbhydra
    #check_ombi
    #check_overseerr
    #check_petio
    #check_pihole
    #check_plex
    #check_plex_auth
    #check_portainer
    #check_prowlarr
    #check_qbittorrent
    #check_radarr
    #check_radarr4k
    #check_readynas
    #check_rutorrent
    #check_sabnzbd
    #check_sonarr
    #check_sonarr4k
    #check_tautulli
    #check_tdarr
    #check_transmission
    #check_unifi_controller
    #check_unifi_protect
    #check_unraid
    #check_vcenter
    #check_xbackbone
}

check_lock_file
