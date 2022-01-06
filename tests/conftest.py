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

import pytest

from mender_test_containers.container_props import *
from mender_test_containers.conftest import *

TEST_CONTAINER_LIST = [MenderTestRaspbian]


@pytest.fixture(scope="session", params=TEST_CONTAINER_LIST)
def setup_test_container_props(request):
    return request.param


def pytest_addoption(parser):
    parser.addoption("--mender-client-version", required=True)
    parser.addoption("--mender-client-deb-version", required=True)
    parser.addoption("--mender-connect-version", required=True)
    parser.addoption("--mender-connect-deb-version", required=True)
    parser.addoption("--mender-configure-version", required=True)
    parser.addoption("--mender-configure-deb-version", required=True)
    parser.addoption("--mender-gateway-version", required=False, default="none")
    parser.addoption("--mender-gateway-deb-version", required=False, default="none")
    parser.addoption("--mender-monitor-version", required=False, default="none")
    parser.addoption("--mender-monitor-deb-version", required=False, default="none")
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
        "mender-gateway": request.config.getoption("--mender-gateway-deb-version"),
        "mender-monitor": request.config.getoption("--mender-monitor-deb-version"),
    }


# Required for mender_test_containers/conftest.py::setup_mender_configured, which
# is only used on addons packages tests. Use version 2.5.0 (dependency)
@pytest.fixture(scope="session")
def mender_deb_version(request):
    return "2.5.0"
