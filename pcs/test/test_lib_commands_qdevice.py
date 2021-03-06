from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from unittest import TestCase
import logging

from pcs.test.tools.pcs_mock import mock
from pcs.test.tools.assertions import (
    assert_raise_library_error,
    assert_report_item_list_equal,
)
from pcs.test.tools.custom_mock import MockLibraryReportProcessor

from pcs.common import report_codes
from pcs.lib.env import LibraryEnvironment
from pcs.lib.errors import LibraryError, ReportItemSeverity as severity
from pcs.lib.external import (
    DisableServiceError,
    EnableServiceError,
    StartServiceError,
    StopServiceError,
    KillServicesError,
)

import pcs.lib.commands.qdevice as lib


class QdeviceTestCase(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()
        self.lib_env = LibraryEnvironment(self.mock_logger, self.mock_reporter)


@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: True)
class QdeviceDisabledOnCmanTest(QdeviceTestCase):
    def base_test(self, func):
        assert_raise_library_error(
            func,
            (
                severity.ERROR,
                report_codes.CMAN_UNSUPPORTED_COMMAND,
                {}
            )
        )

    def test_setup(self):
        self.base_test(
            lambda: lib.qdevice_setup(self.lib_env, "bad model", False, False)
        )

    def test_destroy(self):
        self.base_test(
            lambda: lib.qdevice_destroy(self.lib_env, "bad model")
        )

    def test_enable(self):
        self.base_test(
            lambda: lib.qdevice_enable(self.lib_env, "bad model")
        )

    def test_disable(self):
        self.base_test(
            lambda: lib.qdevice_disable(self.lib_env, "bad model")
        )

    def test_start(self):
        self.base_test(
            lambda: lib.qdevice_start(self.lib_env, "bad model")
        )

    def test_stop(self):
        self.base_test(
            lambda: lib.qdevice_stop(self.lib_env, "bad model")
        )

    def test_kill(self):
        self.base_test(
            lambda: lib.qdevice_kill(self.lib_env, "bad model")
        )


@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
class QdeviceBadModelTest(QdeviceTestCase):
    def base_test(self, func):
        assert_raise_library_error(
            func,
            (
                severity.ERROR,
                report_codes.INVALID_OPTION_VALUE,
                {
                    "option_name": "model",
                    "option_value": "bad model",
                    "allowed_values": ["net"],
                }
            )
        )

    def test_setup(self):
        self.base_test(
            lambda: lib.qdevice_setup(self.lib_env, "bad model", False, False)
        )

    def test_destroy(self):
        self.base_test(
            lambda: lib.qdevice_destroy(self.lib_env, "bad model")
        )

    def test_enable(self):
        self.base_test(
            lambda: lib.qdevice_enable(self.lib_env, "bad model")
        )

    def test_disable(self):
        self.base_test(
            lambda: lib.qdevice_disable(self.lib_env, "bad model")
        )

    def test_start(self):
        self.base_test(
            lambda: lib.qdevice_start(self.lib_env, "bad model")
        )

    def test_stop(self):
        self.base_test(
            lambda: lib.qdevice_stop(self.lib_env, "bad model")
        )

    def test_kill(self):
        self.base_test(
            lambda: lib.qdevice_kill(self.lib_env, "bad model")
        )


