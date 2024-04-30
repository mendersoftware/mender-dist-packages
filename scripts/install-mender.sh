#!/bin/bash
# Copyright 2023 Northern.tech AS
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
set -e

CHANNEL="stable"

# All available components
AVAILABLE_COMPONENTS="\
mender-auth \
mender-client \
mender-client4 \
mender-configure \
mender-configure-demo \
mender-configure-timezone \
mender-connect \
mender-gateway \
mender-monitor \
mender-monitor-demo \
mender-update \
"

# Default components (installed when no flags and no specified components)
DEFAULT_COMPONENTS="\
mender-client4 \
mender-configure \
mender-connect \
"

# Default components for legacy distributions (installed when no flags and no specified components)
DEFAULT_COMPONENTS_LEGACY="\
mender-client \
mender-configure \
mender-connect \
"

# Demo components (added with --demo flag)
DEMO_COMPONENTS="\
mender-configure-demo \
mender-configure-timezone \
"

# All commercial components (require --jwt-token flag)
COMMERCIAL_COMPONENTS="\
mender-gateway \
mender-monitor \
mender-monitor-demo \
"

# Commercial default components (added with --commercial flag)
COMMERCIAL_DEFAULT_COMPONENTS="\
mender-monitor \
"

# Commercial demo components (added with --commercial and --demo flags)
COMMERCIAL_DEMO_COMPONENTS="\
mender-monitor-demo \
"

SELECTED_COMPONENTS="$DEFAULT_COMPONENTS"
DEMO="0"

if [[ "$*" == *"--force-mender-client4"* ]]; then
    FORCE_MENDER_CLIENT4="1"
else
    FORCE_MENDER_CLIENT4="0"
fi

# mender-setup CLI
MENDER_SETUP_CLI="mender-setup"

# Path where to install the Mender APT repository
MENDER_APT_SOURCES_LIST="/etc/apt/sources.list.d/mender.list"

# URL prefix for the commercial components
MENDER_COMMERCIAL_DOWNLOAD_URL="https://downloads.customer.mender.io/content/hosted/"

# URL path for the commercial components, formatted by version, distribution and release
ARCHITECTURE=$(dpkg --print-architecture)
declare -A COMMERCIAL_COMP_TO_URL_PATH_F=(
  [mender-gateway]="mender-gateway/debian/%s/mender-gateway_%s-1+%s+%s_$ARCHITECTURE.deb"
  [mender-monitor]="mender-monitor/debian/%s/mender-monitor_%s-1+%s+%s_all.deb"
  [mender-monitor-demo]="mender-monitor/debian/%s/mender-monitor-demo_%s-1+%s+%s_all.deb"
)

# URL path for mender-gateway demo, formatted by version
MENDER_GATEWAY_EXAMPLES_URL_PATH_F="mender-gateway/examples/%s/mender-gateway-examples-%s.tar"

export DEBIAN_FRONTEND=noninteractive

