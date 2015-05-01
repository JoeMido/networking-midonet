# Copyright (C) 2015 Midokura SARL.
# All Rights Reserved.
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

import contextlib
import mock

from midonet.neutron.common import config  # noqa
from midonet.neutron.db import agent_membership_db  # noqa
from midonet.neutron.db import data_state_db  # noqa
from midonet.neutron.db import data_version_db as dv_db
from midonet.neutron.db import port_binding_db as pb_db  # noqa
from midonet.neutron.db import task_db  # noqa
from neutron_lbaas.db.loadbalancer import loadbalancer_db  # noqa

from midonet.neutron.common import exceptions as exc
from neutron.db import api as db_api
from neutron.db import l3_db
from neutron.db import models_v2
from neutron.extensions import portbindings
from neutron.tests.unit import _test_extension_portbindings as test_bindings
from neutron.tests.unit.db import test_db_base_plugin_v2 as test_plugin
from neutron.tests.unit.extensions import test_extra_dhcp_opt as test_dhcpopts
from neutron.tests.unit.extensions import test_l3 as test_l3_plugin
from neutron.tests.unit.extensions import test_l3_ext_gw_mode as test_gw_mode
from neutron.tests.unit.extensions import test_securitygroup as test_sg
from oslo_config import cfg
from sqlalchemy.orm import sessionmaker
import sys
sys.modules["midonetclient"] = mock.Mock()
sys.modules["midonetclient.neutron"] = mock.Mock()
sys.modules["midonetclient.neutron.client"] = mock.Mock()
sys.modules["midonetclient.topology"] = mock.Mock()
sys.modules["midonetclient.topology.hosts"] = mock.Mock()


MIDONET_PLUGIN_NAME = 'midonet.neutron.tests.unit.test_midonet_plugin_api.MidonetApiTestPluginV2'


def get_session():
    engine = db_api.get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

from midonet.neutron import plugin_api

midonet_opts = [
    cfg.StrOpt('midonet_uri', default='http://localhost:8080/midonet-api',
               help=_('MidoNet API server URI.')),
    cfg.StrOpt('username', default='admin',
               help=_('MidoNet admin username.')),
    cfg.StrOpt('password', default='passw0rd',
               secret=True,
               help=_('MidoNet admin password.')),
    cfg.StrOpt('project_id',
               default='77777777-7777-7777-7777-777777777777',
               help=_('ID of the project that MidoNet admin user '
                      'belongs to.'))
]


cfg.CONF.register_opts(midonet_opts, "MIDONET")


# Derives from `object` (via at least NeutronDbPluginV2), but pylint
# can't see that without having the midonet libraries available.
# pylint: disable=super-on-old-class
class MidonetApiTestPluginV2(plugin_api.MidonetApiMixin):

    vendor_extensions = plugin_api.MidonetApiMixin.supported_extension_aliases
    supported_extension_aliases = ['external-net', 'router', 'security-group',
                                   'agent', 'dhcp_agent_scheduler', 'binding',
                                   'quotas'] + vendor_extensions

    __native_bulk_support = True

    def __init__(self):
        super(MidonetApiTestPluginV2, self).__init__()


class MidonetPluginApiV2TestCase(test_plugin.NeutronDbPluginV2TestCase):

    def setUp(self,
              plugin=MIDONET_PLUGIN_NAME,
              ext_mgr=None,
              service_plugins=None):
        super(MidonetPluginApiV2TestCase, self).setUp(plugin=plugin)

    def tearDown(self):
        super(MidonetPluginApiV2TestCase, self).tearDown()

    @contextlib.contextmanager
    def _updated_network(self):
        with self.network(name="myname") as n:
            args = {'network': {'name': 'myothername'}}
            try:
                yield self._update('networks', n['network']['id'], args)
            except:
                yield n

    @contextlib.contextmanager
    def _updated_fip(self):
        with self.subnet() as sub:
            with self.floatingip_no_assoc(sub) as fp:
                with self.port(sub) as p:
                    addr = p['port']['fixed_ips'][0]['ip_address']
                    pid = p['port']['id']
                    args = {'floatingip': {'port_id': pid,
                                           'fixed_ip_address': addr}}
                    try:
                        yield self._update('floatingips',
                                           fp['floatingip']['id'],
                                           args)
                    except:
                        yield fp


class TestMidonetNetworksV2(MidonetPluginApiV2TestCase,
                            test_plugin.TestNetworksV2):

    def test_network_status_result(self):
        with self._updated_network() as net:
            self.assertEqual(net['network']['status'], 'ACTIVE')

    def test_network_status_db(self):
        with self._updated_network() as net:
            session = get_session()
            net_db = session.query(models_v2.Network).filter_by(
                id=net['network']['id']).first()
            self.assertEqual(net_db['status'], 'ACTIVE')

    def test_network_status_db_error(self):
        self.plugin.api_cli.update_network.side_effect = exc.MidonetApiException(msg="FAKE")
        with self._updated_network() as net:
            session = get_session()
            net_db = session.query(models_v2.Network).filter_by(
                id=net['network']['id']).first()
            self.assertEqual(net_db['status'], 'DOWN')
        self.plugin.api_cli.update_network.side_effect = None