@mock.patch("pcs.lib.external.start_service")
@mock.patch("pcs.lib.external.enable_service")
@mock.patch("pcs.lib.commands.qdevice.qdevice_net.qdevice_setup")
@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class QdeviceNetSetupTest(QdeviceTestCase):
    def test_success(self, mock_net_setup, mock_net_enable, mock_net_start):
        lib.qdevice_setup(self.lib_env, "net", False, False)

        mock_net_setup.assert_called_once_with("mock_runner")
        mock_net_enable.assert_not_called()
        mock_net_start.assert_not_called()
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.QDEVICE_INITIALIZATION_SUCCESS,
                    {
                        "model": "net",
                    }
                )
            ]
        )

    def test_start_enable_success(
        self, mock_net_setup, mock_net_enable, mock_net_start
    ):
        lib.qdevice_setup(self.lib_env, "net", True, True)

        mock_net_setup.assert_called_once_with("mock_runner")
        mock_net_enable.assert_called_once_with("mock_runner", "corosync-qnetd")
        mock_net_start.assert_called_once_with("mock_runner", "corosync-qnetd")
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.QDEVICE_INITIALIZATION_SUCCESS,
                    {
                        "model": "net",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_ENABLE_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_START_STARTED,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_START_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )

    def test_init_failed(
        self, mock_net_setup, mock_net_enable, mock_net_start
    ):
        mock_net_setup.side_effect = LibraryError("mock_report_item")
        self.assertRaises(
            LibraryError,
            lambda: lib.qdevice_setup(self.lib_env, "net", False, False)
        )
        mock_net_setup.assert_called_once_with("mock_runner")
        mock_net_enable.assert_not_called()
        mock_net_start.assert_not_called()
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            []
        )

    def test_enable_failed(
        self, mock_net_setup, mock_net_enable, mock_net_start
    ):
        mock_net_enable.side_effect = EnableServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_setup(self.lib_env, "net", True, True),
            (
                severity.ERROR,
                report_codes.SERVICE_ENABLE_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )

        mock_net_setup.assert_called_once_with("mock_runner")
        mock_net_enable.assert_called_once_with("mock_runner", "corosync-qnetd")
        mock_net_start.assert_not_called()
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.QDEVICE_INITIALIZATION_SUCCESS,
                    {
                        "model": "net",
                    }
                )
            ]
        )

    def test_start_failed(
        self, mock_net_setup, mock_net_enable, mock_net_start
    ):
        mock_net_start.side_effect = StartServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_setup(self.lib_env, "net", True, True),
            (
                severity.ERROR,
                report_codes.SERVICE_START_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )

        mock_net_setup.assert_called_once_with("mock_runner")
        mock_net_enable.assert_called_once_with("mock_runner", "corosync-qnetd")
        mock_net_start.assert_called_once_with("mock_runner", "corosync-qnetd")
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.QDEVICE_INITIALIZATION_SUCCESS,
                    {
                        "model": "net",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_ENABLE_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_START_STARTED,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )


@mock.patch("pcs.lib.external.stop_service")
@mock.patch("pcs.lib.external.disable_service")
@mock.patch("pcs.lib.commands.qdevice.qdevice_net.qdevice_destroy")
@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class QdeviceNetDestroyTest(QdeviceTestCase):
    def test_success(self, mock_net_destroy, mock_net_disable, mock_net_stop):
        lib.qdevice_destroy(self.lib_env, "net")

        mock_net_stop.assert_called_once_with("mock_runner", "corosync-qnetd")
        mock_net_disable.assert_called_once_with(
            "mock_runner",
            "corosync-qnetd"
        )
        mock_net_destroy.assert_called_once_with()
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_STARTED,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_DISABLE_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.QDEVICE_DESTROY_SUCCESS,
                    {
                        "model": "net",
                    }
                )
            ]
        )

    def test_stop_failed(
        self, mock_net_destroy, mock_net_disable, mock_net_stop
    ):
        mock_net_stop.side_effect = StopServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_destroy(self.lib_env, "net"),
            (
                severity.ERROR,
                report_codes.SERVICE_STOP_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )

        mock_net_stop.assert_called_once_with("mock_runner", "corosync-qnetd")
        mock_net_disable.assert_not_called()
        mock_net_destroy.assert_not_called()
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_STARTED,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )

    def test_disable_failed(
        self, mock_net_destroy, mock_net_disable, mock_net_stop
    ):
        mock_net_disable.side_effect = DisableServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_destroy(self.lib_env, "net"),
            (
                severity.ERROR,
                report_codes.SERVICE_DISABLE_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )

        mock_net_stop.assert_called_once_with("mock_runner", "corosync-qnetd")
        mock_net_disable.assert_called_once_with(
            "mock_runner",
            "corosync-qnetd"
        )
        mock_net_destroy.assert_not_called()
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_STARTED,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )

    def test_destroy_failed(
        self, mock_net_destroy, mock_net_disable, mock_net_stop
    ):
        mock_net_destroy.side_effect = LibraryError("mock_report_item")

        self.assertRaises(
            LibraryError,
            lambda: lib.qdevice_destroy(self.lib_env, "net")
        )

        mock_net_stop.assert_called_once_with("mock_runner", "corosync-qnetd")
        mock_net_disable.assert_called_once_with(
            "mock_runner",
            "corosync-qnetd"
        )
        mock_net_destroy.assert_called_once_with()
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_STARTED,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_DISABLE_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )


