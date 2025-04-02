#!/usr/bin/python3
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

import packaging.version

import pytest

from mender_test_containers.container_props import *
from mender_test_containers.conftest import *

TEST_CONTAINER_LIST = [MenderTestRaspbian]


TEST_PACKAGES = [
    "mender-client",
    "mender-connect",
    "mender-configure",
    "mender-artifact",
    "mender-app-update-module",
    "mender-setup",
    "mender-snapshot",
    "mender-flash",
    "mender-gateway",
    "mender-monitor",
]


@pytest.fixture(scope="session", params=TEST_CONTAINER_LIST)
def setup_test_container_props(request):
    return request.param


def pytest_addoption(parser):
    for pkg in TEST_PACKAGES:
        parser.addoption(
            f"--{pkg}-version", required=False, help=f"Leave empty to skip {pkg} tests"
        )
        parser.addoption(f"--{pkg}-deb-version", required=False)

    parser.addoption(
        "--commercial-tests", action="store_true", required=False, default=False
    )


@pytest.fixture(scope="session")
def mender_version(request):
    return request.config.getoption("--mender-client-version")


@pytest.fixture(scope="session")
def mender_client_package_name(mender_version):
    if mender_version.startswith("3."):
        return "mender-client"
    return "mender-client4"


@pytest.fixture(scope="session")
def mender_connect_version(request):
    return request.config.getoption("--mender-connect-version")


@pytest.fixture(scope="session")
def mender_configure_version(request):
    return request.config.getoption("--mender-configure-version")


@pytest.fixture(scope="session")
def mender_artifact_version(request):
    return request.config.getoption("--mender-artifact-version")


@pytest.fixture(scope="session")
def mender_app_update_module_version(request):
    return request.config.getoption("--mender-app-update-module-version")


@pytest.fixture(scope="session")
def mender_setup_version(request):
    return request.config.getoption("--mender-setup-version")


@pytest.fixture(scope="session")
def mender_snapshot_version(request):
    return request.config.getoption("--mender-snapshot-version")


@pytest.fixture(scope="session")
def mender_flash_version(request):
    return request.config.getoption("--mender-flash-version")


@pytest.fixture(scope="session")
def mender_gateway_version(request):
    return request.config.getoption("--mender-gateway-version")


@pytest.fixture(scope="session")
def mender_monitor_version(request):
    return request.config.getoption("--mender-monitor-version")


def did_not_boot(err, *args):
    return issubclass(err[0], TestContainerDidNotboot)


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--commercial-tests"):
        skip_commercial = pytest.mark.skip(
            reason="run with the commercial-tests option"
        )
        for item in items:
            if "commercial" in item.keywords:
                item.add_marker(skip_commercial)

    flaky_marker = pytest.mark.flaky(max_runs=3, rerun_filter=did_not_boot)
    for item in items:
        item.add_marker(flaky_marker)

    for pkg in TEST_PACKAGES:
        if not config.getoption(f"--{pkg}-version"):
            for item in items:
                if pkg.replace("-", "_") in item.keywords:
                    item.add_marker(pytest.mark.skip(reason=f"Skip {pkg} tests"))


@pytest.fixture(scope="session")
def mender_dist_packages_versions(request):
    """Returns dict matching package names and current versions"""

    return {
        pkg: request.config.getoption(f"--{pkg}-deb-version") for pkg in TEST_PACKAGES
    } | {"mender-client4": request.config.getoption("--mender-client-deb-version")}


# Required for mender_test_containers/conftest.py::setup_mender_configured, which
# is only used on addons packages tests. Use version 3.2.1 (mender-connect dependency)
@pytest.fixture(scope="session")
def mender_deb_version(request):
    return "3.2.1"


def min_version_impl(request, marker, min_version):
    version_mark = request.node.get_closest_marker(marker)
    if version_mark is not None:
        try:
            if packaging.version.Version(
                version_mark.args[0]
            ) > packaging.version.Version(min_version):
                pytest.skip("Test requires %s %s" % (marker, version_mark.args[0]))
        except packaging.version.InvalidVersion:
            # Indicates that 'version' is likely a string (master).
            pass


@pytest.fixture(autouse=True)
def min_mender_client_version(request):
    min_version_impl(
        request,
        "min_mender_client_version",
        request.config.getoption("--mender-client-version"),
    )


@pytest.fixture(autouse=True)
def min_mender_connect_version(request):
    min_version_impl(
        request,
        "min_mender_connect_version",
        request.config.getoption("--mender-connect-version"),
    )


@pytest.fixture(autouse=True)
def min_mender_configure_version(request):
    min_version_impl(
        request,
        "min_mender_configure_version",
        request.config.getoption("--mender-configure-version"),
    )


@pytest.fixture(autouse=True)
def min_mender_artifact_version(request):
    min_version_impl(
        request,
        "min_mender_artifact_version",
        request.config.getoption("--mender-artifact-version"),
    )


@pytest.fixture(autouse=True)
def min_mender_app_update_module_version(request):
    min_version_impl(
        request,
        "min_mender_app_update_module_version",
        request.config.getoption("--mender-app-update-module-version"),
    )


@pytest.fixture(autouse=True)
def min_setup_version(request):
    min_version_impl(
        request,
        "min_setup_version",
        request.config.getoption("--mender-setup-version"),
    )


@pytest.fixture(autouse=True)
def min_snapshot_version(request):
    min_version_impl(
        request,
        "min_snapshot_version",
        request.config.getoption("--mender-snapshot-version"),
    )


@pytest.fixture(autouse=True)
def min_flash_version(request):
    min_version_impl(
        request,
        "min_flash_version",
        request.config.getoption("--mender-flash-version"),
    )


@pytest.fixture(autouse=True)
def min_mender_monitor_version(request):
    min_version_impl(
        request,
        "min_mender_monitor_version",
        request.config.getoption("--mender-monitor-version"),
    )


@pytest.fixture(autouse=True)
def min_mender_gateway_version(request):
    min_version_impl(
        request,
        "min_mender_gateway_version",
        request.config.getoption("--mender-gateway-version"),
    )
