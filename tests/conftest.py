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

from distutils.version import LooseVersion

import pytest

from mender_test_containers.container_props import *
from mender_test_containers.conftest import *

TEST_CONTAINER_LIST = [MenderTestRaspbian]


@pytest.fixture(scope="session", params=TEST_CONTAINER_LIST)
def setup_test_container_props(request):
    return request.param


def pytest_addoption(parser):
    parser.addoption("--mender-client-version", required=False)
    parser.addoption("--mender-client-deb-version", required=False)
    parser.addoption("--mender-connect-version", required=False)
    parser.addoption("--mender-connect-deb-version", required=False)
    parser.addoption("--mender-configure-version", required=False)
    parser.addoption("--mender-configure-deb-version", required=False)
    parser.addoption("--mender-artifact-version", required=False)
    parser.addoption("--mender-artifact-deb-version", required=False)
    parser.addoption("--mender-app-update-module-version", required=False)
    parser.addoption("--mender-app-update-module-deb-version", required=False)
    parser.addoption("--mender-gateway-version", required=False)
    parser.addoption("--mender-gateway-deb-version", required=False)
    parser.addoption("--mender-monitor-version", required=False)
    parser.addoption("--mender-monitor-deb-version", required=False)
    parser.addoption(
        "--commercial-tests", action="store_true", required=False, default=False
    )


@pytest.fixture(scope="session")
def mender_version(request):
    return request.config.getoption("--mender-client-version")


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
def mender_gateway_version(request):
    return request.config.getoption("--mender-gateway-version")


@pytest.fixture(scope="session")
def mender_monitor_version(request):
    return request.config.getoption("--mender-monitor-version")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--commercial-tests"):
        for item in items:
            if "commercial" not in item.keywords:
                item.add_marker(pytest.mark.skip(reason="not a commercial test"))
    else:
        skip_commercial = pytest.mark.skip(
            reason="run with the commercial-tests option"
        )
        for item in items:
            if "commercial" in item.keywords:
                item.add_marker(skip_commercial)


@pytest.fixture(scope="session")
def mender_dist_packages_versions(request):
    """Returns dict matching package names and current versions"""

    return {
        "mender-client": request.config.getoption("--mender-client-deb-version"),
        "mender-connect": request.config.getoption("--mender-connect-deb-version"),
        "mender-configure": request.config.getoption("--mender-configure-deb-version"),
        "mender-artifact": request.config.getoption("--mender-artifact-deb-version"),
        "mender-app-update-module": request.config.getoption(
            "--mender-app-update-module-deb-version"
        ),
        "mender-gateway": request.config.getoption("--mender-gateway-deb-version"),
        "mender-monitor": request.config.getoption("--mender-monitor-deb-version"),
    }


# Required for mender_test_containers/conftest.py::setup_mender_configured, which
# is only used on addons packages tests. Use version 3.2.1 (mender-connect dependency)
@pytest.fixture(scope="session")
def mender_deb_version(request):
    return "3.2.1"


def min_version_impl(request, marker, min_version):
    version_mark = request.node.get_closest_marker(marker)
    if version_mark is not None:
        try:
            if LooseVersion(version_mark.args[0]) > LooseVersion(min_version):
                pytest.skip("Test requires %s %s" % (marker, version_mark.args[0]))
        except TypeError:
            # Type error indicates that 'version' is likely a string (master).
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
