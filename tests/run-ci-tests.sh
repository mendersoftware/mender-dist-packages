#!/bin/bash
# Copyright 2026 Northern.tech AS
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

cd "$(dirname "$0")"

pkg_flags=""

# Only adds the pytest --foo-version / --foo-deb-version pair when the build job
# for that package produced a deb-version artifact (i.e. the package was
# actually built).
maybe_add_pkg_flag() {
  local pkg="$1" version="$2" filename="$3"
  local path="../output/opensource/${OS_FAMILY}-${OS_VERSION_NAME}-amd64/$filename"
  if [ -f "$path" ]; then
    pkg_flags="$pkg_flags --$pkg-version $version --$pkg-deb-version $(cat "$path")"
  else
    echo "Skipping $pkg in pytest args: $path not present"
  fi
}

maybe_add_pkg_flag mender-client "$MENDER_VERSION" mender-client4-deb-version
maybe_add_pkg_flag mender-connect "$MENDER_CONNECT_VERSION" mender-connect-deb-version
maybe_add_pkg_flag mender-configure "$MENDER_CONFIGURE_VERSION" mender-configure-deb-version
maybe_add_pkg_flag mender-setup "$MENDER_SETUP_VERSION" mender-setup-deb-version
maybe_add_pkg_flag mender-snapshot "$MENDER_SNAPSHOT_VERSION" mender-snapshot-deb-version
maybe_add_pkg_flag mender-flash "$MENDER_FLASH_VERSION" mender-flash-deb-version
maybe_add_pkg_flag mender-container-modules "$MENDER_CONTAINER_MODULES_VERSION" mender-container-modules-deb-version
maybe_add_pkg_flag mender-client-version-inventory-script "$MENDER_CLIENT_VERSION_INVENTORY_SCRIPT_VERSION" mender-client-version-inventory-script-deb-version

COMMERCIAL_OUTPUT="../output/commercial/${OS_FAMILY}-${OS_VERSION_NAME}-amd64"
commercial_tests_flags=""
if [ -f "$COMMERCIAL_OUTPUT/mender-gateway-deb-version" ] &&
   [ -f "$COMMERCIAL_OUTPUT/mender-monitor-deb-version" ]; then
  commercial_tests_flags="--commercial-tests"
  commercial_tests_flags="$commercial_tests_flags --mender-gateway-version $MENDER_GATEWAY_VERSION"
  commercial_tests_flags="$commercial_tests_flags --mender-gateway-deb-version $(cat $COMMERCIAL_OUTPUT/mender-gateway-deb-version)"
  commercial_tests_flags="$commercial_tests_flags --mender-monitor-version $MENDER_MONITOR_VERSION"
  commercial_tests_flags="$commercial_tests_flags --mender-monitor-deb-version $(cat $COMMERCIAL_OUTPUT/mender-monitor-deb-version)"
  commercial_tests_flags="$commercial_tests_flags --mender-orchestrator-version $MENDER_ORCHESTRATOR_VERSION"
  commercial_tests_flags="$commercial_tests_flags --mender-orchestrator-deb-version $(cat $COMMERCIAL_OUTPUT/mender-orchestrator-deb-version)"
  # NOTE: Although mender-orchestrator-support is built with no closed source secrets, it cannot be tested without mender-orchestrator so it belongs to "commercial tests"
  commercial_tests_flags="$commercial_tests_flags --mender-orchestrator-support-version $MENDER_ORCHESTRATOR_SUPPORT_VERSION"
  commercial_tests_flags="$commercial_tests_flags --mender-orchestrator-support-deb-version $(cat $COMMERCIAL_OUTPUT/mender-orchestrator-support-deb-version)"
fi

# Fail loudly if no packages were built at all, otherwise pytest would silently
# skip every test and the test job would falsely report green.
if [ -z "${pkg_flags}${commercial_tests_flags}" ]; then
  echo "ERROR: no packages produced *-deb-version artifacts; refusing to run pytest with empty arguments" >&2
  exit 1
fi

exec python3 -m pytest -v \
  ${pkg_flags} \
  ${commercial_tests_flags} \
  --junit-xml results.xml
