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

# URL prefix from where to download commercial compoments, formatted by auth (hosted|on-prem)
# TODO: Update after MC-5726
MENDER_COMMERCIAL_DOWNLOAD_URL_F="https://download.mender.io/content/%s/"

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
    # Keep first block under 80 characters
    echo "usage: install-mender.sh [-h] [-c channel] [--demo] [--commercial] [--auth auth]"
    echo "                         [--jwt-token token] [--username user] [component...]"
    echo "  -h, --help          print this help"
    echo "  -c CHANNEL          channel: stable(default)|experimental"
    echo "  --demo              use defaults appropriate for demo"
    echo "  --commercial        install commercial components, requires --auth and either --jwt-token or --username"
    echo "  --auth AUTH         auth method: hosted|on-prem, used when installing commercial components. hosted requires"
    echo "                      either --jwt-token or --username, on-prem requires --username"
    echo "  --jwt-token TOKEN   Hosted Mender JWT token, to download commercial components"
    echo "  --username USER     Mender Enterprise or Hosted Mender username, to download commercial components. Password will be prompted"
    echo "  <component>         list of components to install"
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
    while [ $# -gt 0 ]
    do
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
                SELECTED_COMPONENTS="$SELECTED_COMPONENTS $DEMO_COMPONENTS"
                ;;
            --commercial)
                if [[ ! "$args_copy" == *"--auth"* ]]; then
                    echo "ERROR: commercial requires --auth argument."
                    echo "Aborting."
                    exit 1
                fi
                SELECTED_COMPONENTS="$SELECTED_COMPONENTS $COMMERCIAL_COMPONENTS"
                ;;
            --auth)
                if [ -n "$2" ]; then
                    COMMERCIAL_AUTH="$2"
                    shift
                else
                    echo "ERROR: auth requires a non-empty option argument."
                    echo "Aborting."
                    exit 1
                fi
                if [[ "$COMMERCIAL_AUTH" == "hosted" ]]; then
                    if [[ ! "$args_copy" == *"--jwt-token"* && ! "$args_copy" == *"--username"* ]]; then
                        echo "ERROR: auth hosted requires either --jwt-token or --username arguments."
                        echo "Aborting."
                        exit 1
                    fi
                elif [[ "$COMMERCIAL_AUTH" == "on-prem" ]]; then
                    if [[ ! "$args_copy" == *"--username"* ]]; then
                        echo "ERROR: auth on-prem requires --username argument."
                        echo "Aborting."
                        exit 1
                    fi
                else
                    echo "ERROR: Unrecognized auth argument \"$COMMERCIAL_AUTH\". Valid values are: hosted|on-prem"
                    echo "Aborting."
                    exit 1
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
            --username)
                if [ -n "$2" ]; then
                    USERNAME="$2"
                    shift
                else
                    echo "ERROR: username requires a non-empty option argument."
                    echo "Aborting."
                    exit 1
                fi
                ;;
            *)
                if is_known_component "$1"; then
                    if echo "$COMMERCIAL_COMPONENTS" | egrep -q "(^| )$1( |\$)"; then
                        if [[ ! "$args_copy" == *"--auth"* ]]; then
                            echo "ERROR: commercial package $1 requires --auth argument."
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

    url_base=$(printf $MENDER_COMMERCIAL_DOWNLOAD_URL_F $COMMERCIAL_AUTH)
    echo "  Installing commercial components from $url_base"

    # Translate Debian "channel" into Mender version
    if [ "$CHANNEL" = "experimental" ]; then
        version="master"
    else
        version="latest"
    fi

    # Download deb packages
    for c in $selected_components_commercial; do
        url="$url_base$(printf ${COMMERCIAL_COMP_TO_URL_PATH_F[$c]} $version $version)"
        if [[ -n "$JWT_TOKEN" ]]; then
            auth_args="-H \"Authorization: Bearer $JWT_TOKEN\""
        else
            auth_args="-u $USERNAME"
        fi
        eval curl -fLsS "$auth_args" -O "$url" ||
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

banner
init "$@"
print_components
get_deps
add_repo
do_install_open
do_install_commercial

exit 0
