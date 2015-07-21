# Copyright (C) 2015 Midokura SARL.
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

from oslo_log import helpers as log_helpers
from oslo_log import log as logging

from neutron.db import l3_gwmode_db
from neutron.i18n import _LE, _LI
from neutron.plugins.common import constants
from neutron.api import extensions as neutron_extensions
from midonet.neutron import extensions
from neutron.extensions import portbindings
from oslo_utils import importutils
from neutron.common import topics
from neutron.api.rpc.handlers import dhcp_rpc
from neutron.db import agents_db
from neutron.api.rpc.handlers import metadata_rpc
from oslo_config import cfg
from neutron.common import rpc as n_rpc
from neutron.db import db_base_plugin_v2
from oslo_utils import excutils
from neutron.common import constants as n_const
from neutron.db import agentschedulers_db

LOG = logging.getLogger(__name__)


class MidonetL3ServicePlugin(l3_gwmode_db.L3_NAT_db_mixin,
                             agentschedulers_db.DhcpAgentSchedulerDbMixin,
                             db_base_plugin_v2.NeutronDbPluginV2):

    """Implements L3 Router service plugin for Midonet.

    """

    supported_extension_aliases = ["router", "ext-gw-mode"]

    def __init__(self):
        super(MidonetL3ServicePlugin, self).__init__()

        # Instantiate MidoNet API client
        self._load_client()

        neutron_extensions.append_api_extensions_path(extensions.__path__)
        self.setup_rpc()

        self.network_scheduler = importutils.import_object(
            cfg.CONF.network_scheduler_driver
        )

    def _load_client(self):
        try:
            self.client = importutils.import_object(cfg.CONF.MIDONET.client)
            LOG.debug("Loaded midonet client '%(client)s'",
                      {'client': self.client})
        except ImportError:
            with excutils.save_and_reraise_exception():
                LOG.exception(_LE("Error loading midonet client '%(client)s'"),
                              {'client': self.client})

    def setup_rpc(self):
        # RPC support
        self.topic = topics.PLUGIN
        self.conn = n_rpc.create_connection(new=True)
        self.endpoints = [dhcp_rpc.DhcpRpcCallback(),
                          agents_db.AgentExtRpcCallback(),
                          metadata_rpc.MetadataRpcCallback()]
        self.conn.create_consumer(self.topic, self.endpoints,
                                  fanout=False)
        # Consume from all consumers in a thread
        self.conn.consume_in_threads()

    def get_plugin_type(self):
        return constants.L3_ROUTER_NAT

    def get_plugin_description(self):
        """Returns string description of the plugin."""
        return ("Midonet L3 Router Service Plugin")

    @log_helpers.log_method_call
    def create_router(self, context, router):
        LOG.debug("MidonetMixin.create_router called: router=%(router)s",
                  {"router": router})

        with context.session.begin(subtransactions=True):
            r = super(MidonetL3ServicePlugin, self).create_router(context, router)
            self.client.create_router_precommit(context, r)

        try:
            self.client.create_router_postcommit(r)
        except Exception as ex:
            with excutils.save_and_reraise_exception():
                LOG.error(_LE("Failed to create a router %(r_id)s in Midonet:"
                              "%(err)s"), {"r_id": r["id"], "err": ex})
                try:
                    self.delete_router(context, r['id'])
                except Exception:
                    LOG.exception(_LE("Failed to delete a router %s"), r["id"])

        LOG.debug("MidonetMixin.create_router exiting: router=%(router)s.",
                  {"router": r})
        return r

    @log_helpers.log_method_call
    def update_router(self, context, id, router):
        LOG.debug("MidonetMixin.update_router called: id=%(id)s "
                  "router=%(router)r", {"id": id, "router": router})

        with context.session.begin(subtransactions=True):
            r = super(MidonetL3ServicePlugin, self).update_router(context, id, router)
            self.client.update_router_precommit(context, id, r)

        self.client.update_router_postcommit(id, r)

        LOG.debug("MidonetMixin.update_router exiting: router=%r", r)
        return r

    @log_helpers.log_method_call
    def delete_router(self, context, id):
        LOG.debug("MidonetMixin.delete_router called: id=%s", id)

        with context.session.begin(subtransactions=True):
            super(MidonetL3ServicePlugin, self).delete_router(context, id)
            self.client.delete_router_precommit(context, id)

        self.client.delete_router_postcommit(id)

        LOG.debug("MidonetMixin.delete_router exiting: id=%s", id)

    @log_helpers.log_method_call
    def add_router_interface(self, context, router_id, interface_info):
        LOG.debug("MidonetMixin.add_router_interface called: "
                  "router_id=%(router_id)s, interface_info=%(interface_info)r",
                  {'router_id': router_id, 'interface_info': interface_info})

        with context.session.begin(subtransactions=True):
            info = super(MidonetL3ServicePlugin, self).add_router_interface(
                context, router_id, interface_info)
            self.client.add_router_interface_precommit(context, router_id,
                                                       info)

        try:
            self.client.add_router_interface_postcommit(router_id, info)
        except Exception as ex:
            LOG.error(_LE("Failed to create MidoNet resources to add router "
                          "interface. info=%(info)s, router_id=%(router_id)s, "
                          "error=%(err)r"),
                      {"info": info, "router_id": router_id, "err": ex})
            with excutils.save_and_reraise_exception():
                self.remove_router_interface(context, router_id, info)

        LOG.debug("MidonetMixin.add_router_interface exiting: info=%r", info)
        return info

    @log_helpers.log_method_call
    def remove_router_interface(self, context, router_id, interface_info):
        LOG.debug("MidonetMixin.remove_router_interface called: "
                  "router_id=%(router_id)s, interface_info=%(interface_info)r",
                  {'router_id': router_id, 'interface_info': interface_info})

        with context.session.begin(subtransactions=True):
            info = super(MidonetL3ServicePlugin, self).remove_router_interface(
                context, router_id, interface_info)
            self.client.remove_router_interface_precommit(context, router_id,
                                                          info)

        self.client.remove_router_interface_postcommit(router_id, info)

        LOG.debug("MidonetMixin.remove_router_interface exiting: info=%r",
                  info)
        return info

    @log_helpers.log_method_call
    def create_floatingip(self, context, floatingip):
        LOG.debug("MidonetMixin.create_floatingip called: ip=%r", floatingip)

        with context.session.begin(subtransactions=True):
            fip = super(MidonetL3ServicePlugin, self).create_floatingip(context,
                                                              floatingip)
            self.client.create_floatingip_precommit(context, fip)

        try:
            self.client.create_floatingip_postcommit(fip)
        except Exception as ex:
            with excutils.save_and_reraise_exception():
                LOG.error(_LE("Failed to create floating ip %(fip)s: %(err)s"),
                          {"fip": fip, "err": ex})
                try:
                    self.delete_floatingip(context, fip['id'])
                except Exception:
                    LOG.exception(_LE("Failed to delete a floating ip %s"),
                                  fip['id'])

        LOG.debug("MidonetMixin.create_floatingip exiting: fip=%r", fip)
        return fip

    @log_helpers.log_method_call
    def delete_floatingip(self, context, id):
        LOG.debug("MidonetMixin.delete_floatingip called: id=%s", id)

        with context.session.begin(subtransactions=True):
            super(MidonetL3ServicePlugin, self).delete_floatingip(context, id)
            self.client.delete_floatingip_precommit(context, id)

        self.client.delete_floatingip_postcommit(id)

        LOG.debug("MidonetMixin.delete_floatingip exiting: id=%r", id)

    @log_helpers.log_method_call
    def update_floatingip(self, context, id, floatingip):
        LOG.debug("MidonetMixin.update_floatingip called: id=%(id)s "
                  "floatingip=%(floatingip)s ",
                  {'id': id, 'floatingip': floatingip})

        with context.session.begin(subtransactions=True):
            fip = super(MidonetL3ServicePlugin, self).update_floatingip(context, id,
                                                              floatingip)
            self.client.update_floatingip_precommit(context, id, fip)

            # Update status based on association
            if fip.get('port_id') is None:
                fip['status'] = n_const.FLOATINGIP_STATUS_DOWN
            else:
                fip['status'] = n_const.FLOATINGIP_STATUS_ACTIVE
            self.update_floatingip_status(context, id, fip['status'])

        self.client.update_floatingip_postcommit(id, fip)

        LOG.debug("MidonetMixin.update_floating_ip exiting: fip=%s", fip)
        return fip