@mock.patch("pcs.lib.external.enable_service")
@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class QdeviceNetEnableTest(QdeviceTestCase):
    def test_success(self, mock_net_enable):
        lib.qdevice_enable(self.lib_env, "net")
        mock_net_enable.assert_called_once_with("mock_runner", "corosync-qnetd")
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_ENABLE_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )

    def test_failed(self, mock_net_enable):
        mock_net_enable.side_effect = EnableServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_enable(self.lib_env, "net"),
            (
                severity.ERROR,
                report_codes.SERVICE_ENABLE_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )
        mock_net_enable.assert_called_once_with("mock_runner", "corosync-qnetd")


@mock.patch("pcs.lib.external.disable_service")
@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class QdeviceNetDisableTest(QdeviceTestCase):
    def test_success(self, mock_net_disable):
        lib.qdevice_disable(self.lib_env, "net")
        mock_net_disable.assert_called_once_with(
            "mock_runner",
            "corosync-qnetd"
        )
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_DISABLE_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )

    def test_failed(self, mock_net_disable):
        mock_net_disable.side_effect = DisableServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_disable(self.lib_env, "net"),
            (
                severity.ERROR,
                report_codes.SERVICE_DISABLE_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )
        mock_net_disable.assert_called_once_with(
            "mock_runner",
            "corosync-qnetd"
        )


@mock.patch("pcs.lib.external.start_service")
@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class QdeviceNetStartTest(QdeviceTestCase):
    def test_success(self, mock_net_start):
        lib.qdevice_start(self.lib_env, "net")
        mock_net_start.assert_called_once_with("mock_runner", "corosync-qnetd")
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_START_STARTED,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_START_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )

    def test_failed(self, mock_net_start):
        mock_net_start.side_effect = StartServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_start(self.lib_env, "net"),
            (
                severity.ERROR,
                report_codes.SERVICE_START_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )
        mock_net_start.assert_called_once_with("mock_runner", "corosync-qnetd")
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_START_STARTED,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )


@mock.patch("pcs.lib.external.stop_service")
@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class QdeviceNetStopTest(QdeviceTestCase):
    def test_success(self, mock_net_stop):
        lib.qdevice_stop(self.lib_env, "net")
        mock_net_stop.assert_called_once_with("mock_runner", "corosync-qnetd")
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_STARTED,
                    {
                        "service": "quorum device",
                    }
                ),
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_SUCCESS,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )

    def test_failed(self, mock_net_stop):
        mock_net_stop.side_effect = StopServiceError(
            "test service",
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_stop(self.lib_env, "net"),
            (
                severity.ERROR,
                report_codes.SERVICE_STOP_ERROR,
                {
                    "service": "test service",
                    "reason": "test error",
                }
            )
        )
        mock_net_stop.assert_called_once_with("mock_runner", "corosync-qnetd")
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_STOP_STARTED,
                    {
                        "service": "quorum device",
                    }
                )
            ]
        )


@mock.patch("pcs.lib.external.kill_services")
@mock.patch("pcs.lib.env.is_cman_cluster", lambda self: False)
@mock.patch.object(
    LibraryEnvironment,
    "cmd_runner",
    lambda self: "mock_runner"
)
class QdeviceNetKillTest(QdeviceTestCase):
    def test_success(self, mock_net_kill):
        lib.qdevice_kill(self.lib_env, "net")
        mock_net_kill.assert_called_once_with(
            "mock_runner",
            ["corosync-qnetd"]
        )
        assert_report_item_list_equal(
            self.mock_reporter.report_item_list,
            [
                (
                    severity.INFO,
                    report_codes.SERVICE_KILL_SUCCESS,
                    {
                        "services": ["quorum device"],
                    }
                )
            ]
        )

    def test_failed(self, mock_net_kill):
        mock_net_kill.side_effect = KillServicesError(
            ["test service"],
            "test error"
        )

        assert_raise_library_error(
            lambda: lib.qdevice_kill(self.lib_env, "net"),
            (
                severity.ERROR,
                report_codes.SERVICE_KILL_ERROR,
                {
                    "services": ["test service"],
                    "reason": "test error",
                }
            )
        )
        mock_net_kill.assert_called_once_with(
            "mock_runner",
            ["corosync-qnetd"]
        )
