#!/bin/bash

set -e

CHANNEL="stable"

# Each available component shall be in only one of the lists below
AVAILABLE_COMPONENTS="\
mender-client \
mender-configure \
mender-configure-demo \
mender-configure-timezone \
mender-connect \
mender-monitor \
"

DEFAULT_COMPONENTS="\
mender-client \
mender-configure \
mender-connect \
"

DEMO_COMPONENTS="\
mender-configure-demo \
mender-configure-timezone \
"

COMMERCIAL_COMPONENTS="\
mender-monitor \
"

SELECTED_COMPONENTS="$DEFAULT_COMPONENTS"
DEMO="0"

# URL prefix from where to download commercial compoments
MENDER_COMMERCIAL_DOWNLOAD_URL="https://downloads.customer.mender.io/content/hosted/"

# URL path for the actual components, formatted by version
declare -A COMMERCIAL_COMP_TO_URL_PATH_F=(
  [mender-monitor]="mender-monitor/debian/%s/mender-monitor_%s-1_all.deb"
)

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
    echo "  -h, --help          print this help"
    echo "  -c CHANNEL          channel: stable(default)|experimental"
    echo "  --demo              use defaults appropriate for demo"
    echo "  --commercial        install commercial components, requires --jwt-token"
    echo "  --jwt-token TOKEN   Hosted Mender JWT token"
    echo ""
    echo "If no components are specified, defaults will be installed"
    echo ""
    echo "Anything after a '--' gets passed directly to 'mender setup' command."
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
                SELECTED_COMPONENTS="$SELECTED_COMPONENTS $COMMERCIAL_COMPONENTS"
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
            --)
                shift
                MENDER_SETUP_ARGS="$@"
                break
                ;;
            *)
                if is_known_component "$1"; then
                    if echo "$COMMERCIAL_COMPONENTS" | egrep -q "(^| )$1( |\$)"; then
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

init() {
    REPO_URL=https://downloads.mender.io/repos/debian

    parse_args "$@"

    ARCH=$(dpkg --print-architecture)
    echo "  Detected architecture:"
    printf "\t%s\n" "$ARCH"

    echo "  Installing from channel:"
    printf "\t%s\n" "$CHANNEL"
}

get_deps() {
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg
}

add_repo() {
    curl -fsSL $REPO_URL/gpg | apt-key add -

    repo="deb [arch=$ARCH] $REPO_URL $CHANNEL main"

    echo "Checking if mender sources already exist in '/etc/apt/sources.list'..."
    if grep -F "$repo" /etc/apt/sources.list; then
        echo "Removing the old mender debian source list from /etc/apt/sources.list..."
        if ! sed -i.bak -e "\,$REPO_URL,d" /etc/apt/sources.list; then
            echo "Failed to remove the existing mender debian source from '/etc/apt/sources.list'."
            echo "This probably means that there already exists a source in your sources.list."
            echo "Please remove it manually before proceeding."
            exit 1
        fi
    fi

    echo "$repo" > /etc/apt/sources.list.d/mender.list
}

do_install_open() {
    # Filter out commercial components
    local selected_components_open=""
    for c in $SELECTED_COMPONENTS; do
        if ! echo "$COMMERCIAL_COMPONENTS" | egrep -q "(^| )$c( |\$)"; then
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

    echo "  Success! Please run \`mender setup\` to configure the client."
}

do_install_commercial() {
    # Filter commercial components
    local selected_components_commercial=""
    for c in $SELECTED_COMPONENTS; do
        if echo "$COMMERCIAL_COMPONENTS" | egrep -q "(^| )$c( |\$)"; then
            selected_components_commercial="$selected_components_commercial $c"
        fi
    done

    # Return if no commercial components selected
    if [ -z "$selected_components_commercial" ]; then
        return
    fi

    echo "  Installing commercial components from $MENDER_COMMERCIAL_DOWNLOAD_URL"

    # Translate Debian "channel" into Mender version
    if [ "$CHANNEL" = "experimental" ]; then
        version="master"
    else
        version="latest"
    fi

    # Download deb packages
    for c in $selected_components_commercial; do
        url="$MENDER_COMMERCIAL_DOWNLOAD_URL$(printf ${COMMERCIAL_COMP_TO_URL_PATH_F[$c]} $version $version)"
        curl -fLsS -H "Authorization: Bearer $JWT_TOKEN" -O "$url" ||
                (echo ERROR: Cannot get $c from $url; exit 1)
    done

    # Install all of them at once and fallback to install missing dependencies
    local deb_packages_glob=$(echo $selected_components_commercial | sed -e 's/ /*.deb /g; s/$/*.deb/')
    dpkg --install $deb_packages_glob || apt-get -f -y install

    # Check individually each package
    for c in $selected_components_commercial; do
        dpkg --status $c || (echo ERROR: $c could not be installed; exit 1)
    done

    echo "  Success!"
}

do_setup_mender() {
    # Return if mender-client was not installed
    if [[ ! "$SELECTED_COMPONENTS" == *"mender-client"* ]]; then
        return
    fi

    # Return if no setup options were passed and no DEMO
    if [ -z "$MENDER_SETUP_ARGS" -a "$DEMO" -eq 0 ]; then
        return
    fi

    local mender_setup_args="$MENDER_SETUP_ARGS"
    if [ "$DEMO" -eq 1 ]; then
        mender_setup_args="$mender_setup_args --demo-intervals"
    fi

    echo "  Setting up mender with options: $mender_setup_args"
    mender setup $mender_setup_args
    pidof systemd && systemctl restart mender-client
    echo "  Success!"
}

do_setup_addons() {
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
}

banner
init "$@"
print_components
get_deps
add_repo
do_install_open
do_install_commercial
do_setup_mender
do_setup_addons

exit 0
