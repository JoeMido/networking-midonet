# Copyright 2015 Midokura SARL
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

import collections
import datetime
from oslo_serialization import jsonutils
import sqlalchemy as sa

from neutron.common import exceptions as n_exc
from neutron.db import model_base
from neutron import i18n
from oslo_log import log as logging
import uuid

CONF_ID = '00000000-0000-0000-0000-000000000001'

CREATE = "CREATE"
DELETE = "DELETE"
UPDATE = "UPDATE"
FLUSH = "FLUSH"

NETWORK = "NETWORK"
SUBNET = "SUBNET"
ROUTER = "ROUTER"
PORT = "PORT"
FLOATING_IP = "FLOATINGIP"
SECURITY_GROUP = "SECURITYGROUP"
SECURITY_GROUP_RULE = "SECURITYGROUPRULE"
POOL = "POOL"
VIP = "VIP"
HEALTH_MONITOR = "HEALTHMONITOR"
MEMBER = "MEMBER"
PORT_BINDING = "PORTBINDING"
CONFIG = "CONFIG"
AGENT_MEMBERSHIP = "AGENTMEMBERSHIP"


OP_IMPORT = 'IMPORT'
OP_FLUSH = 'FLUSH'

LOG = logging.getLogger(__name__)
_LI = i18n._LI


class Task(model_base.BASEV2):
    __tablename__ = 'midonet_tasks'

    id = sa.Column(sa.Integer(), primary_key=True)
    type = sa.Column(sa.String(length=36))
    tenant_id = sa.Column(sa.String(255))
    data_type = sa.Column(sa.String(length=36))
    data = sa.Column(sa.Text(length=2 ** 24))
    resource_id = sa.Column(sa.String(36))
    transaction_id = sa.Column(sa.String(40))
    created_at = sa.Column(sa.DateTime(), default=datetime.datetime.utcnow)


def create_task(context, type, task_id=None, data_type=None,
                resource_id=None, data=None):

    with context.session.begin(subtransactions=True):
        db = Task(id=task_id,
                  type=type,
                  tenant_id=context.tenant,
                  data_type=data_type,
                  data=None if data is None else jsonutils.dumps(data),
                  resource_id=resource_id,
                  transaction_id=context.request_id)
        context.session.add(db)


def create_config_task(session, data):
    data['id'] = CONF_ID
    with session.begin(subtransactions=True):
        db = Task(type=CREATE,
                  tenant_id=None,
                  data_type=CONFIG,
                  data=jsonutils.dumps(data),
                  resource_id=data['id'],
                  transaction_id=str(uuid.uuid4()))
        session.add(db)


class MidonetClusterException(n_exc.NeutronException):
    message = _("Midonet Cluster Error: %(msg)s")


class MidoClusterMixin(object):

    def _flush(self, context):
        try:
            context.session.execute('LOCK TABLES midonet_tasks WRITE')
            with context.session.begin(subtransactions=True):
                context.session.execute('TRUNCATE TABLE midonet_tasks')
                create_task(context, FLUSH, task_id=1)
        finally:
            context.session.execute('UNLOCK TABLES')

    def _import(self, context):
        try:
            # lock the entire database so we can take a snapshot of the
            # data we need.
            context.session.execute('FLUSH TABLES WITH READ LOCK')

            database = collections.OrderedDict({
                NETWORK: self.get_networks(context),
                SUBNET: self.get_subnets(context),
                PORT: self.get_ports(context),
                ROUTER: self.get_routers(context),
                FLOATING_IP: self.get_floatingips(context),
                SECURITY_GROUP: self.get_security_groups(context),
                SECURITY_GROUP_RULE: self.get_security_group_rules(context),
                POOL: self.get_pools(context),
                VIP: self.get_vips(context),
                HEALTH_MONITOR: self.get_health_monitors(context),
                MEMBER: self.get_members(context)})

            # record how much items we have processed so far. We compare
            # this to another count after we lock midonet_tasks to make
            # sure nothing snuck in between the locks.
            task_count = context.session.query(Task).count()
        finally:
            context.session.execute('UNLOCK TABLES')
        try:
            context.session.execute('LOCK TABLES midonet_tasks WRITE')
            with context.session.begin(subtransactions=True):
                if task_count != context.session.query(Task).count():
                    error_msg = ("The database has been updated while the "
                                 "rebuild operation is in progress")
                    raise MidonetClusterException(msg=error_msg)

                for key in database:
                    for item in database[key]:
                        create_task(context, CREATE, data_type=key,
                                    resource_id=item['id'], data=item)
        finally:
            context.session.execute('UNLOCK TABLES')

    def create_cluster(self, context, cluster):
        LOG.info(_LI('MidoClusterMixin.create_cluster called: cluster=%r'),
                 cluster)

        op = cluster['cluster']['op']
        if op == OP_FLUSH:
            self._flush(context)
        elif op == OP_IMPORT:
            self._import(context)

        # Neutron assumes that any create_* call returns a dictionary. Even
        # though we do nothing with 'cluster', we still return it back to
        # neutron to satisfy this assumption.
        LOG.info(_LI("MidoClusterMixin.create_cluster exiting: cluster=%r"),
                 cluster)
        return cluster
