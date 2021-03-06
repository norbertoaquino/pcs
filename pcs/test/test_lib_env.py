from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from unittest import TestCase
import logging

from pcs.test.tools.assertions import assert_raise_library_error
from pcs.test.tools.custom_mock import MockLibraryReportProcessor
from pcs.test.tools.misc import get_test_resource as rc
from pcs.test.tools.pcs_mock import mock

from pcs.lib.env import LibraryEnvironment
from pcs.common import report_codes
from pcs.lib import reports
from pcs.lib.corosync.config_facade import ConfigFacade as CorosyncConfigFacade
from pcs.lib.errors import (
    LibraryError,
    ReportItemSeverity as severity,
)

class LibraryEnvironmentTest(TestCase):
    def setUp(self):
        self.mock_logger = mock.MagicMock(logging.Logger)
        self.mock_reporter = MockLibraryReportProcessor()

    def test_logger(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual(self.mock_logger, env.logger)

    def test_report_processor(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual(self.mock_reporter, env.report_processor)

    def test_user_set(self):
        user = "testuser"
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            user_login=user
        )
        self.assertEqual(user, env.user_login)

    def test_user_not_set(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual(None, env.user_login)

    def test_usergroups_set(self):
        groups = ["some", "group"]
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            user_groups=groups
        )
        self.assertEqual(groups, env.user_groups)

    def test_usergroups_not_set(self):
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertEqual([], env.user_groups)

    @mock.patch("pcs.lib.env.is_cman_cluster")
    def test_is_cman_cluster(self, mock_is_cman):
        mock_is_cman.return_value = True
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        self.assertTrue(env.is_cman_cluster)
        self.assertTrue(env.is_cman_cluster)
        self.assertEqual(1, mock_is_cman.call_count)

    @mock.patch("pcs.lib.env.replace_cib_configuration_xml")
    @mock.patch("pcs.lib.env.get_cib_xml")
    def test_cib_set(self, mock_get_cib, mock_push_cib):
        cib_data = "test cib data"
        new_cib_data = "new test cib data"
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            cib_data=cib_data
        )

        self.assertFalse(env.is_cib_live)

        self.assertEqual(cib_data, env.get_cib_xml())
        self.assertEqual(0, mock_get_cib.call_count)

        env.push_cib_xml(new_cib_data)
        self.assertEqual(0, mock_push_cib.call_count)

        self.assertEqual(new_cib_data, env.get_cib_xml())
        self.assertEqual(0, mock_get_cib.call_count)

    @mock.patch("pcs.lib.env.replace_cib_configuration_xml")
    @mock.patch("pcs.lib.env.get_cib_xml")
    def test_cib_not_set(self, mock_get_cib, mock_push_cib):
        cib_data = "test cib data"
        new_cib_data = "new test cib data"
        mock_get_cib.return_value = cib_data
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)

        self.assertTrue(env.is_cib_live)

        self.assertEqual(cib_data, env.get_cib_xml())
        self.assertEqual(1, mock_get_cib.call_count)

        env.push_cib_xml(new_cib_data)
        self.assertEqual(1, mock_push_cib.call_count)

    @mock.patch("pcs.lib.env.check_corosync_offline_on_nodes")
    @mock.patch("pcs.lib.env.reload_corosync_config")
    @mock.patch("pcs.lib.env.distribute_corosync_conf")
    @mock.patch("pcs.lib.env.get_local_corosync_conf")
    def test_corosync_conf_set(
        self, mock_get_corosync, mock_distribute, mock_reload,
        mock_check_offline
    ):
        corosync_data = "totem {\n    version: 2\n}\n"
        new_corosync_data = "totem {\n    version: 3\n}\n"
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            corosync_conf_data=corosync_data
        )

        self.assertFalse(env.is_corosync_conf_live)

        self.assertEqual(corosync_data, env.get_corosync_conf_data())
        self.assertEqual(corosync_data, env.get_corosync_conf().config.export())
        self.assertEqual(0, mock_get_corosync.call_count)

        env.push_corosync_conf(
            CorosyncConfigFacade.from_string(new_corosync_data)
        )
        self.assertEqual(0, mock_distribute.call_count)

        self.assertEqual(new_corosync_data, env.get_corosync_conf_data())
        self.assertEqual(0, mock_get_corosync.call_count)
        mock_check_offline.assert_not_called()
        mock_reload.assert_not_called()

    @mock.patch("pcs.lib.env.reload_corosync_config")
    @mock.patch("pcs.lib.env.distribute_corosync_conf")
    @mock.patch("pcs.lib.env.get_local_corosync_conf")
    @mock.patch.object(
        CorosyncConfigFacade,
        "get_nodes",
        lambda self: "mock node list"
    )
    @mock.patch.object(
        LibraryEnvironment,
        "node_communicator",
        lambda self: "mock node communicator"
    )
    @mock.patch.object(
        LibraryEnvironment,
        "cmd_runner",
        lambda self: "mock cmd runner"
    )
    def test_corosync_conf_not_set(
        self, mock_get_corosync, mock_distribute, mock_reload
    ):
        corosync_data = open(rc("corosync.conf")).read()
        new_corosync_data = corosync_data.replace("version: 2", "version: 3")
        mock_get_corosync.return_value = corosync_data
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)

        self.assertTrue(env.is_corosync_conf_live)

        self.assertEqual(corosync_data, env.get_corosync_conf_data())
        self.assertEqual(corosync_data, env.get_corosync_conf().config.export())
        self.assertEqual(2, mock_get_corosync.call_count)

        env.push_corosync_conf(
            CorosyncConfigFacade.from_string(new_corosync_data)
        )
        mock_distribute.assert_called_once_with(
            "mock node communicator",
            self.mock_reporter,
            "mock node list",
            new_corosync_data,
            False
        )
        mock_reload.assert_called_once_with("mock cmd runner")

    @mock.patch("pcs.lib.env.check_corosync_offline_on_nodes")
    @mock.patch("pcs.lib.env.reload_corosync_config")
    @mock.patch("pcs.lib.env.distribute_corosync_conf")
    @mock.patch("pcs.lib.env.get_local_corosync_conf")
    @mock.patch.object(
        CorosyncConfigFacade,
        "get_nodes",
        lambda self: "mock node list"
    )
    @mock.patch.object(
        LibraryEnvironment,
        "node_communicator",
        lambda self: "mock node communicator"
    )
    def test_corosync_conf_not_set_need_offline_success(
        self, mock_get_corosync, mock_distribute, mock_reload,
        mock_check_offline
    ):
        corosync_data = open(rc("corosync.conf")).read()
        new_corosync_data = corosync_data.replace("version: 2", "version: 3")
        mock_get_corosync.return_value = corosync_data
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)

        self.assertTrue(env.is_corosync_conf_live)

        self.assertEqual(corosync_data, env.get_corosync_conf_data())
        self.assertEqual(corosync_data, env.get_corosync_conf().config.export())
        self.assertEqual(2, mock_get_corosync.call_count)

        conf_facade = CorosyncConfigFacade.from_string(new_corosync_data)
        conf_facade._need_stopped_cluster = True
        env.push_corosync_conf(conf_facade)
        mock_check_offline.assert_called_once_with(
            "mock node communicator",
            self.mock_reporter,
            "mock node list",
            False
        )
        mock_distribute.assert_called_once_with(
            "mock node communicator",
            self.mock_reporter,
            "mock node list",
            new_corosync_data,
            False
        )
        mock_reload.assert_not_called()

    @mock.patch("pcs.lib.env.check_corosync_offline_on_nodes")
    @mock.patch("pcs.lib.env.reload_corosync_config")
    @mock.patch("pcs.lib.env.distribute_corosync_conf")
    @mock.patch("pcs.lib.env.get_local_corosync_conf")
    @mock.patch.object(
        CorosyncConfigFacade,
        "get_nodes",
        lambda self: "mock node list"
    )
    @mock.patch.object(
        LibraryEnvironment,
        "node_communicator",
        lambda self: "mock node communicator"
    )
    def test_corosync_conf_not_set_need_offline_fail(
        self, mock_get_corosync, mock_distribute, mock_reload,
        mock_check_offline
    ):
        corosync_data = open(rc("corosync.conf")).read()
        new_corosync_data = corosync_data.replace("version: 2", "version: 3")
        mock_get_corosync.return_value = corosync_data
        def raiser(dummy_communicator, dummy_reporter, dummy_nodes, dummy_force):
            raise LibraryError(
                reports.corosync_not_running_check_node_error("test node")
            )
        mock_check_offline.side_effect = raiser
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)

        self.assertTrue(env.is_corosync_conf_live)

        self.assertEqual(corosync_data, env.get_corosync_conf_data())
        self.assertEqual(corosync_data, env.get_corosync_conf().config.export())
        self.assertEqual(2, mock_get_corosync.call_count)

        conf_facade = CorosyncConfigFacade.from_string(new_corosync_data)
        conf_facade._need_stopped_cluster = True
        assert_raise_library_error(
            lambda: env.push_corosync_conf(conf_facade),
            (
                severity.ERROR,
                report_codes.COROSYNC_NOT_RUNNING_CHECK_NODE_ERROR,
                {"node": "test node"}
            )
        )
        mock_check_offline.assert_called_once_with(
            "mock node communicator",
            self.mock_reporter,
            "mock node list",
            False
        )
        mock_distribute.assert_not_called()
        mock_reload.assert_not_called()

    @mock.patch("pcs.lib.env.CommandRunner")
    def test_cmd_runner_no_options(self, mock_runner):
        expected_runner = mock.MagicMock()
        mock_runner.return_value = expected_runner
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        runner = env.cmd_runner()
        self.assertEqual(expected_runner, runner)
        mock_runner.assert_called_once_with(
            self.mock_logger,
            self.mock_reporter,
            {}
        )

    @mock.patch("pcs.lib.env.CommandRunner")
    def test_cmd_runner_all_options(self, mock_runner):
        expected_runner = mock.MagicMock()
        mock_runner.return_value = expected_runner
        user = "testuser"
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            user_login=user
        )
        runner = env.cmd_runner()
        self.assertEqual(expected_runner, runner)
        mock_runner.assert_called_once_with(
            self.mock_logger,
            self.mock_reporter,
            {"CIB_user": user}
        )

    @mock.patch("pcs.lib.env.NodeCommunicator")
    def test_node_communicator_no_options(self, mock_comm):
        expected_comm = mock.MagicMock()
        mock_comm.return_value = expected_comm
        env = LibraryEnvironment(self.mock_logger, self.mock_reporter)
        comm = env.node_communicator()
        self.assertEqual(expected_comm, comm)
        mock_comm.assert_called_once_with(
            self.mock_logger,
            self.mock_reporter,
            {},
            None,
            []
        )

    @mock.patch("pcs.lib.env.NodeCommunicator")
    def test_node_communicator_all_options(self, mock_comm):
        expected_comm = mock.MagicMock()
        mock_comm.return_value = expected_comm
        user = "testuser"
        groups = ["some", "group"]
        tokens = {"node": "token"}
        env = LibraryEnvironment(
            self.mock_logger,
            self.mock_reporter,
            user_login=user,
            user_groups=groups,
            auth_tokens_getter=lambda:tokens
        )
        comm = env.node_communicator()
        self.assertEqual(expected_comm, comm)
        mock_comm.assert_called_once_with(
            self.mock_logger,
            self.mock_reporter,
            tokens,
            user,
            groups
        )
