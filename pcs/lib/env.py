from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from lxml import etree

from pcs.lib import reports
from pcs.lib.external import (
    is_cman_cluster,
    CommandRunner,
    NodeCommunicator,
)
from pcs.lib.corosync.config_facade import ConfigFacade as CorosyncConfigFacade
from pcs.lib.corosync.live import (
    get_local_corosync_conf,
    reload_config as reload_corosync_config,
)
from pcs.lib.nodes_task import (
    distribute_corosync_conf,
    check_corosync_offline_on_nodes,
)
from pcs.lib.pacemaker import (
    get_cib,
    get_cib_xml,
    replace_cib_configuration_xml,
)


class LibraryEnvironment(object):
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        logger,
        report_processor,
        user_login=None,
        user_groups=None,
        cib_data=None,
        corosync_conf_data=None,
        auth_tokens_getter=None,
    ):
        self._logger = logger
        self._report_processor = report_processor
        self._user_login = user_login
        self._user_groups = [] if user_groups is None else user_groups
        self._cib_data = cib_data
        self._corosync_conf_data = corosync_conf_data
        self._is_cman_cluster = None
        # TODO tokens probably should not be inserted from outside, but we're
        # postponing dealing with them, because it's not that easy to move
        # related code currently - it's in pcsd
        self._auth_tokens_getter = auth_tokens_getter
        self._auth_tokens = None

    @property
    def logger(self):
        return self._logger

    @property
    def report_processor(self):
        return self._report_processor

    @property
    def user_login(self):
        return self._user_login

    @property
    def user_groups(self):
        return self._user_groups

    @property
    def is_cman_cluster(self):
        if self._is_cman_cluster is None:
            self._is_cman_cluster = is_cman_cluster(self.cmd_runner())
        return self._is_cman_cluster

    def get_cib_xml(self):
        if self.is_cib_live:
            return get_cib_xml(self.cmd_runner())
        else:
            return self._cib_data

    def get_cib(self):
        return get_cib(self.get_cib_xml())

    def push_cib_xml(self, cib_data):
        if self.is_cib_live:
            replace_cib_configuration_xml(self.cmd_runner(), cib_data)
        else:
            self._cib_data = cib_data

    def push_cib(self, cib):
        #etree returns bytes: b'xml'
        #python 3 removed .encode() from bytes
        #run(...) calls subprocess.Popen.communicate which calls encode...
        #so here is bytes to str conversion
        self.push_cib_xml(etree.tostring(cib).decode())

    @property
    def is_cib_live(self):
        return self._cib_data is None

    def get_corosync_conf_data(self):
        if self._corosync_conf_data is None:
            return get_local_corosync_conf()
        else:
            return self._corosync_conf_data

    def get_corosync_conf(self):
        return CorosyncConfigFacade.from_string(self.get_corosync_conf_data())

    def push_corosync_conf(
        self, corosync_conf_facade, skip_offline_nodes=False
    ):
        corosync_conf_data = corosync_conf_facade.config.export()
        if self.is_corosync_conf_live:
            node_list = corosync_conf_facade.get_nodes()
            if corosync_conf_facade.need_stopped_cluster:
                check_corosync_offline_on_nodes(
                    self.node_communicator(),
                    self.report_processor,
                    node_list,
                    skip_offline_nodes
                )
            distribute_corosync_conf(
                self.node_communicator(),
                self.report_processor,
                node_list,
                corosync_conf_data,
                skip_offline_nodes
            )
            if not corosync_conf_facade.need_stopped_cluster:
                reload_corosync_config(self.cmd_runner())
                self.report_processor.process(
                    reports.corosync_config_reloaded()
                )
        else:
            self._corosync_conf_data = corosync_conf_data

    @property
    def is_corosync_conf_live(self):
        return self._corosync_conf_data is None

    def cmd_runner(self):
        runner_env = dict()
        if self.user_login:
            runner_env["CIB_user"] = self.user_login
        return CommandRunner(self.logger, self.report_processor, runner_env)

    def node_communicator(self):
        return NodeCommunicator(
            self.logger,
            self.report_processor,
            self.__get_auth_tokens(),
            self.user_login,
            self.user_groups
        )

    def __get_auth_tokens(self):
        if self._auth_tokens is None:
            if self._auth_tokens_getter:
                self._auth_tokens = self._auth_tokens_getter()
            else:
                self._auth_tokens = {}
        return self._auth_tokens
