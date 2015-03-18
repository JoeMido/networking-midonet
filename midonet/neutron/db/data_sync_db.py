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

from midonet.neutron.common import exceptions as mexc
import midonet.neutron.db.agent_membership_db as am_db
import midonet.neutron.db.data_state_db as ds_db
import midonet.neutron.db.data_version_db as dv_db
import midonet.neutron.db.port_binding_db as pb_db
from midonet.neutron.db import task_db
from neutron.db import l3_db
from neutron.db import models_v2
from neutron.db import securitygroups_db as sg_db
from neutron_lbaas.db.loadbalancer import loadbalancer_db as lb_db
import signal
import sys


class TaskTableAccess(Exception):
    pass


models = [(task_db.NETWORK, models_v2.Network),
          (task_db.SUBNET, models_v2.Subnet),
          (task_db.PORT, models_v2.Port),
          (task_db.ROUTER, l3_db.Router),
          (task_db.FLOATING_IP, l3_db.FloatingIP),
          (task_db.SECURITY_GROUP, sg_db.SecurityGroup),
          (task_db.SECURITY_GROUP_RULE, sg_db.SecurityGroupRule),
          (task_db.POOL, lb_db.Pool),
          (task_db.VIP, lb_db.Vip),
          (task_db.HEALTH_MONITOR, lb_db.HealthMonitor),
          (task_db.MEMBER, lb_db.Member),
          (task_db.AGENT_MEMBERSHIP, am_db.AgentMembership),
          (task_db.PORT_BINDING, pb_db.PortBinding)]


def validate_sync_operation(session):
    sync_status, task_status = dv_db.get_data_version_states(session)
    if sync_status is not None and sync_status is not "COMPLETED":
        raise TaskTableAccess("sync is NOT completed")
    if task_status is not None and task_status is not "COMPLETED":
        raise TaskTableAccess("sync_tasks is NOT completed")
    if not ds_db.is_task_table_readonly(session):
        raise mexc.DataStateReadOnly()
    last_task_id = task_db.get_most_recent_task_id(session)
    lp_task_id = ds_db.get_last_processed_task_id(session)
    if lp_task_id is not None and lp_task_id is not last_task_id:
        raise TaskTableAccess("The cluster is not finished processing tasks")


def sync_data(session, mido_config):
    validate_sync_operation(session)

    dv_db.create_data_version(session)

    def abort(signal, frame):
        dv_db.abort_last_version(session)
        sys.exit(0)

    signal.signal(signal.SIGINT, abort)

    try:
        task_db.reset_task_table(session)

        task_db.new_task(session, task_db.CREATE, "operator", "sync",
                         task_id=1, data_type=task_db.DATA_VERSION_SYNC)

        task_db.create_config_task(session, dict(mido_config))

        for key, model in models:
            for item in session.query(model).all():
                task_db.new_task(session, task_db.CREATE, "operator", "sync",
                                 data_type=key, resource_id=item['id'],
                                 data=item)

        with session.begin(subtransactions=True):
            task_db.new_task(session, task_db.CREATE, "operator",
                             "sync", data_type=task_db.DATA_VERSION_ACTIVATE)
            dv_db.complete_last_version(session)
            version_id = dv_db.get_last_version_id(session)
            ds_db.update_active_version(session, version_id)
        session.commit()
    except Exception:
        dv_db.error_last_version(session)
        raise
