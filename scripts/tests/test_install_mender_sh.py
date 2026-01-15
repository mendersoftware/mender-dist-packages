#!/usr/bin/python3
# Copyright 2024 Northern.tech AS
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

import pytest

from common import DEBIAN_REF_DISTRO, SCRIPT_SERVER_ADDR, SCRIPT_SERVER_PORT
from common import script_server, generic_debian_container
from common import check_installed, local_apt_repo_from_built_packages


@pytest.mark.usefixtures("script_server")
class TestInstallMenderScript:
    @pytest.mark.parametrize("channel", ["", "stable", "experimental"])
    def test_default(
        self, generic_debian_container, channel,
    ):
        """Default, no arg install installs mender-client and add-ons (stable)."""

        client_package = "mender-client4"
        # Only Debian 11 in "stable" mode is still using "mender-client"
        if DEBIAN_REF_DISTRO == "bullseye" and (channel == "stable" or channel == ""):
            client_package = "mender-client"

        if channel != "":
            channel = "-c " + channel

        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- {channel}"
        )

        for pkg in [client_package, "mender-configure", "mender-connect"]:
            check_installed(generic_debian_container, pkg)

        # piggyback misc cmdline tests to save an extra container run
        # help
        res = generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- -h"
        )
        assert "usage:" in res.stdout.decode()

        # invalid arg/module
        res = generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- unknown",
            warn=True,
        )
        assert res.returncode == 1
        assert "Unsupported argument: `unknown`" in res.stdout.decode()

    def test_default_setup_mender(
        self, generic_debian_container,
    ):
        """Pass mender setup args, should be propagated"""

        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- -- --demo --device-type cool-device --hosted-mender --tenant-token my-secret-token"
        )

        result = generic_debian_container.run("cat /etc/mender/mender.conf")
        assert '"ServerURL": "https://hosted.mender.io"' in result.stdout.decode()

        result = generic_debian_container.run("cat /var/lib/mender/device_type")
        assert result.stdout.decode().strip() == "device_type=cool-device"

        result = generic_debian_container.run("cat /etc/mender/mender-connect.conf")
        assert '"User": "nobody"' in result.stdout.decode()

    def test_default_setup_addons(
        self, generic_debian_container,
    ):
        """Setup for add-ons (passing --demo)"""

        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- --demo"
        )

        result = generic_debian_container.run("cat /etc/mender/mender-connect.conf")
        assert '"User": "root"' in result.stdout.decode()

    def test_client(
        self, generic_debian_container,
    ):
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-client"
        )

        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect", installed=False)
        check_installed(generic_debian_container, "mender-configure", installed=False)

        res = generic_debian_container.run("dpkg --status mender-connect", warn=True)
        assert res.returncode == 1

    def test_connect(
        self, generic_debian_container,
    ):
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-connect"
        )

        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure", installed=False)

    def test_configure(
        self, generic_debian_container,
    ):
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-configure"
        )

        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-connect", installed=False)
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_mender_v3_series(
        self, generic_debian_container,
    ):
        # Install latest stable software (client v3)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s"
        )

        # Now upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")

        # Only mender-client should be upgraded
        # We are using stable branch so only Debian Bullseye will use "mender-client,
        # everything else will have "mender-client4"
        if DEBIAN_REF_DISTRO == "bullseye":
            check_installed(generic_debian_container, "mender-client")
            check_installed(generic_debian_container, "mender-update", installed=False)
            check_installed(generic_debian_container, "mender-auth", installed=False)
            check_installed(generic_debian_container, "mender-flash", installed=False)
            check_installed(generic_debian_container, "mender-setup", installed=False)
            check_installed(
                generic_debian_container, "mender-snapshot", installed=False
            )
        else:
            # Debian 12 / 13 will pull the dependencies
            check_installed(generic_debian_container, "mender-client4")
            check_installed(generic_debian_container, "mender-update")
            check_installed(generic_debian_container, "mender-auth")
            check_installed(generic_debian_container, "mender-flash")
            check_installed(generic_debian_container, "mender-setup")
            check_installed(generic_debian_container, "mender-snapshot")

        # The addons should not be removed
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_mender_v4_series_meta_package_with_addons(
        self, generic_debian_container,
    ):
        # Install default stable software (legacy client v3 + addons)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s"
        )

        # Now install freshly built mender-client4
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-update mender-client4"
        )

        # Only Debian Bullseye stable is using "mender-client" and it will be removed
        # with the "Status: deinstall ok config-files" result
        # On Debian Bookworm / Trixi it will not be installed at all
        if DEBIAN_REF_DISTRO == "bullseye":
            check_installed(generic_debian_container, "mender-client", installed=False)
        check_installed(generic_debian_container, "mender-client4")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")
        # The addons should not be removed
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_mender_v4_series_meta_package_only_client(
        self, generic_debian_container,
    ):
        # Install only the legacy client v3)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s -- mender-client"
        )

        # Now install freshly built mender-client4
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client4"
        )

        # mender-client should be removed and mender-client4 + all packages should be installed
        check_installed(generic_debian_container, "mender-client", installed=False)
        check_installed(generic_debian_container, "mender-client4")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")

    def test_upgrade_mender_v4_series_explicit_auth_update(
        self, generic_debian_container,
    ):
        # Install default stable software (legacy client v3 + addons)
        generic_debian_container.run(
            f"curl http://{SCRIPT_SERVER_ADDR}:{SCRIPT_SERVER_PORT}/install-mender.sh | bash -s"
        )

        # Now install freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-auth mender-update"
        )

        # Only Debian Bullseye stable is still using mender-client and will have it removed
        if DEBIAN_REF_DISTRO == "bullseye":
            check_installed(generic_debian_container, "mender-client", installed=False)
            check_installed(generic_debian_container, "mender-client4", installed=False)
        else:
            # On Debian Bookworm / Trixie mender-client4 will not be affected
            check_installed(generic_debian_container, "mender-client4")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        # The addons should not be removed
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")
