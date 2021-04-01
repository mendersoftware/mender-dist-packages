#!/usr/bin/python3
# Copyright 2021 Northern.tech AS
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

import pytest


def verify_package_version(version, deb_version):
    # For master, expect something like: "0.0~git20191022.dade697-1+b279517265"
    master_version_re = re.compile(
        r"[0-9]+\.[0-9]+\.[0-9]+~git[0-9]+\.([a-z0-9]+)-1\+b([0-9]+|LOCAL)"
    )

    if version == "master":
        m = master_version_re.match(deb_version)
        assert m is not None, "Cannot match %s" % deb_version
    else:
        assert deb_version == version + "-1"


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