class TestMidonetL3NatTestCase(MidonetPluginApiV2TestCase,
                               test_l3_plugin.L3NatDBIntTestCase):

    def test_floatingip_with_invalid_create_port(self):
        self._test_floatingip_with_invalid_create_port(MIDONET_PLUGIN_NAME)

    def test_floating_ip_status_result(self):
        with self._updated_fip() as fip:
            self.assertEqual(fip['floatingip']['status'], 'ACTIVE')

    def test_floating_ip_status_db(self):
        with self._updated_fip() as fip:
            session = get_session()
            fid = fip['floatingip']['id']
            fp_db = session.query(l3_db.FloatingIP).filter_by(id=fid).first()
            self.assertEqual(fp_db['status'], 'ACTIVE')

    def test_floating_ip_status_db_error(self):
        self.plugin.api_cli.update_floating_ip.side_effect = exc.MidonetApiException(msg="FAKE")
        with self._updated_fip() as fip:
            session = get_session()
            fp_db = session.query(l3_db.FloatingIP).filter_by(
                id=fip['floatingip']['id']).first()
            self.assertEqual(fp_db['status'], 'DOWN')
        self.plugin.api_cli.update_floating_ip.side_effect = None

    @contextlib.contextmanager
    def _updated_router(self):
        with self.router(name="myrouter") as r:
            args = {'router': {'name': 'myothername'}}
            try:
                yield self._update('routers', r['router']['id'], args)
            except:
                yield r

    def test_router_status_result(self):
        with self._updated_router() as r:
            self.assertEqual(r['router']['status'], 'ACTIVE')

    def test_router_status_db(self):
        with self._updated_router() as r:
            session = get_session()
            r_db = session.query(l3_db.Router).filter_by(
                id=r['router']['id']).first()
            self.assertEqual(r_db['status'], 'ACTIVE')

    def test_router_status_db_error(self):
        self.plugin.api_cli.update_router.side_effect = exc.MidonetApiException(msg="FAKE")
        try:
            with self._updated_router() as r:
                session = get_session()
                r_db = session.query(l3_db.Router).filter_by(
                    id=r['router']['id']).first()
                self.assertEqual(r_db['status'], 'DOWN')
        finally:
            self.plugin.api_cli.update_router.side_effect = None


class TestMidonetSecurityGroup(MidonetPluginApiV2TestCase,
                               test_sg.TestSecurityGroups):

    pass


class TestMidonetSubnetsV2(MidonetPluginApiV2TestCase,
                           test_plugin.TestSubnetsV2):

    pass


class TestMidonetPortsV2(MidonetPluginApiV2TestCase,
                         test_plugin.TestPortsV2):

    def setUp(self):
        super(TestMidonetPortsV2, self).setUp()

    def test_vif_port_binding(self):
        with self.port(name='myname') as port:
            self.assertEqual('midonet', port['port']['binding:vif_type'])
            self.assertTrue(port['port']['admin_state_up'])

    @contextlib.contextmanager
    def _updated_port(self):
        with self.port(name="myport") as p:
            args = {'port': {'name': 'myothername'}}
            try:
                yield self._update('ports', p['port']['id'], args)
            except:
                yield p

    def test_port_status_result(self):
        with self._updated_port() as p:
            self.assertEqual(p['port']['status'], 'ACTIVE')

    def test_port_status_db(self):
        with self._updated_port() as p:
            session = get_session()
            port_db = session.query(models_v2.Port).filter_by(
                id=p['port']['id']).first()
            self.assertEqual(port_db['status'], 'ACTIVE')

    def test_port_status_db_error(self):
        self.plugin.api_cli.update_port.side_effect = exc.MidonetApiException(msg="FAKE")
        with self._updated_port() as p:
            session = get_session()
            port_db = session.query(models_v2.Port).filter_by(
                id=p['port']['id']).first()
            self.assertEqual(port_db['status'], 'DOWN')
        self.plugin.api_cli.update_port.side_effect = None


class TestMidonetPluginPortBinding(MidonetPluginApiV2TestCase,
                                   test_bindings.PortBindingsTestCase):

    VIF_TYPE = portbindings.VIF_TYPE_MIDONET
    HAS_PORT_FILTER = True


class TestExtGwMode(MidonetPluginApiV2TestCase,
                    test_gw_mode.ExtGwModeIntTestCase):

    pass


class TestExtraDHCPOpts(MidonetPluginApiV2TestCase,
                        test_dhcpopts.TestExtraDhcpOpt):
    pass
