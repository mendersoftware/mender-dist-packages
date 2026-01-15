#!/usr/bin/python3
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

import pytest

from common import DEBIAN_REF_DISTRO
from common import script_server, generic_debian_container
from common import (
    check_installed,
    local_apt_repo_from_built_packages,
    local_apt_repo_from_upstream_packages,
    local_apt_repo_from_test_packages,
)


@pytest.mark.skipif(
    DEBIAN_REF_DISTRO != "bullseye",
    reason="Debian 11 is the only one requiring full cycle of package upgrades",
)
@pytest.mark.usefixtures("script_server")
class TestUpgradeMenderV4:
    def test_upgrade_from_v3_to_v4_to_build(
        self, generic_debian_container,
    ):
        # Install mender-client 3.5.1 (epoch 0:)
        local_apt_repo_from_upstream_packages(
            generic_debian_container,
            [
                f"m/mender-client/mender-client_3.5.1-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"m/mender-connect/mender-connect_2.1.1-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"m/mender-configure/mender-configure_1.1.1-1+debian+{DEBIAN_REF_DISTRO}_all.deb",
            ],
            "/mender_3_5_1",
        )
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client mender-connect mender-configure"
        )

        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

        # Upgrade to mender-client 4.0.0
        local_apt_repo_from_test_packages(
            generic_debian_container,
            [
                f"mender-client_4.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-update_4.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-auth_4.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-flash_1.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-setup_1.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-snapshot_1.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-connect_2.2.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-configure_1.1.2-1+debian+{DEBIAN_REF_DISTRO}_all.deb",
            ],
            "/mender_4_0_0",
        )
        # Note the use of apt instead of apt-get - the latter wouldn't install the new packages
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

        # Upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-update")
        check_installed(generic_debian_container, "mender-auth")
        check_installed(generic_debian_container, "mender-flash")
        check_installed(generic_debian_container, "mender-setup")
        check_installed(generic_debian_container, "mender-snapshot")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_from_v3_to_build(
        self, generic_debian_container,
    ):
        # Install mender-client 3.5.2 (epoch 1:)
        local_apt_repo_from_upstream_packages(
            generic_debian_container,
            [
                f"m/mender-client/mender-client_3.5.2-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"m/mender-connect/mender-connect_2.2.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"m/mender-configure/mender-configure_1.1.1-1+debian+{DEBIAN_REF_DISTRO}_all.deb",
            ],
            "/mender_3_5_2",
        )
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client mender-connect mender-configure"
        )
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

        # Upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")

    def test_upgrade_from_v4_to_build(
        self, generic_debian_container,
    ):
        # Install mender-client 4.0.0
        local_apt_repo_from_test_packages(
            generic_debian_container,
            [
                f"mender-client_4.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-update_4.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-auth_4.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-flash_1.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-setup_1.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-snapshot_1.0.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-connect_2.2.0-1+debian+{DEBIAN_REF_DISTRO}_amd64.deb",
                f"mender-configure_1.1.2-1+debian+{DEBIAN_REF_DISTRO}_all.deb",
            ],
            "/mender_4_0_0",
        )
        generic_debian_container.run(
            "DEBIAN_FRONTEND=noninteractive apt install --assume-yes mender-client mender-connect mender-configure"
        )

        # Upgrade to the freshly built packages
        local_apt_repo_from_built_packages(generic_debian_container)
        generic_debian_container.run("apt --assume-yes upgrade")
        check_installed(generic_debian_container, "mender-client")
        check_installed(generic_debian_container, "mender-connect")
        check_installed(generic_debian_container, "mender-configure")
