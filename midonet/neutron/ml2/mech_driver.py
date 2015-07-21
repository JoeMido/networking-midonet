# Copyright (C) 2015 Midokura SARL.
# All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from neutron.common import constants

from oslo_log import helpers as log_helpers
from oslo_log import log as logging
from midonet.neutron.common import config  # noqa
from midonetclient import client
from midonet.neutron.ml2 import sg_callback

from neutron.plugins.ml2 import driver_api as api
from oslo_config import cfg
from neutron.extensions import portbindings

LOG = logging.getLogger(__name__)


class MidonetMechanismDriver(api.MechanismDriver):

    """ML2 Mechanism Driver for Midonet."""

    @log_helpers.log_method_call

    def __init__(self):
        self.vif_type = portbindings.VIF_TYPE_MIDONET
        self.supported_vnic_types = [portbindings.VNIC_TYPE]
        self.vif_details = {portbindings.CAP_PORT_FILTER: True}

    def initialize(self):
        conf = cfg.CONF.MIDONET
        self.api_cli = client.MidonetClient(conf.midonet_uri, conf.username,
                                            conf.password,
                                            project_id=conf.project_id)
        self.sec_handler = sg_callback.MidonetSecurityGroupsHandler(self.api_cli)

    @classmethod
    def filter_create_security_group_attributes(cls, sg, context):
        """Filter out security-group attributes not required for a create."""
        pass

    @classmethod
    def filter_create_security_group_rule_attributes(cls, sg_rule, context):
        """Filter out sg-rule attributes not required for a create."""
        pass

    @classmethod
    def filter_update_security_group_attributes(cls, sg, context):
        """Filter out security-group attributes for an update operation."""
        pass

    @classmethod
    def filter_update_security_group_rule_attributes(cls, sg_rule, context):
        """Filter out sg-rule attributes for an update operation."""
        pass

    @log_helpers.log_method_call
    def create_network_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def create_network_postcommit(self, context):
        network = context.current
        self.api_cli.create_network(network)

    @log_helpers.log_method_call
    def update_network_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def update_network_postcommit(self, context):
        network = context.current
        network_id = context.current['id']
        self.api_cli.update_network(network_id, network)

    @log_helpers.log_method_call
    def delete_network_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def delete_network_postcommit(self, context):
        network_id = context.current['id']
        self.api_cli.delete_network(network_id)

    @log_helpers.log_method_call
    def create_subnet_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def create_subnet_postcommit(self, context):
        subnet = context.current
        self.api_cli.create_subnet(subnet)

    @log_helpers.log_method_call
    def update_subnet_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def update_subnet_postcommit(self, context):
        subnet = context.current
        subnet_id = context.current['id']
        self.api_cli.update_subnet(subnet_id, subnet)

    @log_helpers.log_method_call
    def delete_subnet_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def delete_subnet_postcommit(self, context):
        subnet_id = context.current['id']
        self.api_cli.delete_subnet(subnet_id)

    @log_helpers.log_method_call
    def create_port_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def create_port_postcommit(self, context):
        port = context.current
        self.api_cli.create_port(port)

    @log_helpers.log_method_call
    def update_port_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def update_port_postcommit(self, context):
        port = context.current
        port_id = context.current['id']
        self.api_cli.update_port(port_id, port)

    @log_helpers.log_method_call
    def delete_port_precommit(self, context):
        pass

    @log_helpers.log_method_call
    def delete_port_postcommit(self, context):
        port_id = context.current['id']
        self.api_cli.delete_port(port_id)

    @log_helpers.log_method_call
    def bind_port(self, context):
        for segment in context.segments_to_bind:
            context.set_binding(segment[api.ID],
                                self.vif_type,
                                self.vif_details,
                                constants.PORT_STATUS_ACTIVE)