banner (){
    echo "
                          _
 _ __ ___   ___ _ __   __| | ___ _ __
| '_ \` _ \ / _ \ '_ \ / _\` |/ _ \ '__|
| | | | | |  __/ | | | (_| |  __/ |
|_| |_| |_|\___|_| |_|\__,_|\___|_|

Running the Mender installation script.
--
"

}

usage() {
    echo "usage: install-mender.sh [options] [component...] [-- [options-for-mender-setup] ]"
    echo ""
    echo "options: [-h, help] [-c channel] [--demo] [--commercial]"
    echo "  -h, --help             print this help"
    echo "  -c CHANNEL             channel: stable(default)|experimental"
    echo "  --demo                 use defaults appropriate for demo"
    echo "  --commercial           install commercial components, requires --jwt-token"
    echo "  --force-mender-client4 install the Mender Client 4.x series on all the distros"
    echo "  --jwt-token TOKEN      Hosted Mender JWT token"
    echo ""
    echo "If no components are specified, defaults will be installed"
    echo ""
    echo "Anything after a '--' gets passed directly to the client setup tool."
    echo ""
    echo "This script will install the Mender Client 3.x series on Ubuntu jammy or older, "
    echo "and on Debian bullseye or older. On newer distributions, it will install the "
    echo "Mender Client 4.x series. If you want to force the installation of the latest "
    echo "major version of the Mender Client on older distributions, please use the "
    echo "flag --force-mender-client4."
    echo ""
    echo "Supported components (x = installed by default):"
    for c in $AVAILABLE_COMPONENTS; do
        if echo "$DEFAULT_COMPONENTS" | egrep -q "(^| )$c( |\$)"; then
            echo -n " (x) "
        else
            echo -n " (-) "
        fi
        echo "$c"
    done
}

is_known_component() {
    for known in $AVAILABLE_COMPONENTS; do
        if [ "$1" = "$known" ]; then
            return 0
        fi
    done
    return 1
}

is_commercial_component() {
    for comp in $COMMERCIAL_COMPONENTS; do
        if [ "$1" = "$comp" ]; then
            return 0
        fi
    done
    return 1
}

parse_args() {
    local selected_components=""
    local args_copy="$@"
    while [ $# -gt 0 ]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -c)
                if [ -n "$2" ]; then
                    CHANNEL="$2"
                    shift
                else
                    echo "ERROR: channel requires a non-empty option argument."
                    echo "Aborting."
                    exit 1
                fi
                ;;
            --demo)
                DEMO="1"
                SELECTED_COMPONENTS="$SELECTED_COMPONENTS $DEMO_COMPONENTS"
                ;;
            --commercial)
                if [[ ! "$args_copy" == *"--jwt-token"* ]]; then
                    echo "ERROR: commercial requires --jwt-token argument."
                    echo "Aborting."
                    exit 1
                fi
                SELECTED_COMPONENTS="$SELECTED_COMPONENTS $COMMERCIAL_DEFAULT_COMPONENTS"
                if [[ "$args_copy" == *"--demo"* ]]; then
                    SELECTED_COMPONENTS="$SELECTED_COMPONENTS $COMMERCIAL_DEMO_COMPONENTS"
                fi
                ;;
            --jwt-token)
                if [ -n "$2" ]; then
                    JWT_TOKEN="$2"
                    shift
                else
                    echo "ERROR: jwt-token requires a non-empty option argument."
                    echo "Aborting."
                    exit 1
                fi
                ;;
            --force-mender-client4)
                ;;
            --)
                shift
                MENDER_SETUP_ARGS="$@"
                break
                ;;
            *)
                if is_known_component "$1"; then
                    if is_commercial_component "$1"; then
                        if [[ ! "$args_copy" == *"--jwt-token"* ]]; then
                            echo "ERROR: $1 requires --jwt-token argument."
                            echo "Aborting."
                            exit 1
                        fi
                    fi
                    selected_components="$selected_components $1 "
                else
                    echo "Unsupported argument: \`$1\`"
                    echo "Run \`mender-install.sh -h\` for help."
                    echo "Aborting."
                    exit 1
                fi
                ;;
        esac
        shift
    done
    if [ -n "$selected_components" ]; then
        SELECTED_COMPONENTS="$selected_components"
    fi
}

print_components() {
    echo "  Selected components:"
    for c in $SELECTED_COMPONENTS; do
        printf "\t%s\n" "$c"
    done
}


#
# $1 - component
# $2 - mender-release
#
# Note, requires jq and curl
function get_version_of() {
    which jq 2>&1 >/dev/null || { echo >&2 "'jq' needs to be installed"; exit 1; }
    [[ $# -ne 2 ]] && { echo >&2 "get_version_of requires two arguments. Got  $#"; exit 1; }
    local -r component_name="$1"
    local -r mender_release="$2"
    local -r major_minor="$(echo -e ${mender_release} | cut --delimiter=. --fields=1,2)"
    local -r versions_json="$(curl --fail https://docs.mender.io/releases/versions.json)"
    echo "$versions_json" | jq --raw-output "$(cat <<EOF
.releases |
."${major_minor}" |
."${mender_release}" |
.repos |
.[] |
 select(.name == "${component_name}") |
.version
EOF
)"
}

#
# Returns the latest Mender release version
# from `docs.mender.io/`
#
# Note, requires jq and curl
function get_latest_mender_release() {
    [[ $# -ne 0 ]] && { echo >&2 "get_latest_mender_release takes no arguments"; exit 1; }
    local -r versions_json="$(curl --fail https://docs.mender.io/releases/versions.json)"
    local -r release_series="$(echo "${versions_json}" | jq '.releases | keys | max')"
    local -r latest_release="$(echo "${versions_json}" | jq --raw-output "$(cat <<EOF
.releases[] |
 to_entries[].key |
 select(startswith($release_series))
EOF
)" |
head --lines=1
)"
    echo ${latest_release}
}

#
# $1 - The package to install
#
function get_latest_version_of_commercial_component() {
    [[ $# -ne 1 ]] && { echo >&2 "get_latest_version_of_commercial_component requires one argument"; exit 1; }
    local component_name="$1"
    case "${component_name}" in
        mender-monitor|mender-monitor-demo)
            local -r version_of="$(get_version_of "monitor-client" "$(get_latest_mender_release)")"
            ;;
        *)
            local -r version_of="$(get_version_of "${component_name}" "$(get_latest_mender_release)")"
            ;;
    esac
    if [[ -z "${version_of}" ]]; then
        echo >&2 "get_latest_of ${component_name} returned empty unexpectedly"
        echo >&2 "most likely there is something wrong with the version lookup in "
        echo >&2 "the versions.json file"
        exit 1
    fi
    echo "${version_of}"
}

init() {
    REPO_URL=https://downloads.mender.io/repos/debian

    parse_args "$@"

    ARCH=$(dpkg --print-architecture)
    echo "  Detected architecture:"
    printf "\t%s\n" "$ARCH"

    echo "  Installing from channel:"
    printf "\t%s\n" "$CHANNEL"

    # Translate Debian "channel" into Mender version for commercial packages
    if [ "$CHANNEL" = "experimental" ]; then
        VERSION="master"
    else
        VERSION="latest"
    fi

    echo " Installing commercial components from source:"
    printf "\t%s\n" "$VERSION"
}

get_deps() {
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        jq
}

maybe_remove_existing_gpg_key() {
    # In the past we installed the Mender APT GPG key using "apt-key add" which is now deprecated.
    # This function checks if a Mender key is already installed and, if so, removes it so that we
    # can add it "the right way".
    apt-key list >/dev/null 2>/dev/null || return 0
    mender_key=$(apt-key list 2>/dev/null | grep -B1 "Mender Team <mender@northern.tech>" | head -n1)
    if [[ -n "${mender_key}" ]]; then
        apt-key 2>/dev/null del "${mender_key}"
    fi
}

add_repo() {
    maybe_remove_existing_gpg_key
    curl -fsSL $REPO_URL/gpg | tee /etc/apt/trusted.gpg.d/mender.asc

    local repo_deprecated="deb [arch=$ARCH] $REPO_URL $CHANNEL main"
    if grep -F "$repo_deprecated" /etc/apt/sources.list >/dev/null; then
        echo "ERROR: deprecated repository found in apt sources lists."
        echo "Please remove it manually with: sudo sed -i.bak -e \"\,$repo_deprecated,d\" /etc/apt/sources.list"
        echo "See https://docs.mender.io for updated APT repos information"
        exit 1
    fi
    if test -f "$MENDER_APT_SOURCES_LIST" && \
            grep -F "$repo_deprecated" "$MENDER_APT_SOURCES_LIST" >/dev/null; then
        echo "ERROR: deprecated repository found in apt sources lists."
        echo "Please remove it manually with: sudo rm $MENDER_APT_SOURCES_LIST"
        echo "See https://docs.mender.io for updated APT repos information"
        exit 1
    fi

    local repo="deb [arch=$ARCH] $REPO_URL $LSB_DIST/$DIST_VERSION/$CHANNEL main"
    echo "Installing Mender APT repository at $MENDER_APT_SOURCES_LIST..."
    echo "$repo" > "$MENDER_APT_SOURCES_LIST"
}

do_install_open() {
    # Filter out commercial components
    local selected_components_open=""
    for c in $SELECTED_COMPONENTS; do
        if ! is_commercial_component "$c"; then
            selected_components_open="$selected_components_open $c"
        fi
    done

    # Return if no open source components selected
    if [ -z "$selected_components_open" ]; then
        return
    fi

    echo "  Installing open source components from APT repository"

    apt-get update
    apt-get install -y \
       -o Dpkg::Options::="--force-confdef" \
       -o Dpkg::Options::="--force-confold" \
       $selected_components_open

    echo "  Success! Please run \``mender_setup_cli`\` as superuser to configure the client."
}

do_install_commercial() {
    # Filter commercial components
    local selected_components_commercial=""
    local c
    for c in $SELECTED_COMPONENTS; do
        if is_commercial_component "$c"; then
            selected_components_commercial="$selected_components_commercial $c"
        fi
    done

    # Return if no commercial components selected
    if [ -z "$selected_components_commercial" ]; then
        return
    fi

    echo "  Installing commercial components from $MENDER_COMMERCIAL_DOWNLOAD_URL"

    # Download deb packages
    local url
    for c in $selected_components_commercial; do
        local component_version="$VERSION"
        [ "$component_version" = "latest" ] && component_version="$(get_latest_version_of_commercial_component ${c})"
        echo "Installing ${c} (${component_version})"
        url="${MENDER_COMMERCIAL_DOWNLOAD_URL}$(printf ${COMMERCIAL_COMP_TO_URL_PATH_F[$c]} $component_version $component_version $LSB_DIST $DIST_VERSION)"
        if ! curl -fLsS -H "Authorization: Bearer $JWT_TOKEN" -O "$url"; then
            echo "ERROR: Cannot get $c from $url"
            exit 1
        fi
    done

    # Install all of them at once and fallback to install missing dependencies
    local -r deb_packages_glob=$(echo $selected_components_commercial | sed -e 's/ /*.deb /g; s/$/*.deb/')
    local -r deb_packages_expanded=$(echo $deb_packages_glob | tr ' ' '\n' | sort | uniq )
    dpkg --install $deb_packages_expanded || apt-get -f -y install

    # Check individually each package
    for c in $selected_components_commercial; do
        dpkg --status $c || { echo ERROR: $c could not be installed; exit 1; }
    done

    # Remove packages from working dir
    rm $deb_packages_expanded

    echo "  Success!"
}

do_setup_mender_client() {
    # Return if mender nor mender-setup were installed
    if ! which mender-setup >/dev/null && ! which mender >/dev/null; then
        return
    fi

    # Return if no setup options were passed
    if [ -z "$MENDER_SETUP_ARGS" ]; then
        return
    fi

    echo "  Setting up mender with options: $MENDER_SETUP_ARGS"
    `mender_setup_cli` $MENDER_SETUP_ARGS
    pidof systemd >/dev/null 2>&1 && {
        systemctl is-enabled mender-authd >/dev/null 2>&1 && systemctl restart mender-authd
        systemctl is-enabled mender-updated >/dev/null 2>&1 && systemctl restart mender-updated
        systemctl is-enabled mender-client >/dev/null 2>&1 && systemctl restart mender-client
    }
    echo "  Success!"
}

do_setup_other_components() {
    # Setup for mender-connect
    if [[ "$SELECTED_COMPONENTS" == *"mender-connect"* ]]; then
        if [ "$DEMO" -eq 1 ]; then
            echo "  Setting up mender-connect with user 'root' and shell 'bash'"
            cat > /etc/mender/mender-connect.conf << EOF
{
  "User": "root",
  "ShellCommand": "/bin/bash"
}
EOF
            pidof systemd && systemctl restart mender-connect
            echo "  Success!"
        fi
    fi

    # Setup for mender-gateway
    if [[ "$SELECTED_COMPONENTS" == *"mender-gateway"* ]]; then
        if [ "$DEMO" -eq 1 ]; then
            echo "  Setting up mender-gateway with demo configuration, certificates and key"
            local gateway_version="$VERSION"
            [ "$gateway_version" = "latest" ] && gateway_version="$(get_latest_version_of_commercial_component mender-gateway)"
            local url="${MENDER_COMMERCIAL_DOWNLOAD_URL}$(printf ${MENDER_GATEWAY_EXAMPLES_URL_PATH_F} $gateway_version $gateway_version)"
            if ! curl -fLsS -H "Authorization: Bearer $JWT_TOKEN" -O "$url"; then
                echo "ERROR: Cannot get mender-gateway-examples from $url"
                exit 1
            fi
            tar -C / --strip-components=2 -xvf mender-gateway-examples-${gateway_version}.tar

            pidof systemd && systemctl restart mender-gateway

            # Remove examples package from working dir
            rm mender-gateway-examples-${gateway_version}.tar

            echo "  Success!"
        fi
    fi
}

command_exists() {
    command -v "$@" > /dev/null 2>&1
}

select_mender_client_legacy() {
    if [ "$FORCE_MENDER_CLIENT4" -ne 1 ]; then
        DEFAULT_COMPONENTS="$DEFAULT_COMPONENTS_LEGACY"
        SELECTED_COMPONENTS="$DEFAULT_COMPONENTS"
        MENDER_SETUP_CLI="mender setup"
    fi
}

mender_setup_cli() {
    if which mender-setup >/dev/null; then
        echo "mender-setup"
    elif which mender >/dev/null; then
        echo "mender setup"
    else
        echo $MENDER_SETUP_CLI
    fi
}

# Set the LSB_DIST and DIST_VERSION variables guessing the distribution and version;
# It also checks if this is a forked Linux distro.
# Credits: https://get.docker.com/
check_dist_and_version() {
    # Every system that we officially support has /etc/os-release
    if [ -r /etc/os-release ]; then
        LSB_DIST="$(. /etc/os-release && echo "$ID" | tr '[:upper:]' '[:lower:]')"
    fi
    case "$LSB_DIST" in
        ubuntu)
            if command_exists lsb_release; then
                DIST_VERSION="$(lsb_release --codename | cut -f2)"
            fi
            if [ -z "$DIST_VERSION" ] && [ -r /etc/lsb-release ]; then
                DIST_VERSION="$(. /etc/lsb-release && echo "$DISTRIB_CODENAME")"
            fi
            case "$DIST_VERSION" in
                jammy)
                    DIST_VERSION="jammy"
                    select_mender_client_legacy
                ;;
                focal)
                    DIST_VERSION="focal"
                    select_mender_client_legacy
                ;;
                *)
                    echo "ERROR: your distribution's version ($DIST_VERSION) is either not recognized or not supported."
                    echo "Aborting."
                    exit 1
                ;;
            esac
        ;;
        debian|raspbian)
            DIST_VERSION="$(sed 's/\/.*//' /etc/debian_version | sed 's/\..*//')"
            case "$DIST_VERSION" in
                12)
                    DIST_VERSION="bookworm"
                ;;
                11)
                    DIST_VERSION="bullseye"
                    select_mender_client_legacy
                ;;
                10)
                    DIST_VERSION="buster"
                    select_mender_client_legacy
                ;;
                *)
                    echo "ERROR: your distribution's version ($DIST_VERSION) is either not recognized or not supported."
                    echo "Aborting."
                    exit 1
                ;;
            esac
        ;;
        *)
            echo "ERROR: your distribution ($LSB_DIST) is either not recognized or not supported."
            echo "Aborting."
            exit 1
        ;;
    esac

    # Check for lsb_release command existence, it usually exists in forked distros
    if command_exists lsb_release; then
        # Check if the `-u` option is supported
        set +e
        lsb_release -a -u > /dev/null 2>&1
        lsb_release_exit_code=$?
        set -e

        # Check if the command has exited successfully, it means we're in a forked distro
        if [ "$lsb_release_exit_code" = "0" ]; then
            # Get the upstream release info
            LSB_DIST=$(lsb_release -a -u 2>&1 | tr '[:upper:]' '[:lower:]' | grep -E 'id' | cut -d ':' -f 2 | tr -d '[:space:]')
            DIST_VERSION=$(lsb_release -a -u 2>&1 | tr '[:upper:]' '[:lower:]' | grep -E 'codename' | cut -d ':' -f 2 | tr -d '[:space:]')
        else
            if [ -r /etc/debian_version ] && [ "$LSB_DIST" != "ubuntu" ] && [ "$LSB_DIST" != "raspbian" ]; then
                if [ "$LSB_DIST" = "osmc" ]; then
                    # OSMC runs Raspbian
                    LSB_DIST=raspbian
                else
                    # We're Debian and don't even know it!
                    LSB_DIST=debian
                fi
                DIST_VERSION="$(sed 's/\/.*//' /etc/debian_version | sed 's/\..*//')"
                case "$DIST_VERSION" in
                    12)
                        DIST_VERSION="bookworm"
                    ;;
                    11)
                        DIST_VERSION="bullseye"
                        select_mender_client_legacy
                    ;;
                    10)
                        DIST_VERSION="buster"
                        select_mender_client_legacy
                    ;;
                    *)
                        echo "ERROR: your distribution's version ($DIST_VERSION) is either not recognized or not supported."
                        echo "Aborting."
                        exit 1
                    ;;
                esac
            fi
        fi
    fi

    echo "  Detected distribution:"
    printf "\t%s/%s\n" "$LSB_DIST" "$DIST_VERSION"

    if [[ "$LSB_DIST" == "raspbian" ]]; then
        LSB_DIST="debian"
        echo "  Raspbian detected. Using compatible distribution:"
        printf "\t%s/%s\n" "$LSB_DIST" "$DIST_VERSION"
    fi
}

check_dist_and_version
banner
init "$@"
print_components
get_deps
add_repo
do_install_open
do_install_commercial
do_setup_mender_client
do_setup_other_components

exit 0
