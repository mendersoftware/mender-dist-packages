#!/bin/sh

set -e

CHANNEL="stable"

AVAILABLE_COMPONENTS="mender-client \
mender-configure \
mender-configure-demo \
mender-configure-timezone \
mender-connect"

DEFAULT_COMPONENTS="mender-client \
mender-configure \
mender-connect"

DEMO_COMPONENTS="$AVAILABLE_COMPONENTS"

SELECTED_COMPONENTS="$DEFAULT_COMPONENTS"

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
    echo "usage: install-mender.sh [-h] [-c channel] [component...]"
    echo "  -h             print this help"
    echo "  -c CHANNEL     channel: stable(default)|experimental"
    echo "  --demo         use defaults appropriate for demo"
    echo "  <component>    list of components to install"
    echo ""
    echo "Supported components (x = installed by default):"
    for c in $AVAILABLE_COMPONENTS
    do
        if echo "$DEFAULT_COMPONENTS" | egrep -q "(^| )$c( |\$)"; then
            echo -n " (x) "
        else
            echo -n " (-) "
        fi
        echo "$c"
    done
}

is_known_component() {
    for known in $DEFAULT_COMPONENTS
    do
        if [ "$1" = "$known" ]; then
            return 0
        fi
    done
    return 1
}

parse_args() {
    selected_components=""
    while [ $# -gt 0 ]
    do
        case $1 in
            -h)
                usage
                exit 0
                ;;
            -c)
                if [ -n "$2" ]; then
                    CHANNEL=$2
                    shift
                else
                    echo "ERROR: channel requires a non-empty option argument."
                    echo "Aborting."
                    exit 1
                fi
                ;;
            --demo)
                SELECTED_COMPONENTS="$DEMO_COMPONENTS"
                ;;
            *)
                if is_known_component "$1"; then
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
    for c in $SELECTED_COMPONENTS
    do
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

    if ! grep -F "$repo" /etc/apt/sources.list; then
  echo "adding $repo to /etc/apt/sources.list"
        echo "$repo" >> /etc/apt/sources.list
    fi
}

do_install() {
    apt-get update
    apt-get install -y \
       -o Dpkg::Options::="--force-confdef" \
       -o Dpkg::Options::="--force-confold" \
       $SELECTED_COMPONENTS

    echo "  Success!"
    echo "  Please run \`mender setup\` to configure the client."
    exit 0
}

banner
init "$@"
print_components
get_deps
add_repo
do_install
