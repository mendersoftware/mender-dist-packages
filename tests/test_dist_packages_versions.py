#!/usr/bin/python3
# Copyright 2022 Northern.tech AS
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

import re

from conftest import get_debian_distro_version


def verify_package_version(version, deb_version):
    distro = "debian"
    # Inherit this from the CI calling the tests
    distro_version = get_debian_distro_version()

    if version == "master":
        # Example package: mender-setup_1.1.0~git20251006.0edfbc5-1+debian+bullseye+builder2084488895
        m = re.match(
            rf"[0-9]+\.[0-9]+\.[0-9]+~git[0-9]+\.([a-z0-9]+)-[1-9][0-9]*\+debian\+{distro_version}\+builder([0-9]+|LOCAL)",
            deb_version,
        )
        assert m is not None, "Cannot match (master) %s" % deb_version
    else:
        m = re.match(rf"{version}-[1-9][0-9]*\+{distro}\+{distro_version}", deb_version)
        assert m is not None, "Cannot match (non master) %s" % deb_version


def test_versions(
    mender_version,
    mender_connect_version,
    mender_configure_version,
    mender_dist_packages_versions,
):
    verify_package_version(
        mender_version, mender_dist_packages_versions["mender-client"]
    )
    verify_package_version(
        mender_connect_version, mender_dist_packages_versions["mender-connect"]
    )
    verify_package_version(
        mender_configure_version, mender_dist_packages_versions["mender-configure"]
    )
